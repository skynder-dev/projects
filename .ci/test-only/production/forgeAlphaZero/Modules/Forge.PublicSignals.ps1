# Public attention proxies and explicit source-access boundaries. No creative authority.
function Assert-ForgeZazzleNetworkAllowed([string]$Url) {
 $u=[Uri]$Url
 if($u.Host-ceq'feed.zazzle.com'-and$u.PathAndQuery.Contains('st=')){
  $e=New-Object InvalidOperationException 'Source refused by captured robots policy: feed.zazzle.com Disallow /*st=* (checked 2026-10-15T20:06:54Z). Historical captures retained; no new request, parameter removal, retry or bypass.'
  $e.Data['source_status']='robots_disallowed';$e.Data['source_network_requests']=0;throw $e
 }
 throw 'Unreviewed Zazzle network path; no alternate query or endpoint allowed'
}
function Test-ForgeRobotsAllows([string]$Text,[string]$Url) {
 # Restricted ASCII endpoint policy evaluator: agent groups, wildcard rules, longest match and allow-on-tie.
 $groups=@();$agents=@();$rules=@();$hasRules=$false
 foreach($line in ($Text-split"`n")){
  $value=($line-split'#',2)[0].Trim();if(!$value){continue};if($value-notmatch'^([^:]+):(.*)$'){throw 'Malformed robots policy; no request allowed'};$name=$Matches[1].Trim().ToLowerInvariant();$arg=$Matches[2].Trim()
  if($name-ceq'user-agent'){if($hasRules){$groups+=,[pscustomobject]@{agents=$agents;rules=$rules};$agents=@();$rules=@();$hasRules=$false};$agents+=,$arg.ToLowerInvariant()}
  elseif($name-in@('allow','disallow')-and$agents.Count){$hasRules=$true;if($arg){$rules+=,[pscustomobject]@{allow=($name-ceq'allow');pattern=$arg}}}
 }
 if($agents.Count){$groups+=,[pscustomobject]@{agents=$agents;rules=$rules}}
 $specific=@($groups|Where-Object{$_.agents-contains'merchforge'})
 $chosen=if($specific.Count){$specific}else{@($groups|Where-Object{$_.agents-contains'*'})}
 $target=([Uri]$Url).PathAndQuery;$best=-1;$allowed=$true
 foreach($g in $chosen){foreach($r in $g.rules){$p=$r.pattern;$end=$p.EndsWith('$');if($end){$p=$p.Substring(0,$p.Length-1)};$regex='^'+[regex]::Escape($p).Replace('\*','.*');if($end){$regex+='$'}
  if($target-cmatch$regex){$length=$p.Replace('*','').Length;if($length-gt$best-or($length-eq$best-and$r.allow)){$best=$length;$allowed=$r.allow}}
 }}
 return $allowed
}
function Invoke-ForgePublicSignalHttp([string]$Url) {
 $u=[Uri]$Url
 if($u.Scheme-cne'https'-or$u.UserInfo-or$u.Port-ne443-or$u.Fragment){throw 'Invalid public signal URI'}
 $ok=($Url-in@('https://wikimedia.org/robots.txt','https://www.wikimedia.org/robots.txt','https://trends.google.com/robots.txt','https://trends.google.com/trending/rss?geo=US'))-or($u.Host-ceq'wikimedia.org'-and$u.PathAndQuery-cmatch'^/api/rest_v1/metrics/pageviews/per-article/en\.wikipedia\.org/all-access/user/(Cycling|Scrapbooking|Triathlon)/monthly/[0-9]{10}/[0-9]{10}$')
 if(!$ok){throw 'Unreviewed public signal endpoint; no alternate service or query allowed'}
 Add-Type -AssemblyName System.Net.Http
 $handler=New-Object Net.Http.HttpClientHandler;$handler.UseProxy=$false;$handler.AllowAutoRedirect=$false;$handler.UseCookies=$false
 $client=New-Object Net.Http.HttpClient($handler);$client.Timeout=[TimeSpan]::FromSeconds(25);$client.MaxResponseContentBufferSize=512KB
 $null=$client.DefaultRequestHeaders.TryAddWithoutValidation('User-Agent','MerchForge/2.24 (owner-authorized local research; no retries) .NET/4.8')
 try{$response=$client.GetAsync($Url).GetAwaiter().GetResult();try{$bytes=$response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult();$text=(New-Object Text.UTF8Encoding($false,$true)).GetString($bytes)
  return [pscustomobject]@{url=$Url;captured_at=[DateTime]::UtcNow.ToString('o');http_status=[int]$response.StatusCode;body_text=$text;body_sha256=(Get-ByteSha256Hex $bytes);location=[string]$response.Headers.Location}
 }finally{$response.Dispose()}}finally{$client.Dispose()}
}
function Get-ForgePublicSignalWindow([DateTime]$NowUtc=([DateTime]::UtcNow)) {
 $endMonth=(New-Object DateTime($NowUtc.Year,$NowUtc.Month,1,0,0,0,[DateTimeKind]::Utc)).AddMonths(-1)
 return [pscustomobject]@{first_month=$endMonth.AddMonths(-14).ToString('yyyyMM');last_month=$endMonth.ToString('yyyyMM');start=$endMonth.AddMonths(-14).ToString('yyyyMMdd')+'00';end=$endMonth.AddMonths(1).AddDays(-1).ToString('yyyyMMdd')+'00';month_count=15}
}
function ConvertFrom-ForgeWikiViews($Capture,[string]$Article,$Window) {
 if($Capture.http_status-ne200){throw 'Pageviews unavailable; not zero'}
 if((ConvertFrom-ResearchUtc $Capture.captured_at)-gt[DateTime]::UtcNow.AddMinutes(5)){throw 'Pageviews capture dated in future'}
 if((Get-StringSha256Hex $Capture.body_text)-cne$Capture.body_sha256){throw 'Pageviews captured bytes changed'}
 $data=ConvertFrom-ForgeJsonObjectStrict $Capture.body_text
 if($data.items-isnot[Array]-or$data.items.Count-ne15){throw 'Pageviews series is incomplete; no comparison'}
 $series=@();$first=[DateTime]::ParseExact($Window.first_month,'yyyyMM',[Globalization.CultureInfo]::InvariantCulture)
 for($i=0;$i-lt15;$i++){$x=$data.items[$i];$expected=$first.AddMonths($i).ToString('yyyyMM')+'0100'
  if($x.project-cne'en.wikipedia'-or$x.article-cne$Article-or$x.agent-cne'user'-or$x.access-cne'all-access'-or$x.granularity-cne'monthly'-or$x.timestamp-cne$expected-or($x.views-isnot[int]-and$x.views-isnot[long])-or$x.views-lt0){throw 'Pageviews article, scope, month sequence or count invalid'}
  $series+=,[pscustomobject]@{month=$expected.Substring(0,6);views=[long]$x.views}
 }
 $current=[long]0;$previous=[long]0;$increased=0;$decreased=0;$perMonth=@()
 for($i=0;$i-lt3;$i++){$a=$series[$i];$b=$series[$i+12];$previous+=$a.views;$current+=$b.views;if($b.views-gt$a.views){$increased++};if($b.views-lt$a.views){$decreased++};$perMonth+=,[pscustomobject]@{current_month=$b.month;views=$b.views;previous_year_month=$a.month;previous_views=$a.views}}
 $pct=if($previous-gt0){[math]::Round(100.0*($current-$previous)/$previous,1)}else{$null}
 $largest=($series[12..14].views|Measure-Object -Maximum).Maximum;$share=if($current-gt0){[math]::Round(100.0*$largest/$current,1)}else{$null}
 return [pscustomobject]@{series=$series;same_season_months=$perMonth;current_quarter_views=$current;previous_year_same_quarter_views=$previous;change_pct=$pct;months_increased=$increased;months_decreased=$decreased;largest_month_share_pct=$share;more_than_half_views_in_one_month=($current-gt0-and$largest*2-gt$current);attention_pattern=if($previous-eq0){'baseline_zero_no_growth_percentage'}elseif($increased-eq3){'all_three_months_article_attention_increased'}elseif($decreased-eq3){'all_three_months_article_attention_decreased'}else{'mixed_months_do_not_treat_total_change_as_persistent_growth'};scope='English Wikipedia article views classified user/all-access, worldwide language audience; not unique people, US buyers, apparel searches, purchases, sales or marketplace competition. Article scope and news/events can change reading attention.';demand_verified=$false;market_rank=$null}
}
function ConvertFrom-ForgeTrendsRss($Capture) {
 if($Capture.http_status-ne200){throw 'Trending RSS unavailable; not zero interest'}
 $captured=ConvertFrom-ResearchUtc $Capture.captured_at;if($captured-gt[DateTime]::UtcNow.AddMinutes(5)){throw 'Trending capture dated in future'}
 if((Get-StringSha256Hex $Capture.body_text)-cne$Capture.body_sha256){throw 'Trending RSS captured bytes changed'}
 $settings=New-Object Xml.XmlReaderSettings;$settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit;$settings.XmlResolver=$null;$settings.MaxCharactersInDocument=512KB
 $sr=New-Object IO.StringReader $Capture.body_text;$reader=[Xml.XmlReader]::Create($sr,$settings);$doc=New-Object Xml.XmlDocument;$doc.XmlResolver=$null
 try{$doc.Load($reader)}finally{$reader.Dispose();$sr.Dispose()}
 $nodes=@($doc.SelectNodes('/rss/channel/item'));if($nodes.Count-gt100){throw 'Trending RSS exceeds bounded sample'}
 $ns=New-Object Xml.XmlNamespaceManager $doc.NameTable;$ns.AddNamespace('ht','https://trends.google.com/trending/rss');$rows=@()
 foreach($node in $nodes){$t=$node.SelectSingleNode('title');$d=$node.SelectSingleNode('pubDate');if($null-eq$t-or$null-eq$d-or$t.InnerText.Length-gt500){throw 'Incomplete trending item'};$published=[DateTimeOffset]::Parse($d.InnerText,[Globalization.CultureInfo]::InvariantCulture);$traffic=$node.SelectSingleNode('ht:approx_traffic',$ns)
  if($published.UtcDateTime-gt$captured.AddMinutes(5)-or($traffic-and$traffic.InnerText.Length-gt80)){throw 'Trending item time or traffic display invalid'}
  $rows+=,[pscustomobject]@{title=$t.InnerText;published_at=$published.UtcDateTime.ToString('o');approx_traffic_display=if($traffic){$traffic.InnerText}else{''}}
 }
 return [pscustomobject]@{region='US';rows=$rows;scope='Current bounded US trending-search topics; approximate traffic is a display field, not exact niche search volume, purchases or sales. A niche absent from the feed has unobserved coverage, not zero interest.'}
}
function Get-ForgeSampleCompetitionProxy($Followup) {
 Assert-ForgeDiscoveryCapture $Followup.capture $Followup.query 10
 $a=Get-ForgeDiscoveryAssessment $Followup.capture.observations (@(Get-ForgeDiscoveryVocabulary|Where-Object{$_.key-ceq$Followup.key})[0]) -AssessmentAt (ConvertFrom-ResearchUtc $Followup.capture.captured_at)
 $indices=@($a.row_reviews|Where-Object{$_.status-ceq'eligible_title_sample'}|ForEach-Object{$_.index});$rows=@();$i=0;foreach($row in $Followup.capture.observations){$i++;if($indices-contains$i){$rows+=,$row}}
 $groups=@($rows|Group-Object {([string]$_.creator).Trim().ToLowerInvariant()}|Sort-Object Count -Descending);$share=if($rows.Count){[math]::Round(100.0*$groups[0].Count/$rows.Count,1)}else{$null}
 return [pscustomobject]@{captured_at=$Followup.capture.captured_at;source_url=$Followup.capture.source_url;eligible_products=$a.eligible_unique_products;creator_labels=$a.distinct_eligible_creators;largest_creator_label_share_pct=$share;duplicate_title_records=$a.duplicate_title_records;price_display_examples=@($rows|Select-Object -First 2 -ExpandProperty price_display);numeric_price_comparison='not_comparable_without_explicit_currency_codes';scope='Distribution of creator labels and repeated title strings inside the bounded historical Zazzle sample only. Labels are not verified independent sellers; this is not market share, low competition, design uniqueness or market size.';market_competition_verified=$false}
}
function Get-ForgePublicSignalsComparison($Report) {
 if($Report.schema-cne'forge.public_signals.v1'-or$Report.topics-isnot[Array]-or$Report.topics.Count-gt3){throw 'Invalid public signals envelope'}
 foreach($n in @('model_requests','gpu_requests','drafts_created','approvals_created')){$v=Get-PropertyValue $Report $n;if(($v-isnot[int]-and$v-isnot[long])-or$v-ne0){throw 'Public proxies cannot grant creative authority'}}
 if($Report.market_rank_available-isnot[bool]-or$Report.market_rank_available){throw 'Unsupported proxy market authority'}
 if((ConvertFrom-ResearchUtc $Report.completed_at)-gt[DateTime]::UtcNow.AddMinutes(5)){throw 'Public signals dated in future'}
 if(($Report.source_requests-isnot[int]-and$Report.source_requests-isnot[long])-or$Report.source_requests-lt0-or$Report.source_requests-gt7){throw 'Invalid public signal request counter'}
 $mapped=@{cycling='Cycling';scrapbooking='Scrapbooking';triathlon='Triathlon'};$seen=@{};$result=@();$window=$Report.window
 if($window.first_month-cnotmatch'^[0-9]{6}$'-or$window.last_month-cnotmatch'^[0-9]{6}$'-or([DateTime]::ParseExact($window.first_month,'yyyyMM',[Globalization.CultureInfo]::InvariantCulture)).AddMonths(14).ToString('yyyyMM')-cne$window.last_month){throw 'Invalid proxy month window'}
 $firstMonth=[DateTime]::ParseExact($window.first_month,'yyyyMM',[Globalization.CultureInfo]::InvariantCulture);$lastMonth=$firstMonth.AddMonths(14)
 if($window.start-cne($firstMonth.ToString('yyyyMMdd')+'00')-or$window.end-cne($lastMonth.AddMonths(1).AddDays(-1).ToString('yyyyMMdd')+'00')-or$lastMonth-ge(New-Object DateTime([DateTime]::UtcNow.Year,[DateTime]::UtcNow.Month,1))){throw 'Proxy window must contain completed matching calendar months'}
 $trends=$null;try{if($Report.trends_capture.url-cne'https://trends.google.com/trending/rss?geo=US'){throw 'Trends region endpoint changed'};$trends=ConvertFrom-ForgeTrendsRss $Report.trends_capture}catch{}
 foreach($topic in $Report.topics){
  if($seen.ContainsKey($topic.key)-or!$mapped.ContainsKey($topic.key)-or$topic.article-cne$mapped[$topic.key]-or$topic.product_sample.key-cne$topic.key){throw 'Topic/source mapping invalid'};$seen[$topic.key]=$true
  $url='https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/user/'+$topic.article+'/monthly/'+$window.start+'/'+$window.end
  $attention=$null;$errorText='';try{if($topic.wiki_capture.url-cne$url){throw 'Article endpoint binding changed'};$attention=ConvertFrom-ForgeWikiViews $topic.wiki_capture $topic.article $window}catch{$errorText=$_.Exception.Message}
  $vocab=@(Get-ForgeDiscoveryVocabulary|Where-Object{$_.key-ceq$topic.key})[0];$matchesInFeed=@(if($null-ne$trends){$trends.rows|Where-Object{Get-ForgeDiscoveryAlias $_.title $vocab}})
  $result+=,[pscustomobject]@{key=$topic.key;article=$topic.article;attention_status=if($null-ne$attention){'observed_article_attention_proxy'}else{'unavailable_no_zero_inference'};attention=$attention;error=$errorText;wiki_source_url=$url;wiki_captured_at=$topic.wiki_capture.captured_at;sample_competition=(Get-ForgeSampleCompetitionProxy $topic.product_sample);trends_coverage=if($null-eq$trends){'source_unavailable_not_zero'}elseif(!$matchesInFeed.Count){'not_observed_in_current_trending_feed_not_zero_interest'}else{'matching_current_trending_title_requires_context'};trends_matches=$matchesInFeed;market_rank=$null;profit_score=$null;research_disposition='Compare attention trajectory, inspect events and seek apparel-specific corroboration before investing in a design; no commercial winner is established.'}
 }
 $latest=Get-ForgePublicSignalWindow;$latestMonth=[DateTime]::ParseExact($latest.last_month,'yyyyMM',[Globalization.CultureInfo]::InvariantCulture);$lag=($latestMonth.Year-$lastMonth.Year)*12+$latestMonth.Month-$lastMonth.Month
 return [pscustomobject]@{topics=$result;trends=$trends;window_lag_months=$lag;market_rank_available=$false;refusal='No apparel-specific purchase/search history, comparable marketplace coverage, verified seller independence or sales data. Article attention and sampled listing composition cannot establish a promising commercial niche.'}
}
function Invoke-ForgePublicSignalsRefresh([string]$RunPath='',$RunState=$null) {
 $discovery=Read-ForgeLatestNicheDiscovery;if($null-eq$discovery){throw 'No saved topic discovery to compare; no source query or model was launched'}
 $mapped=@{cycling='Cycling';scrapbooking='Scrapbooking';triathlon='Triathlon'};$targets=@($discovery.followups|Where-Object{$mapped.ContainsKey($_.key)}|Select-Object -First 3)
 if(!$targets.Count){throw 'No verified article mapping for current saved topics; no arbitrary article search, fallback or ranking'}
 $ctx=[pscustomobject]@{requests=0;trace=@();urls=@{}};$window=Get-ForgePublicSignalWindow
 function Read-Signal([string]$Url){
  if($RunPath){Assert-AutoResearchNotCancelled $RunPath};if($ctx.requests-ge7-or$ctx.urls.ContainsKey($Url)){throw 'Public signal request budget or no-retry boundary exceeded'}
  $ctx.urls[$Url]=$true;$ctx.requests++
  try{$cap=Invoke-ForgePublicSignalHttp $Url}catch{$cap=[pscustomobject]@{url=$Url;captured_at=[DateTime]::UtcNow.ToString('o');http_status=0;body_text='';body_sha256=(Get-StringSha256Hex '');location='';error=$_.Exception.Message}}
  $ctx.trace+=,$cap
  if($null-ne$RunState){$RunState.source_requests=$ctx.requests;$RunState.phase='public signal: '+([Uri]$Url).Host;if($RunPath){Write-AutoResearchRun $RunPath $RunState}}
  if($RunPath){Assert-AutoResearchNotCancelled $RunPath};return $cap
 }
 $wikiPolicy=Read-Signal 'https://wikimedia.org/robots.txt'
 if($wikiPolicy.http_status-in@(301,302,307,308)-and$wikiPolicy.location-ceq'https://www.wikimedia.org/robots.txt'){$wikiPolicy=Read-Signal $wikiPolicy.location}
 $wikiAllowed=$wikiPolicy.http_status-eq404-or($wikiPolicy.http_status-eq200-and(Test-ForgeRobotsAllows $wikiPolicy.body_text ('https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/user/Cycling/monthly/'+$window.start+'/'+$window.end)))
 $topics=@();$wikiRefused=$false
 foreach($target in $targets){
  if($RunPath){Assert-AutoResearchNotCancelled $RunPath};$article=$mapped[$target.key];$url='https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/user/'+$article+'/monthly/'+$window.start+'/'+$window.end
  if(!$wikiAllowed-or$wikiRefused){$cap=[pscustomobject]@{url=$url;captured_at=[DateTime]::UtcNow.ToString('o');http_status=-1;body_text='';body_sha256=(Get-StringSha256Hex '');error='Not requested after unavailable/disallowed policy or source refusal'}}else{$cap=Read-Signal $url;if($cap.http_status-in@(403,429)){$wikiRefused=$true}}
  $topics+=,[pscustomobject]@{key=$target.key;article=$article;wiki_capture=$cap;product_sample=$target}
 }
 $trendsPolicy=Read-Signal 'https://trends.google.com/robots.txt';$trendsUrl='https://trends.google.com/trending/rss?geo=US'
 $trendsAllowed=$trendsPolicy.http_status-eq404-or($trendsPolicy.http_status-eq200-and(Test-ForgeRobotsAllows $trendsPolicy.body_text $trendsUrl))
 $trends=if($trendsAllowed){Read-Signal $trendsUrl}else{[pscustomobject]@{url=$trendsUrl;captured_at=[DateTime]::UtcNow.ToString('o');http_status=-1;body_text='';body_sha256=(Get-StringSha256Hex '');error='Trending RSS not requested after policy unavailable/disallowed/refused'}}
 if($RunPath){Assert-AutoResearchNotCancelled $RunPath}
 $report=[pscustomobject]@{schema='forge.public_signals.v1';completed_at=[DateTime]::UtcNow.ToString('o');window=$window;topics=$topics;trends_capture=$trends;request_trace=$ctx.trace;source_requests=$ctx.requests;max_source_requests=7;model_requests=0;gpu_requests=0;drafts_created=0;approvals_created=0;market_rank_available=$false;zazzle_network_status='robots_disallowed_new_requests';selection_basis='Saved source-discovered topics with explicitly verified article mapping; product samples are historical and unchanged. No biography, generated card counts or popularity-to-sales inference.'}
 $null=Get-ForgePublicSignalsComparison $report;$null=Save-ForgeNicheEvidenceRun $report -Storage 'public-signals-v1';return $report
}
function Read-ForgeLatestPublicSignals {
 $root=Join-Path $script:StateRoot 'public-signals-v1';$ptr=Join-Path $root 'latest.sha256';$origin='bundled_public_capture'
 if(Test-Path -LiteralPath $root){$item=Get-Item -LiteralPath $root -Force;if($item-isnot[IO.DirectoryInfo]-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Public signal storage is redirected or invalid'};if(!(Test-Path -LiteralPath $ptr)-and@(Get-ChildItem -LiteralPath $root -Force).Count){throw 'Public signal pointer missing; reports retained without older substitution'}}
 if(Test-Path -LiteralPath $ptr){$item=Get-Item -LiteralPath $ptr -Force;if($item-isnot[IO.FileInfo]-or$item.Length-gt128-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Invalid public signal pointer'};$sha=[IO.File]::ReadAllText($ptr).Trim();if($sha-cnotmatch'^[0-9a-f]{64}$'){throw 'Invalid signal SHA'};$payload=Read-LocalCheckEvidencePayload (Join-Path $root ($sha+'.json'));if($payload.sha256-cne$sha){throw 'Public signal snapshot changed'};$report=$payload.data;$origin='saved_local_capture'}
 else{$file=Join-Path (Split-Path $script:ModuleRoot -Parent) 'Data\Forge.PublicSignalsSnapshot.json';if(!(Test-Path -LiteralPath $file)){return $null};$report=(Read-LocalCheckEvidencePayload $file).data}
 $comparison=Get-ForgePublicSignalsComparison $report
 Add-OrSetProperty $report 'comparison' $comparison;Add-OrSetProperty $report 'display_origin' $origin;return $report
}
function Refresh-ForgePublicSignalsSummary {
 if($null-eq$AutoResearchPublicSignalsSummary){return};$ru=$script:Locale-ceq'ru';$es=$script:Locale-ceq'es'
 try{$r=Read-ForgeLatestPublicSignals;if($null-eq$r){$AutoResearchPublicSignalsSummary.Text=if($ru){'Сигналы внимания ещё не сохранены. Zazzle: новые RSS-запросы запрещены robots /*st=*; прежние наблюдения сохранены.'}elseif($es){'Sin señales guardadas. Nuevas consultas RSS Zazzle bloqueadas por robots /*st=*; capturas históricas conservadas.'}else{'No attention signals saved. New Zazzle RSS reads blocked by robots /*st=*; historical captures retained.'};return}
  $lines=New-Object Collections.Generic.List[string]
  $lines.Add($(if($ru){'СРАВНЕНИЕ ПРОКСИ — внимание к теме отдельно от спроса на футболки и конкуренции рынка.'}elseif($es){'COMPARACIÓN DE PROXIES — atención al tema separada de demanda de camisetas y competencia.'}else{'PROXY COMPARISON — topic attention is separate from T-shirt demand and marketplace competition.'}))
  $lines.Add(('Capture: '+$r.completed_at+' | '+$r.display_origin+' | months '+$r.window.first_month+'..'+$r.window.last_month))
  $lines.Add(('Window lag: '+$r.comparison.window_lag_months+' completed months; refresh before relying on an older window. Trends source: '+$r.trends_capture.url+' | '+$r.trends_capture.captured_at))
  $lines.Add($(if($ru){'Zazzle: новые запросы заблокированы правилом robots /*st=* от 15.10.2026; ниже только прежняя выборка. Wikimedia: English Wikipedia, user/all-access, весь мир; это просмотры статей, не люди или покупки. Сравниваются одинаковые три месяца год к году, не объёмы разных статей как размер рынка.'}elseif($es){'Zazzle: nuevas solicitudes bloqueadas por robots /*st=*; muestra histórica. Wikimedia: English Wikipedia, user/all-access, global; vistas de artículos, no personas ni compras. Mismos tres meses interanuales, no tamaño de mercado entre artículos.'}else{'Zazzle new reads blocked by robots /*st=*; product observations below are historical. Wikimedia: English Wikipedia user/all-access worldwide article views, not people or purchases. Same three months year-on-year, not cross-article market size.'}))
  foreach($t in $r.comparison.topics){$lines.Add('');$lines.Add($t.article+' | '+$t.attention_status)
   if($null-ne$t.attention){$a=$t.attention;$lines.Add(('Article views: '+$a.current_quarter_views+' vs '+$a.previous_year_same_quarter_views+'; change '+$(if($null-eq$a.change_pct){'undefined (zero baseline)'}else{[string]$a.change_pct+'%'})+'; months up/down '+$a.months_increased+'/'+$a.months_decreased+'; largest month '+$a.largest_month_share_pct+'%'))
    $lines.Add(('Pattern: '+$a.attention_pattern));if($a.more_than_half_views_in_one_month){$lines.Add($(if($ru){'Больше половины просмотров квартала приходится на один месяц; проверьте события. Рост суммы не доказывает устойчивый интерес или спрос.'}elseif($es){'Más de la mitad de vistas en un mes: revisar eventos; el total no demuestra interés sostenido ni demanda.'}else{'More than half of quarter views fall in one month: check events. A larger total does not establish persistent interest or demand.'}))}
    foreach($m in $a.same_season_months){$lines.Add(($m.current_month+': '+$m.views+' | '+$m.previous_year_month+': '+$m.previous_views))}
   }else{$lines.Add($t.error+'; unavailable is not zero interest.')}
   $lines.Add(('Source: '+$t.wiki_source_url+' | '+$t.wiki_captured_at))
   $s=$t.sample_competition;$lines.Add(('Historical listing sample '+$s.captured_at+': '+$s.eligible_products+' product IDs; '+$s.creator_labels+' creator labels; largest label share '+$s.largest_creator_label_share_pct+'%; repeated titles '+$s.duplicate_title_records+'. Not marketplace competition or independent sellers.'))
   $lines.Add(('Listing source: '+$s.source_url));$lines.Add(('US trending-feed coverage: '+$t.trends_coverage))
  }
  $lines.Add('');$lines.Add($(if($ru){'Коммерческий рейтинг отклонён: нет проверяемой связи этих прокси с покупателями футболок, продажами и охватом конкурентов. Изменение внимания помогает выбрать, что перепроверить; не даёт победителя ниши, прогноза продаж или approval. Цена без ISO-кода валюты не сравнивается численно.'}elseif($es){'Sin clasificación comercial: no hay vínculo verificado con compradores de camisetas, ventas o cobertura de competidores. Los proxies guían qué comprobar; no dan ganador, ventas ni aprobación. Precio sin código ISO no se compara.'}else{'Commercial ranking refused: no validated link to apparel buyers, sales or competitor coverage. Proxies guide further checks, not a winning niche, sales forecast or approval. Prices without ISO currency codes are not numerically compared.'}))
  $AutoResearchPublicSignalsSummary.Text=$lines-join[Environment]::NewLine
 }catch{$AutoResearchPublicSignalsSummary.Text='Public signal snapshot unavailable; files retained, no older substitution or ranking: '+$_.Exception.Message}
}
