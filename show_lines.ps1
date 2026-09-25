$targets = @(
  @('src/actba64/ImportBuilder.abp', 333),
  @('src/actba64/ImportBuilder.abp', 360),
  @('src/actba64/ImportBuilder.abp', 379),
  @('src/actba64/ImportBuilder.abp', 426),
  @('src/actba64/ImportBuilder.abp', 430),
  @('src/actba64/ImportBuilder.abp', 457),
  @('src/actba64/Types.abp', 492),
  @('src/actba64/Types.abp', 538),
  @('src/actba64/Types.abp', 574),
  @('src/actba64/Types.abp', 616),
  @('src/actba64/Types.abp', 664),
  @('src/actba64/Types.abp', 694),
  @('src/actba64/Emiter.abp', 5),
  @('src/actba64/Ast.abp', 5)
)
foreach ($t in $targets) {
  $f = $t[0]; $n = [int]$t[1]
  $lines = Get-Content -LiteralPath $f
  Write-Output ("{0}({1}): {2}" -f (Split-Path $f -Leaf), $n, $lines[$n - 1])
}
