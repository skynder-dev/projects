# Local owner-entered scenario arithmetic. Never a sales forecast, approval or print gate.
function Register-EconomicsUiText {
    $texts=@{
        en=@{'econ.title'='Economics scenario';'econ.button'='Review economics scenario';'econ.unknown'='Economics not evaluated for this exact artwork/listing/profile. Reason: {0}. Print compatibility does not establish profitability.';'econ.never'='not recoverable under these inputs';'econ.summary'='Owner-entered scenario: contribution/unit {0}; units to cover fixed cost: {1}. Source date {2} ({3} day(s) old): {4}. Cost scope: {5}. Actual sales and net profit remain unverified.'}
        ru=@{'econ.title'='Сценарий экономики';'econ.button'='Проверить сценарий экономики';'econ.unknown'='Экономика точного файла, листинга и профиля не оценена. Причина: {0}. Совместимость печати не доказывает прибыльность.';'econ.never'='не возмещаются при этих вводных';'econ.summary'='Сценарий владельца: вклад с единицы {0}; единиц для покрытия постоянных затрат: {1}. Источник от {2} ({3} дн.): {4}. Учтённые и исключённые затраты: {5}. Фактические продажи и чистая прибыль не подтверждены.';'econ.explicit'='Это мои явные вводные сценария; их полнота независимо не проверена.';'econ.confirm_required'='Подтвердите, что это ваши явные вводные сценария.';'econ.saved'='Сценарий сохранён для точного файла и листинга. Одобрение дизайна и публикация не выполнялись.';'econ.field.Currency'='Код валюты (одна валюта для всех сумм)';'econ.field.Price'='Цена продажи из указанного источника';'econ.field.Royalty'='Роялти с единицы из указанного источника';'econ.field.Variable'='Дополнительные затраты с единицы, ещё не вычтенные из роялти';'econ.field.Fixed'='Постоянные затраты для возмещения';'econ.field.Source'='Источник цены и роялти';'econ.field.Observed'='Дата источника (ГГГГ-ММ-ДД)';'econ.field.Scope'='Учтённые и ещё не учтённые затраты'}
        es=@{'econ.title'='Escenario económico';'econ.button'='Revisar escenario económico';'econ.unknown'='Economía sin evaluar para este archivo, ficha y perfil exactos. Motivo: {0}. La compatibilidad de impresión no demuestra rentabilidad.';'econ.never'='no recuperable con estos datos';'econ.summary'='Escenario del propietario: contribución por unidad {0}; unidades para cubrir el coste fijo: {1}. Fuente del {2} (hace {3} días): {4}. Costes incluidos y excluidos: {5}. Las ventas reales y el beneficio neto siguen sin verificar.';'econ.explicit'='Estos son mis datos explícitos del escenario; su integridad no se ha verificado independientemente.';'econ.confirm_required'='Confirma que son tus datos explícitos del escenario.';'econ.saved'='Escenario guardado para el archivo y la ficha exactos; no se aprobó el diseño ni se publicó.';'econ.field.Currency'='Código de moneda (una moneda para todos los importes)';'econ.field.Price'='Precio de venta de la fuente indicada';'econ.field.Royalty'='Regalía por unidad de la fuente indicada';'econ.field.Variable'='Coste adicional por unidad, aún no descontado de la regalía';'econ.field.Fixed'='Coste fijo que recuperar';'econ.field.Source'='Fuente del precio y de la regalía';'econ.field.Observed'='Fecha de la fuente (AAAA-MM-DD)';'econ.field.Scope'='Costes incluidos y costes aún excluidos'}
    }
    $texts.ru['econ.intro']='Явные вводные для {0} / {1}. Пустые затраты неизвестны; ноль вводите только намеренно. Все суммы в одной валюте. Не учитывайте повторно производственные затраты площадки, уже вычтенные из роялти. Это не одобрение дизайна и не прогноз продаж.'
    $texts.es['econ.intro']='Datos explícitos para {0} / {1}. Los costes vacíos son desconocidos; escribe cero solo si corresponde. Usa una moneda y no vuelvas a descontar costes de producción ya incluidos en la regalía. Esto no aprueba el diseño ni predice ventas.'
    $texts.en['econ.nonpositive']='Additional sales do not create positive unit contribution under these inputs.'
    $texts.ru['econ.nonpositive']='При этих вводных дополнительные продажи не дают положительного вклада с единицы.'
    $texts.es['econ.nonpositive']='Con estos datos las ventas adicionales no generan una contribución positiva por unidad.'
    foreach($loc in $texts.Keys){if($null-eq$script:UiText[$loc]){$script:UiText[$loc]=@{}};foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]}}
}
function Get-LocalEconomicsBinding($Lc) {
    if($null-eq$Lc){throw 'Open a saved concept first.'}
    $acc=Get-PropertyValue $Lc 'active_acceptance';$pub=Get-PropertyValue $Lc 'publication'
    if($null-eq$acc-or$null-eq$pub){throw 'Accept exact artwork and save its listing before evaluating economics.'}
    $rid=[string](Get-PropertyValue $Lc 'source_revision_id');$rh=[string](Get-PropertyValue $Lc 'source_revision_hash')
    if([string](Get-PropertyValue $acc 'concept_revision_id')-cne$rid-or[string](Get-PropertyValue $acc 'revision_hash')-cne$rh-or[string](Get-PropertyValue $pub 'acceptance_fingerprint')-cne[string](Get-PropertyValue $acc 'lineage_fingerprint')){throw 'Artwork or listing lineage is stale; review the current saved version first.'}
    $profile=Get-LocalAmazonPrintProfile
    if($null-eq$profile){throw 'Import the current product/channel print profile before binding an economics scenario.'}
    $market=([string]$profile.marketplace).Trim().ToLowerInvariant()
    $currencies=@{'amazon.com_us'='USD';'amazon.com'='USD';'us'='USD';'amazon.co.uk'='GBP';'uk'='GBP';'amazon.de'='EUR';'amazon.fr'='EUR';'amazon.it'='EUR';'amazon.es'='EUR';'amazon.co.jp'='JPY';'amazon.ca'='CAD';'amazon.com.au'='AUD'}
    if(!$currencies.ContainsKey($market)){throw 'Economics currency mapping is unavailable for this channel profile. Print/export checks remain separate.'}
    return [pscustomobject][ordered]@{concept_key=[string]$Lc.concept_key;revision_id=$rid;revision_hash=$rh;acceptance_fingerprint=[string]$acc.lineage_fingerprint;artwork_sha256=[string]$acc.asset_sha256;listing_hash=(Get-LocalPublicationHash $pub);marketplace=[string]$profile.marketplace;product_type_key=[string]$profile.product_type_key;expected_currency=$currencies[$market];profile_sha256=(Get-StringSha256Hex ($profile|ConvertTo-Json -Depth 40 -Compress))}
}
function ConvertTo-LocalEconomicsAmount($Value,[string]$Name) {
    $text=([string]$Value).Trim();$amount=[decimal]0
    if(!$text-or$text-notmatch'^\d+(\.\d{1,4})?$'-or![decimal]::TryParse($text,[Globalization.NumberStyles]::AllowDecimalPoint,[Globalization.CultureInfo]::InvariantCulture,[ref]$amount)-or$amount-lt0-or$amount-gt1000000000){throw ($Name+': enter an explicit non-negative amount (decimal point, up to four decimal places). Blank means unknown; it is not zero.')}
    return $amount
}
function New-LocalEconomicsScenario($Fields,$Binding,[datetime]$NowUtc=([DateTime]::UtcNow)) {
    $currency=Resolve-LocalSalesCurrency ([string](Get-PropertyValue $Fields 'currency')) ''
    if(!$currency.currency){throw 'Use an explicit supported currency code, such as USD. No exchange rate is assumed.'}
    if($currency.currency-cne[string](Get-PropertyValue $Binding 'expected_currency')){throw 'Scenario currency must match the exact channel profile; no conversion is performed.'}
    $price=ConvertTo-LocalEconomicsAmount (Get-PropertyValue $Fields 'sale_price') 'Sale price'
    $royalty=ConvertTo-LocalEconomicsAmount (Get-PropertyValue $Fields 'royalty_per_unit') 'Royalty per unit'
    $variable=ConvertTo-LocalEconomicsAmount (Get-PropertyValue $Fields 'additional_cost_per_unit') 'Additional cost per unit'
    $fixed=ConvertTo-LocalEconomicsAmount (Get-PropertyValue $Fields 'fixed_cost') 'Fixed cost'
    if($price-le0-or$royalty-gt$price){throw 'Sale price must be positive and the royalty cannot exceed the sale price.'}
    $source=([string](Get-PropertyValue $Fields 'source_ref')).Trim();$scope=([string](Get-PropertyValue $Fields 'cost_scope')).Trim()
    if(!$source-or!$scope){throw 'Record the price/royalty source and what costs are included or still excluded.'}
    $observed=$null;try{$observed=[DateTime]::ParseExact(([string](Get-PropertyValue $Fields 'observed_on')).Trim(),'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture)}catch{throw 'Source date must be YYYY-MM-DD.'}
    if($observed.Date-gt$NowUtc.ToUniversalTime().Date){throw 'Source date cannot be in the future.'}
    $contribution=$royalty-$variable;$breakEven=$null
    if($fixed-eq0){$breakEven='0'}elseif($contribution-gt0){$breakEven=([decimal]::Ceiling($fixed/$contribution)).ToString('0',[Globalization.CultureInfo]::InvariantCulture)}
    $inv=[Globalization.CultureInfo]::InvariantCulture
    $inputs=[pscustomobject][ordered]@{currency=$currency.currency;sale_price=$price.ToString('0.####',$inv);royalty_per_unit=$royalty.ToString('0.####',$inv);additional_cost_per_unit=$variable.ToString('0.####',$inv);fixed_cost=$fixed.ToString('0.####',$inv);source_ref=$source;cost_scope=$scope;observed_on=$observed.ToString('yyyy-MM-dd')}
    $plan=[pscustomobject][ordered]@{schema='forge.unit_economics_scenario.v1';binding=$Binding;inputs=$inputs;contribution_per_unit=$contribution.ToString('0.####',$inv);break_even_units=$breakEven;positive_contribution=($contribution-gt0);created_at=$NowUtc.ToUniversalTime().ToString('o');authority='owner_entered_assumptions_not_independently_verified';sales_forecast=$null;net_profit_verified=$false}
    Add-OrSetProperty $plan 'scenario_sha256' (Get-StringSha256Hex ($plan|ConvertTo-Json -Depth 20 -Compress))
    return $plan
}
function Get-LocalEconomicsSnapshot($Lc,[datetime]$NowUtc=([DateTime]::UtcNow)) {
    $none=[pscustomobject]@{evaluated=$false;reason='not_evaluated';financial_readiness_claim=$false;scenario=$null}
    $plan=Get-PropertyValue $Lc 'economics_scenario';if($null-eq$plan){return $none}
    try {
        if([string](Get-PropertyValue $plan 'schema')-cne'forge.unit_economics_scenario.v1'){throw 'unsupported_scenario'}
        $copy=$plan|ConvertTo-Json -Depth 30|ConvertFrom-Json;$sha=[string](Get-PropertyValue $copy 'scenario_sha256');$copy.PSObject.Properties.Remove('scenario_sha256')
        if($sha-cne(Get-StringSha256Hex ($copy|ConvertTo-Json -Depth 20 -Compress))){throw 'scenario_hash_mismatch'}
        $binding=Get-LocalEconomicsBinding $Lc
        if(($binding|ConvertTo-Json -Depth 20 -Compress)-cne($plan.binding|ConvertTo-Json -Depth 20 -Compress)){throw 'scenario_lineage_changed'}
        $created=ConvertTo-ForgeUtcDateTime $plan.created_at;if($created-gt$NowUtc.ToUniversalTime().AddMinutes(10)){throw 'scenario_date_invalid'}
        $verified=New-LocalEconomicsScenario $plan.inputs $binding $created
        if($verified.scenario_sha256-cne$sha){throw 'scenario_calculation_mismatch'}
        return [pscustomobject]@{evaluated=$true;reason='owner_entered_scenario';financial_readiness_claim=$false;source_age_days=($NowUtc.Date-([DateTime]::ParseExact($plan.inputs.observed_on,'yyyy-MM-dd',[Globalization.CultureInfo]::InvariantCulture))).Days;scenario=$verified}
    }catch{$none.reason=$_.Exception.Message;return $none}
}
function Format-LocalEconomicsSnapshot($Snapshot) {
    if(!$Snapshot.evaluated){return ((Get-UiText 'econ.unknown' 'Economics not evaluated for this exact artwork/listing/profile. Reason: {0}. Print compatibility does not establish profitability.')-f$Snapshot.reason)}
    $p=$Snapshot.scenario;$c=$p.inputs.currency;$inv=[Globalization.CultureInfo]::InvariantCulture
    $contribution=$c+' '+[string]::Format($inv,'{0:0.0000}',[decimal]::Parse($p.contribution_per_unit,$inv))
    $breakEven=if($null-eq$p.break_even_units){Get-UiText 'econ.never' 'no finite break-even under these inputs'}else{[string]$p.break_even_units}
    $text=((Get-UiText 'econ.summary' 'Owner-entered scenario: contribution/unit {0}; units to cover fixed cost: {1}. Source date {2} ({3} day(s) old): {4}. Cost scope: {5}. Actual sales and net profit remain unverified.')-f$contribution,$breakEven,$p.inputs.observed_on,$Snapshot.source_age_days,$p.inputs.source_ref,$p.inputs.cost_scope)
    if(!$p.positive_contribution){$text+=' '+(Get-UiText 'econ.nonpositive' 'Additional sales do not create positive unit contribution under these inputs.')}
    return $text
}
function Save-LocalEconomicsScenario($Fields,$ExpectedBinding=$null) {
    if($null-eq$script:Current-or$script:Dirty-or$script:PublicationDirty){throw 'Open and save the current concept and listing first.'}
    $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;$binding=Get-LocalEconomicsBinding $lc
    $identity=Get-LocalCurrentRevisionIdentity $script:Current.concept
    if($identity.id-cne$binding.revision_id-or$identity.hash-cne$binding.revision_hash){throw 'The saved concept changed; refresh before saving economics.'}
    if($null-ne$ExpectedBinding-and($ExpectedBinding|ConvertTo-Json -Depth 20 -Compress)-cne($binding|ConvertTo-Json -Depth 20 -Compress)){throw 'Artwork, listing or channel changed while the economics form was open. Reopen it to review the new target.'}
    $plan=New-LocalEconomicsScenario $Fields $binding
    $prior=Get-LocalEconomicsSnapshot $lc
    if($prior.evaluated-and($prior.scenario.inputs|ConvertTo-Json -Depth 10 -Compress)-ceq($plan.inputs|ConvertTo-Json -Depth 10 -Compress)){
        $PublicationEconomics.Text=Format-LocalEconomicsSnapshot $prior
        return $prior.scenario
    }
    Add-OrSetProperty $lc 'economics_scenario' $plan;Invalidate-LocalCorePackages $lc 'economics_scenario_changed';Write-LocalCoreState $s
    $PublicationEconomics.Text=Format-LocalEconomicsSnapshot (Get-LocalEconomicsSnapshot $lc)
    return $plan
}
function New-LocalEconomicsDialog($Lc) {
    $binding=Get-LocalEconomicsBinding $Lc
    $esc={param([string]$s) [Security.SecurityElement]::Escape($s)}
    $labels=[ordered]@{Currency='Currency code (one currency for all amounts)';Price='Sale price from the cited source';Royalty='Royalty per unit from the cited source';Variable='Additional cost per unit (not already deducted from royalty)';Fixed='Fixed cost to recover';Source='Price / royalty source reference';Observed='Source date (YYYY-MM-DD)';Scope='Costs included and costs still excluded'}
    $fields='';foreach($k in $labels.Keys){$fields+='<TextBlock Text="'+(& $esc (Get-UiText ('econ.field.'+$k) $labels[$k]))+'" Margin="0,9,0,3"/><TextBox x:Name="'+$k+'"/>'}
    $x=@"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" Title="$(& $esc (Get-UiText 'econ.title' 'Economics scenario'))" Width="640" Height="740" MinWidth="480" MinHeight="420" ShowInTaskbar="False" WindowStartupLocation="CenterOwner">
<Grid Margin="16"><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
<TextBlock Text="$(& $esc ((Get-UiText 'econ.intro' 'Explicit assumptions for {0} / {1}. Blank costs are unknown; enter zero only when intended. Use one currency and avoid counting platform production costs again if already deducted from the royalty. Nothing here approves a design or predicts sales.')-f$binding.marketplace,$binding.product_type_key))" TextWrapping="Wrap" Margin="0,0,0,8"/>
<ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto"><StackPanel>$fields</StackPanel></ScrollViewer>
<StackPanel Grid.Row="2" Margin="0,10,0,0"><CheckBox x:Name="Explicit" Content="$(& $esc (Get-UiText 'econ.explicit' 'These are my explicit scenario inputs; their completeness is not independently verified.'))"/><TextBlock x:Name="ErrorText" Foreground="#FFFF8A80" TextWrapping="Wrap" Margin="0,6,0,0"/><StackPanel Orientation="Horizontal" HorizontalAlignment="Right" Margin="0,8,0,0"><Button x:Name="Save" Content="$(& $esc (Get-UiText 'chk.ok' 'Save'))" MinWidth="110" IsDefault="True" Margin="0,0,8,0"/><Button x:Name="Cancel" Content="$(& $esc (Get-UiText 'chk.cancel' 'Cancel'))" MinWidth="110" IsCancel="True"/></StackPanel></StackPanel></Grid></Window>
"@
    $dialog=[Windows.Markup.XamlReader]::Parse($x)
    try{if($Window.IsLoaded){$dialog.Owner=$Window};$dialog.Background=$Window.Background;$dialog.Foreground=$Window.Foreground;$dialog.Resources.MergedDictionaries.Add($Window.Resources)}catch{}
    $snapshot=Get-LocalEconomicsSnapshot $Lc
    if($snapshot.evaluated){$inputs=$snapshot.scenario.inputs;$mapping=@{Currency='currency';Price='sale_price';Royalty='royalty_per_unit';Variable='additional_cost_per_unit';Fixed='fixed_cost';Source='source_ref';Observed='observed_on';Scope='cost_scope'};foreach($k in $mapping.Keys){$dialog.FindName($k).Text=[string](Get-PropertyValue $inputs $mapping[$k])}}
    $dialog.Tag=[pscustomobject]@{binding=$binding;fields=$null}
    return $dialog
}
function Read-LocalEconomicsDialog($Dialog) {
    $fields=[ordered]@{};$mapping=@{Currency='currency';Price='sale_price';Royalty='royalty_per_unit';Variable='additional_cost_per_unit';Fixed='fixed_cost';Source='source_ref';Observed='observed_on';Scope='cost_scope'}
    foreach($k in $mapping.Keys){$fields[$mapping[$k]]=[string]$Dialog.FindName($k).Text}
    return [pscustomobject]$fields
}
function Complete-LocalEconomicsDialog($Dialog,[bool]$Modal=$true) {
    try{
        if(!$Dialog.FindName('Explicit').IsChecked){throw (Get-UiText 'econ.confirm_required' 'Confirm that the inputs are your explicit scenario assumptions.')}
        $fields=Read-LocalEconomicsDialog $Dialog
        $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s
        $binding=Get-LocalEconomicsBinding $lc
        if(($Dialog.Tag.binding|ConvertTo-Json -Depth 20 -Compress)-cne($binding|ConvertTo-Json -Depth 20 -Compress)){throw 'Artwork, listing or channel changed while this form was open. Reopen it to review the new target.'}
        $null=New-LocalEconomicsScenario $fields $binding
        $Dialog.Tag.fields=$fields;$Dialog.FindName('ErrorText').Text='';if($Modal){$Dialog.DialogResult=$true};return $true
    }catch{$Dialog.Tag.fields=$null;$Dialog.FindName('ErrorText').Text=$_.Exception.Message;return $false}
}
function Connect-LocalEconomicsDialog($Dialog,[bool]$Modal=$true) {
    $Dialog.FindName('Save').Add_Click({$null=Complete-LocalEconomicsDialog $Dialog $Modal}.GetNewClosure())
}
function Invoke-LocalEconomicsDialog {
    try{
        if($null-eq$script:Current-or$script:Dirty-or$script:PublicationDirty){throw 'Save the current concept and listing first.'}
        $s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s
        $dialog=New-LocalEconomicsDialog $lc
        Connect-LocalEconomicsDialog $dialog
        if($dialog.ShowDialog()-eq$true){$null=Save-LocalEconomicsScenario $dialog.Tag.fields $dialog.Tag.binding;$StatusText.Text=Get-UiText 'econ.saved' 'Economics scenario saved for the exact current artwork and listing; no design approval or publication occurred.'}
    }catch{Show-Error $_.Exception.Message}
}
