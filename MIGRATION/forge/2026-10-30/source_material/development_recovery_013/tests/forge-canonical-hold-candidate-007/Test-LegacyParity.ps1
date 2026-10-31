param([Parameter(Mandatory=$true)][string]$ModuleRoot,[Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
function Get-PropertyValue($Object,$Name,$Default=$null){if($null-eq$Object){return $Default};if($Object-is[Collections.IDictionary]){return $Object[$Name]};$p=$Object.PSObject.Properties[$Name];if($null-ne$p){return $p.Value};return $Default}
foreach($n in @('Forge.Media.ps1','Forge.DataViews.ps1','Forge.LocalCore.ps1','Forge.ResearchDrafts.ps1','Forge.PublicEvidence.ps1','Forge.LocalAI.ps1')){. (Join-Path $ModuleRoot $n)}
$fixture=Get-Content (Join-Path (Split-Path $PSScriptRoot) 'forge-rejection-review-dev-001/acceptance-frozen-copy/fixtures/synthetic-valid-fields.json') -Raw -Encoding utf8|ConvertFrom-Json
$results=[ordered]@{}
foreach($case in @('original_fixture','substantive_without_stems','vacuous_keywords','english_owner','missing_print_uncertainty')){
 $v=$fixture|ConvertTo-Json -Depth 40|ConvertFrom-Json
 switch($case){substantive_without_stems{$v.concept_text='Надпись перечисляет этапы ремонта, а изображённые крупные детали постепенно складываются в один инструмент: зритель читает последовательность действий и видит её результат.'} vacuous_keywords{$v.concept_text=('Смысл, метафора, связь, символ, шутка. Всё красиво. '*4)} english_owner{$v.target_buyer='An English paragraph describing the audience without any Russian words.'} missing_print_uncertainty{$v.differentiation=$v.differentiation.Replace('Качество печати не проверено.','')}}
 $errorText=$null;try{$null=ConvertFrom-ForgeLocalAIContent ($v|ConvertTo-Json -Depth 40)}catch{$errorText=$_.Exception.Message}
 $results[$case]=[ordered]@{accepted=($null-eq$errorText);error=$errorText}
}
$results|ConvertTo-Json -Depth 10|Set-Content $OutputPath -Encoding utf8
