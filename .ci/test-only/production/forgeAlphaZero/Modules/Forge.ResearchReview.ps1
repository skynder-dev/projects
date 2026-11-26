. (Join-Path $PSScriptRoot 'Forge.OwnerLanguage.ps1')
# Review overlay never edits model output or upgrades research_verified.
function Register-NicheEvidenceUiText {
 if($null-eq$script:UiText){return}
 $translations=@{
 en=@{refresh='Refresh niche evidence (no AI)';header='LATEST PRODUCT EVIDENCE FOR ORIGINAL RESEARCH TOPIC';audience='AUDIENCE: official activity context only; apparel buyers and motives unverified.';products='PRODUCT EXISTENCE: captured Zazzle listing text only; not images or purchases.';unavailable='PRODUCT EXISTENCE: source unavailable; not checked, not a zero-product observation.';empty='PRODUCT EXISTENCE: no eligible products observed in this bounded capture; absence is not established.';demand='DEMAND: no Amazon sales or purchase evidence; unverified.';compare='WHY / NEXT STEP: suitable for bounded title comparison only; no market-entry conclusion.';hold='WHY / NEXT STEP: insufficient distinct relevant title/creator records; keep the niche unverified.';limits='Creator labels and product IDs are not verified independent sellers or distinct designs. Lexical filtering is not semantic buyer verification. Observations older than one day are excluded; opening a card does not fetch sources. Counts and popularity ordering do not prove demand.'}
 ru=@{refresh='Обновить основания ниш (без AI)';header='ПОСЛЕДНЯЯ ПРОВЕРКА ТОВАРНЫХ ОСНОВАНИЙ ИСХОДНОЙ ТЕМЫ';audience='АУДИТОРИЯ: подтверждён только контекст занятия; покупатели футболок и их мотивы не исследованы.';products='НАЛИЧИЕ ТОВАРОВ: получен текст карточек Zazzle; это не изображения и не покупки.';unavailable='НАЛИЧИЕ ТОВАРОВ: источник недоступен; наличие не проверено. Это не нулевая выборка.';empty='НАЛИЧИЕ ТОВАРОВ: в ограниченной выборке нет пригодных записей; отсутствие товаров не доказано.';demand='СПРОС: данных о продажах или покупках Amazon нет; спрос не подтверждён.';compare='ПОЧЕМУ / ДАЛЬШЕ: достаточно только для ограниченного сравнения названий, не для вывода о выходе на рынок.';hold='ПОЧЕМУ / ДАЛЬШЕ: недостаточно разных подходящих названий и авторов; ниша остаётся неподтверждённой.';limits='Имена авторов и ID товаров не доказывают независимость продавцов или различие дизайнов. Лексический отбор не проверяет смысл для покупателя. Записи старше суток исключаются; открытие карточки не запрашивает источник. Количество и порядок popularity не подтверждают спрос.'}
 es=@{refresh='Actualizar pruebas de nichos (sin IA)';header='PRUEBAS DE PRODUCTOS DEL TEMA ORIGINAL';audience='AUDIENCIA: solo contexto de actividad; compradores y motivos sin verificar.';products='EXISTENCIA: texto de anuncios de Zazzle; no imágenes ni compras.';unavailable='EXISTENCIA: fuente inaccesible; sin comprobar, no es una muestra de cero productos.';empty='EXISTENCIA: no se observaron productos aptos en esta muestra limitada; no demuestra ausencia.';demand='DEMANDA: sin pruebas de ventas o compras en Amazon; no verificada.';compare='MOTIVO / SIGUIENTE PASO: comparación limitada de títulos; sin conclusión comercial.';hold='MOTIVO / SIGUIENTE PASO: faltan títulos/autores distintos y pertinentes; nicho sin verificar.';limits='Autores e IDs no demuestran vendedores independientes ni diseños distintos. Cantidad y orden popularity no prueban demanda.'}
 }
 foreach($locale in $translations.Keys){if($null-eq$script:UiText[$locale]){$script:UiText[$locale]=@{}};foreach($key in $translations[$locale].Keys){$script:UiText[$locale]['niche.evidence.'+$key]=$translations[$locale][$key]}}
 $reasons=@{
 en=@{eligible_title_sample='Fully matching T-shirt title';partial_topic_review='Only part of the topic matches';off_topic='No topic match';product_type_unverified='T-shirt product type not confirmed';mixed_theme_or_time_specific_review='Different co-theme, event or year needs review';duplicate_product='Duplicate product identity';source_text_encoding_review='Source title has encoding artifacts';stale_or_undated_observation_review='Stale or undated observation';captured_product_metadata='Listing metadata captured';captured_zero_items='RSS returned zero item records';source_unavailable='Source unavailable; not a zero result';source_refused_no_retry_or_bypass='Source refused; stopped without retry';not_requested_after_source_refusal='Not requested after source refusal'}
 ru=@{eligible_title_sample='Полное совпадение темы и типа футболки';partial_topic_review='Совпала только часть темы';off_topic='Тема не совпала';product_type_unverified='Тип товара «футболка» не подтверждён';mixed_theme_or_time_specific_review='Другая совместная тема, событие или год — нужна проверка';duplicate_product='Повтор того же товара';source_text_encoding_review='Артефакты кодировки в названии источника';stale_or_undated_observation_review='Устаревшая запись или неизвестная дата';captured_product_metadata='Товарные записи получены';captured_zero_items='RSS вернул ноль товарных записей';source_unavailable='Источник недоступен — это не нулевой результат';source_refused_no_retry_or_bypass='Источник отказал; остановлено без повтора';not_requested_after_source_refusal='Не запрашивалось после отказа источника'}
 es=@{eligible_title_sample='Título de camiseta coincidente';partial_topic_review='Coincidencia parcial del tema';off_topic='Tema distinto';product_type_unverified='Tipo camiseta no confirmado';mixed_theme_or_time_specific_review='Otro tema, evento o año; revisar';duplicate_product='Producto duplicado';source_text_encoding_review='Errores de codificación en el título';stale_or_undated_observation_review='Observación antigua o sin fecha';captured_product_metadata='Anuncios capturados';captured_zero_items='RSS devolvió cero anuncios';source_unavailable='Fuente inaccesible; no es resultado cero';source_refused_no_retry_or_bypass='Fuente rechazó; sin reintento';not_requested_after_source_refusal='No solicitado tras el rechazo'}
 }
 foreach($locale in $reasons.Keys){foreach($key in $reasons[$locale].Keys){$script:UiText[$locale]['niche.evidence.row.'+$key]=$reasons[$locale][$key]}}
 $script:UiText.en['niche.evidence.origin.bundle']='Bundled public-source capture; opening did not refresh the source.';$script:UiText.en['niche.evidence.origin.local']='Saved local public-source capture; original dates retained.'
 $script:UiText.ru['niche.evidence.origin.bundle']='Публичный снимок из пакета; открытие не обновляет источник.';$script:UiText.ru['niche.evidence.origin.local']='Сохранённый локальный публичный снимок; исходные даты сохранены.'
 $script:UiText.es['niche.evidence.origin.bundle']='Captura pública incluida; abrir no actualiza la fuente.';$script:UiText.es['niche.evidence.origin.local']='Captura pública local guardada; fechas originales conservadas.'
 $script:UiText.en['niche.evidence.storage_error']='Source evidence storage is unavailable or incomplete; existing reports retained. Refresh sources on Home or restore a verified data copy. No current product/demand confidence is inferred.'
 $script:UiText.ru['niche.evidence.storage_error']='Хранилище оснований недоступно или неполно; отчёты сохранены. Обновите источники на Home или восстановите проверенную копию данных. Достоверного текущего вывода о товарах и спросе нет.'
 $script:UiText.es['niche.evidence.storage_error']='Pruebas inaccesibles o incompletas; informes conservados. Actualiza fuentes en Home o restaura una copia verificada. Sin conclusión actual sobre productos o demanda.'
}
function Format-ForgeLatestNicheEvidenceForDraft($Draft,[switch]$Compact,[switch]$Summary) {
 try{
  $report=Read-ForgeLatestNicheEvidence;if($null-eq$report){return 'Свежая выборка товаров ещё не собрана. Её можно обновить на главной без AI; открытие карточки не обновляет источники.'}
  $packet=Get-PropertyValue (Get-PropertyValue $Draft 'provenance') 'research_packet';$text=(@(Get-PropertyValue $packet 'rows'|ForEach-Object{[string](Get-PropertyValue $_ 'query')})-join' ')+' '+[string](Get-PropertyValue $Draft.provenance 'niche_name')
  $key=if($text-match'(?i)garden|grower|container'){'urban_gardening'}elseif($text-match'(?i)stargaz|astronom|observing|night.sky'){'night_sky'}else{''}
  $origin=if([string](Get-PropertyValue $report 'display_origin')-ceq'bundled_public_capture'){Get-UiText 'niche.evidence.origin.bundle' 'Bundled public-source capture; opening did not refresh the source.'}else{Get-UiText 'niche.evidence.origin.local' 'Saved local public-source capture; original dates retained.'}
  $matches=@($report.topics|Where-Object{$_.key-ceq$key});if($matches.Count-ne1){return 'Последняя проверка товаров не охватывает исходную тему этой карточки. Вывода о спросе нет.'};$topic=$matches[0];$r=$topic.assessment
  $lines=@((Get-UiText 'niche.evidence.header' 'LATEST PRODUCT EVIDENCE FOR ORIGINAL RESEARCH TOPIC')+': '+$topic.name,
   ($origin+' Дата отчёта '+$report.completed_at+'; состояние выборки: '+$r.sample_status+'. Сохранено записей: '+$r.captured_records+'; подходящих уникальных товаров-футболок: '+$r.eligible_unique_products+'; авторов подходящих записей: '+$r.distinct_eligible_creators+'.'),
   (Get-UiText 'niche.evidence.audience' 'AUDIENCE: context only'),
   (Get-UiText ('niche.evidence.'+$(if([string](Get-PropertyValue $topic 'source_coverage')-ceq'source_unavailable_not_a_zero_sample'){'unavailable'}elseif(!$r.eligible_unique_products){'empty'}else{'products'})) 'PRODUCT EXISTENCE: limited observations'),
   (Get-UiText 'niche.evidence.demand' 'DEMAND: unverified'),
   (Get-UiText ('niche.evidence.'+$(if($r.comparison_eligible){'compare'}else{'hold'})) $r.selection_reason),
   (Get-UiText 'niche.evidence.limits' 'No demand, approval or generation is granted.'))
  if($Summary){return ($lines[0..5]-join"`r`n")}
  foreach($query in $topic.query_reports){$lines+=('Поисковый запрос (оригинал): '+$query.query+' | '+(Get-UiText ('niche.evidence.row.'+$query.status) $query.status)+' | дата сбора: '+[string](Get-PropertyValue $query 'captured_at')+' | '+[string](Get-PropertyValue $query 'source_url'))}
  if(!$Compact){foreach($row in $r.row_reviews){$lines+=((Get-UiText ('niche.evidence.row.'+$row.status) $row.status)+' | '+$row.title+' | '+$row.source_url)}}
  return ($lines-join"`r`n")
 }catch{return (Get-UiText 'niche.evidence.storage_error' 'Source evidence storage unavailable; reports retained. Refresh sources on Home or restore a verified data copy. No demand confidence is inferred.')}
}
function Get-ForgePreparedAudienceContextText($Draft) {
 try{
  $path=Join-Path (Split-Path $script:ModuleRoot -Parent) 'Data\Forge.PreparedHypotheses.json';$seed=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json
  $reviews=@(Get-PropertyValue $seed 'audience_context_reviews'|Where-Object{$null-ne$_-and$_.concept_key-ceq$Draft.concept_key-and$_.revision_hash-ceq$Draft.current_revision_hash})
  if(!$reviews.Count){return 'Дополнительный официальный контекст аудитории не привязан к точной версии этой карточки.'}
  if($reviews.Count-ne1){throw 'Ambiguous audience review'};$review=$reviews[0]
  if($review.demand_verified-isnot[bool]-or$review.demand_verified-or$review.owner_approved-isnot[bool]-or$review.owner_approved){throw 'Invalid audience review authority'}
  $url=[Uri]$review.source_url;if($url.Scheme-cne'https'-or$url.Host-cnotin@('www.farmers.gov','science.nasa.gov')-or$url.UserInfo){throw 'Unsupported official source'}
  $recheck=Get-PropertyValue $review 'latest_listing_source_check';$latest=''
  if($null-ne$recheck){$latest="`r`n"+'Последняя отдельная проверка источника карточек: '+$recheck.checked_at+' | '+$recheck.status+' | сохранено строк: '+$recheck.rows_retained+' | '+$recheck.source_url+' | '+$recheck.error+"`r`n"+'Это не обновляет даты исходных исторических цитат и не подтверждает рыночный спрос.'}
  return ('Официальный контекст деятельности аудитории (проверен '+$review.checked_at+'; отдельно от исходного сбора карточек): '+(Format-ForgeOwnerOriginal ([string]$review.observed_context))+"`r`n"+$review.source_url+"`r`n"+'Интерпретация / нерешённый вопрос: '+(Format-ForgeOwnerOriginal ([string]$review.decision_note))+"`r`n"+'Граница: наличие деятельности не доказывает спрос на одежду, конкуренцию Amazon, права, цену или роялти. Одобрение и связь с организацией не предоставляются.'+$latest)
 }catch{return 'Дополнительный контекст аудитории не удалось проверить. Спрос и одобрение из этого не следуют.'}
}
function Get-ForgeCardEvidenceReview($Draft,[DateTime]$NowUtc=([DateTime]::UtcNow)) {
 $packet=Get-PropertyValue (Get-PropertyValue $Draft 'provenance') 'research_packet';$rows=@(Get-PropertyValue $packet 'rows'|Where-Object{$null-ne$_})
 $review=@();$channels=@();$ages=@();$contexts=0;$currencies=0
 foreach($row in $rows){
  $kind=[string](Get-PropertyValue $row 'observation_kind');if($kind-ceq'audience_context'){$contexts++}
  $channel=[string](Get-PropertyValue $row 'marketplace');if($channel){$channels+=$channel.ToLowerInvariant()}
  if($kind-ceq'marketplace_listing'-and$null-ne(Get-PropertyValue $row 'price')-and[string](Get-PropertyValue $row 'currency')-cmatch'^[A-Z]{3}$'){$currencies++}
  $ages+=Get-ForgeResearchRowAgeStatus $packet $row $NowUtc
  if($kind-cne'marketplace_listing'){continue}
  $tokens=@(Get-ForgeResearchQueryTokens ([string](Get-PropertyValue $row 'query')));$words=@(Get-ForgeResearchQueryTokens ([string](Get-PropertyValue $row 'title')));$matched=@($tokens|Where-Object{$words-contains$_})
  $fit=if(!$tokens.Count){'query_unknown'}elseif(!$matched.Count){'no_topic_word_overlap'}elseif($matched.Count-eq$tokens.Count){'all_topic_words_overlap'}else{'partial_topic_word_overlap'}
  $review+=[pscustomobject]@{citation=[string](Get-PropertyValue $row 'citation_label');title=[string](Get-PropertyValue $row 'title');query=[string](Get-PropertyValue $row 'query');fit=$fit;matched_tokens=$matched;source_url=[string](Get-PropertyValue $row 'source_url')}
 }
 return [pscustomobject]@{schema='forge.card_evidence_review.v1';captured_rows=$rows.Count;listing_rows=$review.Count;audience_context_rows=$contexts;lexical_review=$review;no_overlap=@($review|Where-Object{$_.fit-ceq'no_topic_word_overlap'}).Count;unknown_query=@($review|Where-Object{$_.fit-ceq'query_unknown'}).Count;ages=@($ages|Sort-Object -Unique);channels=@($channels|Sort-Object -Unique);explicit_currency_prices=$currencies;demand_verified=$false;semantic_relevance_verified=$false;competition_verified=$false;creative_approval_granted=$false}
}
function Format-ForgeCardEvidenceReview($Draft){
 $r=Get-ForgeCardEvidenceReview $Draft
 $ages=@{within_application_age_policy='в пределах принятого срока давности';stale='устарело';unverified_age_policy='правило давности не подтверждено';unverified_timestamp='дата не подтверждена';invalid_future_timestamp='некорректная будущая дата'}
 $fits=@{query_unknown='запрос неизвестен';no_topic_word_overlap='слова темы не совпадают';all_topic_words_overlap='все слова темы совпадают';partial_topic_word_overlap='часть слов темы совпадает'}
 $ageText=@($r.ages|ForEach-Object {if($ages.ContainsKey([string]$_)){$ages[[string]$_]}else{'неизвестный исходный код: '+$_}})-join'; '
 $lines=@('Разбор доказательств (пересчитан; оригиналы наблюдений сохранены).',('Сохранено записей: '+$r.captured_rows+'; карточек товаров: '+$r.listing_rows+'; контекстов деятельности: '+$r.audience_context_rows+'. Давность: '+$ageText+'.'),('Наблюдавшиеся каналы (названия источников): '+(@($r.channels)-join', ')+'. Amazon США — отдельное, непроверенное предположение о канале продажи.'),'Аудитория: контекст деятельности и слова продавцов не доказывают, кто покупает одежду, мотив покупки, объём рынка или готовность платить.','Конкуренция: ограниченная выборка не является полным поиском конкурентов. Число заголовков, авторов и порядок выдачи не измеряют продажи, насыщение или возможности.',('Экономика: строк с числовой ценой и явно указанной валютой: '+$r.explicit_currency_prices+'. Это исторические предложения источников, не цены Amazon, роялти, затраты или маржа. Недостающие суммы не подставляются.'),'Совпадение слов — только лексический фильтр, не смысловая проверка. Даже полное совпадение может относиться к иной аудитории, поводу или товару. Наблюдения не удалены.')
 foreach($x in $r.lexical_review){$fit=$fits[[string]$x.fit];if(!$fit){$fit='неизвестный код: '+$x.fit};$lines+=($x.citation+' | '+$fit+' | поисковый запрос (оригинал): '+$x.query+' | оригинальный заголовок: '+$x.title+' | '+$x.source_url)}
 $lines+='Решение владельца: проверяйте точную надпись и композицию как непроверенный творческий замысел. Одобрение идеи не проверяет спрос, конкуренцию, права или печатное качество.'
 $lines+=Format-ForgeLatestNicheEvidenceForDraft $Draft -Compact
 return ($lines-join"`r`n")
}
function Get-ResearchReviewOverlay($Fields,$Context,[string]$RevisionHash='') {
 $facts=@();if($null-ne$Context){foreach($r in $Context.selected_records){$facts+=[pscustomobject]@{citation=$r.citation;evidence_id=$r.evidence_id;source_url=$r.source_url;creator=$r.creator;observation=$r.fact;checked_scope='Captured textual listing metadata only; no images or sales'}}}
 return [pscustomobject]@{schema='forge.research_claim_review.v1';revision_hash=$RevisionHash;source_facts=$facts;model_claims_verified=$false;model_text_role='Unapproved creative hypothesis, not factual competitor/demand/advantage analysis';unsupported_scope=@('Competitor artwork/style, small logos/cursive and visual clutter are not observable in this text feed','Buyer needs, appeal, unique value and comparative advantages are hypotheses','Legibility, print suitability and quality require actual artwork testing','Amazon demand, sales, trends, seasonality and rights remain unknown');model_text_unchanged=$true;research_verified=$false}
}
function Get-ResearchReviewWarning($Draft){
 $p=Get-PropertyValue $Draft 'provenance';if($null-eq(Get-PropertyValue $p 'research_packet')){return ''}
 return 'Границы источников: публичные тексты не являются данными продаж или спроса Amazon. Творческий замысел — непроверенная гипотеза. Ссылки не подтверждают внешний вид конкурентов, мотивы покупателей, преимущества и качество печати. Ниже сохранены исходные наблюдения. Одобрение не создано.'+"`r`n`r`n"+(Format-ForgeCardEvidenceReview $Draft)+"`r`n`r`n"+(Get-ForgePreparedAudienceContextText $Draft)+"`r`n`r`n"+(Format-ForgeLatestNicheEvidenceForDraft $Draft)
}
function Get-ForgeResearchRowAgeStatus($Packet,$Row,[DateTime]$NowUtc=([DateTime]::UtcNow)) {
 try{$days=Get-PropertyValue $Packet.freshness_policy 'max_age_days';if(($days-isnot[int]-and$days-isnot[long])-or$days-lt1-or$days-gt366){return 'unverified_age_policy'}
  $captured=ConvertFrom-ResearchUtc (Get-PropertyValue $Row 'collected_at');$observed=ConvertFrom-ResearchUtc (Get-PropertyValue $Row 'observed_at')
  if($captured-gt$NowUtc.AddMinutes(5)-or$observed-gt$captured.AddMinutes(5)){return 'invalid_future_timestamp'}
  if(($NowUtc-$captured).TotalDays-gt$days-or($NowUtc-$observed).TotalDays-gt$days){return 'stale'}
  return 'within_application_age_policy'
 }catch{return 'unverified_timestamp'}
}
function Format-ResearchEvidenceRows($Packet){
 $lines=@('Импортированные публичные источники. Дата публикации не является датой продажи; цены — исторические наблюдения. Давность пересчитывается; независимой проверки подлинности или рынка нет. Тексты ниже — оригиналы, не русский смысловой перевод.')
 foreach($r in $Packet.rows){$lines+=($r.citation_label+' | тип исходного наблюдения: '+[string](Get-PropertyValue $r 'observation_kind')+' | оригинальный текст: '+[string](Get-PropertyValue $r 'observation_text')+' | оригинальный заголовок: '+[string](Get-PropertyValue $r 'title')+' | автор: '+[string](Get-PropertyValue $r 'creator')+' | показанная цена: '+[string](Get-PropertyValue $r 'price_display')+' | публикация: '+[string](Get-PropertyValue $r 'pub_date')+' | сбор: '+$r.collected_at+' | '+(Get-ForgeResearchRowAgeStatus $Packet $r)+' | '+$r.source_url)}
 return ($lines-join "`r`n`r`n")
}
function Invoke-FreeResearchSearch {
 if($script:Busy){return};Set-Busy $true 'Reading a bounded Zazzle RSS sample; no demand inference'
 try{
  $sample=Get-ZazzleResearchSample ([string]$ResearchQueryBox.Text) 5 -AllowEmpty
  $assessment=Get-ForgeNicheEvidenceAssessment $sample.export.observations ([string]$ResearchQueryBox.Text)
  if(!$sample.export.observations.Count){$script:DiscoverSnapshot=$null;Render-DiscoverSnapshot $null;$DiscoverStatusText.Text='Source returned zero item records for this query. No product, competition or demand conclusion; previous captures retained.'}
  else{$script:DiscoverSnapshot=Import-ForgeResearchFile $sample.path;$script:DiscoverLoadedAt=[DateTime]::UtcNow;Render-DiscoverSnapshot $script:DiscoverSnapshot;$DiscoverStatusText.Text=$assessment.sample_status+' | '+$assessment.eligible_unique_products+' eligible products / '+$assessment.captured_records+' captured. '+$assessment.selection_reason+' Demand unverified.'}
  Update-DiscoverDraftControls
 }catch{$script:DiscoverSnapshot=$null;Render-DiscoverSnapshot $null;Update-DiscoverDraftControls;$DiscoverStatusText.Text='Source unavailable: product existence was not checked. No retry/bypass, no zero-demand inference; previous captures retained.';Show-Error $_.Exception.Message}finally{Set-Busy $false ([string]$DiscoverStatusText.Text)}
}
