# Merch Forge · backup and restore of the owner's local data
# One ZIP with drafts, decisions, artwork, checks, packages, receipts, sales, Amazon profile and generation results.
# Never included: the saved workspace access key, image-provider secrets/config, logs and caches.
# Restore first saves the current data to backups\before-restore-*.zip, verifies every file's SHA-256, moves
# absolute paths to this computer's data folder and writes the state through the normal locked LocalCore writer.

$script:BackupIncludeDirs  = @('local-core-v1','channel-profiles','generation-v1')
$script:BackupIncludeFiles = @('ui-locale.txt','queue-snapshot.json')
$script:BackupLastSkipped = 0
$script:BackupChanged = $false
$script:DataRestoreRecoveryOnly = $false
$script:DataRestoreDisabledControls = @()

function Register-DataBackupUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{ 'backup.title'='Save a copy of Merch Forge data'; 'backup.auto.last'='Automatic copy once a day: last {0}, {1} kept in {2}'; 'backup.auto.failed'='The automatic copy did not work: {0}'; 'backup.auto.none'='Automatic copy once a day: the first one is made shortly after start.'; 'backup.title.restore'='Restore Merch Forge data from a copy'; 'backup.saved'='Copy saved: {0} files in {1}.'; 'backup.restored'='Restored {0} files from the copy. Your previous data was saved to {1}.'; 'backup.confirm'='Replace your current Merch Forge data with the copy from {0} ({1} files)? Your current data will be saved first.'; 'backup.bad'='This file is not a Merch Forge data copy, or it is damaged: {0}'; 'backup.dirty'='Save or discard your unsaved edits first.'; 'backup.newer'='This copy was made by a newer Merch Forge ({0}). Update Merch Forge first.'; 'backup.rolledback'='The copy could not be restored, so your previous data was put back. Reason: {0}'; 'backup.partial'='The copy could not be restored and your previous data could not be put back automatically. Your previous data is saved in {1}. Reason: {0}'; 'backup.skipped'=' Not included (unusual file names): {0}.'; 'backup.inuse'='A file is open in another program: {0}. Close it and try again.'; 'backup.autobusy'='An automatic copy is being made right now. Try again in a minute.'; 'backup.aside'=' Files that were not in the copy were moved to {0}.' }
        ru=@{ 'backup.title'='Сохранить копию данных Merch Forge'; 'backup.auto.last'='Автокопия раз в день: последняя {0}, хранится {1} в {2}'; 'backup.auto.failed'='Автокопия не получилась: {0}'; 'backup.auto.none'='Автокопия раз в день: первая будет сделана вскоре после запуска.'; 'backup.title.restore'='Восстановить данные Merch Forge из копии'; 'backup.saved'='Копия сохранена: файлов {0}, {1}.'; 'backup.restored'='Восстановлено файлов из копии: {0}. Прежние данные сохранены в {1}.'; 'backup.confirm'='Заменить текущие данные Merch Forge копией от {0} (файлов: {1})? Сначала текущие данные будут сохранены.'; 'backup.bad'='Это не копия данных Merch Forge или файл повреждён: {0}'; 'backup.dirty'='Сначала сохраните или отмените несохранённые правки.'; 'backup.newer'='Эта копия сделана более новой версией Merch Forge ({0}). Сначала обновите Merch Forge.'; 'backup.rolledback'='Копию восстановить не удалось, поэтому прежние данные возвращены на место. Причина: {0}'; 'backup.partial'='Копию восстановить не удалось, и прежние данные не удалось вернуть автоматически. Они сохранены в {1}. Причина: {0}'; 'backup.skipped'=' Не вошли (необычные имена файлов): {0}.'; 'backup.inuse'='Файл открыт в другой программе: {0}. Закройте его и повторите.'; 'backup.autobusy'='Сейчас делается автокопия. Повторите через минуту.'; 'backup.aside'=' Файлы, которых не было в копии, перенесены в {0}.' }
        es=@{ 'backup.title'='Guardar una copia de los datos de Merch Forge'; 'backup.auto.last'='Copia automática una vez al día: la última {0}, se guardan {1} en {2}'; 'backup.auto.failed'='La copia automática no funcionó: {0}'; 'backup.auto.none'='Copia automática una vez al día: la primera se hace poco después de iniciar.'; 'backup.title.restore'='Restaurar datos de Merch Forge desde una copia'; 'backup.saved'='Copia guardada: {0} archivos en {1}.'; 'backup.restored'='Se restauraron {0} archivos desde la copia. Tus datos anteriores se guardaron en {1}.'; 'backup.confirm'='¿Reemplazar tus datos actuales de Merch Forge por la copia del {0} ({1} archivos)? Primero se guardarán tus datos actuales.'; 'backup.bad'='Este archivo no es una copia de datos de Merch Forge o está dañado: {0}'; 'backup.dirty'='Primero guarda o descarta las ediciones sin guardar.'; 'backup.newer'='Esta copia la hizo una versión más nueva de Merch Forge ({0}). Actualiza Merch Forge primero.'; 'backup.rolledback'='No se pudo restaurar la copia, así que se volvieron a poner tus datos anteriores. Motivo: {0}'; 'backup.partial'='No se pudo restaurar la copia ni volver a poner tus datos anteriores automáticamente. Están guardados en {1}. Motivo: {0}'; 'backup.skipped'=' No incluidos (nombres de archivo inusuales): {0}.'; 'backup.inuse'='Un archivo está abierto en otro programa: {0}. Ciérralo e inténtalo de nuevo.'; 'backup.autobusy'='Se está haciendo una copia automática. Inténtalo de nuevo en un minuto.'; 'backup.aside'=' Los archivos que no estaban en la copia se movieron a {0}.' }
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
    # Enumeration failures and redirected paths fail closed; unusual names retain the existing explicit skipped count.
    $out=New-Object Collections.Generic.List[string];$skipped=0;$rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\','/')
    foreach($dirName in $script:BackupIncludeDirs){
        $dir=Join-Path $Root $dirName;if(!(Test-Path -LiteralPath $dir)){continue}
        $pending=New-Object Collections.Stack;$pending.Push((Get-Item -LiteralPath $dir -Force -ErrorAction Stop))
        while($pending.Count){
            $item=$pending.Pop()
            if($item.Attributes-band[IO.FileAttributes]::ReparsePoint){throw ('Redirected backup path was preserved, not followed: '+$item.FullName)}
            if($item.PSIsContainer){foreach($child in @(Get-ChildItem -LiteralPath $item.FullName -Force -ErrorAction Stop)){$pending.Push($child)};continue}
            if($item.Name-ceq'restore-transaction.json'-or$item.Name-like'*.lock'-or$item.Name-match'\.tmp[\.\-]'-or$item.Name-like'MerchForge-data-*.zip'){continue}
            $rel=$item.FullName.Substring($rootFull.Length+1).Replace('\','/')
            if(!(Test-BackupRelativePath $rel)){$skipped++;continue};$out.Add($rel)
        }
    }
    foreach($name in $script:BackupIncludeFiles){
        $path=Join-Path $Root $name;if(!(Test-Path -LiteralPath $path)){continue};$item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
        if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw ('Backup input is not an ordinary file: '+$path)};$out.Add($name)
    }
    $script:BackupLastSkipped=$skipped;return @($out|Sort-Object)
}
function Test-BackupRelativePath([string]$Rel) {
    # Plain names only: no '..', drive letters, alternate streams, 8.3 aliases (~) or names Windows silently trims (trailing dot/space).
    if([string]::IsNullOrWhiteSpace($Rel) -or $Rel.StartsWith('/') -or $Rel.StartsWith('\')){return $false}
    $segs=@($Rel -split '[\\/]')
    foreach($s in $segs){ if($s -eq '' -or $s -eq '.' -or $s -eq '..' -or $s -notmatch '^[\w .()\-+,]+$' -or $s.EndsWith('.') -or $s.EndsWith(' ') -or $s.StartsWith(' ')){ return $false } }
    if($segs.Count -eq 1){ return ($script:BackupIncludeFiles -contains $Rel) }
    return ($script:BackupIncludeDirs -contains $segs[0])
}
function Enter-BackupStateLock([string]$Root,[IO.FileStream]$MutationLock=$null) {
    # The auto-copy helper deliberately imports no LocalCore initializers; use the exact same root-scoped lock file.
    $core=Join-Path $Root 'local-core-v1';$path=[IO.Path]::GetFullPath((Join-Path $core 'state-mutation.lock'))
    if($null-ne$MutationLock){if(!$MutationLock.CanWrite-or[IO.Path]::GetFullPath($MutationLock.Name)-ine$path){throw 'Backup capture requires the matching workspace mutation lock.'};return $MutationLock}
    Ensure-Dir $core
    try{return [IO.File]::Open($path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}catch{throw 'Local Forge data is being updated. No partial data copy was published; wait and try again.'}
}
function Copy-FileIntoZipEntry([string]$Path,$Zip,[string]$EntryName,[IO.Stream]$SourceStream=$null) {
    $sha=[Security.Cryptography.SHA256]::Create();$buf=New-Object byte[] 1048576;$total=[int64]0;$src=$SourceStream;$owns=($null-eq$src)
    try {
        if($owns){try{$src=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)}catch{throw ('Backup input disappeared or is in use; the incomplete copy was not published: '+$Path)}}
        $src.Position=0;$entry=$Zip.CreateEntry($EntryName,[IO.Compression.CompressionLevel]::Optimal);$dst=$entry.Open()
        try{while(($n=$src.Read($buf,0,$buf.Length))-gt0){$null=$sha.TransformBlock($buf,0,$n,$null,0);$dst.Write($buf,0,$n);$total+=$n}}finally{$dst.Dispose()}
        $null=$sha.TransformFinalBlock($buf,0,0)
        return [pscustomobject]@{sha256=([BitConverter]::ToString($sha.Hash)).Replace('-','').ToLowerInvariant();size_bytes=$total}
    }finally{if($owns-and$null-ne$src){$src.Dispose()};$sha.Dispose()}
}
function New-ForgeDataBackup([string]$Root,[string]$ZipPath,[IO.FileStream]$MutationLock=$null,[bool]$RecoveryPreimage=$false) {
    Add-Type -AssemblyName System.IO.Compression,System.IO.Compression.FileSystem
    $ownsLock=($null-eq$MutationLock);$stateLock=$null;$handles=@{};$tmp=$ZipPath+'.tmp.'+[Guid]::NewGuid().ToString('N');$tmpOwned=$false
    try {
        if($RecoveryPreimage-and$ownsLock){throw 'A recovery preimage must be captured inside the existing restore transaction.'}
        $stateLock=Enter-BackupStateLock $Root $MutationLock
        if((Test-Path -LiteralPath (Join-Path $Root 'local-core-v1\restore-transaction.json'))-and-not$RecoveryPreimage){throw 'A data restore is incomplete. Use My data > Restore with a verified copy; do not export a mixed workspace as a normal backup.'}
        $files=@(Get-BackupRelativeFiles $Root);$skipped=[int]$script:BackupLastSkipped
        foreach($rel in $files){
            $path=Join-Path $Root ($rel.Replace('/','\'))
            if([IO.Path]::GetFullPath($path)-ieq[IO.Path]::GetFullPath($ZipPath)){throw 'The output archive is also a captured input; select a different backup destination.'}
            try{$handles[$rel]=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)}catch{throw ('Backup input disappeared or is open for writing. No incomplete copy was published: '+$rel)}
        }
        # Every included file is now simultaneously held against writes/replacement on Windows.
        if(($files-join"`n")-cne(@(Get-BackupRelativeFiles $Root)-join"`n")-or$skipped-ne$script:BackupLastSkipped){throw 'The data file inventory changed during capture. No copy was published.'}
        if(-not $RecoveryPreimage){if(!$handles.ContainsKey('local-core-v1/state.json')){throw 'A normal data backup requires a valid primary state; no copy was published.'};$null=Read-ForgeStateFileSnapshot (Join-Path $Root 'local-core-v1\state.json') $true}
        $appVersion='';try{$appVersion=[string]$script:AppVersion}catch{};$entries=@()
        $fs=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$tmpOwned=$true
        try{
            $zip=New-Object IO.Compression.ZipArchive($fs,[IO.Compression.ZipArchiveMode]::Create,$true)
            try{
                foreach($rel in $files){$h=Copy-FileIntoZipEntry (Join-Path $Root ($rel.Replace('/','\'))) $zip ('data/'+$rel) $handles[$rel];if($null-eq$h){throw ('Backup input was not copied: '+$rel)};$entries+=[ordered]@{path=$rel;sha256=$h.sha256;size_bytes=$h.size_bytes}}
                if(($files-join"`n")-cne(@(Get-BackupRelativeFiles $Root)-join"`n")-or$skipped-ne$script:BackupLastSkipped){throw 'The data file inventory changed before snapshot completion. No copy was published.'}
                $manifest=[ordered]@{schema='forge.data_backup.v1';created_at=[DateTime]::UtcNow.ToString('o');app_version=$appVersion;state_schema='forge.local_core.v2';state_root=[IO.Path]::GetFullPath($Root).TrimEnd('\','/');consistency=$(if($RecoveryPreimage){'recovery_preimage_not_a_consistent_workspace'}else{'locked_snapshot_v1'});file_count=$entries.Count;skipped_unsafe_names=$skipped;files=$entries;not_included=@('owner.key','provider-secrets','provider-config.json','logs','caches')}
                $entry=$zip.CreateEntry('backup-manifest.json');$writer=New-Object IO.StreamWriter($entry.Open(),(New-Object Text.UTF8Encoding($false)))
                try{$writer.Write(($manifest|ConvertTo-Json -Depth 6))}finally{$writer.Dispose()}
            }finally{$zip.Dispose()}
            $fs.Flush($true)
        }finally{$fs.Dispose()}
        if(Test-Path -LiteralPath $ZipPath){[IO.File]::Replace($tmp,$ZipPath,($ZipPath+'.previous.'+[guid]::NewGuid().ToString('N')),$true)}else{[IO.File]::Move($tmp,$ZipPath)};$tmpOwned=$false
        return [pscustomobject]@{path=$ZipPath;file_count=$entries.Count;skipped=$skipped;recovery_preimage=$RecoveryPreimage}
    }finally{
        foreach($stream in @($handles.Values)){try{$stream.Dispose()}catch{}}
        if($tmpOwned-and(Test-Path -LiteralPath $tmp)){Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue}
        if($ownsLock-and$null-ne$stateLock){$stateLock.Dispose()}
    }
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
function Get-BackupStreamHash([IO.Stream]$Stream) {
    $position=$Stream.Position;$sha=[Security.Cryptography.SHA256]::Create()
    try{$Stream.Position=0;return ([BitConverter]::ToString($sha.ComputeHash($Stream))).Replace('-','').ToLowerInvariant()}finally{$Stream.Position=$position;$sha.Dispose()}
}
function Write-BackupStreamFromFile([IO.Stream]$Destination,[string]$Source) {
    $inputFile=[IO.File]::Open($Source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try{$Destination.Position=0;$inputFile.CopyTo($Destination);$Destination.SetLength($Destination.Position);$Destination.Flush($true)}finally{$inputFile.Dispose()}
}
function Convert-BackupStatePaths($State,[string]$OldRoot,[string]$NewRoot) {
    # Only live file-location fields move. Historical evidence, receipts, hashes and arbitrary JSON strings remain exact.
    if([string]::IsNullOrWhiteSpace($OldRoot)-or$OldRoot-ieq$NewRoot){return}
    $prefix=$OldRoot.TrimEnd('\','/')+'\';$replacement=$NewRoot.TrimEnd('\','/')+'\'
    foreach($concept in @($State.concepts)){
        foreach($item in @(Get-PropertyValue $concept 'artwork')){
            $path=[string](Get-PropertyValue $item 'local_file_path')
            if($path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){Add-OrSetProperty $item 'local_file_path' ($replacement+$path.Substring($prefix.Length))}
        }
        $acceptance=Get-PropertyValue $concept 'active_acceptance';$path=[string](Get-PropertyValue $acceptance 'local_file_path')
        if($path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){Add-OrSetProperty $acceptance 'local_file_path' ($replacement+$path.Substring($prefix.Length))}
        foreach($item in @(Get-PropertyValue $concept 'packages')){
            foreach($field in @('path','publication_receipt_template')){
                $path=[string](Get-PropertyValue $item $field)
                if($path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){Add-OrSetProperty $item $field ($replacement+$path.Substring($prefix.Length))}
            }
        }
    }
}
function Write-BackupDurableText([string]$Path,[string]$Text) {
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes($Text)
    $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function Restore-BackupPriorMarker([string]$Path,[string]$OwnedSha,[string]$PreviousSha,[string]$Transaction) {
    if($PreviousSha-ceq'missing'){Remove-BackupOwnedMarker $Path $OwnedSha;return}
    $previous=Join-Path $Transaction 'previous-marker.json'
    if((Get-LocalCoreRestoreFileFence $Path)-cne$OwnedSha-or(Get-LocalCoreRestoreFileFence $previous)-cne$PreviousSha){throw 'Recovery marker ownership changed. Existing recovery records were retained.'}
    $temporary=Join-Path $Transaction ('marker.rollback.'+[guid]::NewGuid().ToString('N')+'.json')
    [IO.File]::Copy($previous,$temporary,$false)
    if((Get-FileSha256Hex $temporary)-cne$PreviousSha){throw 'Prior recovery marker copy failed verification.'}
    [IO.File]::Replace($temporary,$Path,(Join-Path $Transaction 'rolled-back-marker.json'),$true)
    if((Get-LocalCoreRestoreFileFence $Path)-cne$PreviousSha){throw 'Prior recovery marker could not be verified.'}
}
function Remove-BackupOwnedMarker([string]$Path,[string]$Sha) {
    if((Get-LocalCoreRestoreFileFence $Path)-cne$Sha){throw 'The restore marker changed. Recovery records were retained; use My data > Restore with a verified copy.'}
    Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
}
function Install-BackupStage($Manifest,[string]$Stage,[string]$Root,[IO.FileStream]$MutationLock=$null,[string]$PreviousBackup='',[string]$ExpectedPendingMarkerSha='missing') {
    $ownsLock=($null-eq$MutationLock);$handles=@{};$rows=New-Object Collections.Generic.List[object]
    $marker=Join-Path $script:LocalCoreRoot 'restore-transaction.json';$markerSha='';$transaction='';$restoreContext=$null;$committed=$false
    try {
        if($ownsLock){$MutationLock=Enter-LocalCoreMutationLock}else{Assert-LocalCoreMutationLock $MutationLock}
        if([IO.Path]::GetFullPath((Join-Path $Root 'local-core-v1')).TrimEnd('\','/')-ine[IO.Path]::GetFullPath($script:LocalCoreRoot).TrimEnd('\','/')){throw 'The restore destination does not match the locked local workspace.'}
        if((Get-LocalCoreRestoreFileFence $marker)-cne$ExpectedPendingMarkerSha){throw 'The pending restore record changed; no current files were replaced.'}
        $files=@(@(Get-PropertyValue $Manifest 'files')|ForEach-Object{[string](Get-PropertyValue $_ 'path')})
        if($files-notcontains'local-core-v1/state.json'){throw 'The data copy has no primary state; no live files were changed.'}
        $stateSource=Join-Path $Stage 'local-core-v1\state.json';$st=Read-LocalCoreStateCandidate $stateSource
        if($null-eq$st){throw 'The data copy has no valid primary state; no live files were changed.'}
        Convert-BackupStatePaths $st ([string](Get-PropertyValue $Manifest 'state_root')) $Root
        $cur=$null
        try{$cur=Read-LocalCoreStateCandidate $script:LocalCoreStatePath}catch{if($_.Exception.Message-like'Unsupported local-core state schema*'){throw}}
        if($null-ne$cur){Add-OrSetProperty $st 'state_revision' ([int64](Get-PropertyValue $cur 'state_revision'));Add-OrSetProperty $st 'last_write_id' ([string](Get-PropertyValue $cur 'last_write_id'))}
        $restoreContext=New-LocalCoreRestoreContext $st $MutationLock
        $rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\','/')+'\';$statePaths=Get-BackupStateFullPaths $Root
        $targets=@{};$seen=@{}
        foreach($entry in @(Get-PropertyValue $Manifest 'files')){
            $rel=[string](Get-PropertyValue $entry 'path')
            if(!(Test-BackupRelativePath $rel)-or$seen.ContainsKey($rel)-or$rel-ieq'local-core-v1/restore-transaction.json'){throw ('Unsafe or duplicate restore path: '+$rel)};$seen[$rel]=$true
            $src=Join-Path $Stage ($rel.Replace('/','\'));$want=([string](Get-PropertyValue $entry 'sha256')).ToLowerInvariant()
            if($want-notmatch'^[0-9a-f]{64}$'-or(Get-FileSha256Hex $src)-cne$want){throw ('The verified restore stage changed: '+$rel)}
            $dst=[IO.Path]::GetFullPath((Join-Path $Root ($rel.Replace('/','\'))))
            if(!$dst.StartsWith($rootFull,[StringComparison]::OrdinalIgnoreCase)){throw ('Unsafe restore path: '+$rel)}
            if($statePaths-contains$dst.ToLowerInvariant()-or$rel-match'^local-core-v1/state(?:\.lastgood)?\.json\.(?:restore-before|restore-replaced|corrupt|retained)\.') {continue};$targets[$rel]=[pscustomobject]@{path=$dst;source=$src;sha=$want}
        }
        $current=@(Get-BackupRelativeFiles $Root);$all=@(@($current)+@($targets.Keys)|Sort-Object -Unique)
        $transaction=Join-Path $Root ('backups\restore-transaction-'+[guid]::NewGuid().ToString('N'));Ensure-Dir $transaction
        foreach($rel in $all){
            $dst=[IO.Path]::GetFullPath((Join-Path $Root ($rel.Replace('/','\'))));if($statePaths-contains$dst.ToLowerInvariant()-or$rel-match'^local-core-v1/state(?:\.lastgood)?\.json\.(?:restore-before|restore-replaced|corrupt|retained)\.') {continue}
            $before=Get-LocalCoreRestoreFileFence $dst;$preimage='';$target=if($targets.ContainsKey($rel)){$targets[$rel]}else{$null}
            if($before-cne'missing'){
                try{$handle=[IO.File]::Open($dst,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}catch{throw ((Get-UiText 'backup.inuse' 'A file is open in another program: {0}. Close it and try again.') -f $dst)}
                $handles[$rel]=$handle
                if((Get-BackupStreamHash $handle)-cne$before){throw ('A file changed during restore preflight: '+$rel)}
                $preimage=Join-Path $transaction ('preimages\'+$rel.Replace('/','\'));Ensure-Dir (Split-Path -Parent $preimage)
                $copy=[IO.File]::Open($preimage,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
                try{$handle.Position=0;$handle.CopyTo($copy);$copy.Flush($true)}finally{$copy.Dispose()}
                if((Get-FileSha256Hex $preimage)-cne$before){throw ('Restore preimage verification failed: '+$rel)}
            }
            $rows.Add([pscustomobject]@{relative=$rel;path=$dst;before_sha256=$before;preimage=$preimage;target_sha256=$(if($null-ne$target){$target.sha}else{'missing'});source=$(if($null-ne$target){$target.source}else{''});changed=$false;aside='';created=$false})
        }
        # All input/preimage validation precedes the marker and first live mutation. Journal survives process termination.
        Assert-LocalCoreRestoreContext $restoreContext $st $MutationLock
        $journal=[ordered]@{schema='forge.data_restore_journal.v1';root=$Root;previous_backup=$PreviousBackup;primary_before_sha256=$restoreContext.primary_sha256;backup_before_sha256=$restoreContext.backup_sha256;files=@($rows.ToArray())}
        $journalPath=Join-Path $transaction 'journal.json';Write-BackupDurableText $journalPath ($journal|ConvertTo-Json -Depth 10)
        $markerData=[ordered]@{schema='forge.data_restore_pending.v1';transaction=$transaction;journal_sha256=(Get-FileSha256Hex $journalPath);previous_backup=$PreviousBackup}
        $markerTmp=Join-Path $transaction 'marker.new.json';Write-BackupDurableText $markerTmp ($markerData|ConvertTo-Json -Depth 5);$markerSha=Get-FileSha256Hex $markerTmp
        if((Get-LocalCoreRestoreFileFence $marker)-cne$ExpectedPendingMarkerSha){throw 'The pending restore record changed before mutation; current files were preserved.'}
        if($ExpectedPendingMarkerSha-ceq'missing'){[IO.File]::Move($markerTmp,$marker)}else{[IO.File]::Replace($markerTmp,$marker,(Join-Path $transaction 'previous-marker.json'),$true)}
        Add-OrSetProperty $restoreContext 'data_restore_marker_sha256' $markerSha
        try {
            foreach($row in $rows){
                if($row.target_sha256-ceq'missing'){
                    if($row.before_sha256-ceq'missing'){continue}
                    $handles[$row.relative].Dispose();$handles.Remove($row.relative)
                    if((Get-LocalCoreRestoreFileFence $row.path)-cne$row.before_sha256){throw ('A file changed before set-aside: '+$row.relative)}
                    $row.aside=Join-Path $transaction ('set-aside\'+$row.relative.Replace('/','\'));Ensure-Dir (Split-Path -Parent $row.aside)
                    [IO.File]::Move($row.path,$row.aside);$row.changed=$true;$script:BackupChanged=$true
                    if((Get-FileSha256Hex $row.aside)-cne$row.before_sha256){throw ('Set-aside bytes changed: '+$row.relative)}
                }else{
                    if($row.before_sha256-ceq'missing'){
                        Ensure-Dir (Split-Path -Parent $row.path);$handles[$row.relative]=[IO.File]::Open($row.path,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$row.created=$true
                    }
                    $row.changed=$true;$script:BackupChanged=$true
                    Write-BackupStreamFromFile $handles[$row.relative] $row.source
                    if((Get-BackupStreamHash $handles[$row.relative])-cne$row.target_sha256){throw ('Restored file verification failed: '+$row.relative)}
                }
            }
            # The same optimistic state/context/raw-file fences still decide the commit.
            Write-LocalCoreState $st -MutationLock $MutationLock -RestoreContext $restoreContext
            if((Get-LocalCoreRestoreFileFence $script:LocalCoreStatePath)-cne[string](Get-PropertyValue $restoreContext 'planned_primary_sha256')){throw 'The restored primary outcome could not be verified.'}
            $committed=$true
        } catch {
            $cause=$_.Exception.Message;$planned=[string](Get-PropertyValue $restoreContext 'planned_primary_sha256')
            $primary=Get-LocalCoreRestoreFileFence $script:LocalCoreStatePath
            # A throw after our exact primary commit is NOT proof of rollback. Retain the committed asset/state pair.
            if($planned-and$primary-ceq$planned){$committed=$true;try{Write-AppLog 'WARN' ('Restore primary committed; postcommit work needs attention: '+$cause)}catch{}}
            else{
                if($primary-cne$restoreContext.primary_sha256-or(Get-LocalCoreRestoreFileFence $script:LocalCoreBackupPath)-cne$restoreContext.backup_sha256){throw ('Restore outcome is uncertain or another writer changed state. No rollback overwrote it. Recovery records: '+$transaction+'. Use My data > Restore with a verified copy. '+$cause)}
                $rollbackErrors=New-Object Collections.Generic.List[string]
                for($i=$rows.Count-1;$i-ge0;$i--){$row=$rows[$i];if(!$row.changed){continue}
                    try{
                        if($row.aside){
                            if((Get-LocalCoreRestoreFileFence $row.path)-cne'missing'-or(Get-LocalCoreRestoreFileFence $row.aside)-cne$row.before_sha256){throw 'Set-aside ownership changed'}
                            [IO.File]::Move($row.aside,$row.path)
                        }elseif($row.created){
                            $owned=Get-BackupStreamHash $handles[$row.relative];$handles[$row.relative].Dispose();$handles.Remove($row.relative)
                            if((Get-LocalCoreRestoreFileFence $row.path)-cne$owned){throw 'New file ownership changed'}
                            [IO.File]::Delete($row.path)
                        }else{
                            if(!$handles.ContainsKey($row.relative)-or(Get-FileSha256Hex $row.preimage)-cne$row.before_sha256){throw 'Preimage or exclusive file ownership unavailable'}
                            Write-BackupStreamFromFile $handles[$row.relative] $row.preimage
                            if((Get-BackupStreamHash $handles[$row.relative])-cne$row.before_sha256){throw 'Rollback bytes failed verification'}
                        }
                    }catch{$rollbackErrors.Add($row.relative+': '+$_.Exception.Message)}
                }
                if($rollbackErrors.Count){throw ('Restore rollback could not be completed safely. Recovery records: '+$transaction+'. Use My data > Restore with a verified copy. '+($rollbackErrors-join'; ')+'; '+$cause)}
                Restore-BackupPriorMarker $marker $markerSha $ExpectedPendingMarkerSha $transaction;$markerSha='';$script:BackupChanged=$false
                throw ('The copy could not be restored; prior files and exact prior state were put back. '+$cause)
            }
        }
        if($committed){
            foreach($row in $rows){
                $actual=if($handles.ContainsKey($row.relative)){Get-BackupStreamHash $handles[$row.relative]}else{Get-LocalCoreRestoreFileFence $row.path}
                if($actual-cne$row.target_sha256){throw ('Restored assets could not be verified after state commit. Recovery records: '+$transaction+'. Use My data > Restore with a verified copy.')}
            }
            Remove-BackupOwnedMarker $marker $markerSha;$markerSha='';return $files.Count
        }
    } finally {
        foreach($handle in @($handles.Values)){try{$handle.Dispose()}catch{}}
        if($ownsLock-and$null-ne$MutationLock){$MutationLock.Dispose()}
    }
}
function Restore-ForgeDataBackupFromPath([string]$ZipPath,[bool]$IsRollback=$false) {
    # One shared lock spans before-copy, installation, commit verification and bounded rollback. No recursive restore.
    $root=$script:StateRoot;$stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N')
    $stage=Join-Path $root ('restore-staging-'+$stamp);$before='';$script:BackupChanged=$false;$autoLock=$null;$stateLock=$null
    try {
        if($IsRollback){throw 'Recursive data restore is no longer supported; use the existing verified Restore action.'}
        Ensure-Dir (Join-Path $root 'backups')
        $deadline=[DateTime]::UtcNow.AddSeconds(20)
        while($null-eq$autoLock){try{$autoLock=[IO.File]::Open((Join-Path $root 'backups\auto-copy.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}catch{if([DateTime]::UtcNow-gt$deadline){throw (Get-UiText 'backup.autobusy' 'An automatic copy is being made right now. Try again in a minute.')};Start-Sleep -Milliseconds 500}}
        try{$m=Read-ForgeDataBackup $ZipPath $stage}catch{throw ((Get-UiText 'backup.bad' 'This file is not a Merch Forge data copy, or it is damaged: {0}')-f$_.Exception.Message)}
        if([string](Get-PropertyValue $m 'state_schema')-notin@('','forge.local_core.v2')){throw ((Get-UiText 'backup.newer' 'This copy was made by a newer Merch Forge ({0}). Update Merch Forge first.')-f[string](Get-PropertyValue $m 'app_version'))}
        if([string](Get-PropertyValue $m 'consistency')-ceq'recovery_preimage_not_a_consistent_workspace'){throw 'This ZIP preserves an interrupted mixed workspace, not a complete restore source. Select the original verified backup or the last consistent before-restore copy.'}
        $stateLock=Enter-LocalCoreMutationLock
        $marker=Join-Path $script:LocalCoreRoot 'restore-transaction.json';$pending=Get-LocalCoreRestoreFileFence $marker
        if($pending-cne'missing'){
            if(!(Confirm 'A previous data restore is incomplete. Continue with this verified copy? Current files and the previous recovery record will be preserved first; this does not publish or generate anything.' 'Recover incomplete data restore')){return [pscustomobject]@{ok=$false;files=0;previous='';cancelled=$true}}
            if((Get-LocalCoreRestoreFileFence $marker)-cne$pending){throw 'The recovery record changed during confirmation. No data was replaced.'}
        }
        $healthyCurrent=$false
        try{$null=Read-ForgeStateFileSnapshot $script:LocalCoreStatePath $true;$healthyCurrent=$true}catch{if($_.Exception.Message-like'Unsupported local-core state schema*'){throw}}
        $before=Join-Path $root ('backups\before-restore-'+$stamp+'.zip');$null=New-ForgeDataBackup $root $before -MutationLock $stateLock -RecoveryPreimage (($pending-cne'missing')-or-not$healthyCurrent)
        $n=Install-BackupStage $m $stage $root -MutationLock $stateLock -PreviousBackup $before -ExpectedPendingMarkerSha $pending
        return [pscustomobject]@{ok=$true;files=$n;previous=$before}
    } catch {
        $why=$_.Exception.Message;Show-Error $why
        return [pscustomobject]@{ok=$false;files=0;previous=$before;error=$why}
    } finally {
        if(Test-Path -LiteralPath $stage){try{Remove-Item -LiteralPath $stage -Recurse -Force}catch{}}
        if($null-ne$stateLock){$stateLock.Dispose()};if($null-ne$autoLock){$autoLock.Dispose()}
    }
}
$script:AutoDataCopyEnabled = $true
function Get-AutoDataCopyStatus {
    $dir=Join-Path $script:StateRoot 'backups'; $copies=@(Get-ChildItem -LiteralPath $dir -Filter 'auto-*.zip' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending)
    $last=$null; try{ $last=Get-Content -LiteralPath (Join-Path $dir 'auto-last.json') -Raw -Encoding UTF8 | ConvertFrom-Json }catch{}
    return [pscustomobject]@{count=$copies.Count;newest=$(if($copies.Count){$copies[0]}else{$null});last=$last;folder=$dir}
}
function Start-AutoDataCopyIfDue([double]$Hours=20) {
    # Once a day, in a hidden separate process; the window never waits for it.
    if(-not $script:AutoDataCopyEnabled){ return $false }
    try {
        $st=Get-AutoDataCopyStatus
        if($null -ne $st.newest -and ([DateTime]::UtcNow-$st.newest.LastWriteTimeUtc).TotalHours -lt $Hours){ return $false }
        $tool=[IO.Path]::GetFullPath((Join-Path $script:ModuleRoot '..\MerchForgeAutoDataCopy.ps1')); if(-not (Test-Path -LiteralPath $tool)){ return $false }
        if($PSVersionTable.PSEdition-cne'Core'-or$PSVersionTable.PSVersion-lt[version]'7.5'){throw 'Automatic backup requires the already-running PowerShell Core 7.5+ host.'}
        $ps=Join-Path $PSHOME 'pwsh.exe';if(!(Test-Path -LiteralPath $ps)){throw 'The current PowerShell host is unavailable for automatic backup.'}
        $null=Start-Process -FilePath $ps -ArgumentList @('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$tool+'"'),'-StateRoot',('"'+$script:StateRoot+'"')) -WindowStyle Hidden
        return $true
    } catch { Write-AppLog 'WARN' ('Automatic data copy could not start: '+$_.Exception.Message); return $false }
}
function Update-DataCopySurface {
    if($null -eq $DataAutoCopyText){return}
    try {
        $st=Get-AutoDataCopyStatus
        $lastAt=$null; try{ if($null -ne $st.last){ $lastAt=[DateTime]::Parse([string](Get-PropertyValue $st.last 'at'),[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime() } }catch{}
        $failedLater=($null -ne $st.last -and [string](Get-PropertyValue $st.last 'state') -eq 'failed' -and $null -ne $lastAt -and ($null -eq $st.newest -or $lastAt -gt $st.newest.LastWriteTimeUtc))
        $DataAutoCopyText.Text=if($failedLater){ (Get-UiText 'backup.auto.failed' 'The automatic copy did not work: {0}') -f [string](Get-PropertyValue $st.last 'error') }
            elseif($null -ne $st.newest){ (Get-UiText 'backup.auto.last' 'Automatic copy once a day: last {0}, {1} kept in {2}') -f $st.newest.LastWriteTime.ToString('yyyy-MM-dd HH:mm'),$st.count,$st.folder }
            else { Get-UiText 'backup.auto.none' 'Automatic copy once a day: the first one is made shortly after start.' }
    } catch {}
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
function Show-DataRestoreRecovery {
    if(!(Test-Path -LiteralPath (Join-Path $script:LocalCoreRoot 'restore-transaction.json'))){return $false}
    $wasRecovery=$script:DataRestoreRecoveryOnly;$script:DataRestoreRecoveryOnly=$true
    $LoginGrid.Visibility='Collapsed';$AppGrid.Visibility='Visible';Hide-ProductSurfaces;$HomeLandingScroll.Visibility='Visible'
    if(-not $wasRecovery){$script:DataRestoreDisabledControls=@()};$pending=New-Object Collections.Stack;$pending.Push($Window)
    while($pending.Count){
        $element=$pending.Pop()
        if(($element-is[Windows.Controls.Primitives.ButtonBase]-or$element-is[Windows.Controls.Primitives.Selector]-or$element-is[Windows.Controls.Primitives.TextBoxBase]-or$element-is[Windows.Controls.PasswordBox])-and-not[object]::ReferenceEquals($element,$DataRestoreButton)){
            if(-not $wasRecovery){$script:DataRestoreDisabledControls+=@([pscustomobject]@{control=$element;enabled=[bool]$element.IsEnabled})};$element.IsEnabled=$false
        }
        if($element-is[Windows.DependencyObject]){foreach($child in [Windows.LogicalTreeHelper]::GetChildren($element)){if($child-is[Windows.DependencyObject]){$pending.Push($child)}}}
    }
    $DataRestoreButton.IsEnabled=$true
    $StatusText.Text='Data restore is incomplete. Use My data > Restore with a verified copy. Current files and recovery records will be preserved; restarting does not clear this safeguard.'
    $DataAutoCopyText.Text='Recovery records: '+(Join-Path $script:StateRoot 'backups')
    return $true
}
function Complete-DataBackupRestore([string]$ZipPath) {
    $r=Restore-ForgeDataBackupFromPath $ZipPath
    if(-not $r.ok){$null=Show-DataRestoreRecovery;return $false}
    if($script:DataRestoreRecoveryOnly){try{foreach($entry in $script:DataRestoreDisabledControls){$entry.control.IsEnabled=$entry.enabled};$script:DataRestoreDisabledControls=@();$script:DataRestoreRecoveryOnly=$false;Initialize-LocalCore;Enter-LocalWorkbench}catch{try{Write-AppLog 'WARN' ('Data restore saved; workspace refresh needs attention: '+$_.Exception.Message)}catch{}}}
    $script:Current=$null; $script:Dirty=$false; $script:PublicationDirty=$false
    try{ Refresh-ResearchDraftQueue }catch{}
    try{ Show-ProductSection 'home' }catch{}
    $StatusText.Text=((Get-UiText 'backup.restored' 'Restored {0} files from the copy. Your previous data was saved to {1}.') -f $r.files,$r.previous)
    return $true
}
