#Requires -Version 5.1
<#
.SYNOPSIS
  Upload songdata.db to a GitHub Release via the REST API.

.NOTES
  Windows PowerShell 5.1 と PowerShell 7+ の差分（このスクリプトで触れる範囲）:
  - Invoke-RestMethod の失敗時、5.1 は多くの場合 InnerException として System.Net.WebException を返す。
    7+ は Microsoft.PowerShell.Commands.HttpResponseException など、型が異なることがある。
  - そのため HTTP ステータス取得は Get-ErrorHttpStatusCode で InnerException を辿る（StrictMode 下で
    $_.Exception.Response を直接読まない）。
  - 文字列の -replace で末尾の $ を使うときは、二重引用符内ではなく単引用符のパターンを使う
    （5.1 で `$"` が誤展開される問題の回避）。ドキュメント: docs/github-releases-songdata.md

.DESCRIPTION
  Intended to run from any folder: copy this .ps1, the .bat, and secrets next to your songdata.db.
  Tag defaults to songdata-YYYY-MM-DD if omitted.

  Authentication and target repository are read only from
  upload-songdata-github-release.secrets.txt in the same folder as this script
  (edit the file shipped under scripts/ in the repo; placeholders must be replaced).

.PARAMETER Tag
  Release tag. If empty: songdata-<today yyyy-MM-dd>. CI downloads songdata.db from the repo's latest GitHub Release.

.PARAMETER SongdataPath
  File to upload. Default: songdata.db next to this script, else repository root songdata.db (when this .ps1 lives under scripts/).

.PARAMETER AssetName
  Asset name on GitHub. Default: songdata.db

.PARAMETER TargetCommitish
  When creating a release for a new remote tag: branch or SHA. If empty, -DefaultBranch is used.

.PARAMETER DefaultBranch
  Used as target_commitish when creating a release if -TargetCommitish is empty. Default: main.
#>
param(
    [Parameter(Mandatory = $false, Position = 0)]
    [string] $Tag = "",

    [Parameter(Mandatory = $false)]
    [string] $SongdataPath = "",

    [Parameter(Mandatory = $false)]
    [string] $AssetName = "songdata.db",

    [Parameter(Mandatory = $false)]
    [string] $TargetCommitish = "",

    [Parameter(Mandatory = $false)]
    [string] $DefaultBranch = "main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$secretsTxt = Join-Path $PSScriptRoot "upload-songdata-github-release.secrets.txt"

function Unwrap-QuotedToken {
    param([string] $Text)
    $s = $Text.Trim()
    if ($s.Length -ge 2) {
        $fc = $s[0]
        $lc = $s[$s.Length - 1]
        if (($fc -eq '"' -and $lc -eq '"') -or ($fc -eq "'" -and $lc -eq "'")) {
            $s = $s.Substring(1, $s.Length - 2).Trim()
        }
    }
    return $s
}

function Normalize-PatLine {
    param([string] $Line)
    $s = $Line.Trim().TrimStart([char]0xFEFF)
    if ($s -match '^(?:GITHUB_TOKEN|GH_TOKEN)\s*=\s*(.+)$') {
        $s = $matches[1].Trim()
    }
    return (Unwrap-QuotedToken -Text $s)
}

function Normalize-RepoLine {
    param([string] $Line)
    $s = $Line.Trim().TrimStart([char]0xFEFF)
    if ($s -match '^(?:GITHUB_REPOSITORY|REPO)\s*=\s*(.+)$') {
        $s = $matches[1].Trim()
    }
    return (Unwrap-QuotedToken -Text $s)
}

function Read-UploadSecretsTxt {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw (@"
Missing secrets file:
  $Path

Use the repository file scripts/upload-songdata-github-release.secrets.txt
(copy it next to this .ps1 if you run outside the repo), then edit line 1 = PAT
and line 2 = owner/repo (UTF-8). No rename is required.
"@).Trim()
    }
    $enc = New-Object System.Text.UTF8Encoding $false
    $rawLines = [System.IO.File]::ReadAllLines($Path, $enc)
    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($line in $rawLines) {
        $t = $line.Trim()
        if (-not $t) { continue }
        if ($t.StartsWith("#")) { continue }
        [void]$lines.Add($t)
    }
    $pat = ""
    $repo = ""
    if ($lines.Count -ge 1) {
        $pat = Normalize-PatLine -Line $lines[0]
    }
    if ($lines.Count -ge 2) {
        $repo = Normalize-RepoLine -Line $lines[1]
    }
    if (-not $pat) {
        throw "Line 1 (Personal Access Token) is missing or empty in: $Path"
    }
    if (-not $repo) {
        throw "Line 2 (owner/repo) is required in: $Path"
    }
    return [pscustomobject]@{ Pat = $pat; Repo = $repo }
}

function Assert-NoPlaceholderToken {
    param([string] $Token)
    if (-not $Token) {
        return
    }
    $lower = $Token.ToLowerInvariant()
    if ($lower -match 'replace_me|^ghp_replace|^github_pat_replace|changeme|paste_your|pasteyour') {
        throw @"
Token in secrets file still looks like a placeholder or example text.

Line 1 must be your REAL Personal Access Token only:
  - Remove ALL of the sample text (for example delete the entire string ghp_REPLACE_ME).
  - Paste the token GitHub shows you ONCE when you create it (you cannot view it again later).
  - Optional: use GITHUB_TOKEN=value form on line 1 only.

See docs/github-releases-songdata.md section "secrets.txt の書き方（詳細）".
"@
    }
    if ($Token.Length -lt 20) {
        throw "Token is too short ($($Token.Length) chars). Check line 1 of upload-songdata-github-release.secrets.txt for a truncated paste."
    }
    if ($Token -notmatch '^(gh[ps]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)') {
        Write-Warning "Token does not start with ghp_/ghs_/github_pat_. If GitHub returns 401, verify the full PAT was pasted on line 1."
    }
}

function Assert-NoPlaceholderRepo {
    param([string] $Repo)
    $r = ($Repo -as [string]).Trim()
    if (-not $r) {
        return
    }
    if ($r -match '(?i)your-github-username|your-repository-name|replace_me|\bowner/repository\b') {
        throw @"
Line 2 of upload-songdata-github-release.secrets.txt still looks like a placeholder.

Replace it with your real GitHub repository as owner/name (example: octocat/hello-world).
"@
    }
}

if (-not $Tag -or $Tag.Trim() -eq "") {
    $Tag = "songdata-" + (Get-Date -Format "yyyy-MM-dd")
}
$Tag = $Tag.Trim()
Write-Host "Release tag: $Tag"

$apiRoot = "https://api.github.com"
$apiVersion = "2022-11-28"

function Get-ApiHeaders {
    param([string] $Token)
    return @{
        Authorization          = "Bearer $Token"
        Accept                 = "application/vnd.github+json"
        "X-GitHub-Api-Version" = $apiVersion
    }
}

function Get-UploadHeaders {
    param([string] $Token)
    return @{
        Authorization          = "Bearer $Token"
        Accept                 = "application/vnd.github+json"
        "X-GitHub-Api-Version" = $apiVersion
        "Content-Type"         = "application/octet-stream"
    }
}

function Invoke-GitHubAuthorized {
    <#
    Wrap Invoke-RestMethod (or similar) with identical 401 handling for all GitHub JSON endpoints.
    #>
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Action,
        [Parameter(Mandatory = $true)]
        [string] $AuditLabel
    )
    try {
        return & $Action
    }
    catch {
        $code = Get-ErrorHttpStatusCode -ErrorRecord $_
        if ($code -eq 401) {
            throw ((Format-GitHubAuthHelp) + "`n`nRequest: $AuditLabel`nOriginal: $($_.Exception.Message)")
        }
        throw
    }
}

function Get-ErrorHttpStatusCode {
    <#
    StrictMode-safe: do not read .Exception.Response directly (RuntimeException etc. lack it).
    Walks InnerException for WebException (Windows PowerShell) or HttpResponseException (PowerShell 7+).
    #>
    param([System.Management.Automation.ErrorRecord] $ErrorRecord)
    $e = $ErrorRecord.Exception
    while ($null -ne $e) {
        if ($e -is [System.Net.WebException]) {
            $wr = $e.Response
            if ($null -ne $wr) {
                return [int]$wr.StatusCode
            }
        }
        elseif ($e.PSObject.Properties.Name -contains 'Response') {
            $wr2 = $e.Response
            if ($null -ne $wr2 -and $wr2.PSObject.Properties.Name -contains 'StatusCode') {
                return [int]$wr2.StatusCode
            }
        }
        $e = $e.InnerException
    }
    return $null
}

function Format-GitHubAuthHelp {
    return @"
GitHub returned 401 Unauthorized. Common causes:

  1) Line 1 of upload-songdata-github-release.secrets.txt is wrong
     - Replace the ENTIRE placeholder (e.g. ghp_REPLACE_ME) with your real PAT.
     - One line, no spaces before/after, no smart quotes. UTF-8 recommended.

  2) PAT permissions
     - Classic: private repo -> scope 'repo'. Public-only -> 'public_repo'.
     - Fine-grained: Repository access includes THIS repo; permission 'Contents' = Read and write.

  3) Expired / revoked token -> create a new PAT at GitHub Settings -> Developer settings.

  4) Organization with SAML SSO -> open the token on GitHub and click "Configure SSO" / Authorize for that org.

See docs/github-releases-songdata.md (section: secrets.txt の書き方（詳細・手順）).
"@
}

function Invoke-GitHubGet {
    param(
        [string] $Uri,
        [hashtable] $Headers
    )
    return Invoke-GitHubAuthorized -AuditLabel "GET $Uri" -Action {
        Invoke-RestMethod -Uri $Uri -Headers $Headers -Method Get
    }
}

function Invoke-GitHubPostJson {
    param(
        [string] $Uri,
        [hashtable] $Headers,
        [hashtable] $Body
    )
    $json = $Body | ConvertTo-Json -Compress
    return Invoke-GitHubAuthorized -AuditLabel "POST $Uri" -Action {
        Invoke-RestMethod -Uri $Uri -Headers $Headers -Method Post -Body $json -ContentType "application/json; charset=utf-8"
    }
}

function Invoke-GitHubDelete {
    param(
        [string] $Uri,
        [hashtable] $Headers
    )
    $null = Invoke-GitHubAuthorized -AuditLabel "DELETE $Uri" -Action {
        Invoke-RestMethod -Uri $Uri -Headers $Headers -Method Delete | Out-Null
    }
}

function Get-ReleaseByTag {
    param(
        [string] $Owner,
        [string] $Name,
        [string] $TagName,
        [hashtable] $Headers
    )
    $enc = [uri]::EscapeDataString($TagName)
    $uri = "$apiRoot/repos/$Owner/$Name/releases/tags/$enc"
    try {
        return Invoke-GitHubGet -Uri $uri -Headers $Headers
    }
    catch {
        $code = Get-ErrorHttpStatusCode -ErrorRecord $_
        if ($code -eq 404) {
            return $null
        }
        throw
    }
}

function New-GitHubRelease {
    param(
        [string] $Owner,
        [string] $Name,
        [string] $TagName,
        [string] $Title,
        [string] $BodyText,
        [string] $Commitish,
        [hashtable] $Headers
    )
    $uri = "$apiRoot/repos/$Owner/$Name/releases"
    $payload = @{
        tag_name   = $TagName
        name       = $Title
        body       = $BodyText
        draft      = $false
        prerelease = $false
    }
    if ($Commitish) {
        $payload["target_commitish"] = $Commitish
    }
    return Invoke-GitHubPostJson -Uri $uri -Headers $Headers -Body $payload
}

function Get-ReleaseAssets {
    param(
        [string] $Owner,
        [string] $Name,
        [int] $ReleaseId,
        [hashtable] $Headers
    )
    $uri = "$apiRoot/repos/$Owner/$Name/releases/$ReleaseId/assets?per_page=100"
    $result = Invoke-GitHubGet -Uri $uri -Headers $Headers
    if ($null -eq $result) {
        return @()
    }
    if ($result -is [System.Array]) {
        return $result
    }
    return @($result)
}

function Remove-ReleaseAsset {
    param(
        [string] $Owner,
        [string] $Name,
        [int] $AssetId,
        [hashtable] $Headers
    )
    $uri = "$apiRoot/repos/$Owner/$Name/releases/assets/$AssetId"
    Invoke-GitHubDelete -Uri $uri -Headers $Headers
}

function Expand-UploadUri {
    param([string] $UploadUrlTemplate, [string] $Name)
    # Single-quoted pattern: in double quotes `$` breaks -replace on Windows PowerShell 5.1
    $base = $UploadUrlTemplate -replace '\{\?name,label\}$', ''
    return ($base + "?name=" + [uri]::EscapeDataString($Name))
}

function Send-ReleaseAsset {
    param(
        [string] $UploadUri,
        [string] $FilePath,
        [string] $Token
    )
    $uh = Get-UploadHeaders -Token $Token
    $null = Invoke-GitHubAuthorized -AuditLabel "POST (upload asset) $UploadUri" -Action {
        Invoke-RestMethod -Uri $UploadUri -Headers $uh -Method Post -InFile $FilePath | Out-Null
    }
}

# --- main ---
$secrets = Read-UploadSecretsTxt -Path $secretsTxt
Assert-NoPlaceholderToken -Token $secrets.Pat
Assert-NoPlaceholderRepo -Repo $secrets.Repo
$token = $secrets.Pat
$headers = Get-ApiHeaders -Token $token

$Repo = $secrets.Repo.Trim()
if (-not $Repo) {
    throw "Line 2 (owner/repo) is empty in: $secretsTxt"
}
$parts = $Repo.Split("/")
if ($parts.Length -ne 2 -or -not $parts[0] -or -not $parts[1]) {
    throw "Repo line 2 must be owner/name (got: $Repo)"
}
$owner = $parts[0]
$name = $parts[1]
Write-Host "API target repository: $owner/$name"

if (-not $SongdataPath) {
    $nextToScript = Join-Path $PSScriptRoot $AssetName
    if (Test-Path -LiteralPath $nextToScript -PathType Leaf) {
        $SongdataPath = $nextToScript
    }
    else {
        $repoRoot = Split-Path $PSScriptRoot -Parent
        $SongdataPath = Join-Path $repoRoot $AssetName
    }
}

if (-not (Test-Path -LiteralPath $SongdataPath -PathType Leaf)) {
    throw "File not found: $SongdataPath (copy songdata.db next to the script, use -SongdataPath, or place $AssetName at the repository root)"
}

$release = Get-ReleaseByTag -Owner $owner -Name $name -TagName $Tag -Headers $headers
if ($null -eq $release) {
    Write-Host "No release for tag; creating: tag=$Tag"
    $title = "$AssetName ($Tag)"
    $notes = "Uploaded via upload-songdata-github-release.ps1"
    $commitish = $TargetCommitish
    if (-not $commitish) {
        $commitish = $DefaultBranch
    }
    $release = New-GitHubRelease -Owner $owner -Name $name -TagName $Tag -Title $title -BodyText $notes -Commitish $commitish -Headers $headers
}

$rid = [int]$release.id
$uploadTpl = [string]$release.upload_url
if (-not $uploadTpl) {
    throw "API response missing upload_url."
}

$assets = Get-ReleaseAssets -Owner $owner -Name $name -ReleaseId $rid -Headers $headers
foreach ($a in $assets) {
    if ($a.name -eq $AssetName) {
        Write-Host "Deleting existing asset: $AssetName (id=$($a.id))"
        Remove-ReleaseAsset -Owner $owner -Name $name -AssetId ([int]$a.id) -Headers $headers
    }
}

$uploadUri = Expand-UploadUri -UploadUrlTemplate $uploadTpl -Name $AssetName
Write-Host "Uploading: $SongdataPath -> $AssetName (release_id=$rid)"
Send-ReleaseAsset -UploadUri $uploadUri -FilePath $SongdataPath -Token $token

$dl = "https://github.com/$owner/$name/releases/download/$Tag/$AssetName"
Write-Host "Done. Public download URL example: $dl"
Write-Host "CI (pages.yml) downloads songdata.db from the latest GitHub Release; this upload used tag: $Tag"
