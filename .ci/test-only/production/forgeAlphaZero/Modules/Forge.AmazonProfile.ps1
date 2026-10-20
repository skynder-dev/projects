# Merch Forge · Amazon print profile inside the app
# Status (valid / expiring / expired / missing) and an owner form that writes the same attestation JSON the
# standalone "Import Amazon Print Profile.ps1" tool reads. The tool itself is run unchanged as a child process,
# so validation and the stored profile are exactly the ones the print checks already trust.

$script:AmazonProfileDialog = $null

function Register-AmazonProfileUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{
            'prof.none'='Not imported. Packages cannot become ready without it. Press "Fill Amazon profile…".';
            'prof.valid'='{0} × {1} px, {2} DPI · {3} / {4} · valid until {5} ({6} days left).';
            'prof.expiring'='Expires soon: {5} ({6} days left). Fill the profile again from the current Amazon template. · {0} × {1} px, {2} DPI · {3} / {4}';
            'prof.expired'='Expired on {0}. Fill the profile again from the current Amazon template.';
            'prof.invalid'='The saved profile is not valid. Fill it again.';
            'prof.imported'='Amazon print profile saved. Valid until {0}.';
            'prof.form.title'='Amazon print profile';
            'prof.form.intro'='Review the saved settings against the current downloaded Amazon template and choose that file. A PNG fills its dimensions automatically. Confirm the reviewed values to save.';
            'prof.form.market'='Marketplace'; 'prof.form.product'='Product type'; 'prof.form.file'='Amazon template file (PNG or PSD)'; 'prof.form.browse'='Choose…';
            'prof.form.key'='Template name'; 'prof.form.width'='Width, px'; 'prof.form.height'='Height, px'; 'prof.form.dpi'='DPI'; 'prof.form.days'='Valid for, days (max 120)';
            'prof.form.ref'='Amazon page you took it from'; 'prof.form.attest'='I copied these values from the current Amazon Merch template.';
            'prof.err.file'='Choose the Amazon template file.'; 'prof.err.attest'='Tick "I copied these values…" to save the profile.';
            'prof.err.size'='Width and height must be between 500 and 10000 px.'; 'prof.err.dpi'='DPI must be between 72 and 600.'; 'prof.err.days'='Valid for must be 1 to 120 days.';
            'prof.err.text'='Fill marketplace, product type and template name.'; 'prof.err.ref'='Paste the Amazon page you took the values from: an https link on merch.amazon.com, developer.amazon.com or sellercentral.amazon.com.';
            'prof.err.artwork'='This file is one of your accepted designs, not the Amazon template. Choose the template file you downloaded from Amazon.'
        }
        ru=@{
            'prof.none'='Не импортирован. Без него пакеты не станут готовыми. Нажмите «Заполнить Amazon-профиль…».';
            'prof.valid'='{0} × {1} пикс., {2} DPI · {3} / {4} · действует до {5} (осталось дней: {6}).';
            'prof.expiring'='Скоро истекает: {5} (осталось дней: {6}). Заполните профиль заново по текущему шаблону Amazon. · {0} × {1} пикс., {2} DPI · {3} / {4}';
            'prof.expired'='Истёк {0}. Заполните профиль заново по текущему шаблону Amazon.';
            'prof.invalid'='Сохранённый профиль недействителен. Заполните его заново.';
            'prof.imported'='Amazon-профиль печати сохранён. Действует до {0}.';
            'prof.form.title'='Amazon-профиль печати';
            'prof.form.intro'='Сверьте сохранённые настройки с актуальным скачанным шаблоном Amazon и выберите этот файл. Размеры PNG подставятся автоматически. Для сохранения подтвердите проверенные значения.';
            'prof.form.market'='Площадка'; 'prof.form.product'='Тип товара'; 'prof.form.file'='Файл шаблона Amazon (PNG или PSD)'; 'prof.form.browse'='Выбрать…';
            'prof.form.key'='Название шаблона'; 'prof.form.width'='Ширина, пикс.'; 'prof.form.height'='Высота, пикс.'; 'prof.form.dpi'='DPI'; 'prof.form.days'='Действует, дней (не больше 120)';
            'prof.form.ref'='Страница Amazon, откуда взяты значения'; 'prof.form.attest'='Я перенёс(ла) эти значения из текущего шаблона Amazon Merch.';
            'prof.err.file'='Выберите файл шаблона Amazon.'; 'prof.err.attest'='Поставьте галочку «Я перенёс(ла) эти значения…», чтобы сохранить профиль.';
            'prof.err.size'='Ширина и высота должны быть от 500 до 10000 пикс.'; 'prof.err.dpi'='DPI должен быть от 72 до 600.'; 'prof.err.days'='Срок действия — от 1 до 120 дней.';
            'prof.err.text'='Заполните площадку, тип товара и название шаблона.'; 'prof.err.ref'='Вставьте ссылку на страницу Amazon, откуда взяты значения: https-ссылку на merch.amazon.com, developer.amazon.com или sellercentral.amazon.com.';
            'prof.err.artwork'='Этот файл — один из ваших принятых макетов, а не шаблон Amazon. Выберите файл шаблона, скачанный с Amazon.'
        }
        es=@{
            'prof.none'='No importado. Sin él los paquetes no pueden estar listos. Pulsa "Rellenar perfil de Amazon…".';
            'prof.valid'='{0} × {1} px, {2} DPI · {3} / {4} · válido hasta {5} (quedan {6} días).';
            'prof.expiring'='Caduca pronto: {5} (quedan {6} días). Rellena el perfil otra vez con la plantilla actual de Amazon. · {0} × {1} px, {2} DPI · {3} / {4}';
            'prof.expired'='Caducó el {0}. Rellena el perfil otra vez con la plantilla actual de Amazon.';
            'prof.invalid'='El perfil guardado no es válido. Rellénalo otra vez.';
            'prof.imported'='Perfil de impresión de Amazon guardado. Válido hasta {0}.';
            'prof.form.title'='Perfil de impresión de Amazon';
            'prof.form.intro'='Revisa los valores guardados frente a la plantilla actual descargada de Amazon y elige ese archivo. Un PNG rellena sus dimensiones automáticamente. Confirma los valores revisados para guardar.';
            'prof.form.market'='Mercado'; 'prof.form.product'='Tipo de producto'; 'prof.form.file'='Archivo de plantilla de Amazon (PNG o PSD)'; 'prof.form.browse'='Elegir…';
            'prof.form.key'='Nombre de la plantilla'; 'prof.form.width'='Ancho, px'; 'prof.form.height'='Alto, px'; 'prof.form.dpi'='DPI'; 'prof.form.days'='Válido, días (máx. 120)';
            'prof.form.ref'='Página de Amazon de donde salen los valores'; 'prof.form.attest'='He copiado estos valores de la plantilla actual de Amazon Merch.';
            'prof.err.file'='Elige el archivo de plantilla de Amazon.'; 'prof.err.attest'='Marca "He copiado estos valores…" para guardar el perfil.';
            'prof.err.size'='Ancho y alto deben estar entre 500 y 10000 px.'; 'prof.err.dpi'='DPI debe estar entre 72 y 600.'; 'prof.err.days'='La validez debe ser de 1 a 120 días.';
            'prof.err.text'='Rellena mercado, tipo de producto y nombre de plantilla.'; 'prof.err.ref'='Pega la página de Amazon de donde salen los valores: un enlace https en merch.amazon.com, developer.amazon.com o sellercentral.amazon.com.';
            'prof.err.artwork'='Este archivo es uno de tus diseños aceptados, no la plantilla de Amazon. Elige el archivo de plantilla que descargaste de Amazon.'
        }
    }
    foreach($loc in $texts.Keys){ if($null -eq $script:UiText[$loc]){$script:UiText[$loc]=@{}}; foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]} }
    if($null -ne $script:StaticUiTranslations){
        $static=@{ ru=@{'Amazon print profile'='Amazon-профиль печати';'Fill Amazon profile…'='Заполнить Amazon-профиль…';'Import profile file…'='Импорт файла профиля…'}; es=@{'Amazon print profile'='Perfil de impresión de Amazon';'Fill Amazon profile…'='Rellenar perfil de Amazon…';'Import profile file…'='Importar archivo de perfil…'} }
        foreach($loc in $static.Keys){ if($null -ne $script:StaticUiTranslations[$loc]){ foreach($k in $static[$loc].Keys){ if(-not $script:StaticUiTranslations[$loc].ContainsKey($k)){$script:StaticUiTranslations[$loc][$k]=$static[$loc][$k]} } } }
    }
}

function ConvertTo-ProfileUtc($Value) {
    if($Value -is [DateTime]){ return $Value.ToUniversalTime() }
    return [DateTime]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
}
function Get-AmazonProfileStatusFrom([bool]$Exists,$ValidProfile,$RawProfile,[datetime]$NowUtc=([DateTime]::UtcNow)) {
    # Pure. state: none | valid | expiring (<= 7 days) | expired | invalid
    if(-not $Exists){ return [pscustomobject]@{state='none';args=@()} }
    if($null -ne $ValidProfile){
        $vu=$null; try{$vu=ConvertTo-ProfileUtc (Get-PropertyValue $ValidProfile 'valid_until')}catch{}
        if($null -eq $vu){ return [pscustomobject]@{state='invalid';args=@()} }
        $days=[int][Math]::Ceiling(($vu-$NowUtc).TotalDays)
        $a=@([int](Get-PropertyValue $ValidProfile 'canvas_width_px'),[int](Get-PropertyValue $ValidProfile 'canvas_height_px'),[int](Get-PropertyValue $ValidProfile 'dpi'),[string](Get-PropertyValue $ValidProfile 'marketplace'),[string](Get-PropertyValue $ValidProfile 'product_type_key'),$vu.ToString('yyyy-MM-dd'),$days)
        return [pscustomobject]@{state=$(if($days -le 7){'expiring'}else{'valid'});args=$a;upload_dimension_policy=(Get-PropertyValue $ValidProfile 'upload_dimension_policy')}
    }
    if($null -ne $RawProfile){ try{ $vu=ConvertTo-ProfileUtc (Get-PropertyValue $RawProfile 'valid_until'); if($vu -le $NowUtc){ return [pscustomobject]@{state='expired';args=@($vu.ToString('yyyy-MM-dd'))} } }catch{} }
    return [pscustomobject]@{state='invalid';args=@()}
}
function Get-AmazonProfileStatus {
    $path=Get-LocalAmazonPrintProfilePath; $exists=Test-Path -LiteralPath $path -PathType Leaf
    $valid=$null; $raw=$null
    if($exists){ try{$valid=Get-LocalAmazonPrintProfile}catch{}; if($null -eq $valid){ try{$raw=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json}catch{} } }
    return (Get-AmazonProfileStatusFrom $exists $valid $raw)
}
function Format-AmazonProfileStatus($Status) {
    $text=[string]::Format([Globalization.CultureInfo]::InvariantCulture,(Get-UiText ('prof.'+$Status.state) ''),[object[]]@($Status.args))
    if([string](Get-PropertyValue $Status 'upload_dimension_policy')-eq'flexible'){$text+=' — Recommended template canvas; uploaded dimensions are flexible. Upload constraints and exact-file print quality are checked separately.'}
    return $text
}
function Update-AmazonProfileSurface {
    if($null -eq $AmazonProfileStatusText){return}
    $st=Get-AmazonProfileStatus
    $AmazonProfileStatusText.Text=Format-AmazonProfileStatus $st
    try{ $AmazonProfileStatusText.Foreground=if($st.state -eq 'valid'){$Window.FindResource('Success')}else{$Window.FindResource('Warning')} }catch{}
}

function Invoke-AmazonProfileImporter([string]$SourcePath) {
    # Runs the unchanged standalone tool non-interactively. Returns @{ok; message}.
    $tool=[IO.Path]::GetFullPath((Join-Path $script:ModuleRoot '..\Import Amazon Print Profile.ps1'))
    $psExe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $psi=New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName=$psExe; $psi.Arguments=('-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -SourcePath "{1}" -NonInteractive' -f $tool,$SourcePath)
    $psi.UseShellExecute=$false; $psi.CreateNoWindow=$true; $psi.RedirectStandardOutput=$true; $psi.RedirectStandardError=$true
    $p=[System.Diagnostics.Process]::Start($psi)
    $errTask=$p.StandardError.ReadToEndAsync(); $outTask=$p.StandardOutput.ReadToEndAsync()
    if(-not $p.WaitForExit(120000)){ try{$p.Kill()}catch{}; return [pscustomobject]@{ok=$false;message='The profile import did not finish in time.'} }
    $p.WaitForExit(); $err=[string]$errTask.Result; $out=[string]$outTask.Result
    if($p.ExitCode -eq 0 -and $out -match 'PROFILE IMPORTED'){ return [pscustomobject]@{ok=$true;message=''} }
    $m=''; foreach($line in ($err -split "`r?`n")){ if($line -match '^PROFILE IMPORT FAIL: (.+)$'){ $m=$Matches[1].Trim() } }
    if(-not $m){ $m=('The profile import failed (exit {0}).' -f $p.ExitCode) }
    return [pscustomobject]@{ok=$false;message=$m}
}
function Import-AmazonPrintProfileFromPath([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)){ Show-Error 'File not found.'; return $false }
    $r=$null;try{$r=Invoke-AmazonProfileImporter $Path}catch{Show-Error $_.Exception.Message;return $false}finally{$script:StageFilterCache=$null;Refresh-StageFilterIfActive}
    if(-not $r.ok){ Show-Error $r.message; return $false }
    $st=Get-AmazonProfileStatus
    $vu=if($st.state -in @('valid','expiring')){[string]$st.args[5]}else{''}
    $StatusText.Text=((Get-UiText 'prof.imported' 'Amazon print profile saved. Valid until {0}.') -f $vu)
    try{ Update-AmazonProfileSurface }catch{}
    # The print check and the policy binding depend on the profile: refresh them for the open idea.
    try{ if($null -ne $script:Current -and $script:ProductSection -eq 'checks'){ Load-LocalChecksUi } elseif($null -ne $script:Current){ $null=Write-LocalCheckRequestBundle } }catch{ Write-AppLog 'WARN' ('Refresh after profile import failed: '+$_.Exception.Message) }
    try{ Update-LocalCoreBusinessSurfaces }catch{}
    return $true
}
function Import-AmazonPrintProfileFile {
    try {
        $dlg=New-Object Microsoft.Win32.OpenFileDialog; $dlg.Title='Amazon print profile JSON'; $dlg.Filter='JSON (*.json)|*.json'
        if($dlg.ShowDialog() -ne $true){return}; $null=Import-AmazonPrintProfileFromPath $dlg.FileName
    } catch { Show-Error $_.Exception.Message }
}

function Get-AcceptedArtworkShas {
    $out=@{}; try{ foreach($c in @((Read-LocalCoreState).concepts)){ $a=Get-PropertyValue $c 'active_acceptance'; $s=([string](Get-PropertyValue $a 'asset_sha256')).ToLowerInvariant(); if($s){$out[$s]=$true} } }catch{}
    return $out
}
function New-AmazonProfileAttestation($Fields,[datetime]$NowUtc=([DateTime]::UtcNow),$ForbiddenShas=$null) {
    # Pure: owner form -> forge.amazon_print_profile_attestation.v1 (the standalone tool re-validates everything).
    $market=([string]$Fields.marketplace).Trim(); $product=([string]$Fields.product_type_key).Trim(); $key=([string]$Fields.template_key).Trim()
    if(-not $market -or -not $product -or -not $key){ throw (Get-UiText 'prof.err.text' 'Fill marketplace, product type and template name.') }
    if(([string]$Fields.template_file_sha256) -notmatch '^[0-9a-f]{64}$'){ throw (Get-UiText 'prof.err.file' 'Choose the Amazon template file.') }
    if($null -ne $ForbiddenShas -and $ForbiddenShas.ContainsKey([string]$Fields.template_file_sha256)){ throw (Get-UiText 'prof.err.artwork' 'This file is one of your accepted designs, not the Amazon template. Choose the template file you downloaded from Amazon.') }
    $w=0;$h=0;$dpi=0;$days=0
    [void][int]::TryParse(([string]$Fields.width).Trim(),[ref]$w); [void][int]::TryParse(([string]$Fields.height).Trim(),[ref]$h); [void][int]::TryParse(([string]$Fields.dpi).Trim(),[ref]$dpi); [void][int]::TryParse(([string]$Fields.days).Trim(),[ref]$days)
    if($w -lt 500 -or $w -gt 10000 -or $h -lt 500 -or $h -gt 10000){ throw (Get-UiText 'prof.err.size' 'Width and height must be between 500 and 10000 px.') }
    if($dpi -lt 72 -or $dpi -gt 600){ throw (Get-UiText 'prof.err.dpi' 'DPI must be between 72 and 600.') }
    if($days -lt 1 -or $days -gt 120){ throw (Get-UiText 'prof.err.days' 'Valid for must be 1 to 120 days.') }
    $ref=([string]$Fields.source_ref).Trim(); $okRef=$false
    try{ $u=[Uri]$ref; $okRef=($u.Scheme -eq 'https' -and $u.Host.ToLowerInvariant() -in @('merch.amazon.com','developer.amazon.com','sellercentral.amazon.com')) }catch{}
    if(-not $okRef){ throw (Get-UiText 'prof.err.ref' 'The source link must be an https Amazon link.') }
    if(-not [bool]$Fields.attested){ throw (Get-UiText 'prof.err.attest' 'Tick "I copied these values…" to save the profile.') }
    $capt=$NowUtc.AddMinutes(-1)
    $result=[ordered]@{schema='forge.amazon_print_profile_attestation.v1';attested=$true;marketplace=$market;product_type_key=$product;template_key=$key;canvas_width_px=$w;canvas_height_px=$h;dpi=$dpi;file_format='png';background='transparent';captured_at=$capt.ToString('o');valid_until=$capt.AddDays($days).ToString('o');template_file_sha256=([string]$Fields.template_file_sha256);source_refs=[object[]]@($ref);note='Filled in the Merch Forge profile form by the owner from the current Amazon Merch template.'}
    if($product-eq'standard_tshirt'-and$market.ToLowerInvariant()-in@('amazon.com_us','amazon.com')){
        $result.upload_dimension_policy='flexible';$result.canvas_role='recommended_template_not_mandatory_upload_size';$result.dpi_role='template_metadata_not_upload_minimum'
        $result.upload_rules=[ordered]@{min_width_px_exclusive=485;min_height_px_exclusive=485;max_file_bytes_exclusive=25000000;file_size_policy_note='Conservative decimal interpretation of official <25MB.';png_bit_depth=8;png_color_model='RGB';required_color_space='sRGB'}
        $result.source_refs=[object[]]@($ref,'https://merch.amazon.com/resource/201849250#newdesigneditor'|Select-Object -Unique)
        $result.note='Owner-reviewed template values. Standard T-shirt template canvas is recommended, not mandatory. Saved US upload baseline: >485px each side, PNG RGB8, sRGB, transparent, <25MB. Current rules and exact-file print quality still require owner review.'
    }
    return $result
}
function Get-AmazonProfileEditorDefaults($Profile=$null) {
    $defaults=[pscustomobject]@{marketplace='amazon.com_us';product_type_key='standard_tshirt';template_key='';width='';height='';dpi='300';days='90';source_ref='';has_saved_values=$false}
    if($null-eq$Profile-or!(Test-ForgeAmazonPrintProfile $Profile $false)){return $defaults}
    $defaults.marketplace=$Profile.marketplace;$defaults.product_type_key=$Profile.product_type_key;$defaults.template_key=$Profile.template_key
    $defaults.width=[string]$Profile.canvas_width_px;$defaults.height=[string]$Profile.canvas_height_px;$defaults.dpi=[string]$Profile.dpi
    $capt=ConvertTo-ProfileUtc $Profile.captured_at;$valid=ConvertTo-ProfileUtc $Profile.valid_until;$defaults.days=[string][math]::Max(1,[math]::Min(120,[math]::Floor(($valid-$capt).TotalDays)))
    $defaults.source_ref=[string]$Profile.PSObject.Properties['source_refs'].Value[0];$defaults.has_saved_values=$true
    return $defaults
}
function Get-AmazonTemplateFileFacts([string]$Path) {
    $w=0; $h=0;$fs=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try{
        $hasher=[Security.Cryptography.SHA256]::Create();try{$sha=([BitConverter]::ToString($hasher.ComputeHash($fs))).Replace('-','').ToLowerInvariant()}finally{$hasher.Dispose()}
        if([IO.Path]::GetExtension($Path).ToLowerInvariant() -eq '.png'){
            try{$fs.Position=0;$dec=[Windows.Media.Imaging.BitmapDecoder]::Create($fs,[Windows.Media.Imaging.BitmapCreateOptions]::DelayCreation,[Windows.Media.Imaging.BitmapCacheOption]::None);$w=[int]$dec.Frames[0].PixelWidth;$h=[int]$dec.Frames[0].PixelHeight}catch{}
        }
    }finally{$fs.Dispose()}
    return [pscustomobject]@{sha256=$sha;width=$w;height=$h;name=[IO.Path]::GetFileNameWithoutExtension($Path)}
}

function New-AmazonProfileDialog {
    $esc={param([string]$s) ([Security.SecurityElement]::Escape($s)).Replace("`r",'').Replace("`n",'&#10;')}   # XML attributes turn raw newlines into spaces
    $lbl={param([string]$k,[string]$f) '<TextBlock Text="'+(& $esc (Get-UiText $k $f))+'" Margin="0,8,0,2" Opacity="0.85"/>'}
    $x=@"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" Title="$(& $esc (Get-UiText 'prof.form.title' 'Amazon print profile'))" Width="640" Height="720" MinWidth="480" MinHeight="420" WindowStartupLocation="CenterOwner" ShowInTaskbar="False">
<Grid Margin="16"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
<TextBlock Text="$(& $esc (Get-UiText 'prof.form.intro' ''))" TextWrapping="Wrap" Margin="0,0,0,8"/>
<ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto"><StackPanel>
$(& $lbl 'prof.form.market' 'Marketplace')<ComboBox x:Name="Market" IsEditable="True" Text="amazon.com_us"><ComboBoxItem Content="amazon.com_us"/><ComboBoxItem Content="amazon.co.uk"/><ComboBoxItem Content="amazon.de"/><ComboBoxItem Content="amazon.fr"/><ComboBoxItem Content="amazon.it"/><ComboBoxItem Content="amazon.es"/><ComboBoxItem Content="amazon.co.jp"/></ComboBox>
$(& $lbl 'prof.form.product' 'Product type')<ComboBox x:Name="Product" IsEditable="True" Text="standard_tshirt"><ComboBoxItem Content="standard_tshirt"/><ComboBoxItem Content="premium_tshirt"/><ComboBoxItem Content="v_neck_tshirt"/><ComboBoxItem Content="tank_top"/><ComboBoxItem Content="long_sleeve_tshirt"/><ComboBoxItem Content="raglan"/><ComboBoxItem Content="sweatshirt"/><ComboBoxItem Content="pullover_hoodie"/><ComboBoxItem Content="zip_hoodie"/></ComboBox>
$(& $lbl 'prof.form.file' 'Amazon template file')<Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><TextBox x:Name="FilePath" IsReadOnly="True"/><Button x:Name="Browse" Grid.Column="1" Content="$(& $esc (Get-UiText 'prof.form.browse' 'Choose…'))" Margin="8,0,0,0" MinWidth="90"/></Grid>
<TextBlock x:Name="FileSha" Opacity="0.6" FontFamily="Consolas" FontSize="11" Margin="0,4,0,0" TextWrapping="Wrap"/>
$(& $lbl 'prof.form.key' 'Template name')<TextBox x:Name="TemplateKey"/>
<Grid Margin="0,0,0,0"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="12"/><ColumnDefinition Width="*"/><ColumnDefinition Width="12"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
<StackPanel>$(& $lbl 'prof.form.width' 'Width, px')<TextBox x:Name="Width"/></StackPanel>
<StackPanel Grid.Column="2">$(& $lbl 'prof.form.height' 'Height, px')<TextBox x:Name="Height"/></StackPanel>
<StackPanel Grid.Column="4">$(& $lbl 'prof.form.dpi' 'DPI')<TextBox x:Name="Dpi" Text="300"/></StackPanel></Grid>
$(& $lbl 'prof.form.days' 'Valid for, days')<TextBox x:Name="Days" Text="90" Width="120" HorizontalAlignment="Left"/>
$(& $lbl 'prof.form.ref' 'Amazon page')<TextBox x:Name="SourceRef" Text=""/>
</StackPanel></ScrollViewer>
<StackPanel Grid.Row="2" Margin="0,10,0,0">
<CheckBox x:Name="Attest" Content="$(& $esc (Get-UiText 'prof.form.attest' 'I copied these values from the current Amazon Merch template.'))"/>
<TextBlock x:Name="ErrorText" Foreground="#FFFF8A80" TextWrapping="Wrap" Margin="0,6,0,0"/>
<StackPanel Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,8,0,0"><Button x:Name="OkButton" Content="$(& $esc (Get-UiText 'chk.ok' 'Save'))" MinWidth="110" Margin="0,0,8,0" IsDefault="True"/><Button x:Name="CancelButton" Content="$(& $esc (Get-UiText 'chk.cancel' 'Cancel'))" MinWidth="110" IsCancel="True"/></StackPanel>
</StackPanel></Grid></Window>
"@
    $w=[Windows.Markup.XamlReader]::Parse($x)
    $stored=$null;$profilePath=Get-LocalAmazonPrintProfilePath
    if(Test-Path -LiteralPath $profilePath -PathType Leaf){try{$stored=(Read-LocalCheckEvidencePayload $profilePath).data}catch{}}
    $defaults=Get-AmazonProfileEditorDefaults $stored
    foreach($pair in @(@('Market','marketplace'),@('Product','product_type_key'),@('TemplateKey','template_key'),@('Width','width'),@('Height','height'),@('Dpi','dpi'),@('Days','days'),@('SourceRef','source_ref'))){$w.FindName($pair[0]).Text=[string]$defaults.PSObject.Properties[$pair[1]].Value}
    # Saved values are review inputs, never a renewed attestation or a substituted template file.
    $w.FindName('Attest').IsChecked=$false
    if($null -ne $Window){
        try{ if($Window.IsLoaded){$w.Owner=$Window} }catch{}
        try{ $w.Background=$Window.Background; $w.Foreground=$Window.Foreground }catch{}
        try{ $w.Resources.MergedDictionaries.Add($Window.Resources) }catch{}
        try{ $w.FindName('Attest').Foreground=$Window.FindResource('Text') }catch{}
    }
    $w.Tag=$null
    return $w
}
function Set-AmazonProfileDialogFile($Dialog,[string]$Path) {
    $f=Get-AmazonTemplateFileFacts $Path
    $Dialog.FindName('FilePath').Text=$Path; $Dialog.FindName('FileSha').Text=('SHA-256 '+$f.sha256)
    if($f.width -gt 0){ $Dialog.FindName('Width').Text=[string]$f.width; $Dialog.FindName('Height').Text=[string]$f.height }
    if([string]::IsNullOrWhiteSpace($Dialog.FindName('TemplateKey').Text)){ $Dialog.FindName('TemplateKey').Text=$f.name }
}
function Read-AmazonProfileDialog($Dialog) {
    $sha=''; $t=[string]$Dialog.FindName('FileSha').Text; if($t -match '([0-9a-f]{64})'){ $sha=$Matches[1] }
    return [pscustomobject]@{marketplace=[string]$Dialog.FindName('Market').Text;product_type_key=[string]$Dialog.FindName('Product').Text;template_key=[string]$Dialog.FindName('TemplateKey').Text;template_file_sha256=$sha;width=[string]$Dialog.FindName('Width').Text;height=[string]$Dialog.FindName('Height').Text;dpi=[string]$Dialog.FindName('Dpi').Text;days=[string]$Dialog.FindName('Days').Text;source_ref=[string]$Dialog.FindName('SourceRef').Text;attested=[bool]$Dialog.FindName('Attest').IsChecked}
}
function Complete-AmazonProfileDialog($Dialog,[bool]$Modal=$true) {
    try { $att=New-AmazonProfileAttestation (Read-AmazonProfileDialog $Dialog) ([DateTime]::UtcNow) (Get-AcceptedArtworkShas) } catch { $Dialog.FindName('ErrorText').Text=$_.Exception.Message; return $false }
    $Dialog.FindName('ErrorText').Text=''; $Dialog.Tag=$att; if($Modal){ $Dialog.DialogResult=$true }
    return $true
}
function Save-AmazonProfileAttestation($Attestation) {
    try {
        $dir=Join-Path $script:LocalCoreExportRoot 'amazon-profile'; Ensure-Dir $dir
        $path=Join-Path $dir ('amazon-print-profile-{0}.json' -f [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss'))
        [IO.File]::WriteAllText($path,($Attestation | ConvertTo-Json -Depth 10),(New-Object System.Text.UTF8Encoding($false)))
    } catch { Show-Error $_.Exception.Message; return $false }
    return (Import-AmazonPrintProfileFromPath $path)
}
function Invoke-AmazonProfileForm {
    try { Invoke-AmazonProfileFormCore } catch { $script:AmazonProfileDialog=$null; Show-Error $_.Exception.Message }
}
function Invoke-AmazonProfileFormCore {
    $d=New-AmazonProfileDialog; $script:AmazonProfileDialog=$d
    $d.FindName('Browse').Add_Click({
        $o=New-Object Microsoft.Win32.OpenFileDialog; $o.Title=Get-UiText 'prof.form.file' 'Amazon template file'; $o.Filter='Amazon template (*.png;*.psd)|*.png;*.psd|All files (*.*)|*.*'
        if($o.ShowDialog($script:AmazonProfileDialog) -eq $true){ try{ Set-AmazonProfileDialogFile $script:AmazonProfileDialog $o.FileName }catch{ $script:AmazonProfileDialog.FindName('ErrorText').Text=$_.Exception.Message } }
    })
    $d.FindName('OkButton').Add_Click({ $null=Complete-AmazonProfileDialog $script:AmazonProfileDialog })
    try { if($d.ShowDialog() -eq $true -and $null -ne $d.Tag){ $null=Save-AmazonProfileAttestation $d.Tag } } finally { $script:AmazonProfileDialog=$null }
}
