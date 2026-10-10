# Merch Forge · Portfolio pipeline board
# Read-only: where every idea stands (decision -> artwork -> checks -> package -> published) and what the next step is.
# Built only from LocalCore state and the Ideas list. Nothing is fabricated; nothing here generates, accepts or publishes.

$script:PipelineOpening = $false
$script:PipelineStageOrder = @('package_ready','checks_ready','artwork_accepted','keep_no_artwork','undecided','edit','regen','published','skip')

function Register-PipelineUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{
            'pipe.title'='Pipeline'; 'pipe.next'='Next actions'; 'pipe.niches'='Decisions by niche';
            'pipe.summary'='{0} idea(s) · {1} need a decision · {2} kept · {3} parked (SKIP) · {4} research draft(s)';
            'pipe.k.undecided'='No decision'; 'pipe.k.keep'='KEEP'; 'pipe.k.artwork'='Artwork accepted'; 'pipe.k.checks'='Checks passed'; 'pipe.k.package'='Package ready'; 'pipe.k.published'='Published';
            'pipe.s.undecided'='No decision'; 'pipe.s.edit'='EDIT'; 'pipe.s.regen'='REGEN'; 'pipe.s.skip'='SKIP'; 'pipe.s.keep_no_artwork'='KEEP · no artwork'; 'pipe.s.artwork_accepted'='Artwork accepted'; 'pipe.s.checks_ready'='Checks passed'; 'pipe.s.package_ready'='Package ready'; 'pipe.s.published'='Published';
            'pipe.n.undecided'='Review the idea: KEEP, EDIT, REGEN or SKIP.'; 'pipe.n.edit'='Rewrite the idea, then decide again.'; 'pipe.n.regen'='Make new artwork for this idea.';
            'pipe.n.keep_no_artwork'='Export the brief, then import or generate artwork and accept one.'; 'pipe.n.artwork_accepted'='Complete the checks (IP, print, policy, metadata).';
            'pipe.n.checks_ready'='Build the manual-upload package.'; 'pipe.n.package_ready'='Upload manually, then import the publication receipt.'; 'pipe.n.published'='Import sales to track it.'; 'pipe.n.skip'='Parked.';
            'biz.home.linked'='Verified linked import · 7d: {0} sale(s), ${1:0.00} · 30d: {2}, ${3:0.00} · 90d: {4}, ${5:0.00}'; 'biz.home.unlinked'='Imported data is not linked to a verified Forge publication receipt; {0} row(s) excluded.'; 'biz.home.none'='Import a sales/royalty CSV to populate local performance.';
            'biz.portfolio.local'='Local core: {0} accepted design(s), {1} valid package(s), {2} verified published product(s). Live listing health is not fabricated.'; 'biz.receipts.some'='Verified published products: {0} · channels: {1}'; 'biz.receipts.none'='No verified local publication receipt imported.';
            'biz.perf.linked'='Verified linked sales rows: {0}. 30-day units: {1}; royalties: ${2:0.00}.'; 'biz.perf.unlinked'='No imported sales rows match a verified Forge product ID. Unlinked rows: {0}.'; 'biz.perf.none'='No local sales CSV imported yet.';
            'biz.sales.some'='Imported: {0} · linked: {1} · unlinked: {2} · undated linked: {3} · future linked: {4}'; 'biz.sales.none'='No local sales data imported.';
            'pipe.empty'='No ideas yet. Create a draft from Discover or reconnect to load ideas.'; 'pipe.draft'='research draft'; 'pipe.niche.none'='(no niche)'
        }
        ru=@{
            'pipe.title'='Конвейер'; 'pipe.next'='Следующие шаги'; 'pipe.niches'='Решения по нишам';
            'pipe.summary'='Идей: {0} · ждут решения: {1} · оставлено: {2} · отложено (ПРОПУСТИТЬ): {3} · черновиков исследования: {4}';
            'pipe.k.undecided'='Без решения'; 'pipe.k.keep'='ОСТАВИТЬ'; 'pipe.k.artwork'='Макет принят'; 'pipe.k.checks'='Проверки пройдены'; 'pipe.k.package'='Пакет готов'; 'pipe.k.published'='Опубликовано';
            'pipe.s.undecided'='Без решения'; 'pipe.s.edit'='ИЗМЕНИТЬ'; 'pipe.s.regen'='ЗАНОВО'; 'pipe.s.skip'='ПРОПУСТИТЬ'; 'pipe.s.keep_no_artwork'='ОСТАВИТЬ · нет макета'; 'pipe.s.artwork_accepted'='Макет принят'; 'pipe.s.checks_ready'='Проверки пройдены'; 'pipe.s.package_ready'='Пакет готов'; 'pipe.s.published'='Опубликовано';
            'pipe.n.undecided'='Посмотрите идею: ОСТАВИТЬ, ИЗМЕНИТЬ, ЗАНОВО или ПРОПУСТИТЬ.'; 'pipe.n.edit'='Перепишите идею и решите снова.'; 'pipe.n.regen'='Сделайте новый макет для этой идеи.';
            'pipe.n.keep_no_artwork'='Экспортируйте бриф, затем импортируйте или сгенерируйте макет и примите один.'; 'pipe.n.artwork_accepted'='Пройдите проверки (IP, печать, политика, метаданные).';
            'pipe.n.checks_ready'='Соберите пакет для ручной загрузки.'; 'pipe.n.package_ready'='Загрузите вручную, затем импортируйте квитанцию публикации.'; 'pipe.n.published'='Импортируйте продажи, чтобы отслеживать.'; 'pipe.n.skip'='Отложено.';
            'biz.home.linked'='Проверенный импорт · 7 дн.: {0} прод., ${1:0.00} · 30 дн.: {2}, ${3:0.00} · 90 дн.: {4}, ${5:0.00}'; 'biz.home.unlinked'='Импортированные данные не связаны с проверенной квитанцией публикации Forge; исключено строк: {0}.'; 'biz.home.none'='Импортируйте CSV с продажами и роялти, чтобы заполнить результаты.';
            'biz.portfolio.local'='Локально: принятых макетов {0}, действующих пакетов {1}, проверенных опубликованных товаров {2}. Состояние карточек не выдумывается.'; 'biz.receipts.some'='Проверенных опубликованных товаров: {0} · площадок: {1}'; 'biz.receipts.none'='Проверенных квитанций публикации пока нет.';
            'biz.perf.linked'='Проверенных строк продаж: {0}. Продаж за 30 дней: {1}; роялти: ${2:0.00}.'; 'biz.perf.unlinked'='Ни одна строка продаж не совпала с проверенным товаром Forge. Несвязанных строк: {0}.'; 'biz.perf.none'='CSV с продажами ещё не импортирован.';
            'biz.sales.some'='Импортировано: {0} · связано: {1} · не связано: {2} · без даты: {3} · с будущей датой: {4}'; 'biz.sales.none'='Данные о продажах не импортированы.';
            'pipe.empty'='Идей пока нет. Создайте черновик в «Поиске» или подключитесь, чтобы загрузить идеи.'; 'pipe.draft'='черновик исследования'; 'pipe.niche.none'='(без ниши)'
        }
        es=@{
            'pipe.title'='Flujo'; 'pipe.next'='Próximos pasos'; 'pipe.niches'='Decisiones por nicho';
            'pipe.summary'='{0} idea(s) · {1} sin decisión · {2} mantenidas · {3} aparcadas (OMITIR) · {4} borrador(es) de investigación';
            'pipe.k.undecided'='Sin decisión'; 'pipe.k.keep'='MANTENER'; 'pipe.k.artwork'='Arte aceptado'; 'pipe.k.checks'='Revisiones superadas'; 'pipe.k.package'='Paquete listo'; 'pipe.k.published'='Publicado';
            'pipe.s.undecided'='Sin decisión'; 'pipe.s.edit'='EDITAR'; 'pipe.s.regen'='REGENERAR'; 'pipe.s.skip'='OMITIR'; 'pipe.s.keep_no_artwork'='MANTENER · sin arte'; 'pipe.s.artwork_accepted'='Arte aceptado'; 'pipe.s.checks_ready'='Revisiones superadas'; 'pipe.s.package_ready'='Paquete listo'; 'pipe.s.published'='Publicado';
            'pipe.n.undecided'='Revisa la idea: MANTENER, EDITAR, REGENERAR u OMITIR.'; 'pipe.n.edit'='Reescribe la idea y decide de nuevo.'; 'pipe.n.regen'='Crea arte nuevo para esta idea.';
            'pipe.n.keep_no_artwork'='Exporta el brief, importa o genera arte y acepta uno.'; 'pipe.n.artwork_accepted'='Completa las revisiones (IP, impresión, política, metadatos).';
            'pipe.n.checks_ready'='Crea el paquete de carga manual.'; 'pipe.n.package_ready'='Súbelo manualmente e importa el recibo de publicación.'; 'pipe.n.published'='Importa ventas para seguirlo.'; 'pipe.n.skip'='Aparcado.';
            'biz.home.linked'='Importación verificada · 7 d: {0} venta(s), ${1:0.00} · 30 d: {2}, ${3:0.00} · 90 d: {4}, ${5:0.00}'; 'biz.home.unlinked'='Los datos importados no están vinculados a un recibo de publicación verificado; {0} fila(s) excluida(s).'; 'biz.home.none'='Importa un CSV de ventas y regalías para ver resultados.';
            'biz.portfolio.local'='Local: {0} diseño(s) aceptado(s), {1} paquete(s) válido(s), {2} producto(s) publicado(s) verificado(s). El estado de las fichas no se inventa.'; 'biz.receipts.some'='Productos publicados verificados: {0} · canales: {1}'; 'biz.receipts.none'='Aún no hay recibos de publicación verificados.';
            'biz.perf.linked'='Filas de ventas verificadas: {0}. Unidades en 30 días: {1}; regalías: ${2:0.00}.'; 'biz.perf.unlinked'='Ninguna fila de ventas coincide con un producto verificado de Forge. Filas sin vincular: {0}.'; 'biz.perf.none'='Aún no se ha importado ningún CSV de ventas.';
            'biz.sales.some'='Importadas: {0} · vinculadas: {1} · sin vincular: {2} · sin fecha: {3} · con fecha futura: {4}'; 'biz.sales.none'='No hay datos de ventas importados.';
            'pipe.empty'='Aún no hay ideas. Crea un borrador desde Descubrir o reconecta para cargar ideas.'; 'pipe.draft'='borrador de investigación'; 'pipe.niche.none'='(sin nicho)'
        }
    }
    foreach($loc in $texts.Keys){ if($null -eq $script:UiText[$loc]){$script:UiText[$loc]=@{}}; foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]} }
    # Static XAML captions on Portfolio that had no translation.
    if($null -ne $script:StaticUiTranslations){
        $static=@{ ru=@{'Products'='Товары';'Channels'='Площадки';'Listing health'='Состояние карточек'}; es=@{'Products'='Productos';'Channels'='Canales';'Listing health'='Estado de fichas'} }
        foreach($loc in $static.Keys){ if($null -ne $script:StaticUiTranslations[$loc]){ foreach($k in $static[$loc].Keys){ if(-not $script:StaticUiTranslations[$loc].ContainsKey($k)){$script:StaticUiTranslations[$loc][$k]=$static[$loc][$k]} } } }
    }
}

# ---------- pure computation (headless-testable) ----------
function Get-ForgePipelineStage($State,$Lc,[string]$ConceptKey,$Concept=$null) {
    # Returns one of: undecided, edit, regen, skip, keep_no_artwork, artwork_accepted, checks_ready, package_ready, published
    if($null -eq $Lc){return 'undecided'}
    $published=$false
    foreach($r in @(Get-PropertyValue $State 'publication_receipts')){
        if($null -eq $r){continue}
        if([string](Get-PropertyValue $r 'concept_key') -eq $ConceptKey){ try{ if(Test-LocalPublicationReceiptAuthority $State $r){$published=$true;break} }catch{} }
    }
    if($published){return 'published'}
    $rid=[string](Get-PropertyValue $Lc 'source_revision_id'); $rhash=[string](Get-PropertyValue $Lc 'source_revision_hash')
    foreach($p in @(Get-PropertyValue $Lc 'packages')){
        if($null -eq $p){continue}
        if([bool](Get-PropertyValue $p 'valid') -and [string](Get-PropertyValue $p 'status') -eq 'READY_FOR_MANUAL_UPLOAD' -and [string](Get-PropertyValue $p 'concept_revision_id') -eq $rid -and [string](Get-PropertyValue $p 'revision_hash') -eq $rhash){return 'package_ready'}
    }
    $acc=Get-PropertyValue $Lc 'active_acceptance'
    if($null -ne $acc -and [string](Get-PropertyValue $acc 'concept_revision_id') -eq $rid -and [string](Get-PropertyValue $acc 'revision_hash') -eq $rhash){
        $ready=$false; try{ $gate=Get-LocalCheckGateSnapshot $Lc; $ready=[bool](Get-PropertyValue $gate 'all_ready') }catch{}
        if($ready){return 'checks_ready'}; return 'artwork_accepted'
    }
    $rec=Get-LocalOwnerDecisionRecord $ConceptKey $Concept $State
    switch([string]$rec.decision){ 'KEEP'{return 'keep_no_artwork'} 'EDIT'{return 'edit'} 'REGEN'{return 'regen'} 'SKIP'{return 'skip'} default{return 'undecided'} }
}
function Get-ForgePortfolioPipeline($State,$Queue) {
    $rows=New-Object System.Collections.Generic.List[object]; $seen=@{}
    $count=@{}; foreach($s in $script:PipelineStageOrder){$count[$s]=0}
    $niches=@{}; $drafts=0
    foreach($item in @($Queue)){
        if($null -eq $item){continue}
        $key=([string](Get-PropertyValue $item 'concept_key')).Trim(); if([string]::IsNullOrWhiteSpace($key) -or $seen.ContainsKey($key)){continue}; $seen[$key]=$true
        $isDraft=[bool](Get-PropertyValue $item 'is_local_draft'); if($isDraft){$drafts++}
        $lc=Get-LocalCoreConcept $key $State
        $concept=$null; if($null -ne $script:Current -and [string](Get-PropertyValue $script:Current.concept 'concept_key') -eq $key){$concept=$script:Current.concept}
        $stage=Get-ForgePipelineStage $State $lc $key $concept
        $count[$stage]++
        $niche=([string](Get-PropertyValue $item 'niche_name')).Trim(); if([string]::IsNullOrWhiteSpace($niche)){$niche=''}
        if(-not $niches.ContainsKey($niche)){$niches[$niche]=[ordered]@{keep=0;edit=0;regen=0;skip=0;undecided=0;total=0}}
        $n=$niches[$niche]; $n.total++
        switch($stage){ 'undecided'{$n.undecided++} 'edit'{$n.edit++} 'regen'{$n.regen++} 'skip'{$n.skip++} default{$n.keep++} }
        $score=0.0; try{$score=[double](Get-PropertyValue $item 'score_total')}catch{}
        $rows.Add([pscustomobject]@{concept_key=$key;title=[string](Get-PropertyValue $item 'title');niche_name=$niche;stage=$stage;stage_rank=[array]::IndexOf($script:PipelineStageOrder,$stage);score_total=$score;is_local_draft=$isDraft;queue_item=$item})
    }
    $keptOrLater=0; foreach($s in @('keep_no_artwork','artwork_accepted','checks_ready','package_ready','published')){$keptOrLater+=$count[$s]}
    $artworkOrLater=$count['artwork_accepted']+$count['checks_ready']+$count['package_ready']+$count['published']
    $checksOrLater=$count['checks_ready']+$count['package_ready']+$count['published']
    $nicheRows=@(); foreach($k in ($niches.Keys | Sort-Object)){ $v=$niches[$k]; $nicheRows+=[pscustomobject]@{niche_name=$k;keep=$v.keep;edit=$v.edit;regen=$v.regen;skip=$v.skip;undecided=$v.undecided;total=$v.total} }
    $sorted=@($rows | Sort-Object @{Expression='stage_rank';Descending=$false},@{Expression='score_total';Descending=$true},title)
    return [pscustomobject]@{
        rows=$sorted
        summary=[pscustomobject]@{ideas=$rows.Count;undecided=$count['undecided'];kept_or_later=$keptOrLater;edit=$count['edit'];regen=$count['regen'];skip=$count['skip'];artwork_or_later=$artworkOrLater;checks_or_later=$checksOrLater;package_ready=$count['package_ready'];published=$count['published'];drafts=$drafts}
        niches=$nicheRows
    }
}

# ---------- UI ----------
function Update-PortfolioPipelineSurface {
    if($null -eq $PortfolioPipelineList){return}
    $state=$null; try{$state=Read-LocalCoreState}catch{Write-AppLog 'WARN' ('Pipeline: local state unavailable: '+$_.Exception.Message);return}
    $p=Get-ForgePortfolioPipeline $state $script:Queue
    $s=$p.summary
    $PortfolioPipelineTitle.Text=Get-UiText 'pipe.title' 'Pipeline'; $PortfolioNextTitle.Text=Get-UiText 'pipe.next' 'Next actions'; $PortfolioNicheTitle.Text=Get-UiText 'pipe.niches' 'Decisions by niche'
    $PortfolioPipelineSummary.Text=if($s.ideas -gt 0){(Get-UiText 'pipe.summary' '{0} idea(s)') -f $s.ideas,$s.undecided,$s.kept_or_later,$s.skip,$s.drafts}else{Get-UiText 'pipe.empty' 'No ideas yet.'}
    $pairs=@(@($PipeUndecidedLabel,'pipe.k.undecided',$PipeUndecidedValue,$s.undecided),@($PipeKeepLabel,'pipe.k.keep',$PipeKeepValue,$s.kept_or_later),@($PipeArtworkLabel,'pipe.k.artwork',$PipeArtworkValue,$s.artwork_or_later),@($PipeChecksLabel,'pipe.k.checks',$PipeChecksValue,$s.checks_or_later),@($PipePackageLabel,'pipe.k.package',$PipePackageValue,$s.package_ready),@($PipePublishedLabel,'pipe.k.published',$PipePublishedValue,$s.published))
    foreach($x in $pairs){ if($null -ne $x[0]){$x[0].Text=Get-UiText ([string]$x[1]) ''}; if($null -ne $x[2]){$x[2].Text=[string][int]$x[3]} }
    $display=@()
    foreach($r in @($p.rows)){
        if($r.stage -eq 'skip'){continue}
        $meta=@(); if($r.niche_name){$meta+=$r.niche_name}; if($r.is_local_draft){$meta+=(Get-UiText 'pipe.draft' 'research draft')}
        $meta+=(Get-UiText ('pipe.n.'+$r.stage) '')
        $display+=[pscustomobject]@{concept_key=$r.concept_key;title=$r.title;stage=$r.stage;stage_label=(Get-UiText ('pipe.s.'+$r.stage) $r.stage);next_label=($meta -join ' · ');queue_item=$r.queue_item}
    }
    $PortfolioPipelineList.ItemsSource=$display
    $lines=New-Object System.Collections.Generic.List[string]
    foreach($n in @($p.niches)){ $name=if($n.niche_name){$n.niche_name}else{Get-UiText 'pipe.niche.none' '(no niche)'}; [void]$lines.Add(('{0}: KEEP {1} · EDIT {2} · REGEN {3} · SKIP {4} · {5} {6}' -f $name,$n.keep,$n.edit,$n.regen,$n.skip,(Get-UiText 'pipe.k.undecided' 'No decision'),$n.undecided)) }
    $PortfolioNicheText.Text=if($lines.Count){$lines -join [Environment]::NewLine}else{'—'}
}
function Open-PortfolioPipelineSelection {
    if($null -eq $PortfolioPipelineList -or $script:PipelineOpening){return}
    $sel=$PortfolioPipelineList.SelectedItem; if($null -eq $sel){return}
    $script:PipelineOpening=$true
    try {
        $script:ProductSection='ideas'; Open-ConceptItem $sel.queue_item
        # Open-ConceptItem returns early when the idea is already open; make sure we still land on it.
        if($null -ne $script:Current -and [string](Get-PropertyValue $script:Current.concept 'concept_key') -eq [string]$sel.concept_key){Show-ProductSection 'ideas'}
    } catch { Show-Error ('Could not open the idea: '+$_.Exception.Message) } finally { $script:PipelineOpening=$false }
}
