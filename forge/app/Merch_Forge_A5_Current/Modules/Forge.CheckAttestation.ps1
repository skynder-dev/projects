# Merch Forge · Owner check confirmation (IP / policy / listing text)
# A plain-language checklist next to the JSON evidence template, and an in-app form that writes the same
# v3 evidence file and imports it through the normal, unchanged validation (Import-LocalCheckEvidenceFromPath).
# Nothing here passes a check by itself: a PASS needs the owner's explicit "I checked this myself" and a reference.

$script:CheckAttestationNames = @('ip','policy','metadata')
$script:ConfirmChecksDialog = $null
$script:LastCheckEvidenceImportOk = $false

function Register-CheckAttestationUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{
            'chk.label.ip'='IP'; 'chk.label.visual'='Artwork'; 'chk.label.print'='Print file'; 'chk.label.policy'='Amazon policy'; 'chk.label.metadata'='Listing text';
            'chk.view.pass'='passed'; 'chk.view.needs_review'='needs checking'; 'chk.view.blocked'='problem'; 'chk.view.not_required'='not required'; 'chk.view.none'='not checked'; 'chk.view.'='not checked';
            'chk.title'='Confirm checks';
            'chk.intro'='Check the items below yourself, then choose a result. A passed check needs a link or a short note on where you checked. This is not a legal opinion.';
            'chk.ip.title'='IP: trademarks and copyright';
            'chk.ip.list'="• Search the main phrase and key words in the USPTO trademark search (tmsearch.uspto.gov), class 025 clothing: no live mark for the same words.`n• No brand names, logos, characters, celebrities, sports teams, song lyrics or movie quotes.`n• The artwork is original (made or generated for you); no copied images, no fonts with restrictive licences.";
            'chk.policy.title'='Amazon Merch content policy';
            'chk.policy.list'="• No hate, violence, adult content, drugs or medical/health claims.`n• Nothing offensive about protected groups; nothing about current tragedies.`n• The design fits the Amazon product template from your print profile.";
            'chk.metadata.title'='Listing text (title, brand, bullets, description)';
            'chk.metadata.list'="• The text honestly describes the design; no other brands or trademarks; no 'official' or 'licensed'.`n• No claims about price, shipping, reviews or 'best seller'; no keyword stuffing; no HTML or emoji.`n• Spelling checked; the language matches the marketplace.";
            'chk.state.unchanged'='Leave as is'; 'chk.state.pass'='Checked: all good'; 'chk.state.needs_review'='Needs more checking'; 'chk.state.blocked'='Problem: do not publish';
            'chk.ref'='Where you checked (link or short note)'; 'chk.note'='Comment (optional)';
            'chk.confirm'='I checked the items marked "all good" myself.';
            'chk.ok'='Save'; 'chk.cancel'='Cancel';
            'chk.err.confirm'='Tick "I checked … myself" to save a passed check.';
            'chk.err.ref'='A passed check needs a link or a short note on where you checked: {0}.';
            'chk.err.none'='Choose a result for at least one check.';
            'chk.err.noaccept'='Accept the artwork for this idea first. Checks are confirmed for the exact accepted artwork and listing.';
            'chk.saved'='Checks saved: {0}.';
            'chk.folder.missing'='The checks folder appears after you accept the artwork.';
            'chk.file.header'='MERCH FORGE · CHECKLIST FOR "{0}"';
            'chk.file.how'="EASIEST: in Merch Forge open Checks and press 'Confirm checks…'.`n`nOR fill the JSON file next to this one ({0}):`n• for ip, policy and metadata set state to pass, needs_review or blocked;`n• for pass also set: source (who checked), checked_at (date and time, e.g. {1}), attested: true, and at least one link in evidence_refs;`n• do not change the other fields; then press 'Import check evidence…'.`n`nThe visual and print checks are done by the app (exact Accept and the print worker).";
            'checks.loaded'='Checks loaded. Press "Confirm checks…" to confirm IP, policy and listing text.'
        }
        ru=@{
            'chk.label.ip'='IP'; 'chk.label.visual'='Макет'; 'chk.label.print'='Файл для печати'; 'chk.label.policy'='Правила Amazon'; 'chk.label.metadata'='Текст карточки';
            'chk.view.pass'='пройдено'; 'chk.view.needs_review'='нужно проверить'; 'chk.view.blocked'='проблема'; 'chk.view.not_required'='не требуется'; 'chk.view.none'='не проверено'; 'chk.view.'='не проверено';
            'chk.title'='Подтвердить проверки';
            'chk.intro'='Проверьте пункты ниже сами и выберите результат. Для «всё в порядке» нужна ссылка или короткая заметка, где вы проверяли. Это не юридическое заключение.';
            'chk.ip.title'='IP: товарные знаки и авторские права';
            'chk.ip.list'="• Найдите главную фразу и ключевые слова в базе товарных знаков USPTO (tmsearch.uspto.gov), класс 025 «одежда»: действующего знака с теми же словами нет.`n• Нет чужих брендов, логотипов, персонажей, знаменитостей, спортивных команд, строк из песен и цитат из фильмов.`n• Рисунок оригинальный (сделан или сгенерирован для вас); нет скопированных картинок и шрифтов с запрещающей лицензией.";
            'chk.policy.title'='Правила контента Amazon Merch';
            'chk.policy.list'="• Нет ненависти, насилия, контента для взрослых, наркотиков, медицинских обещаний.`n• Ничего оскорбительного о защищённых группах; ничего о свежих трагедиях.`n• Рисунок подходит под шаблон товара Amazon из вашего профиля печати.";
            'chk.metadata.title'='Текст карточки (название, бренд, пункты, описание)';
            'chk.metadata.list'="• Текст честно описывает рисунок; нет чужих брендов и товарных знаков; нет слов «официальный», «лицензионный».`n• Нет обещаний о цене, доставке, отзывах, «бестселлер»; нет набивки ключевыми словами; нет HTML и эмодзи.`n• Орфография проверена; язык соответствует площадке.";
            'chk.state.unchanged'='Оставить как есть'; 'chk.state.pass'='Проверено: всё в порядке'; 'chk.state.needs_review'='Нужно проверить ещё'; 'chk.state.blocked'='Есть проблема: не публиковать';
            'chk.ref'='Где проверяли (ссылка или короткая заметка)'; 'chk.note'='Комментарий (необязательно)';
            'chk.confirm'='Я сам(а) проверил(а) пункты, отмеченные «всё в порядке».';
            'chk.ok'='Сохранить'; 'chk.cancel'='Отмена';
            'chk.err.confirm'='Поставьте галочку «Я сам(а) проверил(а)…», чтобы сохранить пройденную проверку.';
            'chk.err.ref'='Для «всё в порядке» нужна ссылка или заметка, где вы проверяли: {0}.';
            'chk.err.none'='Выберите результат хотя бы для одной проверки.';
            'chk.err.noaccept'='Сначала примите макет для этой идеи. Проверки подтверждаются для точного принятого макета и карточки.';
            'chk.saved'='Проверки сохранены: {0}.';
            'chk.folder.missing'='Папка проверок появится после того, как вы примете макет.';
            'chk.file.header'='MERCH FORGE · ЧЕК-ЛИСТ ДЛЯ «{0}»';
            'chk.file.how'="ПРОЩЕ ВСЕГО: в Merch Forge откройте «Проверки» и нажмите «Подтвердить проверки…».`n`nИЛИ заполните JSON-файл рядом с этим ({0}):`n• для ip, policy и metadata укажите state: pass, needs_review или blocked;`n• для pass также укажите: source (кто проверил), checked_at (дата и время, например {1}), attested: true и хотя бы одну ссылку в evidence_refs;`n• остальные поля не меняйте; затем нажмите «Импорт подтверждений…».`n`nПроверки visual и print делает само приложение (точное «Принять» и проверка печати).";
            'checks.loaded'='Проверки загружены. Нажмите «Подтвердить проверки…», чтобы подтвердить IP, правила и текст карточки.'
        }
        es=@{
            'chk.label.ip'='PI'; 'chk.label.visual'='Diseño'; 'chk.label.print'='Archivo de impresión'; 'chk.label.policy'='Política de Amazon'; 'chk.label.metadata'='Texto de la ficha';
            'chk.view.pass'='aprobado'; 'chk.view.needs_review'='hay que revisar'; 'chk.view.blocked'='problema'; 'chk.view.not_required'='no requerido'; 'chk.view.none'='sin revisar'; 'chk.view.'='sin revisar';
            'chk.title'='Confirmar revisiones';
            'chk.intro'='Revisa tú mismo los puntos de abajo y elige un resultado. Una revisión aprobada necesita un enlace o una nota breve de dónde lo comprobaste. No es una opinión legal.';
            'chk.ip.title'='PI: marcas y derechos de autor';
            'chk.ip.list'="• Busca la frase principal y las palabras clave en la búsqueda de marcas de la USPTO (tmsearch.uspto.gov), clase 025 ropa: ninguna marca vigente con las mismas palabras.`n• Sin marcas ajenas, logotipos, personajes, famosos, equipos deportivos, letras de canciones ni citas de películas.`n• El diseño es original (hecho o generado para ti); sin imágenes copiadas ni fuentes con licencias restrictivas.";
            'chk.policy.title'='Política de contenido de Amazon Merch';
            'chk.policy.list'="• Sin odio, violencia, contenido adulto, drogas ni afirmaciones médicas.`n• Nada ofensivo sobre grupos protegidos; nada sobre tragedias recientes.`n• El diseño encaja en la plantilla de producto de Amazon de tu perfil de impresión.";
            'chk.metadata.title'='Texto de la ficha (título, marca, viñetas, descripción)';
            'chk.metadata.list'="• El texto describe el diseño con honestidad; sin otras marcas; sin 'oficial' ni 'con licencia'.`n• Sin promesas de precio, envío, reseñas o 'más vendido'; sin relleno de palabras clave; sin HTML ni emoji.`n• Ortografía revisada; el idioma coincide con el mercado.";
            'chk.state.unchanged'='Dejar como está'; 'chk.state.pass'='Revisado: todo bien'; 'chk.state.needs_review'='Hay que revisar más'; 'chk.state.blocked'='Problema: no publicar';
            'chk.ref'='Dónde lo revisaste (enlace o nota breve)'; 'chk.note'='Comentario (opcional)';
            'chk.confirm'='He revisado yo mismo los puntos marcados como "todo bien".';
            'chk.ok'='Guardar'; 'chk.cancel'='Cancelar';
            'chk.err.confirm'='Marca "He revisado yo mismo…" para guardar una revisión aprobada.';
            'chk.err.ref'='Una revisión aprobada necesita un enlace o una nota de dónde la hiciste: {0}.';
            'chk.err.none'='Elige un resultado para al menos una revisión.';
            'chk.err.noaccept'='Primero acepta el diseño de esta idea. Las revisiones se confirman para el diseño aceptado exacto y su ficha.';
            'chk.saved'='Revisiones guardadas: {0}.';
            'chk.folder.missing'='La carpeta de revisiones aparece después de aceptar el diseño.';
            'chk.file.header'='MERCH FORGE · LISTA DE REVISIÓN PARA "{0}"';
            'chk.file.how'="LO MÁS FÁCIL: en Merch Forge abre Comprobaciones y pulsa 'Confirmar revisiones…'.`n`nO rellena el archivo JSON junto a este ({0}):`n• para ip, policy y metadata pon state: pass, needs_review o blocked;`n• para pass indica también: source (quién revisó), checked_at (fecha y hora, p. ej. {1}), attested: true y al menos un enlace en evidence_refs;`n• no cambies los demás campos; luego pulsa 'Importar evidencias…'.`n`nLas revisiones visual y print las hace la aplicación (Aceptar exacto y el verificador de impresión).";
            'checks.loaded'='Revisiones cargadas. Pulsa "Confirmar revisiones…" para confirmar PI, política y texto de la ficha.'
        }
    }
    foreach($loc in $texts.Keys){ if($null -eq $script:UiText[$loc]){$script:UiText[$loc]=@{}}; foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]} }
    if($null -ne $script:StaticUiTranslations){
        $static=@{ ru=@{'Confirm checks…'='Подтвердить проверки…';'Open checks folder'='Открыть папку проверок';'Local check evidence'='Подтверждение проверок'}; es=@{'Confirm checks…'='Confirmar revisiones…';'Open checks folder'='Abrir carpeta de revisiones';'Local check evidence'='Confirmación de revisiones'} }
        foreach($loc in $static.Keys){ if($null -ne $script:StaticUiTranslations[$loc]){ foreach($k in $static[$loc].Keys){ if(-not $script:StaticUiTranslations[$loc].ContainsKey($k)){$script:StaticUiTranslations[$loc][$k]=$static[$loc][$k]} } } }
    }
}

function Get-CheckChecklistText([string]$Title,[string]$JsonFileName) {
    $lines=New-Object System.Collections.Generic.List[string]
    [void]$lines.Add(((Get-UiText 'chk.file.header' 'MERCH FORGE · CHECKLIST FOR "{0}"') -f $Title)); [void]$lines.Add('')
    [void]$lines.Add((Get-UiText 'chk.intro' '')); [void]$lines.Add('')
    foreach($n in $script:CheckAttestationNames){
        $t=Get-UiText ('chk.'+$n+'.title') $n
        [void]$lines.Add(('{0} [{1}]' -f $t.ToUpperInvariant(),$n)); [void]$lines.Add((Get-UiText ('chk.'+$n+'.list') '')); [void]$lines.Add('')
    }
    [void]$lines.Add('----'); [void]$lines.Add(((Get-UiText 'chk.file.how' '') -f $JsonFileName,([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:00Z'))))
    return (($lines -join "`n").Replace("`r`n","`n").Replace("`n","`r`n"))
}
function Write-LocalCheckChecklistFile([string]$TemplatePath) {
    if([string]::IsNullOrWhiteSpace($TemplatePath)){return $null}
    $dir=Split-Path -Parent $TemplatePath; $leaf=Split-Path -Leaf $TemplatePath
    $base=$leaf -replace '\.template\.json$',''
    $out=Join-Path $dir ($base+'.CHECKLIST.txt')
    $title=''; try{$title=[string](Get-PropertyValue $script:Current.concept 'title')}catch{}
    [IO.File]::WriteAllText($out,(Get-CheckChecklistText $title $leaf),(New-Object System.Text.UTF8Encoding($true)))
    return $out
}

function New-OwnerCheckEvidence($Template,$Answers,[bool]$Confirmed,[datetime]$NowUtc=([DateTime]::UtcNow)) {
    # Pure: fills the app's own v3 template from the owner's answers. Visual/print stay with the app.
    foreach($n in @('visual','print')){ if($null -ne $Template.PSObject.Properties[$n]){ $Template.PSObject.Properties.Remove($n) } }
    $saved=@(); $missingRef=@(); $anyPass=$false
    foreach($n in $script:CheckAttestationNames){
        $a=$null; if($null -ne $Answers){ $a=$Answers[$n] }
        $state=if($null -ne $a){([string]$a.state).Trim().ToLowerInvariant()}else{'unchanged'}
        if($state -notin @('pass','needs_review','blocked')){ if($null -ne $Template.PSObject.Properties[$n]){ $Template.PSObject.Properties.Remove($n) }; continue }
        $c=Get-PropertyValue $Template $n
        if($null -eq $c){ throw ('The evidence template has no {0} section. Accept the artwork again to refresh it.' -f $n) }
        $ref=([string]$a.ref).Trim(); $note=([string]$a.note).Trim()
        if($state -eq 'pass'){ $anyPass=$true; if([string]::IsNullOrWhiteSpace($ref)){ $missingRef+=$n } }
        Add-OrSetProperty $c 'state' $state
        Add-OrSetProperty $c 'source' 'owner_in_app_checklist'
        Add-OrSetProperty $c 'note' $note
        Add-OrSetProperty $c 'checked_at' $NowUtc.AddSeconds(-1).ToString('o')
        Add-OrSetProperty $c 'authority_kind' $(if($state -eq 'pass'){'owner_attested_external'}else{'none'})
        Add-OrSetProperty $c 'attested' ($state -eq 'pass')
        Add-OrSetProperty $c 'evidence_refs' $null; $c.evidence_refs=[object[]]@(@($ref) | Where-Object { $_ })   # direct assignment keeps it an array
        $saved+=$n
    }
    if($saved.Count -eq 0){ throw (Get-UiText 'chk.err.none' 'Choose a result for at least one check.') }
    if($missingRef.Count){ throw ((Get-UiText 'chk.err.ref' 'A passed check needs a link or a short note on where you checked: {0}.') -f ($missingRef -join ', ')) }
    if($anyPass -and -not $Confirmed){ throw (Get-UiText 'chk.err.confirm' 'Tick "I checked … myself" to save a passed check.') }
    return [pscustomobject]@{evidence=$Template;saved=$saved}
}
function Submit-OwnerCheckAnswers($Answers,[bool]$Confirmed) {
    # Returns $true when the evidence was imported by the normal importer.
    if($null -eq $script:Current){ Show-Error 'Choose an idea first.'; return $false }
    $bundle=$null; try{$bundle=Write-LocalCheckRequestBundle}catch{ Show-Error $_.Exception.Message; return $false }
    if($null -eq $bundle){ Show-Error (Get-UiText 'chk.err.noaccept' 'Accept the artwork for this idea first.'); return $false }
    try {
        $tpl=Get-Content -LiteralPath $bundle.evidence_template_path -Raw -Encoding UTF8 | ConvertFrom-Json
        $r=New-OwnerCheckEvidence $tpl $Answers $Confirmed
    } catch { Show-Error $_.Exception.Message; return $false }
    $dir=Split-Path -Parent $bundle.evidence_template_path
    $path=Join-Path $dir (('check-evidence-{0}.owner-{1}.json' -f $bundle.lineage_key.Substring(0,16),[DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')))
    [IO.File]::WriteAllText($path,($r.evidence | ConvertTo-Json -Depth 20),(New-Object System.Text.UTF8Encoding($false)))
    $script:LastCheckEvidenceImportOk=$false
    Import-LocalCheckEvidenceFromPath $path
    $ok=[bool]$script:LastCheckEvidenceImportOk
    if($ok){
        $names=@($r.saved | ForEach-Object { Get-UiText ('chk.'+$_+'.title') $_ }) -join '; '
        $StatusText.Text=((Get-UiText 'chk.saved' 'Checks saved: {0}.') -f $names)
        if($null -ne $LocalCheckStatusText){ $LocalCheckStatusText.Text=$StatusText.Text }
    }
    return $ok
}

function New-ConfirmChecksDialog {
    $esc={param([string]$s) ([Security.SecurityElement]::Escape($s)).Replace("`r",'').Replace("`n",'&#10;')}   # XML attributes turn raw newlines into spaces
    $sections=''
    foreach($n in $script:CheckAttestationNames){
        $sections+=@"
<Border BorderThickness="1" BorderBrush="#33FFFFFF" CornerRadius="8" Padding="12" Margin="0,0,0,10"><StackPanel>
<TextBlock Text="$(& $esc (Get-UiText ('chk.'+$n+'.title') $n))" FontWeight="SemiBold" FontSize="14"/>
<TextBlock Text="$(& $esc (Get-UiText ('chk.'+$n+'.list') ''))" TextWrapping="Wrap" Margin="0,6,0,8" Opacity="0.85"/>
<ComboBox x:Name="State_$n" SelectedIndex="0" Width="320" HorizontalAlignment="Left">
<ComboBoxItem Tag="unchanged" Content="$(& $esc (Get-UiText 'chk.state.unchanged' 'Leave as is'))"/>
<ComboBoxItem Tag="pass" Content="$(& $esc (Get-UiText 'chk.state.pass' 'Checked: all good'))"/>
<ComboBoxItem Tag="needs_review" Content="$(& $esc (Get-UiText 'chk.state.needs_review' 'Needs more checking'))"/>
<ComboBoxItem Tag="blocked" Content="$(& $esc (Get-UiText 'chk.state.blocked' 'Problem: do not publish'))"/>
</ComboBox>
<TextBlock Text="$(& $esc (Get-UiText 'chk.ref' 'Where you checked'))" Margin="0,8,0,2" Opacity="0.8"/><TextBox x:Name="Ref_$n"/>
<TextBlock Text="$(& $esc (Get-UiText 'chk.note' 'Comment'))" Margin="0,6,0,2" Opacity="0.8"/><TextBox x:Name="Note_$n"/>
</StackPanel></Border>
"@
    }
    $x=@"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" Title="$(& $esc (Get-UiText 'chk.title' 'Confirm checks'))" Width="720" Height="760" MinWidth="520" MinHeight="420" WindowStartupLocation="CenterOwner" ShowInTaskbar="False">
<Grid Margin="16"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
<TextBlock Text="$(& $esc (Get-UiText 'chk.intro' ''))" TextWrapping="Wrap" Margin="0,0,0,12"/>
<ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto"><StackPanel>$sections</StackPanel></ScrollViewer>
<StackPanel Grid.Row="2" Margin="0,10,0,0">
<CheckBox x:Name="ConfirmBox" Content="$(& $esc (Get-UiText 'chk.confirm' 'I checked the items marked all good myself.'))"/>
<TextBlock x:Name="ErrorText" Foreground="#FFFF8A80" TextWrapping="Wrap" Margin="0,6,0,0"/>
<StackPanel Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,8,0,0"><Button x:Name="OkButton" Content="$(& $esc (Get-UiText 'chk.ok' 'Save'))" MinWidth="110" Margin="0,0,8,0" IsDefault="True"/><Button x:Name="CancelButton" Content="$(& $esc (Get-UiText 'chk.cancel' 'Cancel'))" MinWidth="110" IsCancel="True"/></StackPanel>
</StackPanel></Grid></Window>
"@
    $w=[Windows.Markup.XamlReader]::Parse($x)
    if($null -ne $Window){
        try{ if($Window.IsLoaded){$w.Owner=$Window} }catch{}
        try{ $w.Background=$Window.Background; $w.Foreground=$Window.Foreground }catch{}
        try{ $w.Resources.MergedDictionaries.Add($Window.Resources) }catch{}
        try{ $w.FindName('ConfirmBox').Foreground=$Window.FindResource('Text') }catch{}
    }
    return $w
}
function Read-ConfirmChecksAnswers($Dialog) {
    $ans=@{}
    foreach($n in $script:CheckAttestationNames){
        $cb=$Dialog.FindName('State_'+$n); $st='unchanged'; if($null -ne $cb -and $null -ne $cb.SelectedItem){$st=[string]$cb.SelectedItem.Tag}
        $ans[$n]=[pscustomobject]@{state=$st;ref=[string]$Dialog.FindName('Ref_'+$n).Text;note=[string]$Dialog.FindName('Note_'+$n).Text}
    }
    return [pscustomobject]@{answers=$ans;confirmed=[bool]$Dialog.FindName('ConfirmBox').IsChecked}
}
function Test-ConfirmChecksAnswers($Read) {
    # Returns '' when the answers can be saved, otherwise a readable reason (shown inside the dialog).
    try { $tpl=[pscustomobject]@{ip=[pscustomobject]@{};policy=[pscustomobject]@{};metadata=[pscustomobject]@{}}; $null=New-OwnerCheckEvidence $tpl $Read.answers $Read.confirmed; return '' } catch { return $_.Exception.Message }
}
function Complete-ConfirmChecksDialog($Dialog,[bool]$Modal=$true) {
    # OK button: validate inside the dialog so the owner can fix the answer without losing it.
    $r=Read-ConfirmChecksAnswers $Dialog; $why=Test-ConfirmChecksAnswers $r
    if($why){ $Dialog.FindName('ErrorText').Text=$why; return $false }
    $Dialog.FindName('ErrorText').Text=''; $Dialog.Tag=$r; if($Modal){ $Dialog.DialogResult=$true }
    return $true
}
function Invoke-ConfirmChecks {
    if($null -eq $script:Current){ Show-Error 'Choose an idea first.'; return }
    $d=New-ConfirmChecksDialog; $script:ConfirmChecksDialog=$d
    $d.FindName('OkButton').Add_Click({ Complete-ConfirmChecksDialog $script:ConfirmChecksDialog })
    try { if($d.ShowDialog() -eq $true -and $null -ne $d.Tag){ $null=Submit-OwnerCheckAnswers $d.Tag.answers $d.Tag.confirmed } } finally { $script:ConfirmChecksDialog=$null }
}
function Open-LocalChecksFolder {
    $dir=$null
    try { if($null -ne $script:Current){ $dir=Join-Path $script:LocalCoreExportRoot (Join-Path (Get-LocalCoreSafeKey ([string]$script:Current.concept.concept_key)) 'checks') } } catch {}
    if([string]::IsNullOrWhiteSpace($dir) -or -not (Test-Path -LiteralPath $dir -PathType Container)){ Show-Error (Get-UiText 'chk.folder.missing' 'The checks folder appears after you accept the artwork.'); return }
    Start-Process -FilePath 'explorer.exe' -ArgumentList ('"'+$dir+'"')
}
