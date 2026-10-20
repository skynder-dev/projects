# Merch Forge · backup and restore of the owner's local data
# One ZIP with drafts, decisions, artwork, checks, packages, receipts, sales, Amazon profile and generation results.
# Never included: the saved workspace access key, image-provider secrets/config, logs and caches.
# Restore first saves the current data to backups\before-restore-*.zip, verifies every file's SHA-256, moves
# absolute paths to this computer's data folder and writes the state through the normal locked LocalCore writer.

$script:BackupIncludeDirs  = @('local-core-v1','channel-profiles','generation-v1','research-import-v1','research-runs-v1','niche-evidence-v1','niche-discovery-v1','public-signals-v1')
$script:BackupIncludeFiles = @('ui-locale.txt','queue-snapshot.json','queue-snapshot.previous.json')
$script:BackupLastSkipped = 0
$script:BackupChanged = $false

function Register-DataBackupUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{ 'backup.title'='Save a copy of Merch Forge data'; 'backup.auto.last'='Automatic copy once a day: last {0}, {1} kept in {2}'; 'backup.auto.failed'='The automatic copy did not work: {0}'; 'backup.auto.none'='Automatic copy once a day: the first one is made shortly after start.'; 'backup.title.restore'='Restore Merch Forge data from a copy'; 'backup.saved'='Copy saved: {0} files in {1}.'; 'backup.restored'='Restored {0} files from the copy. Your previous data was saved to {1}.'; 'backup.confirm'='Replace your current Merch Forge data with the copy from {0} ({1} files)? Your current data will be saved first.'; 'backup.bad'='This file is not a Merch Forge data copy, or it is damaged: {0}'; 'backup.dirty'='Save or discard your unsaved edits first.'; 'backup.newer'='This copy was made by a newer Merch Forge ({0}). Update Merch Forge first.'; 'backup.rolledback'='The copy could not be restored, so your previous data was put back. Reason: {0}'; 'backup.partial'='The copy could not be restored and your previous data could not be put back automatically. Your previous data is saved in {1}. Reason: {0}'; 'backup.skipped'=' Not included (unusual file names): {0}.'; 'backup.inuse'='A file is open in another program: {0}. Close it and try again.'; 'backup.autobusy'='An automatic copy is being made right now. Try again in a minute.'; 'backup.aside'=' Files that were not in the copy were moved to {0}.' }
        ru=@{ 'backup.title'='Сохранить копию данных Merch Forge'; 'backup.auto.last'='Автокопия раз в день: последняя {0}, хранится {1} в {2}'; 'backup.auto.failed'='Автокопия не получилась: {0}'; 'backup.auto.none'='Автокопия раз в день: первая будет сделана вскоре после запуска.'; 'backup.title.restore'='Восстановить данные Merch Forge из копии'; 'backup.saved'='Копия сохранена: файлов {0}, {1}.'; 'backup.restored'='Восстановлено файлов из копии: {0}. Прежние данные сохранены в {1}.'; 'backup.confirm'='Заменить текущие данные Merch Forge копией от {0} (файлов: {1})? Сначала текущие данные будут сохранены.'; 'backup.bad'='Это не копия данных Merch Forge или файл повреждён: {0}'; 'backup.dirty'='Сначала сохраните или отмените несохранённые правки.'; 'backup.newer'='Эта копия сделана более новой версией Merch Forge ({0}). Сначала обновите Merch Forge.'; 'backup.rolledback'='Копию восстановить не удалось, поэтому прежние данные возвращены на место. Причина: {0}'; 'backup.partial'='Копию восстановить не удалось, и прежние данные не удалось вернуть автоматически. Они сохранены в {1}. Причина: {0}'; 'backup.skipped'=' Не вошли (необычные имена файлов): {0}.'; 'backup.inuse'='Файл открыт в другой программе: {0}. Закройте его и повторите.'; 'backup.autobusy'='Сейчас делается автокопия. Повторите через минуту.'; 'backup.aside'=' Файлы, которых не было в копии, перенесены в {0}.' }
        es=@{ 'backup.title'='Guardar una copia de los datos de Merch Forge'; 'backup.auto.last'='Copia automática una vez al día: la última {0}, se guardan {1} en {2}'; 'backup.auto.failed'='La copia automática no funcionó: {0}'; 'backup.auto.none'='Copia automática una vez al día: la primera se hace poco después de iniciar.'; 'backup.title.restore'='Restaurar datos de Merch Forge desde una copia'; 'backup.saved'='Copia guardada: {0} archivos en {1}.'; 'backup.restored'='Se restauraron {0} archivos desde la copia. Tus datos anteriores se guardaron en {1}.'; 'backup.confirm'='¿Reemplazar tus datos actuales de Merch Forge por la copia del {0} ({1} archivos)? Primero se guardarán tus datos actuales.'; 'backup.bad'='Este archivo no es una copia de datos de Merch Forge o está dañado: {0}'; 'backup.dirty'='Primero guarda o descarta las ediciones sin guardar.'; 'backup.newer'='Esta copia la hizo una versión más nueva de Merch Forge ({0}). Actualiza Merch Forge primero.'; 'backup.rolledback'='No se pudo restaurar la copia, así que se volvieron a poner tus datos anteriores. Motivo: {0}'; 'backup.partial'='No se pudo restaurar la copia ni volver a poner tus datos anteriores automáticamente. Están guardados en {1}. Motivo: {0}'; 'backup.skipped'=' No incluidos (nombres de archivo inusuales): {0}.'; 'backup.inuse'='Un archivo está abierto en otro programa: {0}. Ciérralo e inténtalo de nuevo.'; 'backup.autobusy'='Se está haciendo una copia automática. Inténtalo de nuevo en un minuto.'; 'backup.aside'=' Los archivos que no estaban en la copia se movieron a {0}.' }
    }
    $texts.en['backup.incomplete']='The copy does not contain the main workspace state. Existing data was preserved; select a complete data copy.'
    $texts.ru['backup.incomplete']='В копии нет основного состояния рабочего пространства. Текущие данные сохранены; выберите полную копию данных.'
    $texts.es['backup.incomplete']='La copia no contiene el estado principal del espacio de trabajo. Se conservaron los datos actuales; elige una copia completa.'
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
            if($d-in@('research-import-v1','research-runs-v1','niche-evidence-v1','niche-discovery-v1','public-signals-v1')-and($f.Name-like'*.log'-or$f.Name-like'*.rss-rows.json'-or$f.Name-like'*.rss-rows.json.invalid-*'-or$f.Name-match'\.pending\.')){continue}
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
    $normalized=$Rel.Replace('\','/').ToLowerInvariant()
    if($segs[0]-in@('niche-evidence-v1','niche-discovery-v1','public-signals-v1')){return $normalized-cmatch'^(niche-(evidence|discovery)|public-signals)-v1/(latest\.sha256|[0-9a-f]{64}\.json)$'}
    if($segs[0]-ieq'research-import-v1'){return $normalized-cmatch'^research-import-v1/(active\.sha256|[0-9a-f]{64}\.source\.json|captures/[0-9a-f]{64}\.json(\.invalid\.[a-z0-9-]+)?)$'}
    if($segs[0]-ieq'research-runs-v1'){return $normalized-cmatch'^research-runs-v1/(last-completed\.path|[^/]+/(result\.json|plan\.json|planner\.(response\.json|prompt\.txt)|concept-[1-3]\.(response\.json|prompt\.txt)|source-[1-3]\.(capture|selected)\.json|cancel\.request))$'}
    if($segs.Count -eq 1){ return ($script:BackupIncludeFiles -contains $Rel) }
    return ($script:BackupIncludeDirs -contains $segs[0])
}
function Copy-FileIntoZipEntry([string]$Path,$Zip,[string]$EntryName) {
    # Hashes exactly the bytes that go into the ZIP, so a file that changes while saving can never make the copy unrestorable.
    $sha=[Security.Cryptography.SHA256]::Create(); $buf=New-Object byte[] 1048576; $total=[long]0
    $src=$null; try{ $src=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)) }catch{ $sha.Dispose(); $inner=$_.Exception; while($null -ne $inner.InnerException){ $inner=$inner.InnerException }; if($inner -is [System.IO.FileNotFoundException] -or $inner -is [System.IO.DirectoryNotFoundException]){ return $null }; throw ((Get-UiText 'backup.inuse' 'A file is open in another program: {0}. Close it and try again.') -f $Path) }
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
    if($files.Count-gt100000){throw 'The backup contains too many files for a verified restore. Existing copies were preserved.'}
    $appVersion=''; try{$appVersion=[string]$script:AppVersion}catch{}
    $tmp=$ZipPath+'.tmp.'+[Guid]::NewGuid().ToString('N'); $entries=@()
    $fs=[IO.File]::Open($tmp,[IO.FileMode]::CreateNew)
    try {
      try {
        $zip=New-Object System.IO.Compression.ZipArchive($fs,[System.IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach($rel in $files){ $h=Copy-FileIntoZipEntry (Join-Path $Root ($rel.Replace('/','\'))) $zip ('data/'+$rel); if($null -eq $h){continue}; $entries+=[ordered]@{path=$rel;sha256=$h.sha256;size_bytes=$h.size_bytes} }
            $manifest=[ordered]@{schema='forge.data_backup.v1';created_at=[DateTime]::UtcNow.ToString('o');app_version=$appVersion;state_schema='forge.local_core.v2';state_root=[IO.Path]::GetFullPath($Root).TrimEnd('\','/');file_count=$entries.Count;skipped_unsafe_names=$skipped;files=$entries;not_included=@('owner.key','provider-secrets','provider-config.json','logs','caches')}
            $manifestText=$manifest|ConvertTo-Json -Depth 6;if([Text.Encoding]::UTF8.GetByteCount($manifestText)-gt8388608){throw 'The backup manifest exceeds the verified reading limit. Existing copies were preserved.'}
            $me=$zip.CreateEntry('backup-manifest.json'); $w=New-Object IO.StreamWriter($me.Open(),(New-Object Text.UTF8Encoding($false))); try{ $w.Write($manifestText) } finally { $w.Dispose() }
        } finally { $zip.Dispose() }
      } finally { $fs.Dispose() }
    } catch { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue; throw }
    Move-Item -LiteralPath $tmp -Destination $ZipPath -Force
    return [pscustomobject]@{path=$ZipPath;file_count=$entries.Count;skipped=$skipped}
}
function Read-ForgeBackupManifest($Zip,[int]$MaxBytes=8388608) {
    $entries=@($Zip.Entries|Where-Object{$_.FullName-ieq'backup-manifest.json'})
    if($entries.Count-ne1-or$entries[0].FullName-cne'backup-manifest.json'){throw 'Exactly one backup-manifest.json is required.'}
    $entry=$entries[0];if($entry.Length-gt$MaxBytes){throw 'Backup manifest exceeds the safe reading limit.'}
    $stream=$entry.Open();$buffer=New-Object byte[] 65536;$memory=New-Object IO.MemoryStream
    try{while(($n=$stream.Read($buffer,0,$buffer.Length))-gt0){if($memory.Length+$n-gt$MaxBytes){throw 'Backup manifest exceeds the safe reading limit.'};$memory.Write($buffer,0,$n)};$bytes=$memory.ToArray()}finally{$stream.Dispose();$memory.Dispose()}
    $text=(New-Object Text.UTF8Encoding($false,$true)).GetString($bytes);if($text.Length-and$text[0]-eq[char]0xfeff){$text=$text.Substring(1)}
    $m=ConvertFrom-ForgeJsonObjectStrict $text
    if([string](Get-PropertyValue $m 'schema')-cne'forge.data_backup.v1'){throw 'Unknown backup format.'}
    $count=Get-PropertyValue $m 'file_count';$files=$null;if($null-ne$m.PSObject.Properties['files']){$files=$m.PSObject.Properties['files'].Value}
    if(($count-isnot[int]-and$count-isnot[long])-or$count-lt0-or$count-gt100000-or$files-isnot[array]-or$files.Count-ne$count){throw 'Backup file count or file list is invalid.'}
    return $m
}
function Assert-ForgeBackupWorkspaceState($Manifest) {
    $rows=@($Manifest.files|Where-Object{[string](Get-PropertyValue $_ 'path')-ireplace'\\','/'-ieq'local-core-v1/state.json'})
    if($rows.Count-ne1){throw (Get-UiText 'backup.incomplete' 'The copy does not contain the main workspace state. Existing data was preserved; select a complete data copy.')}
}
function Read-ForgeDataBackup([string]$ZipPath,[string]$StageDir) {
    Add-Type -AssemblyName System.IO.Compression,System.IO.Compression.FileSystem
    $zip=[IO.Compression.ZipFile]::OpenRead($ZipPath)
    try{
        $m=Read-ForgeBackupManifest $zip;$want=@{};$total=[decimal]0
        foreach($f in $m.files){
            if($f-isnot[pscustomobject]){throw 'Backup file metadata must be an object.'}
            $p=Get-PropertyValue $f 'path';$hash=Get-PropertyValue $f 'sha256';$size=Get-PropertyValue $f 'size_bytes'
            if($p-isnot[string]-or!(Test-BackupRelativePath $p)){throw 'Unsafe backup path.'}
            if($hash-isnot[string]-or$hash-cnotmatch'^[0-9a-fA-F]{64}$'-or($size-isnot[int]-and$size-isnot[long])-or$size-lt0){throw ('Invalid backup fingerprint or size: '+$p)}
            $key=$p.Replace('\','/').ToLowerInvariant();if($want.ContainsKey($key)){throw ('Duplicate backup path: '+$p)}
            $want[$key]=$f;$total+=[decimal]$size;if($total-gt[long]::MaxValue){throw 'Backup size exceeds the supported range.'}
        }
        $seen=@{};$plan=@()
        foreach($entry in $zip.Entries){
            if($entry.FullName-ceq'backup-manifest.json'){continue}
            if(!$entry.FullName.StartsWith('data/',[StringComparison]::Ordinal)){throw ('Unexpected backup entry: '+$entry.FullName)}
            $rel=$entry.FullName.Substring(5);if(!(Test-BackupRelativePath $rel)){throw 'Unsafe backup entry.'};$key=$rel.Replace('\','/').ToLowerInvariant()
            if($seen.ContainsKey($key)){throw ('Duplicate backup entry: '+$rel)};$seen[$key]=$true
            if(!$want.ContainsKey($key)){throw ('Unlisted backup entry: '+$rel)}
            $meta=$want[$key];if($entry.Length-ne$meta.size_bytes){throw ('Backup size mismatch: '+$rel)}
            $plan+=@([pscustomobject]@{entry=$entry;relative=$rel;meta=$meta})
        }
        if($seen.Count-ne$want.Count){throw 'Backup is missing listed files.'}
        $stageFull=[IO.Path]::GetFullPath($StageDir).TrimEnd('\');Ensure-Dir $StageDir
        foreach($item in $plan){
            $dest=[IO.Path]::GetFullPath((Join-Path $StageDir $item.relative.Replace('/','\')))
            Assert-BackupWorkspaceChild $dest $StageDir;Ensure-Dir (Split-Path -Parent $dest)
            $source=$item.entry.Open();$output=$null;$sha=[Security.Cryptography.SHA256]::Create();$buffer=New-Object byte[] 1048576;$copied=[long]0
            try{
                $output=[IO.File]::Open($dest,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
                while(($n=$source.Read($buffer,0,$buffer.Length))-gt0){if($copied-gt([long]$item.meta.size_bytes-$n)){throw ('Backup entry exceeds its declared size: '+$item.relative)};$output.Write($buffer,0,$n);$null=$sha.TransformBlock($buffer,0,$n,$buffer,0);$copied+=$n}
                $null=$sha.TransformFinalBlock((New-Object byte[] 0),0,0);$output.Flush($true)
                $hash=([BitConverter]::ToString($sha.Hash)).Replace('-','').ToLowerInvariant()
                if($copied-ne$item.meta.size_bytes-or$hash-cne$item.meta.sha256.ToLowerInvariant()){throw ('Backup checksum or size mismatch: '+$item.relative)}
            }finally{if($null-ne$output){$output.Dispose()};$source.Dispose();$sha.Dispose()}
        }
        return $m
    }finally{$zip.Dispose()}
}
function Convert-BackupJsonRoot([string]$Json,[string]$OldRoot,[string]$NewRoot) {
    # Remap filesystem metadata only. Creative text and immutable source/revision snapshots
    # must keep their exact values and hashes, even when they mention the old data folder.
    if([string]::IsNullOrWhiteSpace($OldRoot)-or$OldRoot-ceq$NewRoot){return $Json}
    $null=ConvertFrom-ForgeJsonObjectStrict $Json
    $old=$OldRoot.TrimEnd('\','/');$new=$NewRoot.TrimEnd('\','/')
    $tokens=[regex]::Matches($Json,'"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+')
    $stack=New-Object Collections.ArrayList;$edits=New-Object Collections.ArrayList
    $immutable=@('research_drafts','revisions','production_spec','generation_brief_snapshot','brief_snapshot','brief','research_packet','source_export','original_source','source_fields')
    for($i=0;$i-lt$tokens.Count;$i++){
        $token=$tokens[$i];$value=$token.Value
        if($value-eq'{'-or$value-eq'['){
            $key='';$blocked=$false;$route=@()
            if($stack.Count){$parent=$stack[$stack.Count-1];$key=if($parent.kind-ceq'{'){$parent.key}else{$parent.pathKey};$blocked=$parent.blocked-or$key-in$immutable;$route=@($parent.route);if($parent.kind-ceq'{'){$route+=@($key)}}
            [void]$stack.Add(@{kind=$value;key='';pathKey=$key;blocked=$blocked;route=$route});continue
        }
        if($value-eq'}'-or$value-eq']'){if($stack.Count){$stack.RemoveAt($stack.Count-1)};continue}
        if(!$value.StartsWith('"')-or!$stack.Count){continue}
        $frame=$stack[$stack.Count-1]
        if($i+1-lt$tokens.Count-and$tokens[$i+1].Value-eq':'){$frame.key=[string](ConvertFrom-Json $value);continue}
        $key=if($frame.kind-ceq'{'){$frame.key}else{$frame.pathKey}
        # auto_run_path is an operational link outside immutable revisions/source packets.
        $operationalRun=$frame.route.Count-eq2-and$frame.route[0]-ceq'research_drafts'-and$frame.route[1]-ceq'provenance'-and$key-ceq'auto_run_path'
        if(($frame.blocked-and!$operationalRun)-or$key-notmatch'(?i)^(path|paths|root)$|_(path|paths|root)$'){continue}
        $text=[string](ConvertFrom-Json $value)
        if(!$text.StartsWith($old,[StringComparison]::OrdinalIgnoreCase)){continue}
        if($text.Length-gt$old.Length-and$text[$old.Length]-notin@([char]'\',[char]'/')){continue}
        if($operationalRun){
            try{$ownedPrefix=[IO.Path]::GetFullPath((Join-Path $old 'research-runs-v1')).TrimEnd('\')+'\';$ownedPath=[IO.Path]::GetFullPath($text)}catch{continue}
            if(!$ownedPath.StartsWith($ownedPrefix,[StringComparison]::OrdinalIgnoreCase)){continue}
            $leaf=$ownedPath.Substring($ownedPrefix.Length)
            if(!$leaf-or$leaf-match'[\\/:]'-or$leaf-in@('.','..')){continue}
            $text=$ownedPath
        }
        $replacement=ConvertTo-Json ($new+$text.Substring($old.Length)) -Compress
        [void]$edits.Add(@{at=$token.Index;length=$token.Length;text=$replacement})
    }
    # Preserve every untouched JSON byte, including original source timestamps and escaping.
    for($i=$edits.Count-1;$i-ge0;$i--){$e=$edits[$i];$Json=$Json.Remove($e.at,$e.length).Insert($e.at,$e.text)}
    return $Json
}
function Get-BackupStateFullPaths([string]$Root) {
    return @(([IO.Path]::GetFullPath((Join-Path $Root 'local-core-v1\state.json'))).ToLowerInvariant(),([IO.Path]::GetFullPath((Join-Path $Root 'local-core-v1\state.lastgood.json'))).ToLowerInvariant())
}
function Assert-BackupWorkspaceChild([string]$Path,[string]$Root) {
    $rootFull=[IO.Path]::GetFullPath($Root).TrimEnd('\');$full=[IO.Path]::GetFullPath($Path)
    if(!$full.StartsWith($rootFull+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Restore workspace path escaped its data folder.'}
    $walk=New-Object IO.DirectoryInfo $full
    while($null-ne$walk){if(Test-Path -LiteralPath $walk.FullName){$item=Get-Item -LiteralPath $walk.FullName -Force;if($item.Attributes-band[IO.FileAttributes]::ReparsePoint){throw 'Redirected restore workspace was preserved.'}};if($walk.FullName-ieq$rootFull){return};$walk=$walk.Parent}
    throw 'Restore workspace root could not be verified.'
}
function Clear-BackupRestoreStage([string]$Stage,[string]$Root,$Manifest,[bool]$Owned) {
    if(!$Owned-or!(Test-Path -LiteralPath $Stage)){return}
    Assert-BackupWorkspaceChild $Stage $Root
    if([IO.Path]::GetFileName($Stage)-notlike'restore-staging-*'-or$null-eq$Manifest){Write-AppLog 'WARN' ('Restore stage retained for inspection: '+$Stage);return}
    $allowed=@{'state.check.json'=$true};foreach($f in $Manifest.files){$allowed[([string]$f.path).Replace('/','\').ToLowerInvariant()]=$true}
    $prefix=[IO.Path]::GetFullPath($Stage).TrimEnd('\')+'\'
    foreach($item in @(Get-ChildItem -LiteralPath $Stage -Recurse -Force)){
        Assert-BackupWorkspaceChild $item.FullName $Stage
        $rel=$item.FullName.Substring($prefix.Length).ToLowerInvariant()
        if($item.PSIsContainer){$known=@($allowed.Keys|Where-Object{$_.StartsWith($rel+'\',[StringComparison]::OrdinalIgnoreCase)}).Count-gt0}else{$known=$allowed.ContainsKey($rel)}
        if(!$known){Write-AppLog 'WARN' ('Unknown restore stage content retained: '+$Stage);return}
    }
    Remove-Item -LiteralPath ([IO.Path]::GetFullPath($Stage)) -Recurse -Force
}
function Copy-BackupStageFile([string]$Source,[string]$Destination,[string]$Relative,$Entry,[string]$OldRoot,[string]$NewRoot,[string]$Aside) {
    Assert-BackupWorkspaceChild $Destination $NewRoot
    Ensure-Dir (Split-Path -Parent $Destination)
    $pending=$Destination+'.tmp.'+[Guid]::NewGuid().ToString('N');[IO.File]::Copy($Source,$pending,$false)
    if((Get-FileSha256Hex $pending)-cne([string]$Entry.sha256).ToLowerInvariant()){throw ('Restore copy failed source checksum: '+$Relative)}
    $expected=[string]$Entry.sha256
    if($Relative.Replace('\','/').ToLowerInvariant()-ceq'research-runs-v1/last-completed.path'-and$OldRoot-ne$NewRoot){
        $oldPrefix=[IO.Path]::GetFullPath((Join-Path $OldRoot 'research-runs-v1')).TrimEnd('\')+'\';$value=[IO.Path]::GetFullPath(([IO.File]::ReadAllText($pending)).Trim())
        if(!$value.StartsWith($oldPrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Research run pointer is outside the captured research root; files retained.'}
        $tail=$value.Substring($oldPrefix.Length);if(!$tail-or$tail-match'[\\/:]'-or$tail-in@('.','..')){throw 'Research run pointer is not a direct owned run; files retained.'}
        $moved=Join-Path (Join-Path $NewRoot 'research-runs-v1') $tail;[IO.File]::WriteAllText($pending,$moved,(New-Object Text.UTF8Encoding($false)));$expected=Get-StringSha256Hex $moved
    }
    $historical=$Relative-match'(?i)\.(restore-before|restore-replaced|rollback-replaced|retained|corrupt)\.'
    $immutableEvidence=($Relative.Replace('\','/').ToLowerInvariant()-cmatch'^(local-core-v1/evidence-v1/[0-9a-f]{64}\.json|(niche-(evidence|discovery)|public-signals)-v1/[0-9a-f]{64}\.json|research-import-v1/captures/[0-9a-f]{64}\.json|research-import-v1/[0-9a-f]{64}\.(source|rss-rows)\.json|research-runs-v1/[^/]+/(source-[1-3]\.(capture|selected)|result|plan|planner\.response|concept-[1-3]\.response)\.json)$')
    if($Relative.ToLowerInvariant().EndsWith('.json')-and$OldRoot-ne$NewRoot-and!$historical-and!$immutableEvidence){
        $txt=[IO.File]::ReadAllText($pending);$moved=Convert-BackupJsonRoot $txt $OldRoot $NewRoot
        if($moved-cne$txt){[IO.File]::WriteAllText($pending,$moved,(New-Object Text.UTF8Encoding($false)));$expected=Get-StringSha256Hex $moved}
    }
    if((Get-FileSha256Hex $pending)-cne$expected){throw ('Restore staging hash mismatch: '+$Relative)}
    if(Test-Path -LiteralPath $Destination){
        if((Get-FileSha256Hex $Destination)-ceq$expected){Remove-Item -LiteralPath $pending -Force;return}
        $saved=Join-Path $Aside ('overwritten\'+$Relative.Replace('/','\'));Assert-BackupWorkspaceChild $saved $Aside;Ensure-Dir (Split-Path -Parent $saved)
        if(Test-Path -LiteralPath $saved){throw 'Existing restore recovery file was preserved.'}
        [IO.File]::Replace($pending,$Destination,$saved,$true)
    }else{[IO.File]::Move($pending,$Destination)}
    if((Get-FileSha256Hex $Destination)-cne$expected){throw ('Restored destination failed checksum: '+$Relative)}
}
function New-BackupRollbackAuthority([string]$ZipPath,[string]$Root,[IO.FileStream]$MutationLock) {
    Assert-LocalCoreMutationLock $MutationLock
    $full=[IO.Path]::GetFullPath($ZipPath);$backups=[IO.Path]::GetFullPath((Join-Path $Root 'backups'))+'\'
    if(!$full.StartsWith($backups,[StringComparison]::OrdinalIgnoreCase)-or[IO.Path]::GetFileName($full)-notlike'before-restore-*.zip'){throw 'Exact rollback requires this transaction''s before-restore copy.'}
    $primary=Get-LocalCoreRestoreFileFence $script:LocalCoreStatePath;$backup=Get-LocalCoreRestoreFileFence $script:LocalCoreBackupPath
    $zip=[IO.Compression.ZipFile]::OpenRead($full)
    try{$entry=$zip.GetEntry('backup-manifest.json');$reader=New-Object IO.StreamReader($entry.Open());try{$m=$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}}finally{$zip.Dispose()}
    foreach($pair in @(@('local-core-v1/state.json',$primary),@('local-core-v1/state.lastgood.json',$backup))){$row=@($m.files|Where-Object{$_.path-ceq$pair[0]});if(($pair[1]-ceq'missing'-and$row.Count)-or($pair[1]-cne'missing'-and($row.Count-ne1-or$row[0].sha256-cne$pair[1]))){throw 'State changed while the before-restore copy was made; no restore was started.'}}
    $a=[pscustomobject]@{schema='forge.owned_restore_rollback.v1';root=[IO.Path]::GetFullPath($Root).TrimEnd('\');archive_path=$full;archive_sha256=(Get-FileSha256Hex $full);primary_sha256=$primary;backup_sha256=$backup;restore_context=$null}
    $a.PSTypeNames.Insert(0,'Forge.OwnedRestoreRollback');return $a
}
function Assert-BackupRollbackAuthority($Authority,[string]$ZipPath,[string]$Root,[IO.FileStream]$MutationLock) {
    Assert-LocalCoreMutationLock $MutationLock
    if($null-eq$Authority-or$Authority.PSTypeNames-notcontains'Forge.OwnedRestoreRollback'-or$Authority.schema-cne'forge.owned_restore_rollback.v1'-or$Authority.root-ine[IO.Path]::GetFullPath($Root).TrimEnd('\')-or$Authority.archive_path-ine[IO.Path]::GetFullPath($ZipPath)-or$Authority.archive_sha256-cne(Get-FileSha256Hex $ZipPath)){throw 'Exact rollback does not match the owned before-restore snapshot.'}
}
function Assert-BackupRollbackStateFence($Authority) {
    $ctx=$Authority.restore_context
    $primary=@($Authority.primary_sha256);$backup=@($Authority.backup_sha256,$Authority.primary_sha256)
    if($null-ne$ctx){foreach($n in @('planned_primary_sha256','written_primary_sha256')){$v=[string](Get-PropertyValue $ctx $n);if($v){$primary+=$v}};foreach($n in @('planned_backup_sha256','written_backup_sha256')){$v=[string](Get-PropertyValue $ctx $n);if($v){$backup+=$v}}}
    if($primary-notcontains(Get-LocalCoreRestoreFileFence $script:LocalCoreStatePath)-or$backup-notcontains(Get-LocalCoreRestoreFileFence $script:LocalCoreBackupPath)){throw 'Unexpected state changes were preserved; exact rollback stopped before overwriting them.'}
}
function Restore-LocalCoreRollbackBytes([string]$Stage,$Authority,[IO.FileStream]$MutationLock) {
    Assert-LocalCoreMutationLock $MutationLock;Assert-BackupRollbackStateFence $Authority
    foreach($pair in @(@('local-core-v1\state.json',$script:LocalCoreStatePath,$Authority.primary_sha256),@('local-core-v1\state.lastgood.json',$script:LocalCoreBackupPath,$Authority.backup_sha256))){
        $source=Join-Path $Stage $pair[0];$destination=[string]$pair[1];$expected=[string]$pair[2];$current=Get-LocalCoreRestoreFileFence $destination
        if($current-ceq$expected){continue}
        $retained=$destination+'.rollback-replaced.'+[Guid]::NewGuid().ToString('N').Substring(0,16)+'.json'
        if(Test-Path -LiteralPath $retained){throw 'Existing rollback recovery file was preserved.'}
        if($expected-ceq'missing'){if(Test-Path -LiteralPath $source){throw 'Rollback source unexpectedly contains a missing state file.'};[IO.File]::Move($destination,$retained);continue}
        if((Get-LocalCoreRestoreFileFence $source)-cne$expected){throw 'Exact rollback state bytes differ from the before-restore fence.'}
        $pending=$destination+'.tmp.'+[Guid]::NewGuid().ToString('N');[IO.File]::Copy($source,$pending,$false)
        if((Get-FileSha256Hex $pending)-cne$expected){throw 'Exact rollback staging hash differs; files retained.'}
        if($current-ceq'missing'){[IO.File]::Move($pending,$destination)}else{[IO.File]::Replace($pending,$destination,$retained,$true)}
        if((Get-FileSha256Hex $destination)-cne$expected){throw 'Exact rollback destination failed verification.'}
    }
}
function Install-BackupStage($Manifest,[string]$Stage,[string]$Root,[IO.FileStream]$MutationLock=$null,$Transaction=$null,[switch]$ExactRollback) {
    # Writes a verified stage over the data folder: the state goes last, through the normal locked writer.
    # Files that are not in the copy are removed (the before-restore copy keeps them), so the result equals the copy.
    $oldRoot=[string](Get-PropertyValue $Manifest 'state_root'); $newRoot=[IO.Path]::GetFullPath($Root).TrimEnd('\'); $rootFull=$newRoot.ToLowerInvariant()+'\'
    $files=@(@(Get-PropertyValue $Manifest 'files') | ForEach-Object { [string](Get-PropertyValue $_ 'path') })
    if(!$ExactRollback){Assert-ForgeBackupWorkspaceState $Manifest}
    $statePaths=Get-BackupStateFullPaths $Root; $utf8=New-Object Text.UTF8Encoding($false)
    $stateJson=$null;$preparedState=$null;$restoreContext=$null
    if($ExactRollback){if($null-eq$Transaction-or$oldRoot-ine$newRoot){throw 'Exact rollback requires an owned snapshot from this data folder.'};Assert-BackupRollbackStateFence $Transaction}
    if(!$ExactRollback-and$files -contains 'local-core-v1/state.json'){
        $stateJson=Convert-BackupJsonRoot ([IO.File]::ReadAllText((Join-Path $Stage 'local-core-v1\state.json'))) $oldRoot $newRoot
        $tmpState=Join-Path $Stage 'state.check.json'; [IO.File]::WriteAllText($tmpState,$stateJson,$utf8)
        $preparedState=Read-LocalCoreStateCandidate $tmpState   # schema + envelope, before anything is changed
        Set-ForgeRecoveredSnapshotReview $preparedState 'data_copy_restore' (Get-FileSha256Hex (Join-Path $Stage 'local-core-v1\state.json'))
        Assert-LocalCoreMutationLock $MutationLock
        if([IO.Path]::GetFullPath((Join-Path $Root 'local-core-v1'))-ine[IO.Path]::GetFullPath($script:LocalCoreRoot)){throw 'Restore target differs from the active local-core folder.'}
        $cur=$null;try{$cur=Read-LocalCoreStateCandidate $script:LocalCoreStatePath}catch{if($_.Exception.Message-like'Unsupported local-core state schema*'){throw}}
        if($null-eq$cur){try{$cur=Read-LocalCoreStateCandidate $script:LocalCoreBackupPath}catch{if($_.Exception.Message-like'Unsupported local-core state schema*'){throw}}}
        $diskRev=0;$diskWriteId='';if($null-ne$cur){$diskRev=[int64](Get-PropertyValue $cur 'state_revision');$diskWriteId=[string](Get-PropertyValue $cur 'last_write_id')}
        Add-OrSetProperty $preparedState 'state_revision' $diskRev;Add-OrSetProperty $preparedState 'last_write_id' $diskWriteId
        $restoreContext=New-LocalCoreRestoreContext $preparedState $MutationLock
        if($null-ne$Transaction){$Transaction.restore_context=$restoreContext}
        Preserve-LocalCoreRestorePreimages $restoreContext
    }
    $keep=@{}
    foreach($rel in $files){ $dst=[IO.Path]::GetFullPath((Join-Path $Root ($rel.Replace('/','\')))); if(-not $dst.ToLowerInvariant().StartsWith($rootFull)){ throw ('unsafe path '+$rel) }; $keep[$dst.ToLowerInvariant()]=$true }
    if($null-ne$restoreContext){foreach($path in $restoreContext.preimage_paths){$keep[([IO.Path]::GetFullPath($path)).ToLowerInvariant()]=$true}}
    # Only files a data copy would contain are replaced or set aside; anything else in the folders (odd names, temp files, saved ZIPs) is left alone.
    $current=@(Get-BackupRelativeFiles $Root | ForEach-Object { [IO.Path]::GetFullPath((Join-Path $Root ($_.Replace('/','\')))) })
    $toSetAside=@($current | Where-Object { -not $keep.ContainsKey($_.ToLowerInvariant()) -and $statePaths -notcontains $_.ToLowerInvariant() })
    # Nothing is changed while any affected file is open in another program.
    foreach($pth in @(@($current | Where-Object { $keep.ContainsKey($_.ToLowerInvariant()) -and $statePaths -notcontains $_.ToLowerInvariant() })+$toSetAside)){
        try{ $h=[IO.File]::Open($pth,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None); $h.Dispose() }catch{ throw ((Get-UiText 'backup.inuse' 'A file is open in another program: {0}. Close it and try again.') -f $pth) }
    }
    $aside=Join-Path $Root ('backups\restore-replaced-'+[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N'))
    Assert-BackupWorkspaceChild $aside $Root;New-Item -ItemType Directory -Path $aside -ErrorAction Stop|Out-Null
    $script:BackupChanged=$true
    if($toSetAside.Count){
        foreach($pth in $toSetAside){ $rel=$pth.Substring($rootFull.Length); $dst=Join-Path $aside ('not-in-copy\'+$rel);Assert-BackupWorkspaceChild $dst $aside; Ensure-Dir (Split-Path -Parent $dst);[IO.File]::Move($pth,$dst) }
    }
    foreach($rel in $files){
        $dst=[IO.Path]::GetFullPath((Join-Path $Root ($rel.Replace('/','\'))))
        if($statePaths -contains $dst.ToLowerInvariant()){continue}
        $src=Join-Path $Stage ($rel.Replace('/','\'));$entry=@($Manifest.files|Where-Object{$_.path-ceq$rel})[0]
        Copy-BackupStageFile $src $dst $rel $entry $oldRoot $newRoot $aside
    }
    if($ExactRollback){Restore-LocalCoreRollbackBytes $Stage $Transaction $MutationLock}
    elseif($null -ne $stateJson){
        Write-LocalCoreState $preparedState -MutationLock $MutationLock -RestoreContext $restoreContext
    }
    return $files.Count
}
function Restore-ForgeDataBackupFromPath([string]$ZipPath,[bool]$IsRollback=$false,[IO.FileStream]$MutationLock=$null,$RollbackAuthority=$null) {
    # Returns @{ok; files; previous}. Any failure after the first change puts the before-restore copy back.
    $root=$script:StateRoot; $stamp=[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,6)
    $stage=Join-Path $root ('restore-staging-'+$stamp+'-'+[Guid]::NewGuid().ToString('N')); $before=''; $script:BackupChanged=$false;$stageOwned=$false;$m=$null
    $autoLock=$null;$stateLock=$null;$ownsStateLock=($null-eq$MutationLock);$transaction=$null
    try {
        if(-not $IsRollback){
            Ensure-Dir (Join-Path $root 'backups')
            $deadline=[DateTime]::UtcNow.AddSeconds(20)
            while($null -eq $autoLock){ try{ $autoLock=[IO.File]::Open((Join-Path $root 'backups\auto-copy.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None) }catch{ if([DateTime]::UtcNow -gt $deadline){ throw (Get-UiText 'backup.autobusy' 'An automatic copy is being made right now. Try again in a minute.') }; Start-Sleep -Milliseconds 500 } }
        }
        Assert-BackupWorkspaceChild $stage $root;New-Item -ItemType Directory -Path $stage -ErrorAction Stop|Out-Null;$stageOwned=$true
        try { $m=Read-ForgeDataBackup $ZipPath $stage } catch { throw ((Get-UiText 'backup.bad' 'This file is not a Merch Forge data copy, or it is damaged: {0}') -f $_.Exception.Message) }
        if(!$IsRollback){Assert-ForgeBackupWorkspaceState $m}
        if([string](Get-PropertyValue $m 'state_schema') -notin @('','forge.local_core.v2')){ throw ((Get-UiText 'backup.newer' 'This copy was made by a newer Merch Forge ({0}). Update Merch Forge first.') -f [string](Get-PropertyValue $m 'app_version')) }
        if($ownsStateLock){$stateLock=Enter-LocalCoreMutationLock}else{Assert-LocalCoreMutationLock $MutationLock;$stateLock=$MutationLock}
        if($IsRollback){Assert-BackupRollbackAuthority $RollbackAuthority $ZipPath $root $stateLock;$transaction=$RollbackAuthority}
        if(-not $IsRollback){
            $backups=Join-Path $root 'backups'; Ensure-Dir $backups
            $before=Join-Path $backups ('before-restore-'+$stamp+'.zip'); $null=New-ForgeDataBackup $root $before
            $transaction=New-BackupRollbackAuthority $before $root $stateLock
            foreach($old in @(Get-ChildItem -LiteralPath $backups -Filter 'before-restore-*.zip' -File | Sort-Object LastWriteTimeUtc -Descending | Select-Object -Skip 5)){ try{ Remove-Item -LiteralPath $old.FullName -Force }catch{} }
        }
        $script:BackupChanged=$false
        $n=Install-BackupStage $m $stage $root -MutationLock $stateLock -Transaction $transaction -ExactRollback:$IsRollback
        return [pscustomobject]@{ok=$true;files=$n;previous=$before}
    } catch {
        $why=$_.Exception.Message
        if($script:BackupChanged -and -not $IsRollback -and $before -and (Test-Path -LiteralPath $before)){
            $rb=Restore-ForgeDataBackupFromPath $before $true -MutationLock $stateLock -RollbackAuthority $transaction
            $why=if($rb.ok){(Get-UiText 'backup.rolledback' 'The copy could not be restored, so your previous data was put back. Reason: {0}') -f $why}else{(Get-UiText 'backup.partial' 'The copy could not be restored and your previous data could not be put back automatically. Your previous data is saved in {1}. Reason: {0}') -f $why,$before}
        }
        if(-not $IsRollback){ Show-Error $why }
        return [pscustomobject]@{ok=$false;files=0;previous=$before}
    }
    finally {try{Clear-BackupRestoreStage $stage $root $m $stageOwned}catch{try{Write-AppLog 'WARN' ('Restore stage cleanup retained files: '+$_.Exception.Message)}catch{}};if($ownsStateLock-and$null-ne$stateLock){$stateLock.Dispose()}; if($null -ne $autoLock){ $autoLock.Dispose() } }
}
$script:AutoDataCopyEnabled = $true
function Get-AutoDataCopyStatus {
    $dir=Join-Path $script:StateRoot 'backups'; $copies=@(Get-ChildItem -LiteralPath $dir -Filter 'auto-*.zip' -File -ErrorAction SilentlyContinue | Where-Object{$_.Name-cmatch'^auto-[0-9]{8}-[0-9]{6}(-[0-9a-f]{32})?\.zip$'} | Sort-Object LastWriteTimeUtc -Descending)
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
        $ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
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
function Complete-DataBackupRestore([string]$ZipPath) {
    $r=Restore-ForgeDataBackupFromPath $ZipPath
    if(-not $r.ok){ return $false }
    if($script:LocalCoreRecoveryRequired){
        # A successful, verified restore is the only path out of the recovery screen.
        Initialize-LocalCore
        Set-LocalCoreRecoveryMode $false
        Initialize-GenerationWorkerBridge
    }
    $script:Current=$null; $script:Dirty=$false; $script:PublicationDirty=$false
    try{ Refresh-ResearchDraftQueue }catch{}
    try{ Show-ProductSection 'home' }catch{}
    $StatusText.Text=((Get-UiText 'backup.restored' 'Restored {0} files from the copy. Your previous data was saved to {1}.') -f $r.files,$r.previous)
    return $true
}
