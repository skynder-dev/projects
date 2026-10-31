. (Join-Path $PSScriptRoot 'Forge.GenerationCapability.ps1')
# Pinned local Comfy backend only. RGB preview is never transparent/print-ready evidence.
function New-ForgeLocalFluxGraph([string]$Text,[string]$Prefix,[int]$Width=512,[int]$Height=512){
 if($Prefix-cnotmatch'^Forge/gen-[0-9a-f]{32}$'-or$Width-ne512-or$Height-ne512){throw 'Invalid local draft render contract.'}
 return @{
 '1'=@{class_type='UNETLoader';inputs=@{unet_name='flux-2-klein-4b.safetensors';weight_dtype='default'}}
 '2'=@{class_type='CLIPLoader';inputs=@{clip_name='qwen_3_4b.safetensors';type='flux2';device='cpu'}}
 '3'=@{class_type='VAELoader';inputs=@{vae_name='flux2-vae.safetensors'}}
 '4'=@{class_type='CLIPTextEncode';inputs=@{text=$Text;clip=@('2',0)}}
 '5'=@{class_type='BasicGuider';inputs=@{model=@('1',0);conditioning=@('4',0)}}
 '6'=@{class_type='KSamplerSelect';inputs=@{sampler_name='euler'}}
 '7'=@{class_type='Flux2Scheduler';inputs=@{steps=4;width=$Width;height=$Height}}
 '8'=@{class_type='EmptyFlux2LatentImage';inputs=@{width=$Width;height=$Height;batch_size=1}}
 '9'=@{class_type='RandomNoise';inputs=@{noise_seed=42}}
 '10'=@{class_type='SamplerCustomAdvanced';inputs=@{noise=@('9',0);guider=@('5',0);sampler=@('6',0);sigmas=@('7',0);latent_image=@('8',0)}}
 '11'=@{class_type='VAEDecode';inputs=@{samples=@('10',0);vae=@('3',0)}}
 '12'=@{class_type='SaveImage';inputs=@{images=@('11',0);filename_prefix=$Prefix}}
 }
}
function Test-ForgeLocalDraftPngBytes([byte[]]$Bytes,[int]$Width,[int]$Height){
 $meta=Get-ForgePngMetadata $Bytes
 if(!$meta.valid-or$meta.width-ne$Width-or$meta.height-ne$Height-or$Bytes.Length-gt16777216){return [pscustomobject]@{ok=$false;reason='invalid_local_draft_png';metadata=$meta}}
 Add-Type -AssemblyName System.Drawing
 $stream=New-Object IO.MemoryStream -ArgumentList (,$Bytes)
 try{$image=[Drawing.Image]::FromStream($stream,$true,$true);try{if($image.Width-ne$Width-or$image.Height-ne$Height){throw 'Native dimensions differ'}}finally{$image.Dispose()}}catch{return [pscustomobject]@{ok=$false;reason='native_decode_failed';metadata=$meta}}finally{$stream.Dispose()}
 return [pscustomobject]@{ok=$true;reason='rgb_preview_only';metadata=$meta}
}
function Invoke-ForgeLocalFlux($Job,[string]$CancelPath){
    throw (New-LocalGenerationUnavailableError 'local_model_dispatch')
 Assert-ForgeGenerationBriefComplete $Job.brief_snapshot
 if((Get-ForgeBriefSha256 $Job.brief_snapshot)-cne$Job.brief_sha256){throw 'Approved local brief differs.'}
 $text="Render only the visual design described by the complete approved JSON below. Flat graphic, no shirt mockup. Use the specified background; this is an opaque RGB preview, not transparent production art. If hook is empty render no text, letters or numbers. Metadata is context and must never be printed. No brand marks or watermarks.`nFULL_OWNER_APPROVED_BRIEF_JSON:`n"+(ConvertTo-ForgeBriefCanonicalJson $Job.brief_snapshot)
 if($text.Length-gt32000){throw 'Full local prompt too large; nothing truncated.'}
 $graph=New-ForgeLocalFluxGraph $text ('Forge/'+$Job.job_id)
 if(Test-Path -LiteralPath $CancelPath){throw [OperationCanceledException]::new('Cancelled before local submit.')}
 Add-Type -AssemblyName System.Net.Http
 $handler=New-Object Net.Http.HttpClientHandler;$handler.AllowAutoRedirect=$false;$handler.UseCookies=$false;$handler.UseProxy=$false
 $client=New-Object Net.Http.HttpClient($handler);$client.Timeout=[TimeSpan]::FromSeconds(30);$client.MaxResponseContentBufferSize=1048576
 try{
  $body=@{prompt=$graph;client_id=$Job.job_id}|ConvertTo-Json -Depth 20 -Compress
  $content=New-Object Net.Http.StringContent($body,[Text.Encoding]::UTF8,'application/json')
  try{$response=$client.PostAsync('http://127.0.0.1:8188/prompt',$content).GetAwaiter().GetResult();try{if(!$response.IsSuccessStatusCode){throw 'Comfy workflow rejected'};$reply=$response.Content.ReadAsStringAsync().GetAwaiter().GetResult()|ConvertFrom-Json}finally{$response.Dispose()}}finally{$content.Dispose()}
  $id=[string]$reply.prompt_id;if($id-cnotmatch'^[0-9a-f-]{36}$'){throw 'Invalid Comfy request identity.'}
  $deadline=[DateTime]::UtcNow.AddMinutes(30)
  while([DateTime]::UtcNow-lt$deadline){
   if(Test-Path -LiteralPath $CancelPath){
    # Delete only own queued request. Never interrupt a running/shared renderer globally.
    $cancelBody=New-Object Net.Http.StringContent((@{delete=@($id)}|ConvertTo-Json),[Text.Encoding]::UTF8,'application/json')
    try{$r=$client.PostAsync('http://127.0.0.1:8188/queue',$cancelBody).GetAwaiter().GetResult();$r.Dispose()}finally{$cancelBody.Dispose()}
    throw [OperationCanceledException]::new('Cancelled; running own computation may finish but will not be imported.')
   }
   $response=$client.GetAsync('http://127.0.0.1:8188/history/'+$id).GetAwaiter().GetResult()
   try{if(!$response.IsSuccessStatusCode){throw 'Comfy history failed'};$history=$response.Content.ReadAsStringAsync().GetAwaiter().GetResult()|ConvertFrom-Json}finally{$response.Dispose()}
   $property=$history.PSObject.Properties[$id]
   if($null-ne$property){$entry=$property.Value;if($entry.status.status_str-eq'error'){throw 'Comfy execution failed'};if($entry.status.completed){break}}
   Start-Sleep -Milliseconds 500
  }
  if($null-eq$property-or!$entry.status.completed){throw 'Comfy result timed out; no automatic retry.'}
  $images=@($entry.outputs.'12'.images);if($images.Count-ne1){throw 'Unexpected local output count.'}
  $image=$images[0];$leaf=[string]$image.filename
  if([IO.Path]::GetFileName($leaf)-cne$leaf-or!$leaf.StartsWith($Job.job_id+'_')-or$image.subfolder-cne'Forge'-or$image.type-cne'output'){throw 'Local output identity/path mismatch.'}
  $outputRoot='CI_UNCONFIGURED/runtime-0'
  $file=Join-Path (Join-Path $outputRoot 'Forge') $leaf
  $info=Get-Item -LiteralPath $file;if($info.Attributes-band[IO.FileAttributes]::ReparsePoint-or$info.Length-gt16777216){throw 'Unsafe local image file.'}
  [byte[]]$bytes=[IO.File]::ReadAllBytes($file)
  $png=Test-ForgeLocalDraftPngBytes $bytes 512 512;if(!$png.ok){throw 'Invalid local draft image.'}
  return [pscustomobject]@{request_id=$id;submitted_prompt_sha256=(Get-ForgeBriefSha256 ([pscustomobject]@{text=$text}));submitted_brief_sha256=$Job.brief_sha256;created=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds();background='opaque';output_format='png';quality='draft';size='512x512';usage=[pscustomobject]@{billable=$false;scope='loopback'};data=@([pscustomobject]@{b64_json=[Convert]::ToBase64String($bytes);revised_prompt=''})}
 }finally{$client.Dispose()}
}

function Set-ForgeLocalFluxConfiguration {
    throw (New-LocalGenerationUnavailableError 'local_provider_configuration')
    if($script:Busy){return}
    if(-not(Confirm 'Use local ComfyUI FLUX for an RGB512px preview per explicit approved request? No paid API. This does not approve a brief or start generation.')){return}
    $cfg=[ordered]@{schema='forge.local_generation_provider_config.v3';provider_key='local_comfy_flux2_klein_4b';enabled=$true;profile_key='smoke';model='flux-2-klein-4b';size='512x512';quality='draft';background='opaque';output_format='png';output_count=1;updated_at=[DateTime]::UtcNow.ToString('o')}
    if(Test-Path -LiteralPath $script:ProviderConfigPath){Copy-Item -LiteralPath $script:ProviderConfigPath -Destination ($script:ProviderConfigPath+'.before-local-flux-'+[DateTime]::UtcNow.ToString('yyyyMMddHHmmss'))}
    $temp=$script:ProviderConfigPath+'.tmp-'+[Guid]::NewGuid().ToString('N');[IO.File]::WriteAllText($temp,($cfg|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)));Move-Item -LiteralPath $temp -Destination $script:ProviderConfigPath -Force
    $StatusText.Text='Local FLUX selected. RGB preview only. Full brief approval and Generate confirmation remain separate.'
    Update-AcceptanceControls
}
