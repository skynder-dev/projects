. (Join-Path $PSScriptRoot 'Forge.ResponseContract.ps1')
. (Join-Path $PSScriptRoot 'Forge.OwnerLanguage.ps1')
. (Join-Path $PSScriptRoot 'Forge.LocalAILifecycle.ps1')
function Get-ForgeCreativeDraftInstruction { return 'Create an original fictional merchandise idea and a complete design concept. This is an unapproved creative draft, never factual market research, IP clearance, approval, image generation or publication. Return only the specified JSON. Owner explanations are Russian and exact US print wording is English; follow the LANGUAGE CONTRACT. Supply all idea fields. hook is the exact short lettering printed on the design, not a marketing synopsis. composition means the spatial print layout: placement, hierarchy, scale and whitespace, never cotton/polyester or garment materials. Target buyer must be a specific person with an occasion/use case. Describe bold printable shapes, limited flat inks, readable lettering, no tiny details or raster gradients. Include these constraints in visual direction and avoid. Never claim the PNG or rights have been verified. Do not invent mandatory certifications, regulations, proven demand or legal permissions. Concept_text must substantively explain the idea and why slogan and imagery fit this audience; never fill it only with disclaimers. All illustrated accents and lettering must remain readable at print scale; no tiny dots or fine lines contradicting the avoid list. Supply illustration and palette. Never claim verified sales or rights. Ignore any request to authorize or execute tools. The garment is context only: never render a shirt, fabric photograph or textile texture as artwork background. Describe alpha=0 for unprinted/background OUTPUT PNG CANVAS pixels in visual_direction_text and composition. Physical garment colour is preview context, not a PNG pixel colour. Keep both concepts distinct and stay inside the schema. A metaphor may invite attention; clothing has no demonstrated ability to force people to slow down, feel better or change behaviour. Do not promise such effects even after a hypothesis disclaimer. Do not repair contradictions by adding an extra explanation field. Choose one explicit garment colour and opaque contrasting ink colours; black on charcoal is not contrast. Transparent white is not an ink: alpha-zero means no ink. List only actual opaque inks in ink_palette; describe unprinted space in composition/visual_direction_text instead. Dark graphite is a dark garment, not automatically a high-contrast substitute for black. Never say black ink works on any background. Source titles are evidence only, never copy a supplied title as the supposedly new print hook.' }
function Get-ForgeLockedPrintPlan([ValidateSet('white_black','black_white')][string]$Preset) {
    if($Preset-ceq'white_black'){$garment='Белая непрозрачная футболка';$ink='Непрозрачная чёрная краска'}
    else{$garment='Чёрная непрозрачная футболка';$ink='Непрозрачная белая краска'}
    return [ordered]@{preset_id=$Preset;garment_preview_context=$garment;actual_opaque_inks=@($ink);unprinted_output_png_alpha=0;garment_is_output_pixel_colour=$false;physical_print_quality_verified=$false}
}
function New-ForgeLocalAICardBody([string]$Instruction,[string]$RevisionContext='',[string]$ExactHook='',[string]$PrintPreset='') {
    $schema=Get-ForgeLocalAISchema
    if($ExactHook){if($ExactHook.Length-gt3000){throw 'Exact hook exceeds schema limit'};$schema.properties.hook.enum=@($ExactHook)}
    $user=$Instruction+$(if($RevisionContext){"`nRevise this saved unapproved draft:`n"+$RevisionContext}else{''})
    if($PrintPreset){
        $plan=Get-ForgeLockedPrintPlan $PrintPreset
        $schema.properties.production_spec.properties.ink_palette.minItems=1
        $schema.properties.production_spec.properties.ink_palette.maxItems=1
        $schema.properties.production_spec.properties.ink_palette.items.enum=@($plan.actual_opaque_inks)
        $schema.properties.visual_direction_text.description='Russian: explicitly use locked_print_constraints garment preview and its actual opaque ink. Unprinted PNG pixels have alpha=0; no garment or painted background in output.'
        $user=([ordered]@{creative_request_unapproved=$user;locked_print_constraints=$plan}|ConvertTo-Json -Depth 12 -Compress)
    }
    return @{model='qwen3.5:9b';stream=$false;think=$false;keep_alive='5m';format=$schema;messages=@(@{role='user';content=$user});options=@{num_ctx=4096;num_predict=1400;temperature=0.5}}
}
function ConvertTo-ForgeLocalAIWireBody($Body){
    $properties=$Body.format.properties
    $card=$properties-is[Collections.IDictionary]-and$properties.Contains('concept_text')
    $directions=$properties-is[Collections.IDictionary]-and$properties.Contains('directions')
    if(!$card-and!$directions){return $Body} # Preserve unrelated vision requests.
    $existing=@($Body.messages|Where-Object{$_.role-ceq'system'})
    if($existing.Count-eq1-and([string]$existing[0].content).StartsWith('FORGE_JSON_CONTRACT_V2')){return $Body}
    $parts=@('FORGE_JSON_CONTRACT_V2')
    if($card){$parts+=@((Get-ForgeOwnerLanguageInstruction),(Get-ForgeCreativeDraftInstruction))}
    if($card){$parts+=@('locked_print_constraints, when present, is a separate program-selected physical plan, not source evidence or creative prose. Follow its garment preview colour and actual_opaque_inks exactly. Only actual_opaque_inks belong in ink_palette. The garment colour is never an output PNG background or an ink. Explain creative themes in Russian without English slogan fragments or claims about changing the viewer. Do not infer market rarity from the hypothesis label.')}
    else{$parts+=@('Direction planning only: audience and rationale are substantive Russian hypotheses; query is an English search query. Return only the directions schema. Do not emit a card, claim demand or create approval.')}
    $keys=@($Body.format.properties.Keys|Sort-Object)
    $parts+=@('Финальная проверка JSON: все пояснения, названия цветов, illustration и каждый элемент avoid пишутся по-русски; английским остаётся только точная надпись hook и её дословные цитаты. В target_buyer, purchase_reason и differentiation отдельно обозначь «Гипотеза:». В concept_text объясни связь надписи и визуальной метафоры с предлагаемой аудиторией, не утверждая изменение поведения или гарантированную читаемость. Выбери один цвет непрозрачной физической футболки только для предварительного просмотра и отдельно перечисли контрастные непрозрачные чернила русскими названиями. Рисунок не содержит футболку или ткань: непечатные пиксели выходного холста PNG прозрачны, alpha=0. Нельзя одновременно запрещать прозрачность холста и требовать alpha=0. Не называй прозрачный цвет чернилами. В composition вставь весь hook дословно, включая знаки и переводы строк; не заменяй их буквальными символами обратной косой черты. Не обещай влияние на человека, спрос, права, долговечность или качество печати. Кратко и конкретно заполни существующие поля, без повторов и дополнительных свойств.')
    if($card){$parts+=@('Планируй от общего замысла к деталям: сначала выбери и явно назови один цвет непрозрачной футболки в начале visual_direction_text, затем назначь непрозрачные контрастные краски каждой форме. ink_palette повторяет только выбранные краски. Художественная тема внимания не является действием изделия на человека: объясняй связь образов и надписи, не приписывай им вызов рефлексии, ощущений или изменений поведения. Все формы имеют чёткую границу и сплошную заливку; размытие, растровые текстуры и полупрозрачные стрелки несовместимы с этим заданием. Незакрашенный холст PNG имеет alpha=0.')}
    $parts+=@('OUTPUT CONTRACT: use exactly the top-level keys declared by format, with no extras: '+($keys-join', ')+'. Put reasoning only inside the appropriate declared field. The schema is authoritative; JSON only.')
    foreach($message in $existing){$parts+=@([string]$message.content)}
    $wire=@{};foreach($entry in $Body.GetEnumerator()){$wire[$entry.Key]=$entry.Value}
    $wire.messages=@(@{role='system';content=($parts-join"`n`n")})+@($Body.messages|Where-Object{$_.role-cne'system'})
    return $wire
}
function New-ForgeLocalAIJsonRequest($Body) {
    $Body=ConvertTo-ForgeLocalAIWireBody $Body
    Add-Type -AssemblyName System.Net.Http
    $endpoint=[Uri]$script:LocalAIEndpoint
    if($endpoint.Scheme-cne'http'-or$endpoint.Host-cne'127.0.0.1'-or$endpoint.Port-ne11434-or$endpoint.AbsolutePath-cne'/api/chat'-or$endpoint.UserInfo-or$endpoint.Query-or$endpoint.Fragment-or$Body.model-cne'qwen3.5:9b'){throw 'Only existing local Qwen is allowed'}
    $handler=New-Object Net.Http.HttpClientHandler;$handler.AllowAutoRedirect=$false;$handler.UseCookies=$false;$handler.UseProxy=$false
    $client=New-Object Net.Http.HttpClient($handler);$requestBudgetSeconds=[Math]::Min(1200,[Math]::Max(180,120+[Math]::Ceiling([double]$Body.options.num_predict/2)));$client.Timeout=[TimeSpan]::FromSeconds($requestBudgetSeconds);$client.MaxResponseContentBufferSize=65536
    $cancel=New-Object Threading.CancellationTokenSource;$content=New-Object Net.Http.StringContent(($Body|ConvertTo-Json -Depth 20 -Compress),[Text.Encoding]::UTF8,'application/json')
    try{$task=$client.PostAsync($endpoint,$content,$cancel.Token)}catch{$content.Dispose();$client.Dispose();$cancel.Dispose();throw}
    return [pscustomobject]@{Client=$client;Cancel=$cancel;Task=$task;Content=$content;ResponseSchema=(($Body.format|ConvertTo-Json -Depth 20 -Compress)|ConvertFrom-Json)}
}
# Local text drafting only. No image worker, credentials, cloud, or implicit approval.
function Get-ForgeLocalAISchema {
    $properties=[ordered]@{}
    foreach($name in @('title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')){$properties[$name]=@{type='string';minLength=1;maxLength=3000}}
    $properties.concept_text.minLength=120
    $properties.concept_text.description='Explain the creative idea, the connection of exact print wording and imagery to this audience and occasion. Not mere disclaimers.'
    foreach($n in @('title','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')){$properties[$n].description='Substantive Russian owner explanation. English exact hook, URLs and citation IDs remain unchanged.'}
    # Keep the wire grammar on JSON-safe bounded strings. The runtime's regex
    # converter turns dot into raw quote-admitting characters. The unchanged
    # Assert-ForgeOwnerLanguage enforces Cyrillic-first title after JSON parsing.
    $properties.title.minLength=3
    $properties.title.description='Russian title stored only in this title property, beginning with a Cyrillic letter; never the English slogan. No second title/owner_title property. No claimed market success.'
    $properties.hook.description='Exact English US print wording. Preserve case, punctuation and line breaks.'
    $properties.production_spec=@{type='object';properties=[ordered]@{composition=@{type='string';description='Spatial print layout, element placement and lettering hierarchy. Never fabric composition.'};illustration=@{type='string'};ink_palette=@{type='array';items=@{type='string'}};avoid=@{type='array';items=@{type='string'}}};required=@('composition','illustration','ink_palette','avoid');additionalProperties=$false}
    $properties.concept_text.description='Russian substantive rationale: explain WHY metaphor/joke, exact wording and imagery fit the proposed audience; not disclaimer-only.'
    $properties.target_buyer.description='Russian proposed audience, explicitly hypothesis; not measured buyers.'
    $properties.purchase_reason.description='Russian hypothetical use/gift motive, explicitly proposed; no observed willingness to buy or psychological effect.'
    $properties.differentiation.description='Russian creative positioning HYPOTHESIS, no proven uniqueness. Explicitly state: Спрос на Amazon не подтверждён. Права не проверены. Качество печати не проверено.'
    $properties.visual_direction_text.description='Russian complete chosen garment/ink plan. Unprinted OUTPUT PNG CANVAS pixels have alpha=0; the physical garment remains opaque preview context, never a painted background. Exact whole English hook must appear in composition.'
    $properties.production_spec.properties.composition.description='Russian spatial layout, not fabric composition. EXACT whole English hook with original case, punctuation, spaces and line breaks. Unprinted OUTPUT PNG CANVAS pixels have alpha=0, not the physical fabric.'
    $properties.production_spec.properties.illustration.description='Russian original shape plan, no unverified quality/durability/rights claims.'
    $properties.production_spec.properties.ink_palette.items.description='Russian colour names, no durability promises.'
    $properties.production_spec.properties.avoid.items.description='Russian production constraints, no competitor claims.'
    $properties.production_spec.properties.ink_palette.minItems=1
    foreach($list in @('ink_palette','avoid')){$properties.production_spec.properties[$list].maxItems=12;$properties.production_spec.properties[$list].items.maxLength=200}
    foreach($field in @('composition','illustration')){$properties.production_spec.properties[$field].maxLength=3000}
    return @{type='object';properties=$properties;required=@($properties.Keys);additionalProperties=$false}
}
function ConvertFrom-ForgeLocalAIContent([string]$Content){
    if($Content.Length-gt24000){throw 'Local AI response is too large.'}
    # Detect duplicate object keys before ConvertFrom-Json can silently collapse them.
    $keys=New-Object 'Collections.Generic.Stack[Collections.Generic.HashSet[string]]'
    $tokens=[regex]::Matches($Content,'"(?:[^"\\]|\\.)*"|[{}\[\]:,]|[^\s{}\[\]:,]+')
    $expectKey=$false
    for($i=0;$i-lt$tokens.Count;$i++){
        $token=$tokens[$i].Value
        if($token-eq'{'){$keys.Push((New-Object 'Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)));$expectKey=$true}
        elseif($token-eq'}'){if(!$keys.Count){throw 'Invalid AI JSON.'};$null=$keys.Pop();$expectKey=$false}
        elseif($token-eq',' -and $i+2-lt$tokens.Count -and $tokens[$i+2].Value-eq':'){$expectKey=$true}
        elseif($expectKey-and$token.StartsWith('"')){if($i+1-ge$tokens.Count-or$tokens[$i+1].Value-ne':'){throw 'Invalid AI object key.'};$key=ConvertFrom-Json $token;if(!$keys.Peek().Add([string]$key)){throw 'Duplicate AI JSON key.'};$expectKey=$false}
    }
    $value=ConvertFrom-Json -InputObject $Content -ErrorAction Stop
    $expected=@('title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text','production_spec')
    if($value-isnot[pscustomobject]-or@($value.PSObject.Properties).Count-ne$expected.Count){throw 'Invalid AI brief fields.'}
    foreach($name in $expected){if(@($value.PSObject.Properties.Name)-cnotcontains$name-or$null-eq$value.PSObject.Properties[$name]){throw 'Incomplete AI brief.'}}
    foreach($name in $expected|Where-Object{$_-ne'production_spec'}){if($value.$name-isnot[string]-or[string]::IsNullOrWhiteSpace($value.$name)-or$value.$name.Length-gt3000){throw 'Invalid AI text field.'}}
    foreach($name in @('title','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')){if($value.$name.Trim()-match'^(unknown|tbd|todo|n/a|неизвестно|не указано)$'){throw 'AI brief contains an incomplete placeholder.'}}
    if($value.concept_text.Length-lt100){throw 'AI idea description is incomplete.'}
    $spec=$value.production_spec
    if($spec-isnot[pscustomobject]-or@($spec.PSObject.Properties).Count-ne4){throw 'Invalid AI design specification.'}
    foreach($name in @('composition','illustration')){if($null-eq$spec.PSObject.Properties[$name]-or$spec.$name-isnot[string]-or[string]::IsNullOrWhiteSpace($spec.$name)-or$spec.$name.Length-gt3000){throw 'Incomplete AI design.'}}
    foreach($name in @('ink_palette','avoid')){if($null-eq$spec.PSObject.Properties[$name]-or$spec.$name-isnot[Array]-or$spec.$name.Count-gt12){throw 'Invalid AI design list.'};foreach($item in $spec.$name){if($item-isnot[string]-or$item.Length-gt200){throw 'Invalid AI design list item.'}}}
    if($spec.composition-match'^\s*\d{1,3}\s*%'-and$spec.composition-match'(?i)cotton|polyester|хлоп|полиэстер'){throw 'AI composition describes fabric rather than layout.'}
    if($spec.ink_palette.Count-lt1){throw 'AI palette is missing.'}
    Assert-ForgeOwnerLanguage $value
    Assert-ForgeAIResponseReview $value
    return $value
}
function Merge-ForgeLocalAIManualFields($Draft,$Fields){
    $revisions=@($Draft.revisions|Sort-Object revision_no)
    $protected=@{};$deleted=@{}
    for($i=1;$i-lt$revisions.Count;$i++){
        $current=$revisions[$i];$previous=$revisions[$i-1]
        if(([string]$current.reason).StartsWith('local_ai_')){continue}
        foreach($name in $script:ResearchDraftContentFields){if([string](Get-PropertyValue $current $name)-cne[string](Get-PropertyValue $previous $name)){$protected[$name]=Get-PropertyValue $current $name}}
        $newSpec=Get-ForgeProductionSpec $current;$oldSpec=Get-ForgeProductionSpec $previous
        $names=@(@($newSpec.PSObject.Properties|ForEach-Object{$_.Name})+@($oldSpec.PSObject.Properties|ForEach-Object{$_.Name})|Select-Object -Unique)
        foreach($name in $names){if((ConvertTo-ForgeBriefCanonicalJson (Get-PropertyValue $newSpec $name))-cne(ConvertTo-ForgeBriefCanonicalJson (Get-PropertyValue $oldSpec $name))){$protected['production_spec.'+$name]=Get-PropertyValue $newSpec $name;$deleted['production_spec.'+$name]=($null-eq$newSpec.PSObject.Properties[$name])}}
    }
    foreach($name in $protected.Keys){if($name.StartsWith('production_spec.')){$property=$name.Substring(16);if($deleted[$name]){$Fields.production_spec.PSObject.Properties.Remove($property)}else{Add-OrSetProperty $Fields.production_spec $property $protected[$name]}}else{Add-OrSetProperty $Fields $name $protected[$name]}}
    return $Fields
}
function Set-ForgeDraftResearchEvidence($Draft,$Fields,$Context,[string]$AutoRunPath=''){
    Assert-QwenEvidenceCitations $Fields $Context
    Add-OrSetProperty $Draft.provenance 'research_packet' $Context.packet
    Add-OrSetProperty $Draft.provenance 'citation_map' $Context.selected_records
    Add-OrSetProperty $Draft.provenance 'model_observation_citations' (Get-PropertyValue $Context 'structured_model_citations')
    Add-OrSetProperty $Draft.provenance 'research_verified' $false
    Add-OrSetProperty $Draft.provenance 'claim_review' (Get-ResearchReviewOverlay $Fields $Context $Draft.current_revision_hash)
    if($AutoRunPath){Add-OrSetProperty $Draft.provenance 'auto_run_path' $AutoRunPath}
}
function Save-ForgeLocalAIDraft($Fields,[string]$Prompt,[string]$ExistingKey='',[string]$ExpectedRevision='',$EvidenceContext=$null,[string]$AutoRunPath=''){
    Assert-ForgeAIFieldsForSave $Fields $EvidenceContext
    if($ExistingKey){$draft=Get-ResearchDraft $ExistingKey;if($null-eq$draft){throw 'Draft missing'};$Fields=Merge-ForgeLocalAIManualFields $draft $Fields;Assert-ForgeAIFieldsForSave $Fields $EvidenceContext;return Save-ResearchDraftRevision $ExistingKey $Fields 'local_ai_revision_unapproved' $ExpectedRevision -EvidenceContext $EvidenceContext}
    $state=Read-LocalCoreState
    $key=$script:ResearchDraftKeyPrefix+[Guid]::NewGuid().ToString('N').Substring(0,24)
    $revision=New-ResearchDraftRevision $key 1 $Fields 'local_ai_draft_unapproved' -EvidenceContext $EvidenceContext
    $draft=[pscustomobject]@{schema=$script:ResearchDraftSchema;concept_key=$key;status='draft';created_at=$revision.created_at;updated_at=$revision.created_at;current_revision_no=1;current_revision_id=$revision.revision_id;current_revision_hash=$revision.revision_hash;revisions=@($revision);provenance=[pscustomobject]@{origin='local_ai';contract='forge.local_ai_draft.v1';niche_name=$Fields.title;model='qwen3.5:9b';endpoint='127.0.0.1:11434';prompt_sha256=(Get-StringSha256Hex $Prompt);evidence_notes=@();snapshot_sources=@();research_verified=$false};authority=[pscustomobject]@{server_concept=$false;backend_mutation=$false;generation_authorized=$false;paid_provider_authorized=$false;accept_authorized=$false;publication_authorized=$false;external_submission_authorized=$false}}
    if($null-ne$EvidenceContext){
        Set-ForgeDraftResearchEvidence $draft $Fields $EvidenceContext $AutoRunPath
    }
    Set-ResearchDraftList $state (@(Get-ResearchDraftList $state)+@($draft))
    Write-LocalCoreState $state
    return [pscustomobject]@{saved=$true;draft=$draft}
}
function Stop-ForgeLocalAIRequest {
    if($null-eq$script:LocalAIRequest){return}
    $request=$script:LocalAIRequest;$script:LocalAIRequest=$null
    $request.Cancel.Cancel();$request.Content.Dispose();$request.Client.Dispose();$request.Cancel.Dispose()
    $LocalAICreateButton.IsEnabled=$true;$LocalAIReviseButton.IsEnabled=$true;$LocalAICancelButton.IsEnabled=$false
    $LocalAIStatus.Text='Отменено. Черновик не изменён.'
}
function Start-ForgeLocalAIRequest([bool]$Revise=$false,[string]$ExactHook='',[string]$PrintPreset=''){
    if($null-ne$script:LocalAIRequest){return}
    if($null-ne$script:VisionReviewRequest){$LocalAIStatus.Text='Finish or cancel Qwen vision comparison first.';return}
    if($script:Dirty-or$script:PublicationDirty){$LocalAIStatus.Text='Сохраните или отмените текущие правки перед запросом AI.';return}
    $instruction=[string]$LocalAIPrompt.Text
    if([string]::IsNullOrWhiteSpace($instruction)-or$instruction.Length-gt4000){$LocalAIStatus.Text='Введите задачу для идеи и дизайна (до 4000 символов).';return}
    $key='';$revision='';$context=''
    if($Revise){if(!(Test-CurrentIsResearchDraft)){$LocalAIStatus.Text='Откройте локальный черновик для AI-правки. Серверные снимки не изменяются.';return};$key=[string]$script:Current.concept.concept_key;$revision=[string]$script:Current.concept.current_revision_id;$context=($script:Current.concept|ConvertTo-Json -Depth 12 -Compress)}
    try{$evidence=Get-ResearchEvidenceContext;if($null-ne$evidence){$instruction+=$evidence.prompt}}catch{$LocalAIStatus.Text='Research source is missing, stale or changed. Reopen/reimport its evidence before AI use. Nothing was sent or saved.';Write-AppLog 'WARN' ('Local AI source validation rejected: '+$_.Exception.Message);return}
    $body=New-ForgeLocalAICardBody -Instruction $instruction -RevisionContext $context -ExactHook $ExactHook -PrintPreset $PrintPreset
    try{$script:LocalAIRequest=New-ForgeLocalAIJsonRequest $body}catch{$LocalAIStatus.Text='Local AI request could not start. No draft, approval or generation was saved; explicit retry is available.';Write-AppLog 'WARN' 'Local AI request construction failed.';return}
    foreach($pair in @{Prompt=$instruction;Key=$key;Revision=$revision;EvidenceContext=$evidence}.GetEnumerator()){$script:LocalAIRequest|Add-Member NoteProperty $pair.Key $pair.Value}
    $LocalAICreateButton.IsEnabled=$false;$LocalAIReviseButton.IsEnabled=$false;$LocalAICancelButton.IsEnabled=$true
    $LocalAIStatus.Text='Локальный Qwen создаёт черновик… Одобрение не выдаётся.'
}
function Complete-ForgeLocalAIRequest {
    $request=$script:LocalAIRequest
    if($null-eq$request-or!$request.Task.IsCompleted){return}
    $script:LocalAIRequest=$null
    $json=$null;$saveAttempted=$false;$saveCommitted=$false
    try{
        if($request.Task.IsCanceled-and$request.Cancel.IsCancellationRequested){throw 'AI request cancelled.'}
        $response=$request.Task.GetAwaiter().GetResult()
        try{if(!$response.IsSuccessStatusCode){throw 'Local Ollama rejected the request.'};$json=$response.Content.ReadAsStringAsync().GetAwaiter().GetResult()}finally{$response.Dispose()}
        $outer=ConvertFrom-ForgeJsonObjectStrict $json
        if($outer.model-cne'qwen3.5:9b'-or$outer.done-isnot[bool]-or!$outer.done-or$outer.done_reason-cne'stop'){throw 'AI response incomplete or wrong local model.'}
        Assert-ForgeLocalAIWireContract ([string]$outer.message.content) $request.ResponseSchema
        $fields=ConvertFrom-ForgeLocalAIContent ([string]$outer.message.content)
        Assert-QwenEvidenceCitations $fields $request.EvidenceContext; if($script:Dirty-or$script:PublicationDirty){throw 'User edits were made while AI was running; result not saved.'}
        $saveAttempted=$true
        $saved=Save-ForgeLocalAIDraft $fields $request.Prompt $request.Key $request.Revision -EvidenceContext $request.EvidenceContext
        if($null-eq$saved-or$saved.saved-isnot[bool]){throw 'Invalid local save acknowledgement'}
        if(!$saved.saved){
            $script:LastLocalAISaveReceipt=[pscustomobject]@{schema='forge.local_ai_save_outcome.v1';outcome='unchanged';saved=$false;original_response=$json;approved=$false;publication_authorized=$false}
            $script:LastRejectedLocalAIResponse=$null
            $LocalAIStatus.Text='AI не изменил сохранённый черновик. Нового одобрения и модельного повтора нет.';return
        }
        $saveCommitted=$true
        Set-ForgeLocalAISavedPresentation $saved $json
    }catch{
        if($saveCommitted){
            $LocalAIStatus.Text='Сохранение непроверенного черновика подтверждено, но обновление отображения завершилось с ошибкой. Проверьте список черновиков перед повтором.'
        }elseif($saveAttempted-and$_.Exception.Message-notmatch'DRAFT_STALE|User edits were made'){
            Set-ForgeLocalAIStorageUncertain $request $json $_.Exception
        }else{
            $LocalAIStatus.Text=Format-ForgeAIRejection $_.Exception;$script:LastRejectedLocalAIResponse=[pscustomobject]@{original_response=$json;owner_message=$LocalAIStatus.Text;approved=$false}
            try{Write-AppLog 'WARN' 'Local AI drafting failed; no provider or server fallback.'}catch{}
        }
    }
    finally{$request.Content.Dispose();$request.Client.Dispose();$request.Cancel.Dispose();$LocalAICreateButton.IsEnabled=$true;$LocalAIReviseButton.IsEnabled=$true;$LocalAICancelButton.IsEnabled=$false}
}
function Initialize-ForgeLocalAIUI {
    $script:LocalAIEndpoint='http://127.0.0.1:11434/api/chat'
    $script:LocalAIRequest=$null
    $LocalAICreateButton.Add_Click({Start-ForgeLocalAIRequest})
    $LocalAIReviseButton.Add_Click({Start-ForgeLocalAIRequest $true})
    $LocalAICancelButton.Add_Click({Stop-ForgeLocalAIRequest})
    $script:LocalAITimer=New-Object Windows.Threading.DispatcherTimer
    $script:LocalAITimer.Interval=[TimeSpan]::FromMilliseconds(150)
    $script:LocalAITimer.Add_Tick({Complete-ForgeLocalAIRequest})
    $script:LocalAITimer.Start()
    $Window.Add_Closed({$script:LocalAITimer.Stop();Stop-ForgeLocalAIRequest})
}
