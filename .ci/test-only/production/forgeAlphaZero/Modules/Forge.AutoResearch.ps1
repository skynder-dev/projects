# Bounded, user-started orchestration using the existing source, draft and Qwen modules.
function Get-AutoResearchRoot {return Join-Path $script:StateRoot 'research-runs-v1'}
function Get-ForgeNicheEvidencePlan {
 return @(
  [pscustomobject]@{key='urban_gardening';name='Urban / container gardening';queries=@('urban gardening tshirt','container gardening tshirt')},
  [pscustomobject]@{key='night_sky';name='Amateur sky observing';queries=@('stargazing tshirt','astronomy tshirt')}
 )
}
function Save-ForgeNicheEvidenceRun($Report,[ValidateSet('niche-evidence-v1','niche-discovery-v1','public-signals-v1')][string]$Storage='niche-evidence-v1') {
 $root=Join-Path $script:StateRoot $Storage;Ensure-Dir $root
 $rootItem=Get-Item -LiteralPath $root -Force;if($rootItem-isnot[IO.DirectoryInfo]-or($rootItem.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Niche evidence storage is not an ordinary local directory'}
 $pointer=Join-Path $root 'latest.sha256';if(Test-Path -LiteralPath $pointer){$pointerItem=Get-Item -LiteralPath $pointer -Force;if($pointerItem-isnot[IO.FileInfo]-or($pointerItem.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Non-file or redirected niche evidence pointer retained; no update performed'}}
 $json=$Report|ConvertTo-Json -Depth 40;$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes($json);$sha=Get-ByteSha256Hex $bytes;$path=Join-Path $root ($sha+'.json')
 if(Test-Path -LiteralPath $path){if((Get-FileSha256Hex $path)-cne$sha){throw 'Existing niche evidence snapshot changed; retained'}}else{$f=New-Object IO.FileStream($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$f.Write($bytes,0,$bytes.Length);$f.Flush($true)}finally{$f.Dispose()}}
 $pending=Join-Path $root ('latest.pending.'+[guid]::NewGuid().ToString('N'));[IO.File]::WriteAllText($pending,$sha,(New-Object Text.UTF8Encoding($false)));Move-Item -LiteralPath $pending -Destination (Join-Path $root 'latest.sha256') -Force
 return $path
}
function Invoke-ForgeNicheEvidenceRefresh([string]$RunPath='',$RunState=$null) {
 $topics=@();$requests=0;$cacheHits=0;$stop=$false
 foreach($direction in (Get-ForgeNicheEvidencePlan)){
  $observations=@();$queries=@()
  foreach($query in $direction.queries){
   if($RunPath){Assert-AutoResearchNotCancelled $RunPath}
   if($stop){$queries+=,[pscustomobject]@{query=$query;status='not_requested_after_source_refusal';source_url='';observations=@();network_requests=0};continue}
   try{
    $sample=Get-ZazzleResearchSample $query 10 -AllowEmpty;$requests+=$sample.network_requests;if($sample.cache_hit){$cacheHits++}
    $payload=Read-LocalCheckEvidencePayload $sample.path;$export=$payload.data
    $url='https://feed.zazzle.com/rss?qs='+[Uri]::EscapeDataString($query)+'&st=popularity&sp=30&ps=10';$null=Assert-ForgeRssCacheBinding $export $query $url 10
    $rows=@($export.observations|Where-Object{$null-ne$_})
    $queries+=,[pscustomobject]@{query=$query;status=if($rows.Count){'captured_product_metadata'}else{'captured_zero_items'};source_url=$export.feed_metadata.source_url;captured_at=$export.collected_at;cache_valid_until=$export.feed_metadata.cache_valid_until;capture_sha256=$payload.sha256;raw_rss_sha256=[string](Get-PropertyValue $export.feed_metadata 'raw_rss_sha256');cache_hit=$sample.cache_hit;network_requests=$sample.network_requests;observed_records=$rows.Count}
    $observations+=$rows
   }catch{
    if($_.Exception.Message-ceq'AUTO_RESEARCH_CANCELLED'){throw}
    $attempts=0;if($_.Exception.Data.Contains('source_network_requests')){$attempts=[int]$_.Exception.Data['source_network_requests']};$requests+=$attempts
    $refused=$_.Exception.Data.Contains('source_status')-and$_.Exception.Data['source_status']-ceq'refused'
    if($refused){$stop=$true}
    $queries+=,[pscustomobject]@{query=$query;status=if($refused){'source_refused_no_retry_or_bypass'}else{'source_unavailable'};source_url=('https://feed.zazzle.com/rss?qs='+[Uri]::EscapeDataString($query)+'&st=popularity&sp=30&ps=10');network_requests=$attempts;error=$_.Exception.Message;observed_records=0}
   }
   if($null-ne$RunState){$RunState.source_requests=$requests;$RunState.source_cache_hits=$cacheHits;$RunState.phase='source evidence: '+$query;$RunState.note='Bounded source reads; model requests remain zero.';if($RunPath){Write-AutoResearchRun $RunPath $RunState}}
   if($RunPath){Assert-AutoResearchNotCancelled $RunPath}
  }
  $assessment=Get-ForgeNicheEvidenceAssessment $observations
  $successful=@($queries|Where-Object{$_.status-in@('captured_product_metadata','captured_zero_items')}).Count
  $coverage=if(!$successful){'source_unavailable_not_a_zero_sample'}elseif($successful-lt$queries.Count){'partial_source_coverage'}elseif(!$observations.Count){'sources_returned_zero_items'}else{'bounded_sources_captured'}
  $topics+=,[pscustomobject]@{key=$direction.key;name=$direction.name;source_coverage=$coverage;successful_queries=$successful;query_reports=$queries;observations=$observations;assessment=$assessment;selection_reason=$assessment.selection_reason;audience_evidence='Official activity context is separate; no measured apparel buyer segment';product_evidence=if(!$successful){'Source unavailable: product existence was not checked; do not interpret as zero products'}elseif($assessment.eligible_unique_products){'T-shirt listing metadata observed in this bounded Zazzle capture; not independently verified sales or distinct designs'}else{'No eligible products observed in the returned bounded records; not proof of absence'};demand_evidence='No purchase counts, sales/rank histories or Amazon demand source; unverified'}
 }
 $report=[pscustomobject]@{schema='forge.niche_evidence_run.v1';mode='public_sources_only';completed_at=[DateTime]::UtcNow.ToString('o');topics=$topics;source_requests=$requests;cache_hits=$cacheHits;max_source_requests=4;max_raw_records=40;model_requests=0;gpu_requests=0;drafts_created=0;approvals_created=0;demand_verified=$false;stopped_after_refusal=$stop;selection_policy='Collect both preplanned distinct queries; no pagination, mirrors, alternate services, retry or popularity-to-sales inference.'}
 if($requests-gt4){throw 'Source request budget exceeded'}
 if($RunPath){Assert-AutoResearchNotCancelled $RunPath};$null=Save-ForgeNicheEvidenceRun $report;return $report
}
function Read-ForgeLatestNicheEvidence {
 $root=Join-Path $script:StateRoot 'niche-evidence-v1';$pointer=Join-Path $root 'latest.sha256'
 $origin='bundled_public_capture'
 if(Test-Path -LiteralPath $root){
  $rootItem=Get-Item -LiteralPath $root -Force;if($rootItem-isnot[IO.DirectoryInfo]-or($rootItem.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Niche evidence storage is unavailable or redirected'}
  if(!(Test-Path -LiteralPath $pointer)-and@(Get-ChildItem -LiteralPath $root -Force).Count){throw 'Local niche evidence pointer is missing. Existing reports retained; refresh sources or restore the data backup. Bundled evidence was not substituted.'}
 }
 if(Test-Path -LiteralPath $pointer){
  $pointerItem=Get-Item -LiteralPath $pointer -Force;if($pointerItem-isnot[IO.FileInfo]-or($pointerItem.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Non-file or redirected niche evidence pointer was not followed'}
  $origin='saved_local_capture'
  if((Get-Item -LiteralPath $pointer).Length-gt128){throw 'Niche evidence pointer oversized'};$sha=[IO.File]::ReadAllText($pointer).Trim();if($sha-cnotmatch'^[0-9a-f]{64}$'){throw 'Invalid niche evidence pointer'}
  $payload=Read-LocalCheckEvidencePayload (Join-Path $root ($sha+'.json'));if($payload.sha256-cne$sha){throw 'Niche evidence snapshot changed'};$report=$payload.data
 }else{$path=Join-Path (Split-Path $script:ModuleRoot -Parent) 'Data\Forge.NicheEvidenceSnapshot.json';if(!(Test-Path -LiteralPath $path)){return $null};$report=(Read-LocalCheckEvidencePayload $path).data}
 if($report.schema-cne'forge.niche_evidence_run.v1'-or$report.mode-cne'public_sources_only'-or$report.model_requests-isnot[int]-or$report.model_requests-ne0-or$report.demand_verified-isnot[bool]-or$report.demand_verified-or$report.topics-isnot[Array]-or$report.topics.Count-ne2){throw 'Invalid niche evidence authority'}
 foreach($field in @('gpu_requests','drafts_created','approvals_created')){$v=Get-PropertyValue $report $field;if(($v-isnot[int]-and$v-isnot[long])-or$v-ne0){throw 'Niche evidence cannot grant generation or owner authority'}}
 foreach($field in @('source_requests','cache_hits')){$v=Get-PropertyValue $report $field;if(($v-isnot[int]-and$v-isnot[long])-or$v-lt0-or$v-gt4){throw 'Invalid niche source request counter'}}
 if((ConvertFrom-ResearchUtc $report.completed_at)-gt[DateTime]::UtcNow.AddMinutes(5)){throw 'Niche evidence dated in future'}
 $seen=@{};foreach($topic in $report.topics){if($topic.key-cnotin@('urban_gardening','night_sky')-or$seen.ContainsKey($topic.key)-or$topic.observations-isnot[Array]-or$topic.observations.Count-gt20-or$topic.query_reports-isnot[Array]-or$topic.query_reports.Count-ne2){throw 'Invalid niche evidence budget'};$seen[$topic.key]=$true;Add-OrSetProperty $topic 'assessment' (Get-ForgeNicheEvidenceAssessment $topic.observations)}
 Add-OrSetProperty $report 'display_origin' $origin
 return $report
}
function Read-AutoResearchRun([string]$RunPath){
 $p=Join-Path $RunPath 'result.json';if(!(Test-Path -LiteralPath $p -PathType Leaf)){return $null}
 $file=Get-Item -LiteralPath $p;if($file.Length-gt2097152-or($file.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Research status is oversized or redirected'}
 $run=ConvertFrom-ForgeJsonObjectStrict ([IO.File]::ReadAllText($p))
 if((Get-PropertyValue $run 'schema')-cne'forge.auto_research_run.v1'-or(Get-PropertyValue $run 'status')-cnotin@('running','completed','partial','cancelled','failed','no_supported_candidates')){throw 'Invalid research status envelope'}
 $cardsProperty=$run.PSObject.Properties['cards'];if($null-eq$cardsProperty-or$cardsProperty.Value-isnot[Array]-or$cardsProperty.Value.Count-gt3){throw 'Invalid research cards envelope'}
 foreach($n in @('phase','note')){$text=Get-PropertyValue $run $n;if($text-isnot[string]-or$text.Length-gt8192){throw 'Invalid research status text'}}
 return $run
}
function Assert-AutoResearchNotCancelled([string]$RunPath){if(Test-Path (Join-Path $RunPath 'cancel.request')){throw 'AUTO_RESEARCH_CANCELLED'}}
function Write-AutoResearchRun([string]$RunPath,$Run){$tmp=Join-Path $RunPath ('result.tmp.'+[guid]::NewGuid().ToString('N'));[IO.File]::WriteAllText($tmp,($Run|ConvertTo-Json -Depth 25),(New-Object Text.UTF8Encoding($false)));Move-Item $tmp (Join-Path $RunPath 'result.json') -Force}
function Get-AutoDirectionSchema {return @{type='object';properties=@{directions=@{type='array';minItems=3;maxItems=3;items=@{type='object';properties=@{audience=@{type='string'};query=@{type='string'};rationale=@{type='string'}};required=@('audience','query','rationale');additionalProperties=$false}}};required=@('directions');additionalProperties=$false}}
function Get-AutoConceptSchema($Context=$null) {
 $s=Get-ForgeLocalAISchema
 $s.properties.concept_text.description='Explain WHY the proposed exact wording and imagery fit the audience and occasion. Production instructions or disclaimers alone are not an idea rationale. Explicitly cite an observed title pattern using [E1], [E2] etc; never claim sales or infer unseen graphics.'
 $s.properties.hook.description='Exact short English phrase printed on the garment; not an audience label or marketing summary.'
 $s.properties.visual_direction_text.description='Complete proposed design instructions: garment colour, inks, composition, exact lettering and explicitly transparent unprinted areas. Never just a colour.';$s.properties.visual_direction_text.minLength=120
 $s.properties.target_buyer.minLength=40;$s.properties.purchase_reason.minLength=40;$s.properties.differentiation.minLength=60
 $s.properties.production_spec.properties.composition.minLength=100;$s.properties.production_spec.properties.illustration.minLength=80
 if($null-ne$Context){$s.properties.observation_citations=@{type='array';minItems=1;maxItems=5;items=@{type='string';enum=@($Context.selected_records.citation)}};$s.required+=@('observation_citations');$s.properties.concept_text.description='Explain WHY the proposed wording and imagery fit this audience and occasion, and separately relate the idea to observed title text. Do not substitute production instructions or disclaimers for the rationale. Creative motives are hypotheses; observation_citations contains actual source reference IDs.'}
 return $s
}
function ConvertFrom-AutoConceptContent([string]$Content,$Context){
 $value=ConvertFrom-ForgeJsonObjectStrict $Content
 if(@($value.PSObject.Properties).Count-ne9-or$value.observation_citations-isnot[Array]-or$value.observation_citations.Count-lt1-or$value.observation_citations.Count-gt5){throw 'Auto response lacks structured observation citations'}
 foreach($id in $value.observation_citations){if($id-isnot[string]-or@($Context.selected_records|Where-Object{$_.citation-ceq$id}).Count-ne1){throw 'Auto response invented an observation citation'}}
 $ids=@($value.observation_citations|Select-Object -Unique);$value.PSObject.Properties.Remove('observation_citations')
 $fields=ConvertFrom-ForgeLocalAIContent ($value|ConvertTo-Json -Depth 12)
 Add-OrSetProperty $Context 'structured_model_citations' $ids
 Assert-QwenEvidenceCitations $fields $Context
 return $fields
}
function Assert-AutoConceptComplete($Fields){
 if($Fields.visual_direction_text.Length-lt120-or$Fields.target_buyer.Length-lt40-or$Fields.production_spec.composition.Length-lt100-or$Fields.production_spec.illustration.Length-lt80){throw 'Auto concept lacks complete audience/design instructions'}
 $design=$Fields.visual_direction_text+' '+$Fields.production_spec.illustration+' '+$Fields.production_spec.composition
 if($design-notmatch'(?i)transparent|alpha.zero|unprinted|прозрач|незапечат|альфа'-or$design-notmatch'(?i)shirt|garment|fabric|футбол|ткан'){throw 'Auto concept must specify garment and transparent unprinted areas'}
}
function ConvertFrom-AutoDirections([string]$Content){
 $p=ConvertFrom-ForgeJsonObjectStrict $Content;if(@($p.PSObject.Properties).Count-ne1-or$p.directions-isnot[Array]-or$p.directions.Count-ne3){throw 'Planner must return exactly three directions'}
 $seen=@{};foreach($d in $p.directions){if(@($d.PSObject.Properties).Count-ne3){throw 'Invalid planner fields'};foreach($f in @('audience','query','rationale')){if($d.$f-isnot[string]-or[string]::IsNullOrWhiteSpace($d.$f)-or$d.$f.Length-gt500){throw 'Incomplete planner direction'}};$q=$d.query.Trim().ToLowerInvariant();if($q.Length-gt90-or$q-match'[А-Яа-яЁё]|https?:|[?&=]|\b(key|token|password)\b'-or$seen.ContainsKey($q)){throw 'Invalid/duplicate model query'};if(!(Test-ForgeRussianOwnerText $d.audience)-or!(Test-ForgeRussianOwnerText $d.rationale)){throw 'OWNER_LANGUAGE_RU_REQUIRED: planner audience/rationale'};$claimIssues=@(Get-ForgeUnsupportedClaimIssues ($d.audience+' '+$d.rationale));if($claimIssues.Count-or$d.rationale-notmatch'(?i)гипотез|предполага|предложен|не подтвержд'){throw 'AI_RESPONSE_REVIEW_REQUIRED: направление исследования должно быть гипотезой, без утверждений о спросе, преимуществах или продажах.'};$seen[$q]=$true};return $p
}
function Wait-AutoQwen($Request,[string]$RunPath){
 $watch=[Diagnostics.Stopwatch]::StartNew()
 try{while(!$Request.Task.IsCompleted){if(Test-Path (Join-Path $RunPath 'cancel.request')){$Request.Cancel.Cancel();throw 'AUTO_RESEARCH_CANCELLED'};if($watch.Elapsed.TotalSeconds-gt195){$Request.Cancel.Cancel();throw 'Qwen bounded request timed out'};[Threading.Thread]::Sleep(200)};Assert-AutoResearchNotCancelled $RunPath;$res=$Request.Task.GetAwaiter().GetResult();try{if(!$res.IsSuccessStatusCode){throw 'Local Qwen request failed'};$raw=$res.Content.ReadAsStringAsync().GetAwaiter().GetResult()}finally{$res.Dispose()};$o=$raw|ConvertFrom-Json;if($o.model-cne'qwen3.5:9b'-or$o.done-isnot[bool]-or!$o.done-or$o.done_reason-cne'stop'){throw 'Incomplete/wrong model response'};return [pscustomobject]@{raw=$raw;content=[string]$o.message.content}}finally{$Request.Content.Dispose();$Request.Client.Dispose();$Request.Cancel.Dispose()}
}
function Get-LegacyAutoResearchCard($Draft,[string]$Why){
 $r=Get-ResearchDraftCurrentFields $Draft;if((Get-ResearchDraftContentHash $Draft.concept_key $r)-cne$Draft.current_revision_hash){throw 'Card revision hash differs from the saved current draft'};$p=$Draft.provenance.research_packet;$sourceLines=@();foreach($x in $p.rows){$sourceLines+=($x.citation_label+' | '+$x.creator+' | '+('дата сбора: '+[string](Get-PropertyValue $x 'observed_at'))+' | '+$x.source_url)}
 $used=Get-PropertyValue $Draft.provenance 'model_observation_citations';if($null-eq$used){$used=Get-PropertyValue $Draft.provenance 'creative_basis_citations'};$basis=@();foreach($x in $p.rows){if($used-contains$x.citation_label){$basis+=($x.citation_label+': '+$(if([string](Get-PropertyValue $x 'observation_kind')-ceq'audience_context'){[string](Get-PropertyValue $x 'observation_text')}else{'оригинальный заголовок: '+$x.title}))}}
 $display=$r.title+"`r`nГИПОТЕЗА: спрос Amazon не доказан; одобрения нет.`r`nПочему исследуем (творческая гипотеза; исходное пояснение): "+$Why+"`r`nУказанное основание гипотезы (оригиналы источников): "+($basis-join'; ')+"`r`nАудитория (исходный текст): "+$r.target_buyer+"`r`nПовод (исходный текст): "+$r.purchase_reason+"`r`nТочная английская надпись: "+$r.hook+"`r`nСмысл (исходный текст): "+$r.concept_text+"`r`nДизайн (исходный текст): "+$r.visual_direction_text+"`r`n"+($r.production_spec|ConvertTo-Json -Depth 10)+"`r`nИсточники и оригиналы:`r`n"+($sourceLines-join"`r`n")+"`r`nОграничения: только сохранённые публичные тексты. Контекст деятельности и заголовки не подтверждают мотивы покупателей, преимущества, внешний вид, права, качество печати или продажи."
 $display=$r.title+"`r`n"+(Format-ForgeLatestNicheEvidenceForDraft $Draft -Summary)+"`r`n"+$display;$display+="`r`n"+(Format-ForgeCardEvidenceReview $Draft);$display+="`r`n"+(Get-ForgePreparedAudienceContextText $Draft)
 $issues=@(Get-ForgeConceptReviewIssues $r);if($issues.Count){$display+="`r`nПроверить до одобрения: "+($issues-join' ')}
 return [pscustomobject]@{concept_key=$Draft.concept_key;revision_hash=$Draft.current_revision_hash;rationale=$Why;display_text=$display;review_issues=$issues;research_verified=$false;approved=$false;evidence_count=$p.rows.Count}
}
function Get-AutoResearchCard($Draft,[string]$Why){
 $r=Get-ResearchDraftCurrentFields $Draft
 if((Get-ResearchDraftContentHash $Draft.concept_key $r)-cne$Draft.current_revision_hash){throw 'Card revision hash differs from the saved current draft'}
 try{Assert-ForgeOwnerLanguage $r}catch{
  $legacy=Get-LegacyAutoResearchCard $Draft $Why
  $legacy.display_text="Историческая карточка: ниже сохранён исходный язык. Это не исправленный русский результат нового генератора. Для телефона используется отдельный перевод точной версии, если он подготовлен.`r`n`r`n"+(Format-ForgeOwnerLanguageReview $r)+"`r`n`r`n"+$legacy.display_text
  return $legacy
 }
 if(!(Test-ForgeRussianOwnerText $Why ([string]$r.hook))){throw 'OWNER_LANGUAGE_RU_REQUIRED: rationale'}
 $p=$Draft.provenance.research_packet;$sourceLines=@()
 foreach($x in @($p.rows)){
  $sourceLines+=([string]$x.citation_label+' | автор: '+[string]$x.creator+' | дата наблюдения: '+[string](Get-PropertyValue $x 'observed_at')+' | '+[string]$x.source_url)
  $original=[string](Get-PropertyValue $x 'observation_text');if(!$original){$original=[string]$x.title}
  $sourceLines+=('Оригинальный текст источника (язык источника; не перевод и не вывод о спросе): '+$original)
 }
 $spec=$r.production_spec
 $display=$r.title+"`r`nГИПОТЕЗА. Спрос на Amazon не доказан. Одобрения нет.`r`nПочему исследуем: "+$Why+"`r`nАудитория: "+$r.target_buyer+"`r`nПредполагаемый повод покупки: "+$r.purchase_reason+"`r`nОтличие как гипотеза: "+$r.differentiation+"`r`nТочный текст для печати (английский):`r`n"+$r.hook+"`r`nСмысл идеи: "+$r.concept_text+"`r`nДизайн: "+$r.visual_direction_text+"`r`nКомпозиция: "+$spec.composition+"`r`nИллюстрация: "+$spec.illustration+"`r`nПалитра: "+(@($spec.ink_palette)-join'; ')+"`r`nИзбегать: "+(@($spec.avoid)-join'; ')+"`r`nИсточники и их оригиналы:`r`n"+($sourceLines-join"`r`n")+"`r`nОграничения: публичные тексты и заголовки не подтверждают мотивы покупателей, конкурентные преимущества, внешний вид товаров, права, печатное качество или продажи. Холст 4500×5400 при 300 dpi рекомендован, но не является строгим минимумом. Прозрачность и размеры не доказывают качество рисунка."
 $issues=@(Get-ForgeConceptReviewIssues $r);if($issues.Count){$display+="`r`nПроверить до одобрения: "+($issues-join' ')}
 return [pscustomobject]@{concept_key=$Draft.concept_key;revision_hash=$Draft.current_revision_hash;rationale=$Why;display_text=$display;review_issues=$issues;research_verified=$false;approved=$false;evidence_count=@($p.rows).Count}
}
function Get-ForgeConceptReviewIssues($Fields) {
 $issues=@(Get-ForgeDesignOutputReviewIssues $Fields);$hook=[string](Get-PropertyValue $Fields 'hook');$design=[string](Get-PropertyValue $Fields 'visual_direction_text')
 if($hook-and!$design.Contains($hook)){$issues+='Точная надпись не повторена дословно в замысле дизайна: проверьте регистр, пунктуацию и переносы строк.'}
 $idea=[string](Get-PropertyValue $Fields 'concept_text')
 if($idea-match'(?i)ink|alpha|transparen|garment|gradient|краск|альфа|прозрач|футбол|градиент'-and$idea-notmatch'(?i)because|symboli[sz]|represent|connect|celebrat|express|evok|remind|relat|reflect|signif|meaning|потому|символ|смысл|связ|отраж|метафор'){$issues+='Возможно, вместо смысла описано только изготовление: объясните связь надписи и образов с аудиторией и поводом. Это эвристическая отметка, не смысловой вердикт.'}
 return $issues
}
function Get-AutoSamplePatterns($Packet){return [pscustomobject]@{records=$Packet.rows.Count;distinct_title_strings=@($Packet.rows.title|Sort-Object -Unique).Count;distinct_creators=@($Packet.rows.creator|Sort-Object -Unique).Count;repeated_title_groups=@($Packet.rows|Group-Object title|Where-Object{$_.Count-gt1}).Count;scope='Textual properties of this small Zazzle sample, not distinct design counts, sales or Amazon market coverage';numeric_market_score=$null}}
function Get-LastAutoResearchSnapshot {
 $root=[IO.Path]::GetFullPath((Get-AutoResearchRoot));$last=Join-Path $root 'last-completed.path'
 if(!(Test-Path -LiteralPath $last -PathType Leaf)){return $null}
 try{
  if((Get-Item -LiteralPath $last).Length-gt4096){throw 'Research run pointer is oversized'}
  $path=[IO.Path]::GetFullPath(([IO.File]::ReadAllText($last)).Trim())
  if(!$path.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Research run pointer is outside its local root'}
  $walk=Get-Item -LiteralPath $path -ErrorAction Stop
  while($walk.FullName-cne$root){if($walk.Attributes-band[IO.FileAttributes]::ReparsePoint){throw 'Research run pointer traverses a reparse point'};$walk=$walk.Parent;if($null-eq$walk){throw 'Invalid research run path'}}
  $result=Get-Item -LiteralPath (Join-Path $path 'result.json') -ErrorAction Stop
  if($result.Length-gt2097152-or($result.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Research result is oversized or redirected'}
  $run=Read-AutoResearchRun $path
  if($null-eq$run-or$run.status-cne'completed'-or@($run.cards).Count-lt1-or@($run.cards).Count-gt3){throw 'Completed research result is invalid'}
  $state=Read-LocalCoreState
  foreach($card in $run.cards){if(!(Test-ResearchDraftKey ([string]$card.concept_key))-or$null-eq(Get-ResearchDraft ([string]$card.concept_key) $state)){throw 'Completed research card has no saved draft'}}
  $fresh=$false;try{$fresh=(ConvertFrom-ResearchUtc $run.cache_valid_until)-gt[DateTime]::UtcNow}catch{}
  return [pscustomobject]@{path=$path;run=$run;cache_valid=$fresh}
 }catch{Write-AppLog 'WARN' ('Saved research run unavailable; drafts preserved: '+$_.Exception.Message);return $null}
}
function Restore-AutoResearchCards {
 $saved=Get-LastAutoResearchSnapshot;if($null-eq$saved){return $false}
 $script:AutoResearchRunPath=$saved.path;$AutoResearchCards.ItemsSource=@($saved.run.cards);Refresh-AutoResearchCardsFromSavedDrafts
 $AutoResearchStatus.Text=if($saved.cache_valid){'Saved research cards restored; source cache within TTL. No new requests.'}else{'Saved research cards restored for review; source cache expired or unverified. No new requests; refresh sources before relying on them.'}
 return $true
}
function Get-ForgeResearchSourceRestriction {
 if($script:Locale-ceq'ru'){return 'Живое исследование товаров и поиск новых ниш сейчас недоступны: источник Zazzle запрещает эти запросы правилами robots.txt. Сохранённые гипотезы и снимки остаются доступны для проверки. Можно сравнить публичные показатели внимания кнопкой «Сравнить публичные прокси (без AI)»; они не подтверждают спрос или продажи Amazon.'}
 if($script:Locale-ceq'es'){return 'La investigacion de productos y el descubrimiento de nichos no estan disponibles: las reglas robots.txt de Zazzle prohiben estas consultas. Las hipotesis y capturas guardadas siguen disponibles. Use Comparar proxies publicos (sin IA) para comparar atencion publica; no demuestra demanda ni ventas en Amazon.'}
 return 'Live product research and niche discovery are unavailable: Zazzle robots.txt rules prohibit these queries. Saved hypotheses and captures remain available for review. Use Compare public proxies (no AI) for public attention context; it does not establish Amazon demand or sales.'
}
function Start-AutoResearch([switch]$SourcesOnly,[switch]$DiscoverNiches,[switch]$PublicSignals) {
 if($script:Busy){$AutoResearchStatus.Text='Finish the current operation before starting source or model research.';return}
 if($null-ne$script:AutoResearchProcess-and!$script:AutoResearchProcess.HasExited){$AutoResearchStatus.Text='Research is already running';return}
 if($script:Dirty-or$script:PublicationDirty){$AutoResearchStatus.Text='Save current edits before starting research';return}
 if($null-ne$script:LocalAIRequest){$AutoResearchStatus.Text='A manual local text request is running; finish or cancel it first';return}
 if($null-ne$script:VisionReviewRequest){$AutoResearchStatus.Text='Finish or cancel Qwen vision comparison first';return}
 $root=Get-AutoResearchRoot
 $saved=Get-LastAutoResearchSnapshot;if(!$SourcesOnly-and!$DiscoverNiches-and!$PublicSignals-and$null-ne$saved-and$saved.cache_valid){$script:AutoResearchRunPath=$saved.path;$AutoResearchCards.ItemsSource=@($saved.run.cards);Refresh-AutoResearchCardsFromSavedDrafts;$AutoResearchStatus.Text='Previous bounded run reused within source TTL; no new requests';return}
 if(!$PublicSignals){$AutoResearchStatus.Text=Get-ForgeResearchSourceRestriction;return}
 try{
 Ensure-Dir $root
 $path=Join-Path $root ('run-'+[guid]::NewGuid().ToString('N'));Ensure-Dir $path;$script:AutoResearchRunPath=$path
 $worker=Join-Path (Split-Path $script:ModuleRoot -Parent) 'MerchForgeAutoResearchWorker.ps1';$ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 $cmd="& '"+$worker.Replace("'","''")+"' -PackageRoot '"+(Split-Path $script:ModuleRoot -Parent).Replace("'","''")+"' -RunPath '"+$path.Replace("'","''")+"'"
 if($PublicSignals){$cmd+=' -PublicSignals'}elseif($DiscoverNiches){$cmd+=' -DiscoverNiches'}elseif($SourcesOnly){$cmd+=' -SourcesOnly'}
 $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
 $script:AutoResearchProcess=Start-Process $ps -ArgumentList @('-STA','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $path 'worker.log') -RedirectStandardError (Join-Path $path 'worker-errors.log') -PassThru
 $AutoResearchStatus.Text=if($PublicSignals){'Comparing public attention proxies; up to7 policy/data requests, no models/GPU/market ranking. Zazzle network blocked by robots.'}elseif($DiscoverNiches){'Discovering observed hobby topics: 2 broad RSS queries + at most 3 follow-ups; no AI, GPU or market ranking.'}elseif($SourcesOnly){'Public product evidence refresh: 4 preplanned RSS queries, up to 40 records, zero model/GPU requests'}else{'Research started: at most 3 directions, 15 source records, 4 local model requests'};$script:AutoResearchTimer.Start()
 }catch{
  $script:AutoResearchTimer.Stop()
  try{Write-AppLog 'ERROR' ('Research launch not confirmed: '+$_.Exception.Message)}catch{}
  $AutoResearchStatus.Text=if($script:Locale-ceq'ru'){'Не удалось подтвердить запуск исследования. Карточки и файлы задания сохранены. Автоматического повтора нет. Проверьте состояние задания перед явным повтором.'}elseif($script:Locale-ceq'es'){'No se pudo confirmar el inicio. Tarjetas y archivos conservados. No hay reintento automatico. Compruebe el estado antes de reintentar.'}else{'Research launch could not be confirmed. Cards and run files are retained. No automatic retry. Check run status before explicitly retrying.'}
 }
}
function Cancel-AutoResearch {
 if($null-eq$script:AutoResearchProcess-or$script:AutoResearchProcess.HasExited){$AutoResearchStatus.Text='No active research run to cancel';return}
 if($script:AutoResearchRunPath){
  try{[IO.File]::WriteAllText((Join-Path $script:AutoResearchRunPath 'cancel.request'),'cancel');$AutoResearchStatus.Text='Cancellation requested; current RSS read may take up to 30 seconds. No image generation.'}
  catch{
   $script:AutoResearchTimer.Start()
   try{Write-AppLog 'ERROR' ('Research cancellation request could not be saved: '+$_.Exception.Message)}catch{}
   $AutoResearchStatus.Text=if($script:Locale-ceq'ru'){'Запрос отмены не сохранён. Исследование может продолжаться; наблюдение за состоянием остаётся включённым. Можно повторить отмену явно. Карточки и файлы сохранены.'}elseif($script:Locale-ceq'es'){'No se guardo la cancelacion. El proceso puede continuar; se sigue comprobando su estado. Puede volver a cancelar explicitamente. Tarjetas y archivos conservados.'}else{'Cancellation request was not saved. Research may continue; status monitoring remains active. You can explicitly retry Cancel. Cards and run files are retained.'}
  }
 }
}
function Get-RecoveredAutoResearchCards([string]$RunPath,$ReportedCards=@()) {
 $cards=@($ReportedCards);$seen=@{};foreach($card in $cards){$seen[[string]$card.concept_key]=$true}
 foreach($draft in (Get-ResearchDraftList (Read-LocalCoreState))){
  $p=Get-PropertyValue $draft 'provenance'
  if([string](Get-PropertyValue $p 'auto_run_path')-cne$RunPath-or$null-eq(Get-PropertyValue $p 'research_packet')-or$seen.ContainsKey([string]$draft.concept_key)){continue}
  try{$cards+=@(Get-AutoResearchCard $draft 'Восстановлена сохранённая гипотеза прерванного локального исследования. Проверьте сохранённые источники; спрос на Amazon не подтверждён.');$seen[[string]$draft.concept_key]=$true}catch{Write-AppLog 'WARN' ('Interrupted research card failed verification: '+$_.Exception.Message)}
 }
 return $cards
}
function Update-AutoResearchUi {
 if(!$script:AutoResearchRunPath){return};try{$r=Read-AutoResearchRun $script:AutoResearchRunPath}catch{$AutoResearchStatus.Text='Run status unreadable; saved drafts recovered where verifiable';$script:AutoResearchTimer.Stop();$AutoResearchCards.ItemsSource=@(Get-RecoveredAutoResearchCards $script:AutoResearchRunPath);Refresh-ResearchDraftQueue;return}
 if($null-ne$script:AutoResearchProcess-and$script:AutoResearchProcess.HasExited-and($null-eq$r-or$r.status-eq'running')){$AutoResearchCards.ItemsSource=@(Get-RecoveredAutoResearchCards $script:AutoResearchRunPath);$AutoResearchStatus.Text='Research worker stopped unexpectedly; '+@($AutoResearchCards.ItemsSource).Count+' saved hypotheses available for review. No automatic retry.';$script:AutoResearchTimer.Stop();Refresh-ResearchDraftQueue;return}
 if($null-ne$r-and[string](Get-PropertyValue $r 'research_mode')-in@('public_sources_only','source_niche_discovery','public_attention_proxies')){
  $AutoResearchStatus.Text=$r.status+' | '+$r.note
  if($r.status-cne'running'){$script:AutoResearchTimer.Stop();if($r.research_mode-ceq'public_attention_proxies'){Refresh-ForgePublicSignalsSummary};if($r.research_mode-ceq'source_niche_discovery'){Refresh-ForgeNicheDiscoverySummary};Refresh-AutoResearchCardsFromSavedDrafts;if($null-ne$script:Current-and(Test-CurrentIsResearchDraft)){$draft=Get-ResearchDraft $script:Current.concept.concept_key;if($null-ne$draft){$OverviewWarnings.Text=Get-ResearchReviewWarning $draft}}}
  return
 }
 if($null-ne$r){$AutoResearchStatus.Text=$r.status+' | '+$r.phase+' | '+$r.note;if($r.status-in@('completed','partial','cancelled','failed','no_supported_candidates')){$AutoResearchCards.ItemsSource=@(Get-RecoveredAutoResearchCards $script:AutoResearchRunPath $r.cards);$extra=@($AutoResearchCards.ItemsSource).Count-@($r.cards).Count;if($extra-gt0){$AutoResearchStatus.Text+=" | Recovered "+$extra+" additional saved unapproved hypotheses after interrupted reporting."};$script:AutoResearchTimer.Stop();Refresh-ResearchDraftQueue}}
}
function Refresh-AutoResearchCardsFromSavedDrafts {
 if($null-eq$AutoResearchCards-or$null-eq$AutoResearchCards.ItemsSource){return}
 $selectedKey=if($null-ne$AutoResearchCards.SelectedItem){[string]$AutoResearchCards.SelectedItem.concept_key}else{''}
 $state=Read-LocalCoreState;$cards=@()
 foreach($card in @($AutoResearchCards.ItemsSource)){
  $draft=Get-ResearchDraft ([string]$card.concept_key) $state
  if($null-eq$draft){$prepared=Read-ForgePreparedHypotheses;$fresh=@($prepared.cards|Where-Object{$_.concept_key-ceq$card.concept_key});if($fresh.Count-eq1-and([string]$fresh[0].display_text-cne[string]$card.display_text-or[string]$fresh[0].revision_hash-cne[string]$card.revision_hash)){$cards+=@($fresh[0])}else{$cards+=@($card)};continue}
  try{
   $why=[string](Get-PropertyValue $card 'rationale');if([string]::IsNullOrWhiteSpace($why)){$why='Previously saved research hypothesis. Inspect the saved sources and current brief; no Amazon demand verification.'}
   $current=Get-AutoResearchCard $draft $why
   $current|Add-Member NoteProperty rationale $why -Force
   $current.display_text+="`r`nSAVED REVISION: "+$draft.current_revision_id+' / '+$draft.current_revision_hash+"`r`nReview the current saved brief before approval. Historical source relevance and lettering require owner review."
   $cards+=@($current)
  }catch{$cards+=@([pscustomobject]@{concept_key=$card.concept_key;revision_hash='';display_text='Saved card could not be verified. Open the saved draft to inspect its content; no approval or generation is authorized.';approved=$false;research_verified=$false})}
 }
 $AutoResearchCards.ItemsSource=@($cards)
 if($selectedKey){$selection=@($cards|Where-Object{$_.concept_key-ceq$selectedKey}|Select-Object -First 1);if($selection.Count){$AutoResearchCards.SelectedItem=$selection[0]}}
}
function Read-ForgePreparedHypotheses {
 $p=Join-Path (Split-Path $script:ModuleRoot -Parent) 'Data\Forge.PreparedHypotheses.json';if(!(Test-Path -LiteralPath $p)){return $null}
 $seed=Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json
 if($seed.schema-cne'forge.prepared_hypotheses.v1'-or$seed.research_verified-isnot[bool]-or$seed.research_verified-or$seed.owner_approved-isnot[bool]-or$seed.owner_approved){throw 'Invalid prepared hypothesis authority'}
 foreach($card in $seed.cards){$draft=@($seed.drafts|Where-Object{$_.concept_key-ceq$card.concept_key});if($draft.Count-ne1-or$card.approved-or$card.research_verified-or$draft[0].current_revision_hash-cne$card.revision_hash){throw 'Prepared card has stale or implicit authority'}
  foreach($v in $draft[0].authority.PSObject.Properties){if($v.Value-isnot[bool]-or$v.Value){throw 'Prepared draft must remain unapproved'}}
  if($draft[0].provenance.research_verified){throw 'Prepared draft is a hypothesis only'}
  $fields=Get-ResearchDraftCurrentFields $draft[0];if((Get-ResearchDraftContentHash $draft[0].concept_key $fields)-cne$card.revision_hash){throw 'Prepared draft content changed'}
 }
 foreach($card in $seed.cards){$draft=@($seed.drafts|Where-Object{$_.concept_key-ceq$card.concept_key})[0];$card.display_text=(Get-ResearchDraftCurrentFields $draft).title+"`r`n"+(Format-ForgeLatestNicheEvidenceForDraft $draft -Summary)+"`r`n"+$card.display_text;$card.display_text+="`r`n"+(Format-ForgeCardEvidenceReview $draft)+"`r`n"+(Get-ForgePreparedAudienceContextText $draft);$packet=$draft.provenance.research_packet;$ages=@($packet.rows|ForEach-Object{Get-ForgeResearchRowAgeStatus $packet $_}|Sort-Object -Unique);$card.display_text+=("`r`nSOURCE REVIEW NOW: "+($ages-join', ')+'. Historical prepared card; new lexical query filtering was not applied to this original pilot. Recheck source relevance and exact lettering before approval. No Amazon market verification.')}
 return $seed
}
function Open-AutoResearchCard {
 if($null-eq$AutoResearchCards.SelectedItem){return}
 if($script:Dirty-or$script:PublicationDirty){$AutoResearchStatus.Text='Сначала сохраните текущие изменения: открытие карточки отложено.';return}
 try{$key=[string]$AutoResearchCards.SelectedItem.concept_key;$state=Read-LocalCoreState
  if($null-eq(Get-ResearchDraft $key $state)){$seed=Read-ForgePreparedHypotheses;$draft=@($seed.drafts|Where-Object{$_.concept_key-ceq$key});if($draft.Count-eq1){Set-ResearchDraftList $state (@(Get-ResearchDraftList $state)+@($draft[0]));Write-LocalCoreState $state;Refresh-ResearchDraftQueue}}
  Open-ResearchDraftItem ([pscustomobject]@{concept_key=$key}) $true
 }catch{$AutoResearchStatus.Text=('Card could not be opened: '+$_.Exception.Message)}
}
function Initialize-AutoResearchUi {
 if($null-ne$AutoResearchPublicSignalsButton){$AutoResearchPublicSignalsButton.Content=if($script:Locale-ceq'ru'){'Сравнить публичные прокси (без AI)'}elseif($script:Locale-ceq'es'){'Comparar proxies públicos (sin IA)'}else{'Compare public proxies (no AI)'};$AutoResearchPublicSignalsButton.Add_Click({Start-AutoResearch -PublicSignals})}
 Refresh-ForgePublicSignalsSummary
 if($null-ne$AutoResearchDiscoveryButton){$AutoResearchDiscoveryButton.Content=if($script:Locale-ceq'ru'){'Исследовать новые ниши (без AI)'}elseif($script:Locale-ceq'es'){'Descubrir nichos (sin IA)'}else{'Discover new niches (no AI)'};$AutoResearchDiscoveryButton.Add_Click({Start-AutoResearch -DiscoverNiches})}
 Refresh-ForgeNicheDiscoverySummary
 Register-NicheEvidenceUiText;if($null-ne$AutoResearchSourcesButton){$AutoResearchSourcesButton.Content=Get-UiText 'niche.evidence.refresh' 'Refresh niche evidence (no AI)'}
 $script:AutoResearchProcess=$null;$script:AutoResearchRunPath='';$script:AutoResearchTimer=New-Object Windows.Threading.DispatcherTimer;$script:AutoResearchTimer.Interval=[TimeSpan]::FromSeconds(1);$AutoResearchTimer=$script:AutoResearchTimer
 $AutoResearchTimer.Add_Tick({Update-AutoResearchUi});$AutoResearchStartButton.Add_Click({Start-AutoResearch});$AutoResearchCancelButton.Add_Click({Cancel-AutoResearch});$AutoResearchOpenButton.Add_Click({Open-AutoResearchCard})
 try{$seed=Read-ForgePreparedHypotheses;if($null-ne$seed){$AutoResearchCards.ItemsSource=@($seed.cards);$AutoResearchStatus.Text=((Get-UiText 'research.prepared.count' 'Prepared hypotheses: {0}. Review sources and the exact idea/design; Amazon demand and rights are unverified. No approval is created.')-f@($seed.cards).Count)}}catch{$AutoResearchStatus.Text='Prepared hypothesis cards are unavailable; existing work is preserved.'}
 if($null-ne$AutoResearchSourcesButton){$AutoResearchSourcesButton.Add_Click({Start-AutoResearch -SourcesOnly})}
 $null=Restore-AutoResearchCards
}

# Source-discovered candidates: vocabulary supplies recognizable labels, never a demand prior.
function Get-ForgeDiscoveryVocabulary {
 $specs=@(
  'cycling|Cycling|Велосипед|Ciclismo|cycling,biking,bicycle,bicycles',
  'scrapbooking|Scrapbooking|Скрапбукинг|Scrapbooking|scrapbooking',
  'triathlon|Triathlon|Триатлон|Triatlón|triathlon,triathlete',
  'skating|Skating|Катание на доске|Patinaje|skating,skateboarding',
  'dominoes|Dominoes|Домино|Dominó|dominoes',
  '3d_printing|3D printing|3D-печать|Impresión 3D|3d printing',
  'pickleball|Pickleball|Пиклбол|Pickleball|pickleball,pickle ball',
  'ukulele|Ukulele|Укулеле|Ukelele|ukulele',
  'guitar|Guitar|Гитара|Guitarra|guitar',
  'card_making|Card making|Создание открыток|Tarjetería|card making',
  'darts|Darts|Дартс|Dardos|darts',
  'birdwatching|Birdwatching|Наблюдение за птицами|Observación de aves|birdwatching,bird watching,birding,birder',
  'chess|Chess|Шахматы|Ajedrez|chess',
  'gardening|Gardening|Садоводство|Jardinería|gardening,garden,gardener',
  'astronomy|Astronomy|Астрономия|Astronomía|astronomy,stargazing',
  'hiking|Hiking|Пешие походы|Senderismo|hiking,hiker',
  'camping|Camping|Кемпинг|Acampada|camping,camper',
  'fishing|Fishing|Рыбалка|Pesca|fishing,angler',
  'knitting|Knitting|Вязание спицами|Tejido|knitting,knitter',
  'crochet|Crochet|Вязание крючком|Ganchillo|crochet',
  'beekeeping|Beekeeping|Пчеловодство|Apicultura|beekeeping,beekeeper',
  'pottery|Pottery|Керамика|Cerámica|pottery,potter',
  'woodworking|Woodworking|Работа с деревом|Carpintería|woodworking,woodworker',
  'quilting|Quilting|Квилтинг|Acolchado|quilting,quilter',
  'running|Running|Бег|Correr|running,runner',
  'baking|Baking|Выпечка|Repostería|baking,baker',
  'photography|Photography|Фотография|Fotografía|photography,photographer',
  'reading|Reading|Чтение|Lectura|reading,bookworm',
  'kayaking|Kayaking|Каякинг|Kayak|kayaking,kayaker',
  'sewing|Sewing|Шитьё|Costura|sewing,sewist',
  'origami|Origami|Оригами|Origami|origami',
  'disc_golf|Disc golf|Диск-гольф|Disc golf|disc golf'
 )
 return @($specs|ForEach-Object{$s=$_-split'\|';[pscustomobject]@{key=$s[0];name=$s[1];ru=$s[2];es=$s[3];query=($s[1].ToLowerInvariant()+' tshirt');aliases=@($s[4]-split',')}})
}
function Get-ForgeDiscoveryAlias([string]$Title,$Topic) {
 $normalized=([Net.WebUtility]::HtmlDecode($Title).ToLowerInvariant()-replace'[^a-z0-9]+',' ').Trim()
 foreach($alias in $Topic.aliases){if((' '+$normalized+' ').Contains(' '+$alias+' ')){return [string]$alias}}
 return ''
}
function Get-ForgeDiscoveryAssessment($Observations,$Topic,[datetime]$AssessmentAt=([DateTime]::UtcNow)) {
 $derived=@();$mapping=@();$n=0
 foreach($row in @($Observations|Where-Object{$null-ne$_})){
  $n++;$alias=Get-ForgeDiscoveryAlias ([string](Get-PropertyValue $row 'title')) $Topic
  $copy=$row.PSObject.Copy()
  Add-OrSetProperty $copy 'query' $(if($alias){$alias+' tshirt'}else{$Topic.query})
  $derived+=,$copy;$mapping+=,[pscustomobject]@{index=$n;source_query=[string](Get-PropertyValue $row 'query');matched_alias=$alias;derived_filter_query=[string]$copy.query}
 }
 $assessment=Get-ForgeNicheEvidenceAssessment $derived -NowUtc $AssessmentAt
 Add-OrSetProperty $assessment 'alias_derivation' $mapping
 return $assessment
}
function Get-ForgeDiscoveredCandidates($Captures) {
 $vocabulary=@(Get-ForgeDiscoveryVocabulary);$candidates=New-Object Collections.ArrayList;$byKey=@{};$rowReviews=@();$seen=@{};$duplicates=0
 foreach($capture in $Captures){$index=0;foreach($row in @($capture.observations|Where-Object{$null-ne$_})){
  $index++;$matchedTopics=@($vocabulary|Where-Object{Get-ForgeDiscoveryAlias ([string](Get-PropertyValue $row 'title')) $_})
  $status='no_recognized_topic';$identity='';$topicKey=''
  if($matchedTopics.Count-gt1){$status='multiple_hobby_topics_owner_review'}
  elseif($matchedTopics.Count-eq1){
   $topic=$matchedTopics[0];$topicKey=$topic.key;$screen=Get-ForgeDiscoveryAssessment @($row) $topic;$review=$screen.row_reviews[0];$identity=$review.canonical_product_identity;$status=$review.status
   if($status-ceq'eligible_title_sample'){
    if($seen.ContainsKey($identity)){$duplicates++;$status='duplicate_broad_product_no_extra_weight'}else{
     $seen[$identity]=$true
     if(!$byKey.ContainsKey($topic.key)){
      $candidate=[pscustomobject]@{key=$topic.key;name=$topic.name;query=$topic.query;first_observed_order=$candidates.Count+1;seed_references=@();followup_selected=($candidates.Count-lt3);selection_reason=if($candidates.Count-lt3){'First distinct recognized single-hobby candidate in bounded source order; selected for a follow-up query, not a market rank.'}else{'Observed candidate retained; follow-up request budget already allocated in source order, not rejected for lack of demand.'}}
      [void]$candidates.Add($candidate);$byKey[$topic.key]=$candidate
     }
     $candidate=$byKey[$topic.key];$candidate.seed_references+=,[pscustomobject]@{capture_sha256=$capture.capture_sha256;source_query=$capture.query;row_index=$index;title=$row.title;source_url=$row.source_url;canonical_product_identity=$identity;matched_alias=(Get-ForgeDiscoveryAlias $row.title $topic)}
    }
   }
  }
  $rowReviews+=,[pscustomobject]@{capture_sha256=$capture.capture_sha256;row_index=$index;title=$row.title;source_url=$row.source_url;status=$status;topic_key=$topicKey;canonical_product_identity=$identity}
 }}
 return [pscustomobject]@{candidates=@($candidates);row_reviews=$rowReviews;duplicate_products_ignored=$duplicates;vocabulary_size=$vocabulary.Count;vocabulary=$vocabulary;vocabulary_policy='Fixed, disclosed hobby-label vocabulary; labels become candidates only after attributed source-title matches. Unknown labels and multi-hobby titles are retained for review. Vocabulary omissions and source order limit recall.';selection_policy='First appearance in two broad captures; duplicate product IDs carry no additional weight. Maximum three follow-up queries. Source ordering and listing counts do not estimate demand, market competition, originality or seller independence.'}
}
function Assert-ForgeDiscoveryCapture($Capture,[string]$Query,[int]$Limit) {
 if($Capture.query-cne$Query-or$Capture.observations-isnot[Array]-or$Capture.observations.Count-gt$Limit-or$Capture.status-cnotin@('captured_product_metadata','captured_zero_items','source_refused_no_retry_or_bypass','source_unavailable','not_requested_after_source_refusal')){throw 'Invalid discovery capture envelope'}
 if($Capture.status-in@('captured_product_metadata','captured_zero_items')){
  $url='https://feed.zazzle.com/rss?qs='+[Uri]::EscapeDataString($Query)+'&st=popularity&sp=30&ps='+$Limit
  if($Capture.source_url-cne$url-or$Capture.capture_sha256-cnotmatch'^[0-9a-f]{64}$'-or$Capture.raw_rss_sha256-cnotmatch'^[0-9a-f]{64}$'-or$Capture.limit-ne$Limit-or($Capture.status-ceq'captured_zero_items')-ne($Capture.observations.Count-eq0)){throw 'Discovery capture query/hash/status binding invalid'}
  $null=ConvertFrom-ResearchUtc $Capture.captured_at
  foreach($row in $Capture.observations){if($null-eq$row-or$row.query-cne$Query){throw 'Discovery observation belongs to another source query'}}
 }elseif($Capture.observations.Count){throw 'Unavailable source cannot supply positive discovery rows'}
}
function Read-ForgeDiscoveryCapture([string]$Query,[int]$Limit) {
 $sample=Get-ZazzleResearchSample $Query $Limit -AllowEmpty
 try{
  $payload=Read-LocalCheckEvidencePayload $sample.path;$export=$payload.data
  $url='https://feed.zazzle.com/rss?qs='+[Uri]::EscapeDataString($Query)+'&st=popularity&sp=30&ps='+$Limit
  $null=Assert-ForgeRssCacheBinding $export $Query $url $Limit
  return [pscustomobject]@{query=$Query;limit=$Limit;status=if(@($export.observations).Count){'captured_product_metadata'}else{'captured_zero_items'};capture_sha256=$payload.sha256;source_url=$url;captured_at=$export.collected_at;raw_rss_sha256=[string](Get-PropertyValue $export.feed_metadata 'raw_rss_sha256');cache_hit=[bool]$sample.cache_hit;network_requests=[int]$sample.network_requests;observations=@($export.observations)}
 }catch{$_.Exception.Data['source_network_requests']=[int]$sample.network_requests;throw}
}
function Invoke-ForgeNicheDiscovery([string]$RunPath='',$RunState=$null) {
 $broad=@();$followups=@();$requests=0;$cacheHits=0;$refused=$false
 foreach($query in @('hobby tshirt','hobbies tshirt')){
  if($RunPath){Assert-AutoResearchNotCancelled $RunPath}
  if($refused){$broad+=,[pscustomobject]@{query=$query;status='not_requested_after_source_refusal';observations=@();network_requests=0};continue}
  try{$capture=Read-ForgeDiscoveryCapture $query 20;$broad+=,$capture;$requests+=$capture.network_requests;if($capture.cache_hit){$cacheHits++}}
  catch{$attempts=0;if($_.Exception.Data.Contains('source_network_requests')){$attempts=[int]$_.Exception.Data['source_network_requests']};$requests+=$attempts;$refused=$_.Exception.Data.Contains('source_status')-and$_.Exception.Data['source_status']-ceq'refused';$broad+=,[pscustomobject]@{query=$query;status=if($refused){'source_refused_no_retry_or_bypass'}else{'source_unavailable'};error=$_.Exception.Message;observations=@();network_requests=$attempts}}
  if($null-ne$RunState){$RunState.source_requests=$requests;$RunState.source_cache_hits=$cacheHits;$RunState.phase='broad niche discovery: '+$query;if($RunPath){Write-AutoResearchRun $RunPath $RunState}}
 }
 $discovered=Get-ForgeDiscoveredCandidates $broad
 foreach($candidate in @($discovered.candidates|Where-Object{$_.followup_selected})){
  if($RunPath){Assert-AutoResearchNotCancelled $RunPath}
  $topic=@(Get-ForgeDiscoveryVocabulary|Where-Object{$_.key-ceq$candidate.key})[0]
  if($refused){$capture=[pscustomobject]@{query=$candidate.query;status='not_requested_after_source_refusal';observations=@();network_requests=0}}
  else{try{$capture=Read-ForgeDiscoveryCapture $candidate.query 10;$requests+=$capture.network_requests;if($capture.cache_hit){$cacheHits++}}
   catch{$attempts=0;if($_.Exception.Data.Contains('source_network_requests')){$attempts=[int]$_.Exception.Data['source_network_requests']};$requests+=$attempts;$refused=$_.Exception.Data.Contains('source_status')-and$_.Exception.Data['source_status']-ceq'refused';$capture=[pscustomobject]@{query=$candidate.query;status=if($refused){'source_refused_no_retry_or_bypass'}else{'source_unavailable'};error=$_.Exception.Message;observations=@();network_requests=$attempts}}}
  $assessment=Get-ForgeDiscoveryAssessment $capture.observations $topic
  $recommendation=if($capture.status-notin@('captured_product_metadata','captured_zero_items')){'source_unavailable_no_recommendation'}elseif(!$assessment.comparison_eligible){'insufficient_wording_basis_no_recommendation'}else{'exploratory_wording_review_only'}
  $followups+=,[pscustomobject]@{key=$candidate.key;name=$candidate.name;query=$candidate.query;capture=$capture;assessment=$assessment;recommendation=$recommendation;recommendation_basis='Broad title references identify this topic; the separate focused sample is checked for attributed matching T-shirt titles. This supports wording research only, never sales, low competition or a profitable-niche claim.';demand_evidence='unavailable_no_purchase_sales_or_rank_history';competition_evidence='bounded_listing_overlap_only_market_size_and_seller_independence_unknown';market_rank=$null;opportunity_score=$null}
  if($null-ne$RunState){$RunState.source_requests=$requests;$RunState.source_cache_hits=$cacheHits;$RunState.phase='candidate follow-up: '+$candidate.query;if($RunPath){Write-AutoResearchRun $RunPath $RunState}}
 }
 if($RunPath){Assert-AutoResearchNotCancelled $RunPath}
 if($requests-gt5){throw 'Discovery request budget exceeded'}
 $report=[pscustomobject]@{schema='forge.niche_discovery.v1';mode='source_discovery_without_models';completed_at=[DateTime]::UtcNow.ToString('o');broad_captures=$broad;discovery=$discovered;followups=$followups;source_requests=$requests;cache_hits=$cacheHits;max_source_requests=5;max_raw_records=70;model_requests=0;gpu_requests=0;drafts_created=0;approvals_created=0;demand_verified=$false;market_rank_available=$false;rank_refusal_reason='No comparable purchase/sales/rank-history data, known marketplace coverage, market size, independent-seller count or validated apparel buyer segment. RSS popularity order and sample/card counts cannot rank demand or low competition.';stopped_after_refusal=$refused}
 $null=Save-ForgeNicheEvidenceRun $report -Storage 'niche-discovery-v1'
 return $report
}

function Read-ForgeLatestNicheDiscovery {
 $root=Join-Path $script:StateRoot 'niche-discovery-v1';$pointer=Join-Path $root 'latest.sha256';$origin='bundled_public_capture'
 if(Test-Path -LiteralPath $root){$item=Get-Item -LiteralPath $root -Force;if($item-isnot[IO.DirectoryInfo]-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Discovery root is not an ordinary directory'};if(!(Test-Path -LiteralPath $pointer)-and@(Get-ChildItem -LiteralPath $root -Force).Count){throw 'Discovery pointer missing; existing reports retained; no bundled substitution'}}
 if(Test-Path -LiteralPath $pointer){$item=Get-Item -LiteralPath $pointer -Force;if($item-isnot[IO.FileInfo]-or$item.Length-gt128-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Discovery pointer is invalid'};$sha=[IO.File]::ReadAllText($pointer).Trim();if($sha-cnotmatch'^[0-9a-f]{64}$'){throw 'Discovery pointer hash invalid'};$p=Read-LocalCheckEvidencePayload (Join-Path $root ($sha+'.json'));if($p.sha256-cne$sha){throw 'Discovery snapshot changed'};$report=$p.data;$origin='saved_local_capture'}
 else{$file=Join-Path (Split-Path $script:ModuleRoot -Parent) 'Data\Forge.NicheDiscoverySnapshot.json';if(!(Test-Path -LiteralPath $file)){return $null};$report=(Read-LocalCheckEvidencePayload $file).data}
 if($report.schema-cne'forge.niche_discovery.v1'-or$report.mode-cne'source_discovery_without_models'-or$report.broad_captures-isnot[Array]-or$report.broad_captures.Count-ne2-or$report.followups-isnot[Array]-or$report.followups.Count-gt3){throw 'Invalid discovery envelope'}
 foreach($n in @('model_requests','gpu_requests','drafts_created','approvals_created')){$v=Get-PropertyValue $report $n;if(($v-isnot[int]-and$v-isnot[long])-or$v-ne0){throw 'Discovery cannot grant creative authority'}}
 foreach($n in @('demand_verified','market_rank_available')){$v=Get-PropertyValue $report $n;if($v-isnot[bool]-or$v){throw 'Unsupported discovery market authority'}}
 foreach($n in @('source_requests','cache_hits')){$v=Get-PropertyValue $report $n;if(($v-isnot[int]-and$v-isnot[long])-or$v-lt0-or$v-gt5){throw 'Invalid discovery request count'}}
 if((ConvertFrom-ResearchUtc $report.completed_at)-gt[DateTime]::UtcNow.AddMinutes(5)){throw 'Discovery timestamp in future'}
 $i=0;foreach($c in $report.broad_captures){Assert-ForgeDiscoveryCapture $c @('hobby tshirt','hobbies tshirt')[$i] 20;$i++}
 $derived=Get-ForgeDiscoveredCandidates $report.broad_captures
 $selected=@($derived.candidates|Where-Object{$_.followup_selected});$seen=@{}
 foreach($f in $report.followups){$topic=@(Get-ForgeDiscoveryVocabulary|Where-Object{$_.key-ceq$f.key});if($topic.Count-ne1-or$seen.ContainsKey($f.key)-or$selected.key-cnotcontains$f.key-or$f.query-cne$topic[0].query-or$f.capture.query-cne$f.query-or$f.capture.observations-isnot[Array]-or$f.capture.observations.Count-gt10){throw 'Invalid discovery follow-up binding'};$seen[$f.key]=$true
  Assert-ForgeDiscoveryCapture $f.capture $f.query 10
  $a=Get-ForgeDiscoveryAssessment $f.capture.observations $topic[0];Add-OrSetProperty $f 'assessment' $a;Add-OrSetProperty $f 'market_rank' $null;Add-OrSetProperty $f 'opportunity_score' $null
  Add-OrSetProperty $f 'recommendation' $(if($f.capture.status-notin@('captured_product_metadata','captured_zero_items')){'source_unavailable_no_recommendation'}elseif($a.comparison_eligible){'exploratory_wording_review_only'}else{'insufficient_wording_basis_no_recommendation'})
 }
 Add-OrSetProperty $report 'discovery' $derived;Add-OrSetProperty $report 'display_origin' $origin;return $report
}
function Refresh-ForgeNicheDiscoverySummary {
 if($null-eq$AutoResearchDiscoverySummary){return}
 $ru=$script:Locale-ceq'ru';$es=$script:Locale-ceq'es'
 try{
  $r=Read-ForgeLatestNicheDiscovery
  if($null-eq$r){$AutoResearchDiscoverySummary.Text=if($ru){'Исследование новых ниш ещё не выполнено. Отдельная кнопка читает общий источник и проверяет до трёх найденных тем без AI.'}elseif($es){'Todavía no hay descubrimiento de nichos. El botón consulta una fuente general y hasta tres temas encontrados, sin IA.'}else{'No niche discovery saved yet. The button reads broad sources and follows up at most three observed topics without AI.'};return}
  $lines=New-Object Collections.Generic.List[string]
  $lines.Add($(if($ru){'НОВЫЕ НАПРАВЛЕНИЯ ДЛЯ ИССЛЕДОВАНИЯ — рейтинг спроса/низкой конкуренции недоступен.'}elseif($es){'TEMAS PARA INVESTIGAR — clasificación de demanda/baja competencia no disponible.'}else{'TOPICS FOR FURTHER RESEARCH — demand/low-competition ranking unavailable.'}))
  $lines.Add(('Capture: '+$r.completed_at+' | '+$r.display_origin+' | '+$r.source_requests+' GET; '+$r.cache_hits+' cache | models/GPU/approvals: 0'))
  $lines.Add('Zazzle: historical captures only. New RSS requests blocked by robots /*st=*; policy observed2026-10-15T20:06:54Z. No parameter removal or bypass.')
  $lines.Add($(if($ru){'Темы распознаны по словарю хобби в найденных названиях. Первые три по порядку источника проверяются отдельным запросом; этот порядок не означает качество ниши. Повторные product ID не добавляют вес.'}elseif($es){'Los temas se reconocen con un vocabulario de aficiones en títulos observados. Se consultan los tres primeros según el orden de la fuente; ese orden no indica calidad. Los product ID repetidos no añaden peso.'}else{'Topics use a disclosed hobby vocabulary matched to observed titles. First three in source order receive follow-up queries; order is not niche merit. Repeated product IDs add no weight.'}))
  $lines.Add(('Vocabulary ('+$r.discovery.vocabulary_size+'): '+(($r.discovery.vocabulary|ForEach-Object{if($ru){$_.ru}elseif($es){$_.es}else{$_.name}})-join', ')))
  $vocab=Get-ForgeDiscoveryVocabulary
  foreach($c in $r.discovery.candidates){
   $topic=@($vocab|Where-Object{$_.key-ceq$c.key})[0];$label=if($ru){$topic.ru}elseif($es){$topic.es}else{$topic.name}
   $f=@($r.followups|Where-Object{$_.key-ceq$c.key})
   $lines.Add('');$lines.Add($label+' | query: '+$c.query)
   if(!$f.Count){$lines.Add($(if($ru){'Найдена в общем источнике; отдельная проверка не выполнена из-за лимита. Не отклонена по спросу.'}elseif($es){'Observado; sin consulta adicional por el límite. No rechazado por demanda.'}else{'Observed; no follow-up within budget. Not rejected for lack of demand.'}))}
   else{$lines.Add(('Follow-up: '+$f[0].capture.status+' | '+$f[0].assessment.eligible_unique_products+'/'+$f[0].assessment.captured_records+' matching products | '+$f[0].recommendation));$lines.Add($(if($ru){'Спрос: неизвестен. Конкуренция рынка и независимость продавцов: неизвестны. Доступно только исследование формулировок.'}elseif($es){'Demanda, competencia del mercado e independencia de vendedores: desconocidas. Solo investigación de textos.'}else{'Demand, marketplace competition and seller independence: unknown. Wording research only.'}))}
   foreach($ref in @($c.seed_references|Select-Object -First 2)){$lines.Add(('['+$ref.capture_sha256.Substring(0,12)+':'+$ref.row_index+'] '+$ref.title+' | '+$ref.source_url))}
  }
  if(!$r.discovery.candidates.Count){$lines.Add($(if($ru){'Нет поддержанных кандидатов в этой ограниченной выборке. Недоступность источника не означает нулевой спрос.'}elseif($es){'Sin candidatos respaldados en esta muestra. Fuente no disponible no significa demanda cero.'}else{'No supported candidates in this bounded sample. Unavailable source does not mean zero demand.'}))}
  $lines.Add('');$lines.Add(('Broad source states: '+(($r.broad_captures|ForEach-Object{$_.query+' = '+$_.status})-join'; ')))
  $lines.Add($(if($ru){'Нельзя построить рыночный рейтинг: нет сопоставимых продаж, истории ранга, размера рынка или проверенного сегмента покупателей. RSS popularity, строки и карточки этого не заменяют. Неизвестные словарю темы и смешанные темы сохраняются для ручного анализа; это не полный обзор рынка. Идеи, концепты и approval не менялись.'}elseif($es){'Sin clasificación: faltan ventas comparables, historial de rango, tamaño de mercado y compradores verificados. RSS popularity, filas y tarjetas no los sustituyen. El vocabulario y la muestra limitan la cobertura. No se modificaron ideas, conceptos ni aprobaciones.'}else{'Ranking refused: no comparable sales, rank history, market size or verified buyer segment. RSS popularity, rows and cards cannot substitute. Unknown/mixed topics are retained for review; vocabulary and source sampling limit recall. Ideas, concepts and approvals unchanged.'}))
  $AutoResearchDiscoverySummary.Text=$lines-join[Environment]::NewLine
 }catch{$AutoResearchDiscoverySummary.Text=$(if($ru){'Сохранённое исследование новых ниш недоступно; файлы сохранены, старый отчёт не подставлен. Обновите источники или восстановите проверенную копию. '}elseif($es){'Descubrimiento guardado no disponible; archivos conservados, sin sustituir otro informe. '}else{'Saved niche discovery unavailable; files retained, no older report substituted. Refresh sources or restore a verified copy. '})+$_.Exception.Message}
}
