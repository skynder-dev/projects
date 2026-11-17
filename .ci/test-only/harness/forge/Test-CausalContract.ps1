$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../../production/forgeAlphaZero/Modules/Forge.LocalAI.ps1')
. (Join-Path $PSScriptRoot '../../production/forgeAlphaZero/Modules/Forge.AutoResearch.ps1')
$checks=[ordered]@{};function Check($n,$v){$checks[$n]=[bool]$v;if(!$v){throw $n}}
$s=Get-ForgeLocalAISchema
Check 'schema_palette_nonempty_matches_parser' ($s.properties.production_spec.properties.ink_palette.minItems-eq1)
Check 'schema_lists_max12_matches_parser' ($s.properties.production_spec.properties.ink_palette.maxItems-eq12-and$s.properties.production_spec.properties.avoid.maxItems-eq12)
Check 'schema_list_items_max200_matches_parser' ($s.properties.production_spec.properties.ink_palette.items.maxLength-eq200-and$s.properties.production_spec.properties.avoid.items.maxLength-eq200)
Check 'schema_spec_max3000_matches_parser' ($s.properties.production_spec.properties.composition.maxLength-eq3000-and$s.properties.production_spec.properties.illustration.maxLength-eq3000)
$body=ConvertTo-ForgeLocalAIWireBody (New-ForgeLocalAICardBody 'Synthetic free creative task')
Check 'model_visible_canvas_role_explicit' ($body.messages[0].content-match'PIXELS OF THE OUTPUT PNG CANVAS'-and$body.messages[0].content-match'physical garment remains opaque')
Check 'old_transparent_garment_wording_removed' ($body.messages[0].content-notmatch'unprinted garment areas are transparent')
$auto=Get-AutoConceptSchema ([pscustomobject]@{selected_records=@([pscustomobject]@{citation='E1'})})
Check 'auto_keeps_same_list_bounds_and_nine_fields' ($auto.properties.Count-eq9-and$auto.properties.production_spec.properties.ink_palette.minItems-eq1-and$auto.properties.production_spec.properties.ink_palette.maxItems-eq12)
$source=[IO.File]::ReadAllText((Join-Path $PSScriptRoot '../../production/forgeAlphaZero/MerchForgeAutoResearchWorker.ps1'))
Check 'auto_old_transparent_fabric_target_removed' ($source-notmatch'alpha-zero unprinted fabric|transparent unprinted fabric'-and$source-match'Physical garment colour never becomes the PNG background')
Check 'sampling_not_changed_by_causal_repairs' ($body.options.temperature-eq0.5-and$body.options.num_ctx-eq4096-and$body.options.num_predict-eq1400)
@{status='PASS_OFFLINE_CAUSAL_CONTRACT_ALIGNMENT';passed=$checks.Count;checks=$checks;model_calls=0;cim_calls=0;live_state=0}|ConvertTo-Json -Depth 12|Set-Content (Join-Path $PSScriptRoot 'causal-contract-receipt.json') -Encoding UTF8
'PASS '+$checks.Count
