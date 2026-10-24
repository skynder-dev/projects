# Limited phrase guard for unsupported functional/psychological merchandise claims.
# It never verifies effects, edits a draft or grants semantic/owner approval.
function Get-ForgeInstrumentalEffectIssues([string]$Prose) {
 $issues=@()
 $patterns=@(
  '(?i)(?:инструмент|средств|способ)\w*\s+(?:для\s+)?(?:саморегуляц\w*|снижен\w*\s+стресс\w*|сняти\w*\s+стресс\w*|успокоен\w*)',
  '(?i)(?:служит|становится|является)\s+триггер\w*\s+(?:к|для)\s+(?:коротк\w*\s+)?(?:остановк\w*|пауз\w*|успокоен\w*)'
 )
 foreach($clause in @($Prose-split'(?i)[.!?;\r\n]+|\s+(?:но|а|однако|зато|при\s+этом)\s+')) {
  foreach($pattern in $patterns) {
   foreach($claim in [regex]::Matches($clause,$pattern)) {
    $prefix=$clause.Substring(0,$claim.Index)
    # Only a governing negation in this clause applies. "Not only" is affirmative.
    $direct=$prefix-match'(?i)\bне\s+(?!только\b)(?:(?:является|служит|считается|работает\s+как)\s+)?(?:визуальн\w*\s+|терапевтическ\w*\s+)?$'
    $reported=$prefix-match'(?i)\bне\s+(?:утвержда\w*|обеща\w*|заявля\w*|доказа\w*|позициониру\w*)\s*,?\s*(?:что\s+)?(?:\p{L}+\s+){0,5}$'
    if(!$direct-and!$reported) {$issues+='Неподтверждённая инструментальная или психологическая функция одежды: саморегуляция, снижение стресса или поведенческий триггер требуют отдельной проверки; слово «гипотеза» не подтверждает эффект.'}
   }
  }
 }
 return @($issues|Select-Object -Unique)
}
