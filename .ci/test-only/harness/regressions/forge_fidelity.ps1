param([string]$Candidate,[string]$Output)
$ErrorActionPreference='Stop'
foreach($n in @('Forge.BriefApproval.ps1','Forge.ResponseContract.ps1','Forge.VisionReview.ps1')){. (Join-Path $Candidate ('Modules/'+$n))}
$rows=@();$stamp='2026-01-01T00:00:00Z';$emoji=[char]::ConvertFromUtf32(0x1F600);$replacement=[string][char]0xFFFD
$raw='{"x":"2026-01-01T00:00:00Z","nested":{"dates":["2026-01-01","2026-01-01T12:00:00+02:00",null,true,12],"emoji":"\ud83d\ude00","replacement":"\ufffd"},"2026-01-01T00:00:00Z":"date key"}'
$v=ConvertFrom-ForgeJsonObjectStrict $raw
if($v.x-isnot[string]-or$v.x-cne$stamp-or$v.nested.dates[0]-isnot[string]-or$v.nested.dates[1]-isnot[string]-or$v.nested.emoji-cne$emoji-or$v.nested.replacement-cne$replacement-or$v.$stamp-cne'date key'-or$v.nested.dates[3]-isnot[bool]-or$v.nested.dates[4]-isnot[long]){throw 'Nested scalar fidelity failed'}
$rows+=@{case='nested_objects_arrays_date_key_and_scalar_types';pass=$true}
$schema=@{type='object';properties=@{x=@{type='string'}};required=@('x');additionalProperties=$false}|ConvertTo-Json -Depth 8|ConvertFrom-Json
Assert-ForgeLocalAIWireContract ('{"x":"'+$stamp+'"}') $schema
$rows+=@{case='actual_wire_timestamp_string';pass=$true}
$vision='{"verdict":"uncertain","observed_text":"'+$stamp+'","observed_elements":"'+$emoji+$replacement+'","composition":"date text","findings":[]}'
$report=ConvertFrom-ForgeVisionContent $vision $stamp
if($report.observed_text-cne$stamp-or$report.observed_elements-cne($emoji+$replacement)){throw 'Vision string fidelity failed'}
$rows+=@{case='actual_vision_timestamp_emoji_literal_replacement';pass=$true}
foreach($value in @('\ud800','\udfff','\ud800A','\ud800\ud800','\udfff\ud800',([string][char]0xD800),([string][char]0xDFFF))){
 foreach($raw in @(('{"x":"'+$value+'"}'),('{"a":[{"x":"'+$value+'"}]}'),('{"'+$value+'":"key"}'))){
  $rejected=$false;try{$null=ConvertFrom-ForgeJsonObjectStrict $raw}catch{$rejected=$true};if(!$rejected){throw 'Invalid Unicode scalar accepted'};$rows+=@{case='isolated_surrogate_value_nested_array_or_key';pass=$true}
 }
}
foreach($value in @('\ud83d\ude00',$emoji,('\ud83d'+[char]0xDE00),([string][char]0xD83D+'\ude00'),'\ufffd',$replacement)){
 $v=ConvertFrom-ForgeJsonObjectStrict ('{"a":[{"x":"'+$value+'"}]}');if($v.a[0].x-cne$(if($value-in@('\ufffd',$replacement)){$replacement}else{$emoji})){throw 'Valid Unicode value mutated'};$rows+=@{case='paired_surrogate_or_replacement_preserved';pass=$true}
}
foreach($raw in @(('{"'+$stamp+'":1,"'+$stamp+'":2}'),('{"'+$emoji+'":1,"\ud83d\ude00":2}'),('{"\ud83d'+[char]0xDE00+'":1,"'+$emoji+'":2}'))){$rejected=$false;try{$null=ConvertFrom-ForgeJsonObjectStrict $raw}catch{$rejected=$true};if(!$rejected){throw 'Equivalent string keys accepted twice'};$rows+=@{case='date_or_equivalent_unicode_duplicate_key_rejected';pass=$true}}
@{status='PASS';checks=$rows;PowerShell=$PSVersionTable.PSVersion.ToString();unicode_policy='Unicode scalar strings only; isolated escaped/literal surrogates rejected, valid pairs and U+FFFD preserved';models=0}|ConvertTo-Json -Depth 8|Set-Content $Output -Encoding utf8
Write-Output ('PASS fidelity checks: '+$rows.Count)
