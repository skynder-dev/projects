# Merch Forge · backup and restore of the owner's local data
# One ZIP with drafts, decisions, artwork, checks, packages, receipts, sales, Amazon profile and generation results.
# Never included: the saved workspace access key, image-provider secrets/config, logs and caches.
# Restore first saves the current data to backups\before-restore-*.zip, verifies every file's SHA-256, moves
# absolute paths to this computer's data folder and writes the state through the normal locked LocalCore writer.

$script:BackupIncludeDirs  = @('local-core-v1','channel-profiles','generation-v1')
$script:BackupIncludeFiles = @('ui-locale.txt','queue-snapshot.json')
$script:BackupLastSkipped = 0

function Register-DataBackupUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{ 'backup.title'='Save a copy of Merch Forge data'; 'backup.title.restore'='Restore Merch Forge data from a copy'; 'backup.saved'='Copy saved: {0} files in {1}.'; 'backup.restored'='Restored {0} files from the copy. Your previous data was saved to {1}.'; 'backup.confirm'='Replace your current Merch Forge data with the copy from {0} ({1} files)? Your current data will be saved first.'; 'backup.bad'='This file is not a Merch Forge data copy, or it is damaged: {0}'; 'backup.dirty'='Save or discard your unsaved edits first.'; 'backup.newer'='This copy was made by a newer Merch Forge ({0}). Update Merch Forge first.'; 'backup.rolledback'='The copy could not be restored, so your previous data was put back. Reason: {0}'; 'backup.partial'='The copy could not be restored and your previous data could not be put back automatically. Your previous data is saved in {1}. Reason: {0}'; 'backup.skipped'=' Not included (unusual file names): {0}.' }
        ru=@{ 'backup.title'='Сохранить копию данных Merch Forge'; 'backup.title.restore'='Восстановить данные Merch Forge из копии'; 'backup.saved'='Копия сохранена: файлов {0}, {1}.'; 'backup.restored'='Восстановлено файлов из копии: {0}. Прежние данные сохранены в {1}.'; 'backup.confirm'='Заменить текущие данные Merch Forge копией от {0} (файлов: {1})? Сначала текущие данные будут сохранены.'; 'backup.bad'='Это не копия данных Merch Forge или файл повреждён: {0}'; 'backup.dirty'='Сначала сохраните или отмените несохранённые правки.'; 'backup.newer'='Эта копия сделана более новой версией Merch Forge ({0}). Сначала обновите Merch Forge.'; 'backup.rolledback'='Копию восстановить не удалось, поэтому прежние данные возвращены на место. Причина: {0}'; 'backup.partial'='Копию восстановить не удалось, и прежние данные не удалось вернуть автоматически. Они сохранены в {1}. Причина: {0}'; 'backup.skipped'=' Не вошли (необычные имена файлов): {0}.' }
        es=@{ 'backup.title'='Guardar una copia de los datos de Merch Forge'; 'backup.title.restore'='Restaurar datos de Merch Forge desde una copia'; 'backup.saved'='Copia guardada: {0} archivos en {1}.'; 'backup.restored'='Se restauraron {0} archivos desde la copia. Tus datos anteriores se guardaron en {1}.'; 'backup.confirm'='¿Reemplazar tus datos actuales de Merch Forge por la copia del {0} ({1} archivos)? Primero se guardarán tus datos actuales.'; 'backup.bad'='Este archivo no es una copia de datos de Merch Forge o está dañado: {0}'; 'backup.dirty'='Primero guarda o descarta las ediciones sin guardar.'; 'backup.newer'='Esta copia la hizo una versión más nueva de Merch Forge ({0}). Actualiza Merch Forge primero.'; 'backup.rolledback'='No se pudo restaurar la copia, así que se volvieron a poner tus datos anteriores. Motivo: {0}'; 'backup.partial'='No se pudo restaurar la copia ni volver a poner tus datos anteriores automáticamente. Están guardados en {1}. Motivo: {0}'; 'backup.skipped'=' No incluidos (nombres de archivo inusuales): {0}.' }
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
    # Relative paths (with '/') of everything that belongs in a data copy. Names a restore would refuse are left out (and counted).
    $out=New-Object System.Collections.Generic.List[string]; $skipped=0
    $rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\','/')
    foreach($d in $script:BackupIncludeDirs){
        $dir=Join-Path $Root $d; if(-not (Test-Path -LiteralPath $dir -PathType Container)){continue}
        foreach($f in @(Get-ChildItem -LiteralPath $dir -Recurse -File -Force -ErrorAction SilentlyContinue)){
            # locks, temp files of the app and of the generation worker, earlier data copies saved inside the data folder
            if($f.Name -like '*.lock' -or $f.Name -match '\.tmp[\.\-]' -or $f.Name -like 'MerchForge-data-*.zip'){continue}
            $rel=($f.FullName.Substring($rootFull.Length+1)).Replace('\','/')
            if(-not (Test-BackupRelativePath $rel)){ $skipped++; continue }
            [void]$out.Add($rel)
        }
    }
    foreach($n in $script:BackupIncludeFiles){ if(Test-Path -LiteralPath (Join-Path $Root $n) -PathType Leaf){ [void]$out.Add($n) } }
    $script:BackupLastSkipped=$skipped
    return @($out | Sort-Object)
}
function Test-BackupRelativePath([string]$Rel) {
    # Plain names only: no '..', drive letters, alternate streams, 8.3 aliases (~) or names Windows silently trims (trailing dot/space).
    if([string]::IsNullOrWhiteSpace($Rel) -or $Rel.StartsWith('/') -or $Rel.StartsWith('\')){return $false}
    $segs=@($Rel -split '[\\/]')
    foreach($s in $segs){ if($s -eq '' -or $s -eq '.' -or $s -eq '..' -or $s -notmatch '^[\w .()\-+,]+$' -or $s.EndsWith('.') -or $s.EndsWith(' ') -or $s.StartsWith(' ')){ return $false } }
    if($segs.Count -eq 1){ return ($script:BackupIncludeFiles -contains $Rel) }
    return ($script:BackupIncludeDirs -contains $segs[0])
}
function Copy-FileIntoZipEntry([string]$Path,$Zip,[string]$EntryName) {
    # Hashes exactly the bytes that go into the ZIP, so a file that changes while saving can never make the copy unrestorable.
    $sha=[Security.Cryptography.SHA256]::Create(); $buf=New-Object byte[] 1048576; $total=0
    $src=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
    try {
        $entry=$Zip.CreateEntry($EntryName,[System.IO.Compression.CompressionLevel]::Optimal); $dst=$entry.Open()
        try { while(($n=$src.Read($buf,0,$buf.Length)) -gt 0){ $null=$sha.TransformBlock($buf,0,$n,$null,0); $dst.Write($buf,0,$n); $total+=$n } } finally { $dst.Dispose() }
        $null=$sha.TransformFinalBlock($buf,0,0)
        return [pscustomobject]@{sha256=([BitConverter]::ToString($sha.Hash)).Replace('-','').ToLowerInvariant();size_bytes=$total}
    } finally { $src.Dispose(); $sha.Dispose() }
}
function New-ForgeDataBackup([string]$Root,[string]$ZipPath) {
    Add-Type -AssemblyName System.IO.Compression,System.IO.Compression.FileSystem
    $files=@(Get-BackupRelativeFiles $Root); $skipped=[int]$script:BackupLastSkipped
    $appVersion=''; try{$appVersion=[string]$script:AppVersion}catch{}
    $tmp=$ZipPath+'.tmp.'+[Guid]::NewGuid().ToString('N'); $entries=@()
    $fs=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew)
    try {
        $zip=New-Object System.IO.Compression.ZipArchive($fs,[System.IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach($rel in $files){ $h=Copy-FileIntoZipEntry (Join-Path $Root ($rel.Replace('/','\'))) $zip ('data/'+$rel); $entries+=[ordered]@{path=$rel;sha256=$h.sha256;size_bytes=$h.size_bytes} }
            $manifest=[ordered]@{schema='forge.data_backup.v1';created_at=[DateTime]::UtcNow.ToString('o');app_version=$appVersion;state_schema='forge.local_core.v2';state_root=[IO.Path]::GetFullPath($Root).TrimEnd('\','/');file_count=$files.Count;skipped_unsafe_names=$skipped;files=$entries;not_included=@('owner.key','provider-secrets','provider-config.json','logs','caches')}
            $me=$zip.CreateEntry('backup-manifest.json'); $w=New-Object IO.StreamWriter($me.Open(),(New-Object Text.UTF8Encoding($false))); try{ $w.Write(($manifest | ConvertTo-Json -Depth 6)) } finally { $w.Dispose() }
        } finally { $zip.Dispose() }
    } finally { $fs.Dispose() }
    Move-Item -LiteralPath $tmp -Destination $ZipPath -Force
    return [pscustomobject]@{path=$ZipPath;file_count=$files.Count;skipped=$skipped}
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
function Get-BackupStateFullPaths([string]$Root) {
    return @(([IO.Path]::GetFullPath((Join-Path $Root 'local-core-v1\state.json'))).ToLowerInvariant(),([IO.Path]::GetFullPath((Join-Path $Root 'local-core-v1\state.lastgood.json'))).ToLowerInvariant())
}
function Install-BackupStage($Manifest,[string]$Stage,[string]$Root) {
    # Writes a verified stage over the data folder: the state goes last, through the normal locked writer.
    # Files that are not in the copy are removed (the before-restore copy keeps them), so the result equals the copy.
    $oldRoot=[string](Get-PropertyValue $Manifest 'state_root'); $newRoot=[IO.Path]::GetFullPath($Root).TrimEnd('\'); $rootFull=$newRoot.ToLowerInvariant()+'\'
    $files=@(@(Get-PropertyValue $Manifest 'files') | ForEach-Object { [string](Get-PropertyValue $_ 'path') })
    $statePaths=Get-BackupStateFullPaths $Root; $utf8=New-Object Text.UTF8Encoding($false)
    $stateJson=$null
    if($files -contains 'local-core-v1/state.json'){
        $stateJson=Convert-BackupJsonRoot ([IO.File]::ReadAllText((Join-Path $Stage 'local-core-v1\state.json'))) $oldRoot $newRoot
        $tmpState=Join-Path $Stage 'state.check.json'; [IO.File]::WriteAllText($tmpState,$stateJson,$utf8)
        $null=Read-LocalCoreStateCandidate $tmpState   # schema + envelope, before anything is changed
    }
    $keep=@{}
    foreach($rel in $files){
        $dst=[IO.Path]::GetFullPath((Join-Path $Root ($rel.Replace('/','\'))))
        if(-not $dst.ToLowerInvariant().StartsWith($rootFull)){ throw ('unsafe path '+$rel) }
        $keep[$dst.ToLowerInvariant()]=$true
        if($statePaths -contains $dst.ToLowerInvariant()){continue}
        $src=Join-Path $Stage ($rel.Replace('/','\')); Ensure-Dir (Split-Path -Parent $dst)
        $done=$false
        if($rel.ToLowerInvariant().EndsWith('.json') -and $oldRoot -ne $newRoot){ $txt=[IO.File]::ReadAllText($src); $moved=Convert-BackupJsonRoot $txt $oldRoot $newRoot; if($moved -ne $txt){ [IO.File]::WriteAllText($dst,$moved,$utf8); $done=$true } }
        if(-not $done){ Copy-Item -LiteralPath $src -Destination $dst -Force }
    }
    foreach($d in $script:BackupIncludeDirs){
        $dir=Join-Path $Root $d; if(-not (Test-Path -LiteralPath $dir -PathType Container)){continue}
        foreach($f in @(Get-ChildItem -LiteralPath $dir -Recurse -File -Force -ErrorAction SilentlyContinue)){
            $full=$f.FullName.ToLowerInvariant(); if($keep.ContainsKey($full) -or $statePaths -contains $full -or $f.Name -like '*.lock'){continue}
            Remove-Item -LiteralPath $f.FullName -Force
        }
    }
    if($null -ne $stateJson){
        $st=$stateJson | ConvertFrom-Json
        $diskRev=0; try{ $cur=Read-LocalCoreState; $diskRev=[int64](Get-PropertyValue $cur 'state_revision') }catch{}
        Add-OrSetProperty $st 'state_revision' $diskRev   # the normal writer bumps it; other windows see a newer state
        Write-LocalCoreState $st
    }
    return $files.Count
}
function Restore-ForgeDataBackupFromPath([string]$ZipPath,[bool]$IsRollback=$false) {
    # Returns @{ok; files; previous}. Any failure after the first change puts the before-restore copy back.
    $root=$script:StateRoot; $stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,6)
    $stage=Join-Path $root ('restore-staging-'+$stamp); $before=''; $changed=$false
    try {
        try { $m=Read-ForgeDataBackup $ZipPath $stage } catch { throw ((Get-UiText 'backup.bad' 'This file is not a Merch Forge data copy, or it is damaged: {0}') -f $_.Exception.Message) }
        if([string](Get-PropertyValue $m 'state_schema') -notin @('','forge.local_core.v2')){ throw ((Get-UiText 'backup.newer' 'This copy was made by a newer Merch Forge ({0}). Update Merch Forge first.') -f [string](Get-PropertyValue $m 'app_version')) }
        if(-not $IsRollback){
            $backups=Join-Path $root 'backups'; Ensure-Dir $backups
            $before=Join-Path $backups ('before-restore-'+$stamp+'.zip'); $null=New-ForgeDataBackup $root $before
            foreach($old in @(Get-ChildItem -LiteralPath $backups -Filter 'before-restore-*.zip' -File | Sort-Object LastWriteTimeUtc -Descending | Select-Object -Skip 5)){ try{ Remove-Item -LiteralPath $old.FullName -Force }catch{} }
        }
        $changed=$true
        $n=Install-BackupStage $m $stage $root
        return [pscustomobject]@{ok=$true;files=$n;previous=$before}
    } catch {
        $why=$_.Exception.Message
        if($changed -and -not $IsRollback -and $before -and (Test-Path -LiteralPath $before)){
            $rb=Restore-ForgeDataBackupFromPath $before $true
            $why=if($rb.ok){(Get-UiText 'backup.rolledback' 'The copy could not be restored, so your previous data was put back. Reason: {0}') -f $why}else{(Get-UiText 'backup.partial' 'The copy could not be restored and your previous data could not be put back automatically. Your previous data is saved in {1}. Reason: {0}') -f $why,$before}
        }
        if(-not $IsRollback){ Show-Error $why }
        return [pscustomobject]@{ok=$false;files=0;previous=$before}
    }
    finally { if(Test-Path -LiteralPath $stage){ try{ Remove-Item -LiteralPath $stage -Recurse -Force }catch{} } }
}
function Invoke-DataBackupSave {
    try {
        $dlg=New-Object Microsoft.Win32.SaveFileDialog; $dlg.Title=Get-UiText 'backup.title' 'Save a copy of Merch Forge data'; $dlg.Filter='ZIP (*.zip)|*.zip'; $dlg.FileName=('MerchForge-data-{0}.zip' -f [DateTime]::Now.ToString('yyyy-MM-dd-HHmm'))
        if($dlg.ShowDialog() -ne $true){return}
        $r=New-ForgeDataBackup $script:StateRoot $dlg.FileName
        $StatusText.Text=((Get-UiText 'backup.saved' 'Copy saved: {0} files in {1}.') -f $r.file_count,$r.path)+$(if($r.skipped -gt 0){(Get-UiText 'backup.skipped' ' Not included (unusual file names): {0}.') -f $r.skipped}else{''})
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
