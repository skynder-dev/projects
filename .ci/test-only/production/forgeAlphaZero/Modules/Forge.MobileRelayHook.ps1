# Existing desktop integration, OFF unless the reviewed owner opt-in file exists.
# No service, scheduled task, listener, timer or window is created.
function Start-ForgeMobileSyncIfAuthorized {
 $config=Join-Path $script:StateRoot 'mobile-relay\enabled.json'
 if(!(Test-Path -LiteralPath $config -PathType Leaf)){return $false}
 if($script:Dirty-or$script:PublicationDirty){return $false}
 try{
  if((Get-Item -LiteralPath $config).Length-gt1024){return $false}
  $c=Get-Content -LiteralPath $config -Raw -Encoding UTF8|ConvertFrom-Json
  if($c.schema-cne'forge.mobile.optin.v1'-or-not($c.enabled-is[bool])-or!$c.enabled-or-not($c.supabase_reuse_explicitly_authorized-is[bool])-or!$c.supabase_reuse_explicitly_authorized){return $false}
  $package=[IO.Path]::GetFullPath((Join-Path $script:ModuleRoot '..'));$worker=Join-Path $package 'MobileControl\Start-ForgePhaseOneSync.ps1'
  if(!(Test-Path -LiteralPath $worker -PathType Leaf)-or$package.Contains('"')-or$script:StateRoot.Contains('"')){return $false}
  $exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
  $launchArguments='-STA -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$worker+'" -PackageRoot "'+$package+'" -StateRoot "'+$script:StateRoot+'" -ExternalUseAuthorized'
  # Child has a per-workspace mutex; repeated UI events cannot duplicate a running sync.
  $null=Start-Process -FilePath $exe -ArgumentList $launchArguments -WindowStyle Hidden
  return $true
 }catch{return $false}
}
