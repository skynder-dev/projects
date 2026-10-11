param([string]$ArchivistRoot="D:\Archivist",[string]$SmokeVideo="")
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
function HashFile([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
$StablePtr=Join-Path $ArchivistRoot 'current.txt';$StablePtrHashBefore=$null;if(Test-Path -LiteralPath $StablePtr -PathType Leaf){$StablePtrHashBefore=HashFile $StablePtr}
$Side=Join-Path $ArchivistRoot 'sidecars\auto_edit';$Ptr=Join-Path $Side 'current.txt';if(!(Test-Path $Ptr)){throw 'V52 not activated'};$Slot=(Get-Content $Ptr -Raw).Trim();$Rel=Join-Path (Join-Path $Side 'releases') $Slot
if(!(Test-Path (Join-Path $Rel 'medeng_drop_queue_v40.py'))){throw 'V52 queue missing'};if(!(Test-Path (Join-Path $Rel 'medeng_queue_supervisor_v40.py'))){throw 'V52 supervisor missing'};if(!(Test-Path (Join-Path $Rel 'RETRY_FAILED_JOB_V52.ps1'))){throw 'V52 exact retry helper missing'}
if(!(Test-Path (Join-Path $Rel 'medeng_auto_approval_v39.py'))){throw 'V52 auto approval module missing'}
if(!(Test-Path (Join-Path $Rel 'medeng_review_decision_v39.py'))){throw 'V52 review decision module missing'}
$PM=Join-Path $Rel 'V52_PAYLOAD_MANIFEST.json';if(!(Test-Path $PM -PathType Leaf)){throw 'V52 payload manifest missing'}
$Manifest=Get-Content $PM -Raw|ConvertFrom-Json;if($Manifest.slot -ne $Slot){throw 'V52 slot/manifest mismatch'}
$Wrappers=@('RUN_AUTO_EDIT_QUEUE_V37.ps1','RUN_AUTO_EDIT_SUPERVISOR_V37.ps1','APPROVE_LATEST_AUTO_V37.ps1','APPROVE_LATEST_ALT_A_V37.ps1','APPROVE_LATEST_ALT_B_V37.ps1','APPROVE_LATEST_OVERRIDE_V37.ps1','APPLY_LATEST_OVERRIDE_V37.ps1','EDIT_LATEST_REVIEW_CHOICE_V38.ps1','APPLY_LATEST_REVIEW_CHOICE_V38.ps1')
foreach($n in $Wrappers){$t=Get-Content -LiteralPath (Join-Path $Rel $n) -Raw;if($t -match 'V(3[789]|4[0-9]|50)_PAYLOAD_MANIFEST\.json'){throw "V52 inherited wrapper pins stale manifest: $n"};if($t -notmatch 'V52_PAYLOAD_MANIFEST\.json'){throw "V52 wrapper does not pin V52 manifest: $n"}}

$QueueLauncher=Get-Content -LiteralPath (Join-Path $Rel 'RUN_AUTO_EDIT_QUEUE_V37.ps1') -Raw
if($QueueLauncher -notmatch 'broad RetryFailed is disabled'){throw 'V48 broad retry guard missing'}
if($QueueLauncher -notmatch 'medeng_drop_queue_v40\.py'){throw 'V48 queue launcher does not target queue'}
$IPath=Join-Path $Rel 'install_manifest.json';if(!(Test-Path $IPath)){throw 'V48 install manifest missing'};$I=Get-Content $IPath -Raw|ConvertFrom-Json
foreach($pair in @(@($I.python,$I.python_sha256),@($I.ffmpeg,$I.ffmpeg_sha256))){if(!(Test-Path -LiteralPath $pair[0] -PathType Leaf)){throw "V48 pinned runtime missing: $($pair[0])"};if((HashFile $pair[0]) -ne $pair[1]){throw "V48 pinned runtime changed: $($pair[0])"}}
if($I.probe_backend -ne 'FFMPEG_INPUT_METADATA_V41' -or $I.external_ffprobe_required -ne $false -or $I.ffprobe_compatibility_alias -ne $true){throw 'V48 portable probe contract invalid'}
if($I.ffprobe -ne $I.ffmpeg -or $I.ffprobe_sha256 -ne $I.ffmpeg_sha256){throw 'V48 compatibility alias must pin exact FFmpeg identity'}
if(!(Test-Path (Join-Path $Rel 'medeng_media_probe_v41.py') -PathType Leaf)){throw 'V48 media probe helper missing'}
$env:PYTHONDONTWRITEBYTECODE='1';$env:PATH=(Split-Path -Parent $I.ffmpeg)+';'+$env:PATH
$LogicRaw=& $I.python (Join-Path $Rel 'v42_logic_selftest.py');if($LASTEXITCODE -ne 0){throw "V48 logic self-test failed rc=$LASTEXITCODE"};$Logic=($LogicRaw -join "`n")|ConvertFrom-Json;if($Logic.status -ne 'PASS' -or $Logic.passed -ne $Logic.total){throw 'V48 logic self-test not all PASS'}
$PacingRaw=& $I.python (Join-Path $Rel 'v42_pacing_selftest.py');if($LASTEXITCODE -ne 0){throw "V48 pacing self-test failed rc=$LASTEXITCODE"};$Pacing=($PacingRaw -join "`n")|ConvertFrom-Json;if($Pacing.passed -ne $Pacing.total){throw 'V48 pacing self-test not all PASS'}
$AudioRaw=& $I.python (Join-Path $Rel 'v43_audio_selftest.py');if($LASTEXITCODE -ne 0){throw "V48 audio self-test failed rc=$LASTEXITCODE"};$Audio=($AudioRaw -join "`n")|ConvertFrom-Json;if($Audio.passed -ne $Audio.total){throw 'V48 audio self-test not all PASS'}
$FrameRaw=& $I.python (Join-Path $Rel 'v44_vertical_framing_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V48 framing self-test failed rc=$LASTEXITCODE"};$Frame=($FrameRaw -join "`n")|ConvertFrom-Json;if($Frame.status -ne 'PASS' -or $Frame.passed -ne $Frame.total){throw 'V48 framing self-test not all PASS'}
$FocusRaw=& $I.python (Join-Path $Rel 'v45_vertical_focus_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V48 focus self-test failed rc=$LASTEXITCODE"};$Focus=($FocusRaw -join "`n")|ConvertFrom-Json;if($Focus.status -ne 'PASS' -or $Focus.passed -ne $Focus.total){throw 'V48 focus self-test not all PASS'}
$ResRaw=& $I.python (Join-Path $Rel 'v46_resolution_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V48 resolution self-test failed rc=$LASTEXITCODE"};$Res=($ResRaw -join "`n")|ConvertFrom-Json;if($Res.status -ne 'PASS' -or $Res.passed -ne $Res.total){throw 'V48 resolution self-test not all PASS'}
$ContentRaw=& $I.python (Join-Path $Rel 'v47_audio_content_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V48 audio-content self-test failed rc=$LASTEXITCODE"};$Content=($ContentRaw -join "`n")|ConvertFrom-Json;if($Content.status -ne 'PASS' -or $Content.passed -ne $Content.total){throw 'V48 audio-content self-test not all PASS'}
$CoverRaw=& $I.python (Join-Path $Rel 'v48_cover_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V48 cover self-test failed rc=$LASTEXITCODE"};$Cover=($CoverRaw -join "`n")|ConvertFrom-Json;if($Cover.status -ne 'PASS' -or $Cover.passed -ne $Cover.total){throw 'V48 cover self-test not all PASS'}
$ApprovedCoverRaw=& $I.python (Join-Path $Rel 'v49_approved_cover_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V49 approved-cover self-test failed rc=$LASTEXITCODE"};$ApprovedCover=($ApprovedCoverRaw -join "`n")|ConvertFrom-Json;if($ApprovedCover.status -ne 'PASS' -or $ApprovedCover.passed -ne $ApprovedCover.total){throw 'V49 approved-cover self-test not all PASS'}
$CoverPosRaw=& $I.python (Join-Path $Rel 'v50_cover_position_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V52 cover-position self-test failed rc=$LASTEXITCODE"};$CoverPos=($CoverPosRaw -join "`n")|ConvertFrom-Json;if($CoverPos.status -ne 'PASS' -or $CoverPos.passed -ne $CoverPos.total){throw 'V52 cover-position self-test not all PASS'}
$FpsRaw=& $I.python (Join-Path $Rel 'v51_output_fps_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V52 fps self-test failed rc=$LASTEXITCODE"};$Fps=($FpsRaw -join "`n")|ConvertFrom-Json;if($Fps.status -ne 'PASS' -or $Fps.passed -ne $Fps.total){throw 'V52 fps self-test not all PASS'}
$QualityRaw=& $I.python (Join-Path $Rel 'v52_video_quality_selftest.py') --ffmpeg $I.ffmpeg --package-root $Rel;if($LASTEXITCODE -ne 0){throw "V52 quality self-test failed rc=$LASTEXITCODE"};$Quality=($QualityRaw -join "`n")|ConvertFrom-Json;if($Quality.status -ne 'PASS' -or $Quality.passed -ne $Quality.total){throw 'V52 quality self-test not all PASS'}
if($SmokeVideo){
  if(!(Test-Path $SmokeVideo -PathType Leaf)){throw 'SmokeVideo missing'}
  $T=Join-Path $Side 'self_test_v51';$In=Join-Path $T 'inbox';$Out=Join-Path $T 'outbox';$Q=Join-Path $T 'queue';$Batch=Join-Path $In 'zero_touch'
  if(Test-Path $T){Remove-Item $T -Recurse -Force};New-Item -ItemType Directory -Force -Path $Batch,$Out,$Q|Out-Null
  Copy-Item -LiteralPath $SmokeVideo -Destination (Join-Path $Batch ([IO.Path]::GetFileName($SmokeVideo)))
  '{"schema_version":1,"target_seconds":15,"clip_seconds":3.0,"transition_seconds":0.15,"audio_lufs":-16.0,"audio_true_peak_db":-1.5,"vertical_framing":"fill","vertical_focus_x":0.75,"output_resolution":"social_hd","output_fps":60,"video_quality":"high","audio_content":"mute","cover_mode":"auto","cover_position":0.5,"ready_mode":"settle","approval_mode":"auto","max_attempts":1,"retry_backoff_seconds":30}'|Set-Content -LiteralPath (Join-Path $Batch 'AUTO_EDIT.json') -Encoding UTF8
  $QueueScript=Join-Path $Rel 'RUN_AUTO_EDIT_QUEUE_V37.ps1'
  & $QueueScript -ArchivistRoot $ArchivistRoot -Inbox $In -Outbox $Out -QueueRoot $Q -Once -TargetSeconds 15 -SettleSeconds 0 -BatchSettleSeconds 0
  if($LASTEXITCODE -ne 0){throw "V52 smoke queue failed rc=$LASTEXITCODE"}
  $JobFile=Get-ChildItem $Out -Filter JOB_RESULT.json -Recurse -File|Select-Object -First 1
  if(!$JobFile){
    & $QueueScript -ArchivistRoot $ArchivistRoot -Inbox $In -Outbox $Out -QueueRoot $Q -Once -TargetSeconds 15 -SettleSeconds 0 -BatchSettleSeconds 0
    if($LASTEXITCODE -ne 0){throw "V52 smoke queue second settle scan failed rc=$LASTEXITCODE"}
    $JobFile=Get-ChildItem $Out -Filter JOB_RESULT.json -Recurse -File|Select-Object -First 1
  }
  if(!$JobFile){throw 'V52 smoke result missing after bounded second scan'}
  $Job=$JobFile.DirectoryName
  $JR=Get-Content -LiteralPath $JobFile.FullName -Raw|ConvertFrom-Json;if([double]$JR.clip_seconds -ne 3.0 -or [double]$JR.transition_seconds -ne 0.15){throw 'V52 smoke pacing metadata mismatch'}
  if([double]$JR.audio_lufs -ne -16.0 -or [double]$JR.audio_true_peak_db -ne -1.5){throw 'V52 smoke audio metadata mismatch'}
  if([double]$JR.vertical_focus_x -ne 0.75){throw 'V52 smoke vertical focus metadata mismatch'}
  if([string]$JR.output_resolution -ne 'social_hd'){throw 'V52 smoke output resolution metadata mismatch'}
  if([int]$JR.output_fps -ne 60){throw 'V52 smoke output fps metadata mismatch'}
  if([string]$JR.video_quality -ne 'high'){throw 'V52 smoke video quality metadata mismatch'}
  if([string]$JR.audio_content -ne 'mute'){throw 'V52 smoke audio content metadata mismatch'}
  if(!$JR.cover_assets -or $JR.cover_assets.status -ne 'PASS' -or $JR.cover_assets.covers.Count -ne 2 -or [double]$JR.cover_assets.cover_position -ne 0.5){throw 'V52 smoke cover assets/position invalid'}
  if(!(Test-Path (Join-Path $Job 'Review\AUTO_APPROVAL_V39.json'))){throw 'V52 smoke auto approval record missing'}
  $AR=Get-Content (Join-Path $Job 'Review\AUTO_APPROVAL_V39.json') -Raw|ConvertFrom-Json;if($AR.status -notin @('AUTO_APPROVED','SKIPPED_EXACT_AUTO')){throw "V52 smoke auto approval status invalid: $($AR.status)"}
  $AM=Join-Path $Job 'Approved\APPROVED_MANIFEST.json';if(!(Test-Path $AM)){throw 'V52 smoke Approved manifest missing'};$AO=Get-Content $AM -Raw|ConvertFrom-Json
  if($AO.approval_policy -ne 'AUTO_OPT_IN_V39' -or $AO.semantic_selection_claim -ne $false){throw 'V52 smoke Approved policy invalid'}
  foreach($o in $AO.outputs){$p=Join-Path (Join-Path $Job 'Approved') $o.filename;if(!(Test-Path $p -PathType Leaf)){throw "V52 smoke Approved output missing: $($o.filename)"};if((Get-Item $p).Length -ne [int64]$o.bytes -or (HashFile $p)-ne $o.sha256){throw "V52 smoke Approved output identity mismatch: $($o.filename)"}}
  $ACM=Join-Path $Job 'Approved\Covers\APPROVED_COVER_MANIFEST.json';if(!(Test-Path $ACM -PathType Leaf)){throw 'V52 smoke Approved cover manifest missing'};$ACO=Get-Content $ACM -Raw|ConvertFrom-Json;if($ACO.status -ne 'PASS' -or $ACO.covers.Count -ne 2 -or [double]$ACO.cover_position -ne 0.5 -or $ACO.semantic_selection_claim -ne $false){throw 'V52 smoke Approved covers invalid'}
  foreach($c in $ACO.covers){$p=Join-Path (Join-Path $Job 'Approved\Covers') $c.filename;if(!(Test-Path $p -PathType Leaf)){throw "V52 smoke Approved cover missing: $($c.filename)"};if((Get-Item $p).Length -ne [int64]$c.bytes -or (HashFile $p)-ne $c.sha256){throw "V52 smoke Approved cover identity mismatch: $($c.filename)"}}
  $GP=Join-Path $Out 'LATEST_APPROVED.json';if(!(Test-Path $GP)){throw 'V52 smoke global Approved pointer missing'}
  $ReviewRaw=& $I.python (Join-Path $Rel 'medeng_review_decision_v39.py') prepare --job-outdir $Job --default AUTO;if($LASTEXITCODE -ne 0){throw "V52 smoke review prepare failed rc=$LASTEXITCODE"};$Review=($ReviewRaw -join "`n")|ConvertFrom-Json;if($Review.status -ne 'PASS' -or -not ($Review.available -contains 'AUTO')){throw 'V52 smoke review availability invalid'}
}
if($StablePtrHashBefore){if(!(Test-Path $StablePtr -PathType Leaf) -or (HashFile $StablePtr)-ne $StablePtrHashBefore){throw 'V48 stable pointer mutated'}}
Write-Output "V52_SELF_TEST_PASS logic=$($Logic.passed)/$($Logic.total) pacing=$($Pacing.passed)/$($Pacing.total) audio=$($Audio.passed)/$($Audio.total) framing=$($Frame.passed)/$($Frame.total) focus=$($Focus.passed)/$($Focus.total) resolution=$($Res.passed)/$($Res.total) content=$($Content.passed)/$($Content.total) cover=$($Cover.passed)/$($Cover.total) approved_cover=$($ApprovedCover.passed)/$($ApprovedCover.total) cover_position=$($CoverPos.passed)/$($CoverPos.total) fps=$($Fps.passed)/$($Fps.total) quality=$($Quality.passed)/$($Quality.total) smoke=$([bool]$SmokeVideo)"
