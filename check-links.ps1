# check-links.ps1 - .md / .mdc の相対リンクと #見出し を検査する（外部 URL は見ない）
#
#   .\check-links.ps1        # 壊れたリンクがあれば一覧を出して終了コード 1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

[Console]::OutputEncoding = [Text.Encoding]::UTF8
$files = @(git -C $Root -c core.quotepath=false ls-files -co --exclude-standard -- "*.md" "*.mdc")
if ($LASTEXITCODE -ne 0) { exit 2 }

$fence = [regex]'(?ms)^[ \t]*(```|~~~).*?^[ \t]*\1[^\n]*$'
$inline = [regex]'`[^`\r\n]*`'
$link = [regex]'!?\[[^\]\r\n]*\]\(\s*(<[^>\r\n]+>|[^)\s]+)(?:\s+"[^"]*")?\s*\)'
$heading = [regex]'(?m)^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t#]*\r?$'
$htmlAnchor = [regex]'<a\s+(?:id|name)="([^"]+)"'
$slugDrop = [regex]'[^\p{L}\p{N}\p{M}\p{Pc} -]'
$anchorCache = @{}

function Get-Slugs([string]$path) {
    if ($anchorCache.ContainsKey($path)) { return $anchorCache[$path] }
    $text = $fence.Replace([IO.File]::ReadAllText($path), "")
    $slugs = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($m in $heading.Matches($text)) {
        $plain = $m.Groups[1].Value -replace '\[([^\]]*)\]\([^)]*\)', '$1' -replace '[`*]', ''
        $base = $slugDrop.Replace($plain.Trim().ToLowerInvariant(), "").Replace(" ", "-")
        $slug = $base
        $n = 0
        while (-not $slugs.Add($slug)) { $n++; $slug = "$base-$n" }
    }
    foreach ($m in $htmlAnchor.Matches($text)) { [void]$slugs.Add($m.Groups[1].Value.ToLowerInvariant()) }
    $anchorCache[$path] = $slugs
    return $slugs
}

$errors = New-Object System.Collections.Generic.List[string]
foreach ($rel in $files) {
    $path = Join-Path $Root $rel
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $text = $inline.Replace($fence.Replace([IO.File]::ReadAllText($path), ""), "")
    $dir = Split-Path $path -Parent
    foreach ($m in $link.Matches($text)) {
        $target = $m.Groups[1].Value.Trim('<', '>')
        if ($target -match '^[a-zA-Z][a-zA-Z0-9+.-]*:') { continue }
        $hash = $target.IndexOf('#')
        $file = if ($hash -ge 0) { $target.Substring(0, $hash) } else { $target }
        $anchor = if ($hash -ge 0) { [Uri]::UnescapeDataString($target.Substring($hash + 1)) } else { "" }
        $dest = if ($file) { [IO.Path]::GetFullPath((Join-Path $dir ([Uri]::UnescapeDataString($file)))) } else { $path }
        if (-not (Test-Path -LiteralPath $dest)) {
            $errors.Add("${rel}: $target (ファイルがない)")
        } elseif ($anchor -and $dest -match '\.mdc?$' -and -not (Get-Slugs $dest).Contains($anchor.ToLowerInvariant())) {
            $errors.Add("${rel}: $target (見出しがない)")
        }
    }
}

if ($errors.Count) {
    $errors | ForEach-Object { Write-Host $_ }
    Write-Host "壊れたリンク: $($errors.Count) 件"
    exit 1
}
Write-Host "リンク OK（$($files.Count) ファイル）"
exit 0
