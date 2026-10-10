# Merch Forge · backup and restore of the owner's local data
# One ZIP with drafts, decisions, artwork, checks, packages, receipts, sales, Amazon profile and generation results.
# Never included: the saved workspace access key, image-provider secrets/config, logs and caches.
# Restore first saves the current data to backups\before-restore-*.zip, verifies every file's SHA-256, moves
# absolute paths to this computer's data folder and writes the state through the normal locked LocalCore writer.

$script:BackupIncludeDirs  = @('local-core-v1','channel-profiles','generation-v1')
$script:BackupIncludeFiles = @('ui-locale.txt','queue-snapshot.json')

function Register-DataBackupUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{ 'backup.title'='Save a copy of Merch Forge data'; 'backup.title.restore'='Restore Merch Forge data from a copy'; 'backup.saved'='Copy saved: {0} files in {1}.'; 'backup.restored'='Restored {0} files from the copy. Your previous data was saved to {1}.'; 'backup.confirm'='Replace your current Merch Forge data with the copy from {0} ({1} files)? Your current data will be saved first.'; 'backup.bad'='This file is not a Merch Forge data copy, or it is damaged: {0}'; 'backup.dirty'='Save or discard your unsaved edits first.' }
        ru=@{ 'backup.title'='Сохранить копию данных Merch Forge'; 'backup.title.restore'='Восстановить данные Merch Forge из копии'; 'backup.saved'='Копия сохранена: файлов {0}, {1}.'; 'backup.restored'='Восстановлено файлов из копии: {0}. Прежние данные сохранены в {1}.'; 'backup.confirm'='Заменить текущие данные Merch Forge копией от {0} (файлов: {1})? Сначала текущие данные будут сохранены.'; 'backup.bad'='Это не копия данных Merch Forge или файл повреждён: {0}'; 'backup.dirty'='Сначала сохраните или отмените несохранённые правки.' }
        es=@{ 'backup.title'='Guardar una copia de los datos de Merch Forge'; 'backup.title.restore'='Restaurar datos de Merch Forge desde una copia'; 'backup.saved'='Copia guardada: {0} archivos en {1}.'; 'backup.restored'='Se restauraron {0} archivos desde la copia. Tus datos anteriores se guardaron en {1}.'; 'backup.confirm'='¿Reemplazar tus datos actuales de Merch Forge por la copia del {0} ({1} archivos)? Primero se guardarán tus datos actuales.'; 'backup.bad'='Este archivo no es una copia de datos de Merch Forge o está dañado: {0}'; 'backup.dirty'='Primero guarda o descarta las ediciones sin guardar.' }
    }
    foreach($loc in $texts.Keys){ if($null -eq $script:UiText[$loc]){$script:UiText[$loc]=@{}}; foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]} }
    if($null -ne $script:StaticUiTranslations){
        $static=@{
            ru=@{'Commerce workspace'='Рабочее пространство';'My data'='Мои данные';'A copy of your drafts, decisions, artwork, checks, packages and sales in one file. Access keys are not included.'='Копия черновиков, решений, макетов, проверок, пакетов и продаж в одном файле. Ключи доступа в копию не входят.';'Save a copy…'='Сохранить копию…';'Restore from a copy…'='Восстановить из копии…'}
            es=@{'Commerce workspace'='Espacio de trabajo';'My data'='Mis datos';'A copy of your drafts, decisions, artwork, checks, packages and sales in one file. Access keys are not included.'='Una copia de tus borradores, decisiones, diseños, revisiones, paquetes y ventas en un solo archivo. No incluye las claves de acceso.';'Save a copy…'='Guardar una copia…';'Restore from a copy…'='Restaurar desde una copia…'}
        }
        foreach($loc in $static.Keys){ if($null -ne $script:StaticUiTranslations[$loc]){ foreach($k in $static[$loc].Keys){ if(-not $script:StaticUiTranslations[$loc].ContainsKey($k)){$script:StaticUiTranslations[$loc][$k]=$static[$loc][$k]} } } }
    }
}

function Get-BackupRelativeFiles([string]$Root) {
    # Relative paths (with '/') of everything that belongs in a data copy.
    $out=New-Object System.Collections.Generic.List[string]
    $rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\','/')
    foreach($d in $script:BackupIncludeDirs){
        $dir=Join-Path $Root $d; if(-not (Test-Path -LiteralPath $dir -PathType Container)){continue}
        foreach($f in @(Get-ChildItem -LiteralPath $dir -Recurse -File -Force -ErrorAction SilentlyContinue)){
            if($f.Name -eq 'state-mutation.lock' -or $f.Name -match '\.tmp\.' -or $f.Name -like '*.lock'){continue}
            [void]$out.Add(($f.FullName.Substring($rootFull.Length+1)).Replace('\','/'))
        }
    }
    foreach($n in $script:BackupIncludeFiles){ if(Test-Path -LiteralPath (Join-Path $Root $n) -PathType Leaf){ [void]$out.Add($n) } }
    return @($out | Sort-Object)
}
function Test-BackupRelativePath([string]$Rel) {
    if([string]::IsNullOrWhiteSpace($Rel) -or $Rel.Contains('..') -or $Rel.Contains(':') -or $Rel.StartsWith('/') -or $Rel.StartsWith('\')){return $false}
    $top=($Rel -split '[\\/]')[0]
    return ($script:BackupIncludeDirs -contains $top -or ($script:BackupIncludeFiles -contains $Rel))
}
function New-ForgeDataBackup([string]$Root,[string]$ZipPath) {
    Add-Type -AssemblyName System.IO.Compression,System.IO.Compression.FileSystem
    $files=@(Get-BackupRelativeFiles $Root)
    $entries=@(); foreach($rel in $files){ $full=Join-Path $Root ($rel.Replace('/','\')); $entries+=[ordered]@{path=$rel;sha256=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant();size_bytes=(Get-Item -LiteralPath $full).Length} }
    $appVersion=''; try{$appVersion=[string]$script:AppVersion}catch{}
    $manifest=[ordered]@{schema='forge.data_backup.v1';created_at=[DateTime]::UtcNow.ToString('o');app_version=$appVersion;state_root=[IO.Path]::GetFullPath($Root).TrimEnd('\','/');file_count=$files.Count;files=$entries;not_included=@('owner.key','provider-secrets','provider-config.json','logs','caches')}
    $tmp=$ZipPath+'.tmp.'+[Guid]::NewGuid().ToString('N')
    $fs=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew)
    try {
        $zip=New-Object System.IO.Compression.ZipArchive($fs,[System.IO.Compression.ZipArchiveMode]::Create)
        try {
            $me=$zip.CreateEntry('backup-manifest.json'); $w=New-Object IO.StreamWriter($me.Open(),(New-Object Text.UTF8Encoding($false))); try{ $w.Write(($manifest | ConvertTo-Json -Depth 6)) } finally { $w.Dispose() }
            foreach($rel in $files){ $null=[System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip,(Join-Path $Root ($rel.Replace('/','\'))),('data/'+$rel)) }
        } finally { $zip.Dispose() }
    } finally { $fs.Dispose() }
    Move-Item -LiteralPath $tmp -Destination $ZipPath -Force
    return [pscustomobject]@{path=$ZipPath;file_count=$files.Count}
}
function Read-ForgeDataBackup([string]$ZipPath,[string]$StageDir) {
    # Extracts and verifies a copy. Throws a readable reason when anything is wrong.
    Add-Type -AssemblyName System.IO.Compression,System.IO.Compression.FileSystem
    $zip=[System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $me=$zip.GetEntry('backup-manifest.json'); if($null -eq $me){ throw 'backup-manifest.json is missing' }
        $r=New-Object IO.StreamReader($me.Open()); try{ $m=$r.ReadToEnd() | ConvertFrom-Json } finally { $r.Dispose() }
        if([string](Get-PropertyValue $m 'schema') -ne 'forge.data_backup.v1'){ throw 'unknown format' }
        $want=@{}; foreach($f in @(Get-PropertyValue $m 'files')){ $p=[string](Get-PropertyValue $f 'path'); if(-not (Test-BackupRelativePath $p)){ throw ('unsafe path '+$p) }; $want[$p]=([string](Get-PropertyValue $f 'sha256')).ToLowerInvariant() }
        if($want.Count -ne [int](Get-PropertyValue $m 'file_count')){ throw 'file count does not match' }
        Ensure-Dir $StageDir; $stageFull=[IO.Path]::GetFullPath($StageDir).TrimEnd('\')
        foreach($e in @($zip.Entries)){
            if($e.FullName -eq 'backup-manifest.json'){continue}
            if(-not $e.FullName.StartsWith('data/')){ throw ('unexpected entry '+$e.FullName) }
            $rel=$e.FullName.Substring(5); if(-not $want.ContainsKey($rel)){ throw ('unlisted file '+$rel) }
            $dest=[IO.Path]::GetFullPath((Join-Path $StageDir ($rel.Replace('/','\')))); if(-not $dest.StartsWith($stageFull+'\')){ throw ('unsafe path '+$rel) }
            Ensure-Dir (Split-Path -Parent $dest); [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e,$dest,$true)
            if((Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant() -ne $want[$rel]){ throw ('checksum mismatch '+$rel) }
            $want.Remove($rel)
        }
        if($want.Count){ throw ('missing files: '+(@($want.Keys) -join ', ')) }
        return $m
    } finally { $zip.Dispose() }
}
function Convert-BackupJsonRoot([string]$Json,[string]$OldRoot,[string]$NewRoot) {
    # Absolute paths saved on another computer (or another Windows user) point into that computer's data folder.
    if([string]::IsNullOrWhiteSpace($OldRoot) -or $OldRoot -eq $NewRoot){ return $Json }
    $oldEsc=(ConvertTo-Json $OldRoot.TrimEnd('\')).Trim('"'); $newEsc=(ConvertTo-Json $NewRoot.TrimEnd('\')).Trim('"')
    return [regex]::Replace($Json,([regex]::Escape($oldEsc)+'(?=\\\\|")'),$newEsc.Replace('$','$$'),[Text.RegularExpressions.RegexOptions]::IgnoreCase)
}
function Restore-ForgeDataBackupFromPath([string]$ZipPath) {
    # Returns @{ok; files; previous} ; shows a readable error and returns ok=$false on any problem.
    $root=$script:StateRoot; $stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
    $stage=Join-Path $root ('restore-staging-'+$stamp)
    try {
        try { $m=Read-ForgeDataBackup $ZipPath $stage } catch { throw ((Get-UiText 'backup.bad' 'This file is not a Merch Forge data copy, or it is damaged: {0}') -f $_.Exception.Message) }
        $backups=Join-Path $root 'backups'; Ensure-Dir $backups
        $before=Join-Path $backups ('before-restore-'+$stamp+'.zip'); $null=New-ForgeDataBackup $root $before
        $oldRoot=[string](Get-PropertyValue $m 'state_root'); $newRoot=[IO.Path]::GetFullPath($root).TrimEnd('\')
        $files=@(@(Get-PropertyValue $m 'files') | ForEach-Object { [string](Get-PropertyValue $_ 'path') })
        $utf8=New-Object Text.UTF8Encoding($false); $stateRel='local-core-v1/state.json'
        foreach($rel in $files){
            if($rel -in @($stateRel,'local-core-v1/state.lastgood.json')){continue}
            $src=Join-Path $stage ($rel.Replace('/','\')); $dst=Join-Path $root ($rel.Replace('/','\')); Ensure-Dir (Split-Path -Parent $dst)
            if($rel.ToLowerInvariant().EndsWith('.json')){ [IO.File]::WriteAllText($dst,(Convert-BackupJsonRoot ([IO.File]::ReadAllText($src)) $oldRoot $newRoot),$utf8) } else { Copy-Item -LiteralPath $src -Destination $dst -Force }
        }
        if($files -contains $stateRel){
            $st=(Convert-BackupJsonRoot ([IO.File]::ReadAllText((Join-Path $stage 'local-core-v1\state.json'))) $oldRoot $newRoot) | ConvertFrom-Json
            $diskRev=0; try{ $cur=Read-LocalCoreState; $diskRev=[int64](Get-PropertyValue $cur 'state_revision') }catch{}
            Add-OrSetProperty $st 'state_revision' $diskRev   # the normal writer bumps it; other windows see a newer state
            Write-LocalCoreState $st
        }
        return [pscustomobject]@{ok=$true;files=$files.Count;previous=$before}
    } catch { Show-Error $_.Exception.Message; return [pscustomobject]@{ok=$false;files=0;previous=''} }
    finally { if(Test-Path -LiteralPath $stage){ try{ Remove-Item -LiteralPath $stage -Recurse -Force }catch{} } }
}
function Invoke-DataBackupSave {
    try {
        $dlg=New-Object Microsoft.Win32.SaveFileDialog; $dlg.Title=Get-UiText 'backup.title' 'Save a copy of Merch Forge data'; $dlg.Filter='ZIP (*.zip)|*.zip'; $dlg.FileName=('MerchForge-data-{0}.zip' -f [DateTime]::Now.ToString('yyyy-MM-dd-HHmm'))
        if($dlg.ShowDialog() -ne $true){return}
        $r=New-ForgeDataBackup $script:StateRoot $dlg.FileName
        $StatusText.Text=((Get-UiText 'backup.saved' 'Copy saved: {0} files in {1}.') -f $r.file_count,$r.path)
    } catch { Show-Error $_.Exception.Message }
}
function Invoke-DataBackupRestore {
    try {
        if($script:Dirty -or $script:PublicationDirty){ Show-Error (Get-UiText 'backup.dirty' 'Save or discard your unsaved edits first.'); return }
        $dlg=New-Object Microsoft.Win32.OpenFileDialog; $dlg.Title=Get-UiText 'backup.title.restore' 'Restore Merch Forge data'; $dlg.Filter='ZIP (*.zip)|*.zip'
        if($dlg.ShowDialog() -ne $true){return}
        $when='?'; $count='?'
        try { Add-Type -AssemblyName System.IO.Compression.FileSystem; $z=[System.IO.Compression.ZipFile]::OpenRead($dlg.FileName); try{ $e=$z.GetEntry('backup-manifest.json'); if($null -ne $e){ $rd=New-Object IO.StreamReader($e.Open()); try{ $mm=$rd.ReadToEnd() | ConvertFrom-Json; $when=[string](Get-PropertyValue $mm 'created_at'); $count=[string](Get-PropertyValue $mm 'file_count') } finally { $rd.Dispose() } } } finally { $z.Dispose() } } catch {}
        if(-not (Confirm ((Get-UiText 'backup.confirm' 'Replace your current data with the copy from {0} ({1} files)?') -f $when,$count) 'Merch Forge')){ return }
        Complete-DataBackupRestore $dlg.FileName
    } catch { Show-Error $_.Exception.Message }
}
function Complete-DataBackupRestore([string]$ZipPath) {
    $r=Restore-ForgeDataBackupFromPath $ZipPath
    if(-not $r.ok){ return $false }
    $script:Current=$null; $script:Dirty=$false; $script:PublicationDirty=$false
    try{ Refresh-ResearchDraftQueue }catch{}
    try{ Show-ProductSection 'home' }catch{}
    $StatusText.Text=((Get-UiText 'backup.restored' 'Restored {0} files from the copy. Your previous data was saved to {1}.') -f $r.files,$r.previous)
    return $true
}
