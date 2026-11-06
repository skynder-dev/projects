# One documented, bounded RSS source. No image requests, automatic polling or credentials.
function ConvertFrom-ZazzleRss([string]$Xml,[string]$Query,[string]$SourceUrl,[datetime]$FetchedAt=([DateTime]::UtcNow),[switch]$AllowEmpty) {
 $settings=New-Object Xml.XmlReaderSettings;$settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit;$settings.XmlResolver=$null;$settings.MaxCharactersInDocument=1MB
 $sr=New-Object IO.StringReader $Xml;$reader=[Xml.XmlReader]::Create($sr,$settings);$doc=New-Object Xml.XmlDocument;$doc.XmlResolver=$null
 try{$doc.Load($reader)}finally{$reader.Dispose();$sr.Dispose()}
 $channel=$doc.SelectSingleNode('/rss/channel');if($null-eq$channel){throw 'RSS channel missing'}
 $items=@($channel.SelectNodes('item'));if(!$items.Count-and!$AllowEmpty){throw 'RSS has zero item records; HTTP 200/totalResults is not a product source'}
 if($items.Count-gt20){throw 'RSS pilot accepts at most 20 item records'}
 $ttlNode=$channel.SelectSingleNode('ttl');$ttl=60;if($null-ne$ttlNode){if(![int]::TryParse($ttlNode.InnerText,[ref]$ttl)-or$ttl-lt1-or$ttl-gt1440){throw 'Invalid feed TTL'}}
 $rows=@();$ids=@{};$links=@{};foreach($item in $items){
  $values=@{};foreach($field in @('title','link','guid','author','pubDate','price')){$node=$item.SelectSingleNode($field);$values[$field]=if($null-ne$node){$node.InnerText.Trim()}else{$null}}
  $u=[Uri]$values.link;if($u.Scheme-cne'https'-or$u.Host-cne'www.zazzle.com'-or$u.Port-ne443-or$u.UserInfo-or$u.Fragment-or$u.AbsolutePath-eq'/'-or!$values.title-or!$values.guid-or!$values.author){throw 'Incomplete product link/title/guid/creator attribution'}
  foreach($field in @('title','author','guid','link','price','pubDate')){$max=switch($field){'title'{500};'author'{200};'guid'{512};'link'{2048};'price'{80};'pubDate'{128}};if($null-ne$values[$field]-and$values[$field].Length-gt$max){throw 'Oversized RSS field'}}
  $identity=$u.AbsoluteUri+'|'+$values.title+'|'+$values.author+'|'+$values.price+'|'+$values.pubDate
  if($ids.ContainsKey($values.guid)){if($ids[$values.guid]-cne$identity){throw 'Conflicting rows share an RSS guid'};continue}
  if($links.ContainsKey($u.AbsoluteUri)){if($links[$u.AbsoluteUri]-cne$identity){throw 'Conflicting rows share a product link'};continue}
  $ids[$values.guid]=$identity;$links[$u.AbsoluteUri]=$identity
  $priceDisplay=$values.price;$price=$null;$currency=$null
  $ns=New-Object Xml.XmlNamespaceManager $doc.NameTable;$ns.AddNamespace('media','http://search.yahoo.com/mrss/')
  $mediaPrice=$item.SelectSingleNode('media:price',$ns)
  if($null-ne$mediaPrice-and$mediaPrice.HasAttribute('currency')-and$mediaPrice.GetAttribute('currency')-cmatch'^[A-Z]{3}$'){$currency=$mediaPrice.GetAttribute('currency');$number=0M;if([decimal]::TryParse($mediaPrice.InnerText,[Globalization.NumberStyles]::Number,[Globalization.CultureInfo]::InvariantCulture,[ref]$number)){$price=$number}else{$currency=$null}}
  $missing=@('sales_unknown','amazon_competition_unknown');if(!$priceDisplay){$missing+='price_unknown'};if(!$currency){$missing+='currency_code_not_supplied'};if(!$values.pubDate){$missing+='publication_date_unknown'}
  $rows+=[pscustomobject]@{source_url=$u.AbsoluteUri;observation_kind='marketplace_listing';observation_text=('Observed listing titled '+$values.title+' by creator '+$values.author+'. Price displayed: '+$(if($priceDisplay){$priceDisplay}else{'unknown'})+'. Publication date is listing metadata, not sale date.');observed_at=$FetchedAt.ToString('o');marketplace='zazzle.com';product_id=$values.guid;guid=$values.guid;title=$values.title;creator=$values.author;pub_date=$values.pubDate;price=$price;currency=$currency;price_display=$priceDisplay;query=$Query;feed_source_url=$SourceUrl;price_observed_at=$FetchedAt.ToString('o');missing_flags=$missing}
 }
 return [pscustomobject]@{schema='forge.research_import.v1';adapter_key='public_observations_v1';synthetic=$false;niche=[pscustomobject]@{niche_key=('rss_'+(Get-StringSha256Hex $Query.ToLowerInvariant()).Substring(0,24));name=('Zazzle listing sample: '+$Query);audience='Audience not verified; keywords describe this sample only'};collected_at=$FetchedAt.ToString('o');freshness_policy=[pscustomobject]@{max_age_days=1;basis='Conservative pilot application policy, not a market guarantee'};observations=$rows;feed_metadata=[pscustomobject]@{query=$Query;source_url=$SourceUrl;fetched_at=$FetchedAt.ToString('o');ttl_minutes=$ttl;cache_valid_until=$FetchedAt.AddMinutes($ttl).ToString('o');result_status=if($rows.Count){'items_observed'}else{'no_items_observed'};item_count=$rows.Count;ordering='Zazzle popularity / 30-day sort parameter, not verified sales';total_results_is_sales=$false;description_or_image_saved=$false}}
}
function Assert-ForgeRssCacheBinding($Export,[string]$Query,[string]$Url,[int]$Limit,[DateTime]$NowUtc=([DateTime]::UtcNow)) {
 Assert-ResearchNoSecrets $Export
 if($Export.schema-cne'forge.research_import.v1'-or$Export.adapter_key-cne'public_observations_v1'-or$Export.synthetic-isnot[bool]-or$Export.synthetic){throw 'RSS cache is not a real capture envelope'}
 $meta=$Export.feed_metadata;$ttl=$meta.ttl_minutes
 if($meta.query-cne$Query-or$meta.source_url-cne$Url-or($ttl-isnot[int]-and$ttl-isnot[long])-or$ttl-lt1-or$ttl-gt1440){throw 'RSS cache request binding/TTL changed'}
 $at=ConvertFrom-ResearchUtc $meta.fetched_at;$until=ConvertFrom-ResearchUtc $meta.cache_valid_until
 if($at-gt$NowUtc.AddMinutes(5)-or$until-ne$at.AddMinutes($ttl)-or(ConvertFrom-ResearchUtc $Export.collected_at)-ne$at){throw 'RSS cache capture dates changed'}
 if($Export.observations-isnot[Array]-or$Export.observations.Count-lt0-or$Export.observations.Count-gt$Limit){throw 'RSS cache exceeds the requested record budget'}
 $ids=@{};$links=@{}
 foreach($row in $Export.observations){foreach($n in @('source_url','query','feed_source_url','title','creator','guid','product_id','observation_text')){if((Get-PropertyValue $row $n)-isnot[string]-or[string]::IsNullOrWhiteSpace([string](Get-PropertyValue $row $n))){throw 'RSS cache field has an invalid type'}}
  $uri=[Uri]$row.source_url;if($row.query-cne$Query-or$row.feed_source_url-cne$Url-or(ConvertFrom-ResearchUtc $row.observed_at)-ne$at-or$uri.Host-cne'www.zazzle.com'-or$uri.Port-ne443-or$uri.Scheme-cne'https'-or$uri.UserInfo-or$uri.Fragment-or$uri.AbsolutePath-eq'/'-or$row.observation_kind-cne'marketplace_listing'-or$row.marketplace-cne'zazzle.com'-or!$row.title-or!$row.creator-or!$row.guid-or$row.product_id-cne$row.guid){throw 'RSS cache row does not belong to the captured query'}
  if($ids.ContainsKey($row.guid)-or$links.ContainsKey($row.source_url)){throw 'Duplicate product identity in RSS cache'};$ids[$row.guid]=$true;$links[$row.source_url]=$true
  $expected='Observed listing titled '+$row.title+' by creator '+$row.creator+'. Price displayed: '+$(if($row.price_display){$row.price_display}else{'unknown'})+'. Publication date is listing metadata, not sale date.'
  if($row.observation_text-cne$expected){throw 'RSS cache observation text differs from captured metadata'}
 }
 if($Export.observations.Count){$null=ConvertFrom-PublicResearchExport $Export ('0'*64) $NowUtc}elseif([string](Get-PropertyValue $meta 'result_status')-cne'no_items_observed'-or(Get-PropertyValue $meta 'item_count')-ne0){throw 'Empty RSS cache lacks explicit no-items result'}
 return ($until-gt$NowUtc)
}
function Get-ForgeResearchQueryTokens([string]$Text) {
 $stop=@('t','shirt','shirts','tshirt','tshirts','tee','tees','gift','gifts','funny','men','mens','women','womens','for','and','the','a','of','in','on','with')
 $tokens=@();foreach($m in [regex]::Matches($Text.ToLowerInvariant(),'[a-z0-9]+')){$t=$m.Value;if($stop-contains$t-or$t.Length-lt3){continue};if($t.EndsWith('ing')-and$t.Length-gt6){$t=$t.Substring(0,$t.Length-3)}elseif($t.EndsWith('s')-and$t.Length-gt4){$t=$t.Substring(0,$t.Length-1)};$tokens+=$t}
 return @($tokens|Select-Object -Unique)
}
function Get-ForgeNicheEvidenceAssessment($Observations,[string]$Query='',[DateTime]$NowUtc=([DateTime]::UtcNow)) {
 $reviews=@();$identities=@{};$eligible=@();$context=0;$index=0
 foreach($row in @($Observations|Where-Object{$null-ne$_})){
  $index++;$kind=[string](Get-PropertyValue $row 'observation_kind');$title=[string](Get-PropertyValue $row 'title');$url=[string](Get-PropertyValue $row 'source_url')
  $rowQuery=[string](Get-PropertyValue $row 'query');if(!$rowQuery){$rowQuery=$Query};$tokens=@(Get-ForgeResearchQueryTokens $rowQuery);$words=@(Get-ForgeResearchQueryTokens $title);$matched=@($tokens|Where-Object{$words-contains$_})
  $status='unknown_observation';$identity='';$flags=@();$creator=([string](Get-PropertyValue $row 'creator')).Trim().ToLowerInvariant()
  if($kind-ceq'audience_context'){$context++;$status='audience_context_only'}
  elseif($kind-ceq'marketplace_listing'){
   $valid=$false;try{$uri=[Uri]$url;$valid=$uri.Scheme-ceq'https'-and$uri.Host-ceq'www.zazzle.com'-and!$uri.UserInfo-and$uri.Port-eq443;if($valid){$product=[regex]::Match($uri.AbsolutePath,'-(\d{10,})$');$identity=if($product.Success){'zazzle:'+ $product.Groups[1].Value}else{$uri.GetLeftPart([UriPartial]::Path).ToLowerInvariant()}}}catch{}
   $fresh=$false;try{$observed=ConvertFrom-ResearchUtc (Get-PropertyValue $row 'observed_at');$fresh=$observed-le$NowUtc.AddMinutes(5)-and($NowUtc-$observed).TotalDays-le1}catch{};$productType=($title+' '+$url)-match'(?i)(^|[^a-z])(t[ _-]?shirts?|tees?)([^a-z]|$)'
   if(!$valid-or!$title-or!$creator){$status='incomplete_attribution'}
   elseif($identities.ContainsKey($identity)){$status='duplicate_product'}
   else{
    if(!$fresh){$status='stale_or_undated_observation_review'}elseif(!$tokens.Count){$status='query_unknown'}
    elseif(!$matched.Count){$status='off_topic'}
    elseif($matched.Count-ne$tokens.Count){$status='partial_topic_review'}
    elseif(!$productType){$status='product_type_unverified'}elseif($title-match'(?i)\bu[0-9a-f]{4}\b|\\u[0-9a-f]{4}|\uFFFD'){$status='source_text_encoding_review'}
    elseif($title-match'(?i)\b(jesus|christian|religious|wine|beer|suicide|memorial|eclipse|flag|20[0-9]{2})\b'){$status='mixed_theme_or_time_specific_review';$flags+='Explicit co-theme/event/year in title; same hobby word does not establish the same buyer segment.'}
    else{$identities[$identity]=$true;$status='eligible_title_sample';$eligible+=,[pscustomobject]@{creator=$creator;title=$title;identity=$identity}}
   }
  }
  $reviews+=,[pscustomobject]@{index=$index;status=$status;title=$title;source_url=$url;query=$rowQuery;topic_tokens=$tokens;matched_tokens=$matched;canonical_product_identity=$identity;flags=$flags}
 }
 $creators=@($eligible|ForEach-Object{$_.creator}|Sort-Object -Unique).Count;$titles=@($eligible|ForEach-Object{$_.title.Trim().ToLowerInvariant()}|Sort-Object -Unique).Count;$count=$eligible.Count;$compare=$count-ge2-and$creators-ge2-and$titles-ge2
 $sample=if($count-eq0){'no_eligible_observed_products'}elseif(!$compare){'single_or_single_creator_sample'}elseif($count-lt5){'thin_title_sample'}else{'bounded_title_sample'}
 return [pscustomobject]@{schema='forge.niche_evidence_assessment.v1';captured_records=$reviews.Count;audience_context_records=$context;observed_listing_records=@($reviews|Where-Object{$_.status-notin@('audience_context_only','unknown_observation','incomplete_attribution')}).Count;eligible_unique_products=$count;distinct_eligible_creators=$creators;distinct_eligible_title_strings=$titles;duplicate_title_records=$count-$titles;creator_independence_verified=$false;review_or_excluded_records=$reviews.Count-$context-$count;sample_status=$sample;comparison_eligible=$compare;selection_reason=if($compare){'Enough distinct fully matching T-shirt product identities, title strings and creator labels for a bounded wording comparison only; not a demand or opportunity score.'}else{'Insufficient distinct fully matching T-shirt records for automatic comparison; retain the observations without creating a supported niche claim.'};row_reviews=$reviews;relevance_method='Conservative lexical/product-type/co-theme screen, not semantic buyer verification';audience_verified=$false;demand_status='unverified_no_sales_or_purchase_evidence';amazon_demand_verified=$false;market_opportunity_score=$null;zero_result_meaning='No eligible records observed in this bounded capture; not proof of no products or no demand.'}
}
function Select-ForgeRelevantResearchRows($Export,[string]$Query) {
 $assessment=Get-ForgeNicheEvidenceAssessment $Export.observations $Query
 $indices=@($assessment.row_reviews|Where-Object{$_.status-ceq'eligible_title_sample'}|ForEach-Object{$_.index});$kept=@();$i=0
 foreach($row in $Export.observations){$i++;if($indices-contains$i){$kept+=,$row}}
 if(!$assessment.comparison_eligible){$errorObject=New-Object InvalidOperationException ('Insufficient relevant product sample: '+$assessment.sample_status+'. '+$assessment.selection_reason);$errorObject.Data['niche_assessment']=$assessment;throw $errorObject}
 $copy=ConvertFrom-ForgeJsonObjectStrict ($Export|ConvertTo-Json -Depth 30)
 $copy.observations=$kept
 Add-OrSetProperty $copy 'selection_review' ([pscustomobject]@{method=$assessment.relevance_method;query_tokens=@(Get-ForgeResearchQueryTokens $Query);retained=$kept.Count;rejected=@($assessment.row_reviews|Where-Object{$_.status-cne'eligible_title_sample'});assessment=$assessment;demand_verified=$false})
 return $copy
}
function Save-ForgeRssCaptureSnapshot($Export,[string]$Root) {
 $json=$Export|ConvertTo-Json -Depth 30;$sha=Get-StringSha256Hex $json
 $dir=Join-Path $Root 'captures';Ensure-Dir $dir;$path=Join-Path $dir ($sha+'.json')
 if(Test-Path -LiteralPath $path){
  if((Get-Item -LiteralPath $path -Force).Attributes-band[IO.FileAttributes]::ReparsePoint){throw 'A redirected source snapshot was preserved; no source was imported.'}
  if((Get-FileSha256Hex $path)-ceq$sha){return $path}
  [IO.File]::Move($path,($path+'.invalid.'+[Guid]::NewGuid().ToString('N')))
 }
 $pending=$path+'.pending.'+[Guid]::NewGuid().ToString('N');$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes($json)
 $stream=New-Object IO.FileStream($pending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 if((Get-FileSha256Hex $pending)-cne$sha){throw 'Source snapshot staging hash differs; files preserved.'}
 try{[IO.File]::Move($pending,$path)}catch{if((Test-Path -LiteralPath $path)-and(Get-FileSha256Hex $path)-ceq$sha){Remove-Item -LiteralPath $pending -Force}else{throw}}
 return $path
}
function Write-ForgeRssCache([string]$Cache,$Export,[string]$Query,[string]$Url,[int]$Limit,[string]$ExpectedCacheSha='') {
 $json=$Export|ConvertTo-Json -Depth 30;$pending=$Cache+'.pending.'+[Guid]::NewGuid().ToString('N');$bytes=(New-Object Text.UTF8Encoding($false)).GetBytes($json)
 $stream=New-Object IO.FileStream($pending,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
 $verified=ConvertFrom-ForgeJsonObjectStrict ([IO.File]::ReadAllText($pending));$null=Assert-ForgeRssCacheBinding $verified $Query $Url $Limit
 if(Test-Path -LiteralPath $Cache){
  if(!$ExpectedCacheSha-or(Get-FileSha256Hex $Cache)-cne$ExpectedCacheSha){throw 'Shared source cache changed; the separate captured source remains available.'}
  $previous=$Cache+'.previous.'+[Guid]::NewGuid().ToString('N');if(Test-Path -LiteralPath $previous){throw 'Existing cache recovery file was preserved.'}
  [IO.File]::Replace($pending,$Cache,$previous,$true)
 }else{
  if($ExpectedCacheSha){throw 'Shared source cache disappeared; captured source remains available.'}
  [IO.File]::Move($pending,$Cache)
 }
}
function Get-ZazzleResearchSample([string]$Query,[int]$Limit=5,[switch]$AllowEmpty){
 if([string]::IsNullOrWhiteSpace($Query)-or$Query.Length-gt100-or$Limit-lt5-or$Limit-gt20){throw 'Explicit query and 5..20 record pilot limit required'}
 $url='https://feed.zazzle.com/rss?qs='+[Uri]::EscapeDataString($Query)+'&st=popularity&sp=30&ps='+$Limit
 $root=Join-Path $script:StateRoot 'research-import-v1';Ensure-Dir $root;$cache=Join-Path $root ((Get-StringSha256Hex $url)+'.rss-rows.json')
 $expectedCacheSha='';$cached=$null
 if(Test-Path -LiteralPath $cache){try{if((Get-Item -LiteralPath $cache).Length-gt2MB){throw 'RSS cache exceeds size budget'};$expectedCacheSha=Get-FileSha256Hex $cache;$e=ConvertFrom-ForgeJsonObjectStrict (Get-Content -LiteralPath $cache -Raw -Encoding UTF8);if(Assert-ForgeRssCacheBinding $e $Query $url $Limit){$cached=$e}}catch{[IO.File]::Move($cache,($cache+'.invalid-'+[guid]::NewGuid().ToString('N')));throw 'RSS cache rejected and preserved for diagnosis. No source request sent; explicit retry is available.'}}
 if($null-ne$cached){if(!$cached.observations.Count-and!$AllowEmpty){throw 'RSS has zero item records; bounded no-items capture retained; no retry or demand inference'};$capture=Save-ForgeRssCaptureSnapshot $cached $root;return [pscustomobject]@{export=$cached;path=$capture;cache_hit=$true;network_requests=0;cache_warning=''}}
 Assert-ForgeZazzleNetworkAllowed $url
 Add-Type -AssemblyName System.Net.Http
 $handler=New-Object Net.Http.HttpClientHandler;$handler.UseProxy=$false;$handler.AllowAutoRedirect=$false;$handler.UseCookies=$false
 $client=New-Object Net.Http.HttpClient($handler);$client.Timeout=[TimeSpan]::FromSeconds(30);$client.MaxResponseContentBufferSize=1MB
 try{$response=$client.GetAsync($url).GetAwaiter().GetResult();try{if([int]$response.StatusCode-in@(403,429)){$refused=New-Object InvalidOperationException 'Source refused/throttled request; no retry or bypass';$refused.Data['source_status']='refused';$refused.Data['http_status']=[int]$response.StatusCode;throw $refused};if(!$response.IsSuccessStatusCode){throw 'RSS source error; no retry'};$body=$response.Content.ReadAsStringAsync().GetAwaiter().GetResult();$e=ConvertFrom-ZazzleRss $body $Query $url -AllowEmpty;Add-OrSetProperty $e.feed_metadata 'raw_rss_sha256' (Get-StringSha256Hex $body);$null=Assert-ForgeRssCacheBinding $e $Query $url $Limit;$capture=Save-ForgeRssCaptureSnapshot $e $root;$cacheWarning='';try{Write-ForgeRssCache $cache $e $Query $url $Limit $expectedCacheSha}catch{$cacheWarning=$_.Exception.Message;if(Get-Command Write-AppLog -ErrorAction SilentlyContinue){Write-AppLog 'WARN' ('Complete source captured; shared cache update failed: '+$cacheWarning)}};if(!$e.observations.Count-and!$AllowEmpty){throw 'RSS has zero item records; bounded no-items capture retained; no retry or demand inference'};return [pscustomobject]@{export=$e;path=$capture;cache_hit=$false;network_requests=1;cache_warning=$cacheWarning}}finally{$response.Dispose()}}catch{$_.Exception.Data['source_network_requests']=1;throw}finally{$client.Dispose()}
}
