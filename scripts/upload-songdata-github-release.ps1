#Requires -Version 5.1
<#
.SYNOPSIS
  Upload songdata.db to a GitHub Release via the REST API.

.DESCRIPTION
  1) Get release by tag, or create it
  2) Delete same-named asset if present
  3) POST raw bytes to upload_url

  Auth: optional -Token, else env GITHUB_TOKEN / GH_TOKEN, else values from
  upload-songdata-github-release.local.ps1 (see .example file; gitignored).

.PARAMETER Tag
  Release tag (e.g. songdata-2026-05-26). Match SONGDATA_RELEASE_TAG in Actions.

.PARAMETER Repo
  owner/repo. Default: env GITHUB_REPOSITORY after optional local.ps1.

.PARAMETER Token
  PAT override. Prefer leaving empty and using local.ps1 or env vars.

.PARAMETER SongdataPath
  File to upload. Default: repo data/songdata.db

.PARAMETER AssetName
  Asset name on GitHub. Default: songdata.db

.PARAMETER TargetCommitish
  Only when creating a release: target branch/sha if tag missing remotely.
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $Tag,

    [Parameter(Mandatory = $false)]
    [string] $Repo = "",

    [Parameter(Mandatory = $false)]
    [string] $Token = "",

    [Parameter(Mandatory = $false)]
    [string] $SongdataPath = "",

    [Parameter(Mandatory = $false)]
    [string] $AssetName = "songdata.db",

    [Parameter(Mandatory = $false)]
    [string] $TargetCommitish = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$localCfg = Join-Path $PSScriptRoot "upload-songdata-github-release.local.ps1"
if (Test-Path -LiteralPath $localCfg) {
    . $localCfg
}

$apiRoot = "https://api.github.com"
$apiVersion = "2022-11-28"

function Get-RepoToken {
    param([string] $CmdLineToken)
    if ($CmdLineToken) {
        return $CmdLineToken
    }
    $t = $env:GITHUB_TOKEN
    if (-not $t) { $t = $env:GH_TOKEN }
    if (-not $t) {
        throw "Missing token. Set GITHUB_TOKEN or GH_TOKEN, pass -Token, or create scripts/upload-songdata-github-release.local.ps1 (see .example)."
    }
    return $t
}

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

function Invoke-GitHubGet {
    param(
        [string] $Uri,
        [hashtable] $Headers
    )
    return Invoke-RestMethod -Uri $Uri -Headers $Headers -Method Get
}

function Invoke-GitHubPostJson {
    param(
        [string] $Uri,
        [hashtable] $Headers,
        [hashtable] $Body
    )
    $json = $Body | ConvertTo-Json -Compress
    return Invoke-RestMethod -Uri $Uri -Headers $Headers -Method Post -Body $json -ContentType "application/json; charset=utf-8"
}

function Invoke-GitHubDelete {
    param(
        [string] $Uri,
        [hashtable] $Headers
    )
    Invoke-RestMethod -Uri $Uri -Headers $Headers -Method Delete | Out-Null
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
        $resp = $_.Exception.Response
        if ($null -ne $resp -and [int]$resp.StatusCode -eq 404) {
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
    # Use single-quoted pattern: in double quotes, `$` would break the -replace argument list on Windows PowerShell 5.1
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
    Invoke-RestMethod -Uri $UploadUri -Headers $uh -Method Post -InFile $FilePath | Out-Null
}

# --- main ---
$token = Get-RepoToken -CmdLineToken $Token
$headers = Get-ApiHeaders -Token $token

if (-not $Repo -or $Repo.Trim() -eq "") {
    $Repo = $env:GITHUB_REPOSITORY
}
if (-not $Repo -or $Repo.Trim() -eq "") {
    throw "Set repo with -Repo owner/name or GITHUB_REPOSITORY (e.g. in local.ps1)."
}
$parts = $Repo.Trim().Split("/")
if ($parts.Length -ne 2 -or -not $parts[0] -or -not $parts[1]) {
    throw "Repo must be owner/name: $Repo"
}
$owner = $parts[0]
$name = $parts[1]

if (-not $SongdataPath) {
    $repoRoot = Split-Path $PSScriptRoot -Parent
    $SongdataPath = Join-Path (Join-Path $repoRoot "data") $AssetName
}

if (-not (Test-Path -LiteralPath $SongdataPath -PathType Leaf)) {
    throw "File not found: $SongdataPath"
}

$release = Get-ReleaseByTag -Owner $owner -Name $name -TagName $Tag -Headers $headers
if ($null -eq $release) {
    Write-Host "No release for tag; creating: tag=$Tag"
    $title = "$AssetName ($Tag)"
    $notes = "Uploaded via scripts/upload-songdata-github-release.ps1"
    $release = New-GitHubRelease -Owner $owner -Name $name -TagName $Tag -Title $title -BodyText $notes -Commitish $TargetCommitish -Headers $headers
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
