$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../production/forgeAlphaZero/Modules/Forge.LocalAI.ps1')
. (Join-Path $PSScriptRoot 'AlphaZeroFixture.ps1')
$schema=Get-ForgeLocalAISchema;$checks=[ordered]@{}
function Check($n,$v){$checks[$n]=[bool]$v;if(!$v){throw $n}}
function ActualSaveAccepts($name,$value){
 $before=$value|ConvertTo-Json -Depth 40 -Compress
 Assert-ForgeLocalAIWireContract $before $schema
 $parsed=ConvertFrom-ForgeLocalAIContent $before
 Assert-ForgeAIFieldsForSave $parsed
 Check ($name+'_actual_save_gate') $true
 Check ($name+'_raw_fields_preserved') (($parsed|ConvertTo-Json -Depth 40 -Compress)-ceq$before)
 Check ($name+'_caller_not_mutated') (($value|ConvertTo-Json -Depth 40 -Compress)-ceq$before)
}
$separators=@(0x002D,0x2010,0x2011,0x2012,0x2013,0x2014,0x2212,0xFE63,0xFF0D)
foreach($point in $separators){
 $name='dash_'+$point.ToString('X4');$token='alpha'+[char]$point+'zero';$value=New-AlphaZeroFixtureFields;Set-AlphaZeroFixtureToken $value $token
 Check ($name+'_whole_token_screen') (Test-ForgeRussianOwnerText $value.visual_direction_text $value.hook)
 ActualSaveAccepts $name $value
}
$accepted=@('ALPHA-ZERO',('Alpha'+[char]0x2011+'Zero'),'(alpha-zero)','[alpha-zero]','«alpha-zero»','"alpha-zero"','alpha-zero/alpha-zero',"alpha-zero`r`n",'alpha=0',('alpha-zero '+[char]::ConvertFromUtf32(0x1F642)))
$n=0;foreach($token in $accepted){$n++;$value=New-AlphaZeroFixtureFields;Set-AlphaZeroFixtureToken $value $token;ActualSaveAccepts ('bounded_valid_'+$n) $value}
$value=New-AlphaZeroFixtureFields;$value.production_spec.avoid[0]='Не закрашивать незапечатанные области: alpha-zero.';ActualSaveAccepts 'nested_avoid_token' $value
$value=New-AlphaZeroFixtureFields;$value.hook='ALPHA-ZERO CREW';Set-AlphaZeroFixtureToken $value 'alpha-zero'
$value.visual_direction_text+=' Точная надпись '+$value.hook+'.'
ActualSaveAccepts 'exact_print_text_containing_technical_token' $value
Check 'exact_english_print_exclusion_retained' (Test-ForgeRussianOwnerText ('Русский пример '+$value.hook) $value.hook)
$value=New-AlphaZeroFixtureFields;$value.hook='ALPHA';Set-AlphaZeroFixtureToken $value 'ALPHA-ZERO'
ActualSaveAccepts 'printed_prefix_overlaps_whole_technical_token' $value
$value=New-AlphaZeroFixtureFields;$value.hook='ZERO CREW';Set-AlphaZeroFixtureToken $value 'ALPHA-ZERO'
$value.visual_direction_text+=' Пример пересечения ALPHA-ZERO CREW.'
ActualSaveAccepts 'printed_suffix_overlaps_whole_technical_token' $value
Check 'print_removal_does_not_create_new_left_token_boundary' (!(Test-ForgeRussianOwnerText 'Русский пример Xalpha-zero' 'X'))
Check 'print_removal_does_not_create_new_right_token_boundary' (!(Test-ForgeRussianOwnerText 'Русский пример alpha-zeroX' 'X'))
$bad=@(
 'zero','Zero','ZERO','alphazero','alpha zero','alpha--zero','alpha- zero','alpha -zero',"alpha-`nzero",
 'xalpha-zero','alpha-zerox','яalpha-zero','alpha-zeroя','éalpha-zero','alpha-zeroé','αalpha-zero','alpha-zeroα','1alpha-zero','alpha-zero1','_alpha-zero','alpha-zero_',
 'alpha-alpha-zero','alpha-zero-alpha','alpha-zero-zero',
 ([char]0x0661+'alpha-zero'),('alpha-zero'+[char]0x0661),
 ([char]0x0301+'alpha-zero'),('alpha-zero'+[char]0x0301),
 ([char]0x203F+'alpha-zero'),('alpha-zero'+[char]0x203F),
 ([char]0x200D+'alpha-zero'),('alpha-zero'+[char]0x200D),
 ([char]::ConvertFromUtf32(0x1D400)+'alpha-zero'),('alpha-zero'+[char]::ConvertFromUtf32(0x1D400)),
 ([char]::ConvertFromUtf32(0x1F642)+'alpha-zero'),('alpha-zero'+[char]::ConvertFromUtf32(0x1F642)),
 ('alpha'+[char]0x200D+'-zero'),('alpha-'+[char]0x200D+'zero'),
 ('alpha'+[char]0x00AD+'zero'),('alpha'+[char]0x058A+'zero'),('alpha'+[char]0x2015+'zero'),
 ('alpha'+[char]0x2011+' zero'),('alpha'+[char]0x2212+'zeroing'),('alpha'+[char]0x2011+[char]0x2011+'zero')
)
$prose=@(
 'alpha-zero this is English prose',
 'English prose before alpha-zero',
 'alpha-zero zero',
 'alpha-zero and high quality print',
 ('alpha'+[char]0x2011+'zero this sentence is English'),
 'alpha-zero print ready',
 'This garment changes your life alpha-zero'
)
$n=0;foreach($fragment in @($bad)+@($prose)){
 $n++;$text='Русское описание: '+$fragment+'.'
 Check ('invalid_fragment_screen_'+$n) (!(Test-ForgeRussianOwnerText $text))
 $value=New-AlphaZeroFixtureFields;$value.visual_direction_text+=' '+$text
 $before=$value|ConvertTo-Json -Depth 40 -Compress
 Assert-ForgeLocalAIWireContract $before $schema
 $reason='';try{Assert-ForgeAIFieldsForSave $value}catch{$reason=$_.Exception.Message}
 Check ('invalid_fragment_actual_save_rejected_'+$n) ($reason-like'OWNER_LANGUAGE_RU_REQUIRED: visual_direction_text*')
 Check ('invalid_fragment_original_preserved_'+$n) (($value|ConvertTo-Json -Depth 40 -Compress)-ceq$before)
}
Check 'technical_token_without_russian_is_not_russian_prose' (!(Test-ForgeRussianOwnerText 'alpha-zero'))
Check 'english_sentence_is_not_russian_prose' (!(Test-ForgeRussianOwnerText 'This English sentence says alpha-zero.'))
$value=New-AlphaZeroFixtureFields;Set-AlphaZeroFixtureToken $value ('alpha'+[char]0x2011+'zero')
$review=Get-ForgeOwnerLanguageReview $value
Check 'review_keeps_raw_preservation_and_no_translation_claim' ($review.original_text_preserved-and!$review.semantic_translation_verified-and!$review.approval_granted-and$review.fields.visual_direction_text-ceq'ru_script_screen_passed')
@{status='PASS_NARROW_ALPHA_ZERO_ACTUAL_SAVE_BOUNDARIES';passed=$checks.Count;checks=$checks;accepted_separator_codepoints=@($separators|ForEach-Object{$_.ToString('X4')});negative_fragments=$n;model_calls=0;actual_network=0;live_state=0;real_owner_approvals=0;raw_unchanged=$true;translation_performed=$false}|ConvertTo-Json -Depth 15|Set-Content (Join-Path $PSScriptRoot 'alpha-zero-receipt.json') -Encoding UTF8
'PASS '+$checks.Count
