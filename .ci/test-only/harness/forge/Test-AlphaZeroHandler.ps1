$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Net.Http
. (Join-Path $PSScriptRoot '../../production/forgeAlphaZero/Modules/Forge.LocalAI.ps1')
. (Join-Path $PSScriptRoot '../../production/forgeAlphaZero/Modules/Forge.PublicEvidence.ps1')
. (Join-Path $PSScriptRoot 'AlphaZeroFixture.ps1')
$LocalAIPrompt=[pscustomobject]@{Text='Synthetic in-memory response fixture. No actual request, image, approval or state.'}
$LocalAIStatus=[pscustomobject]@{Text=''};$LocalAICreateButton=[pscustomobject]@{IsEnabled=$true};$LocalAIReviseButton=[pscustomobject]@{IsEnabled=$true};$LocalAICancelButton=[pscustomobject]@{IsEnabled=$false}
function Get-ResearchEvidenceContext{return $null}
function Write-AppLog($Level,$Message){}
function Save-ForgeLocalAIDraft($Fields,$Prompt,$Key,$Revision,$EvidenceContext){Assert-ForgeAIFieldsForSave $Fields $EvidenceContext;$script:SaveGateCalls++;$script:Captured=$Fields;return [pscustomobject]@{saved=$false}}
function New-ForgeLocalAIJsonRequest($Body){
 $script:FixtureRequests++;$wire=ConvertTo-ForgeLocalAIWireBody $Body;$json=$wire|ConvertTo-Json -Depth 20 -Compress
 $res=New-Object Net.Http.HttpResponseMessage ([Net.HttpStatusCode]::OK);$res.Content=New-Object Net.Http.StringContent($script:ResponseFixture,[Text.Encoding]::UTF8,'application/json')
 $ready=New-Object 'Threading.Tasks.TaskCompletionSource[System.Net.Http.HttpResponseMessage]';$ready.SetResult($res)
 return [pscustomobject]@{Content=(New-Object Net.Http.StringContent($json,[Text.Encoding]::UTF8,'application/json'));ResponseSchema=(($wire.format|ConvertTo-Json -Depth 20)|ConvertFrom-Json);Client=(New-Object Net.Http.HttpClient);Cancel=(New-Object Threading.CancellationTokenSource);Task=$ready.Task}
}
$checks=[ordered]@{};function Check($n,$v){$checks[$n]=[bool]$v;if(!$v){throw $n}}
$cases=@(
 @('ascii','alpha-zero',$true),@('hyphen',('alpha'+[char]0x2010+'zero'),$true),@('nonbreaking',('alpha'+[char]0x2011+'zero'),$true),@('en_dash',('alpha'+[char]0x2013+'zero'),$true),@('minus',('alpha'+[char]0x2212+'zero'),$true),
 @('mixed_prose','alpha-zero this is English prose',$false),@('standalone_zero','zero',$false),@('compound','alpha-alpha-zero',$false),@('suffix','alpha-zeroing',$false)
)
foreach($case in $cases){
 $value=New-AlphaZeroFixtureFields;Set-AlphaZeroFixtureToken $value $case[1];$raw=$value|ConvertTo-Json -Depth 40 -Compress
 $script:ResponseFixture=@{model='qwen3.5:9b';done=$true;done_reason='stop';message=@{role='assistant';content=$raw}}|ConvertTo-Json -Depth 50 -Compress
 $script:LocalAIRequest=$null;$script:VisionReviewRequest=$null;$script:Dirty=$false;$script:PublicationDirty=$false;$script:Current=$null;$script:LastRejectedLocalAIResponse=$null;$script:SaveGateCalls=0;$script:FixtureRequests=0;$script:Captured=$null
 Start-ForgeLocalAIRequest;Check ($case[0]+'_actual_start_fixture') ($null-ne$script:LocalAIRequest)
 Complete-ForgeLocalAIRequest
 Check ($case[0]+'_one_in_memory_fixture_no_network') ($script:FixtureRequests-eq1)
 if($case[2]){
  Check ($case[0]+'_actual_handler_reached_save_gate') ($script:SaveGateCalls-eq1-and$null-eq$script:LastRejectedLocalAIResponse)
  Check ($case[0]+'_raw_content_fields_preserved') (($script:Captured|ConvertTo-Json -Depth 40 -Compress)-ceq$raw)
 }else{
  Check ($case[0]+'_actual_handler_rejects_before_save') ($script:SaveGateCalls-eq0-and$null-ne$script:LastRejectedLocalAIResponse)
  Check ($case[0]+'_rejected_raw_response_preserved') ($script:LastRejectedLocalAIResponse.original_response-ceq$script:ResponseFixture)
 }
 Check ($case[0]+'_request_cleared_controls_restored') ($null-eq$script:LocalAIRequest-and$LocalAICreateButton.IsEnabled-and$LocalAIReviseButton.IsEnabled-and!$LocalAICancelButton.IsEnabled)
}
@{status='PASS_ACTUAL_START_COMPLETE_ALPHA_ZERO_IN_MEMORY';passed=$checks.Count;checks=$checks;synthetic_response_cases=$cases.Count;response_source='Synthetic fixtures, never model output';actual_network=0;model_calls=0;live_state_reads=0;live_state_writes=0;real_owner_approvals=0;images=0;raw_preserved=$true;translation_performed=$false}|ConvertTo-Json -Depth 15|Set-Content (Join-Path $PSScriptRoot 'alpha-zero-handler-receipt.json') -Encoding UTF8
'PASS '+$checks.Count
