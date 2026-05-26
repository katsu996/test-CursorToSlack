#Requires -Version 5.1
<#
.SYNOPSIS
  GitHub Releases REST API で songdata.db をアップロードする。

.DESCRIPTION
  1) タグに紐づく Release を取得、無ければ作成
  2) 同名アセットがあれば削除（再アップロード用）
  3) upload_url へ生バイナリ POST

  認証: 環境変数 GITHUB_TOKEN または GH_TOKEN（classic: repo 権限、細粒度: Contents/Releases 相当）

.PARAMETER Tag
  Release のタグ名（例: songdata-2026-05-26）。Actions 変数 SONGDATA_RELEASE_TAG と揃える。

.PARAMETER Repo
  owner/repo。未指定時は環境変数 GITHUB_REPOSITORY。

.PARAMETER SongdataPath
  アップロードするファイル。既定: リポジトリ直下の data/songdata.db

.PARAMETER AssetName
  GitHub 上のアセット名。既定: songdata.db

.PARAMETER TargetCommitish
  Release 新規作成時のみ使用。タグがリモートに無い場合の指し先（省略時は API 既定＝既定ブランチ）。
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $Tag,

    [Parameter(Mandatory = $false)]
    [string] $Repo = $env:GITHUB_REPOSITORY,

    [Parameter(Mandatory = $false)]
    [string] $SongdataPath = "",

    [Parameter(Mandatory = $false)]
    [string] $AssetName = "songdata.db",

    [Parameter(Mandatory = $false)]
    [string] $TargetCommitish = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$apiRoot = "https://api.github.com"
$apiVersion = "2022-11-28"

function Get-RepoToken {
    $t = $env:GITHUB_TOKEN
    if (-not $t) { $t = $env:GH_TOKEN }
    if (-not $t) {
        throw "GITHUB_TOKEN または GH_TOKEN を設定してください（Release の作成・資産操作に必要）。"
    }
    return $t
}

function Get-ApiHeaders {
    param([string] $Token)
    return @{
        Authorization        = "Bearer $Token"
        Accept               = "application/vnd.github+json"
        "X-GitHub-Api-Version" = $apiVersion
    }
}

function Get-UploadHeaders {
    param([string] $Token)
    return @{
        Authorization        = "Bearer $Token"
        Accept               = "application/vnd.github+json"
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
    $base = $UploadUrlTemplate -replace "\{\?name,label\}$", ""
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
$token = Get-RepoToken
$headers = Get-ApiHeaders -Token $token

if (-not $Repo -or $Repo.Trim() -eq "") {
    throw "リポジトリを -Repo owner/name で指定するか、GITHUB_REPOSITORY を設定してください。"
}
$parts = $Repo.Trim().Split("/")
if ($parts.Length -ne 2 -or -not $parts[0] -or -not $parts[1]) {
    throw "Repo は owner/name 形式である必要があります: $Repo"
}
$owner = $parts[0]
$name = $parts[1]

if (-not $SongdataPath) {
    $repoRoot = Split-Path $PSScriptRoot -Parent
    $SongdataPath = Join-Path (Join-Path $repoRoot "data") $AssetName
}

if (-not (Test-Path -LiteralPath $SongdataPath -PathType Leaf)) {
    throw "ファイルが見つかりません: $SongdataPath"
}

$release = Get-ReleaseByTag -Owner $owner -Name $name -TagName $Tag -Headers $headers
if ($null -eq $release) {
    Write-Host "Release が無いため作成します: tag=$Tag"
    $title = "$AssetName ($Tag)"
    $notes = "Uploaded via scripts/upload-songdata-github-release.ps1"
    $release = New-GitHubRelease -Owner $owner -Name $name -TagName $Tag -Title $title -BodyText $notes -Commitish $TargetCommitish -Headers $headers
}

$rid = [int]$release.id
$uploadTpl = [string]$release.upload_url
if (-not $uploadTpl) {
    throw "API 応答に upload_url がありません。"
}

$assets = Get-ReleaseAssets -Owner $owner -Name $name -ReleaseId $rid -Headers $headers
foreach ($a in $assets) {
    if ($a.name -eq $AssetName) {
        Write-Host "既存アセットを削除します: $AssetName (id=$($a.id))"
        Remove-ReleaseAsset -Owner $owner -Name $name -AssetId ([int]$a.id) -Headers $headers
    }
}

$uploadUri = Expand-UploadUri -UploadUrlTemplate $uploadTpl -Name $AssetName
Write-Host "アップロード中: $SongdataPath -> $AssetName (release_id=$rid)"
Send-ReleaseAsset -UploadUri $uploadUri -FilePath $SongdataPath -Token $token

$dl = "https://github.com/$owner/$name/releases/download/$Tag/$AssetName"
Write-Host "完了。ダウンロード URL（公開リポジトリの例）: $dl"
