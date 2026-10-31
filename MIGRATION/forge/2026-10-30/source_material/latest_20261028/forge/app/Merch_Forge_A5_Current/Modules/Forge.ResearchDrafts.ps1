. (Join-Path $PSScriptRoot 'Forge.OwnerLanguage.ps1')
# Merch Forge · Research -> concept draft (local-first)
# Turns a selected Discover niche into a LOCAL concept draft bound to its research provenance.
# Boundaries: no backend mutation, no paid provider call, no implicit Generate/Accept/Submit authority; full-brief approval is a separate local owner action.
# Drafts live in the LocalCore state (research_drafts[]) and appear in the normal Ideas list.

$script:ResearchDraftSchema = 'forge.research_concept_draft.v1'
$script:ResearchDraftKeyPrefix = 'rd-'
$script:ResearchDraftWorkflowState = 'research_draft'
$script:ResearchDraftContentFields = @('title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')

function Register-ResearchDraftUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{
            'draft.history.hint'='Select a saved revision to compare. Restore copies it to Edit; Save creates a new unapproved revision.';
            'draft.history.confirm'='Copy saved revision {0} into Edit? Unsaved creative edits will be replaced. Save will create a NEW unapproved revision; history is preserved. Artwork acceptance and publication approval are not restored.';
            'draft.history.staged'='Historical content copied to Edit. Save to create a new unapproved revision; no saved state has changed yet.';
            'draft.history.failed'='Restore was not saved. Reopen the latest saved draft before retrying; technical details are in Diagnostics.';
            'draft.create'='Create concept draft'; 'draft.create.hint'='Creates a local draft in Ideas, bound to this niche''s research. No generation, no publishing.';
            'draft.created'='Draft created: {0}'; 'draft.exists'='A draft from this exact research already exists: {0}'; 'draft.count'='{0} local draft(s) from this niche';
            'draft.state'='Research draft'; 'draft.meta'='Local research draft · revision {0} · not on the server';
            'draft.next'='Review this draft: write or fix the hook and visual direction in Edit, then choose KEEP / EDIT / REGEN / SKIP. Artwork: Export brief (no dispatch), then import the finished image.';
            'draft.missing'='Still missing before artwork: {0}.'; 'draft.missing.hook'='hook'; 'draft.missing.visual'='visual direction';
            'draft.provenance'='Research provenance: {0} · score {1} · confidence {2}% · snapshot {3} · {4} matched note(s)';
            'generation.server.fullbrief.blocked'='Configure a local image provider to generate the complete approved brief. Server generation is blocked until the server can preserve every field of that brief.';
            'brief.approval.approve'='Approve idea and design'; 'brief.approval.cancel'='Cancel';
            'brief.approval.title'='Approve idea and design brief';
            'brief.approval.summary'="Approve BOTH the idea and design concept in this complete saved brief?`n`nRevision: {0}`nFull brief SHA-256: {1}`n`n{2}`n`nThis approval applies only to this exact saved content. Any brief edit requires approval again. KEEP alone is not approval. Payment/provider dispatch requires the separate Generate confirmation.";
            'draft.generate.blocked'='Configure a local image provider to generate an explicitly approved research brief, or export the brief and import artwork. Research drafts cannot dispatch to the live server.';
            'draft.saved'='Draft revision {0} saved locally. Earlier owner decisions for this draft no longer apply.'; 'draft.unchanged'='No changes to save.';
            'draft.need.niche'='Select a niche first.'; 'draft.need.live'='Live research is required. No draft is created from missing data.'; 'draft.need.title'='Title cannot be empty.';
            'queue.draft'='Research draft'; 'draft.live.blocked'='This is a local research draft. Live server actions are not available for it.'
        }
        ru=@{
            'draft.history.hint'='Выберите сохранённую ревизию для сравнения. «Восстановить» копирует её в «Правку»; «Сохранить» создаёт новую неутверждённую ревизию.';
            'draft.history.confirm'='Скопировать сохранённую ревизию {0} в «Правку»? Несохранённые творческие правки будут заменены. «Сохранить» создаст НОВУЮ неутверждённую ревизию; история останется. Приёмка макета и утверждение публикации не восстанавливаются.';
            'draft.history.staged'='Историческое содержимое перенесено в «Правку». Нажмите «Сохранить» для новой неутверждённой ревизии. Сохранённые данные пока не изменились.';
            'draft.history.failed'='Восстановление не сохранено. Перед повтором откройте актуальный сохранённый черновик; технические сведения — в диагностике.';
            'draft.create'='Создать черновик концепта'; 'draft.create.hint'='Создаёт локальный черновик в «Идеях», привязанный к исследованию этой ниши. Без генерации и публикации.';
            'draft.created'='Черновик создан: {0}'; 'draft.exists'='Черновик из этого же исследования уже есть: {0}'; 'draft.count'='Локальных черновиков из этой ниши: {0}';
            'draft.state'='Черновик исследования'; 'draft.meta'='Локальный черновик исследования · ревизия {0} · не на сервере';
            'draft.next'='Проверьте черновик: допишите хук и визуальное направление во вкладке «Правка», затем выберите ОСТАВИТЬ / ПРАВКА / ЗАНОВО / ПРОПУСТИТЬ. Артворк: «Экспорт брифа» (без отправки), затем импорт готового изображения.';
            'draft.missing'='До артворка не хватает: {0}.'; 'draft.missing.hook'='хука'; 'draft.missing.visual'='визуального направления';
            'draft.provenance'='Источник исследования: {0} · оценка {1} · уверенность {2}% · снимок {3} · связанных заметок: {4}';
            'generation.server.fullbrief.blocked'='Для генерации полного утверждённого брифа настройте локального провайдера изображений. Серверная генерация заблокирована: сервер пока не передаёт все поля брифа без потерь.';
            'brief.approval.approve'='Утвердить идею и дизайн'; 'brief.approval.cancel'='Отмена';
            'brief.approval.title'='Утвердить идею и дизайн';
            'brief.approval.summary'="Утвердить И ИДЕЮ, И КОНЦЕПЦИЮ ДИЗАЙНА в этом полном сохранённом брифе?`n`nРевизия: {0}`nSHA-256 полного брифа: {1}`n`n{2}`n`nУтверждение относится только к этому содержимому. После любой правки нужно утвердить бриф снова. «ОСТАВИТЬ» само по себе не является утверждением. Платная отправка провайдеру требует отдельного подтверждения генерации.";
            'draft.generate.blocked'='Для генерации утверждённого брифа настройте локального провайдера изображений. Либо экспортируйте бриф и импортируйте макет. Черновики не отправляются на сервер.';
            'draft.saved'='Ревизия черновика {0} сохранена локально. Прежние решения владельца по черновику больше не действуют.'; 'draft.unchanged'='Изменений нет.';
            'draft.need.niche'='Сначала выберите нишу.'; 'draft.need.live'='Нужны живые данные исследования. Из отсутствующих данных черновик не создаётся.'; 'draft.need.title'='Название не может быть пустым.';
            'queue.draft'='Черновик исследования'; 'draft.live.blocked'='Это локальный черновик исследования. Действия на сервере для него недоступны.'
        }
        es=@{
            'draft.history.hint'='Selecciona una revisión guardada para comparar. Restaurar la copia a Editar; Guardar crea una revisión nueva sin aprobación.';
            'draft.history.confirm'='¿Copiar la revisión guardada {0} a Editar? Se reemplazarán los cambios creativos sin guardar. Guardar creará una revisión NUEVA sin aprobación; el historial se conserva. No se restauran la aceptación del arte ni la aprobación de publicación.';
            'draft.history.staged'='Contenido histórico copiado a Editar. Guarda para crear una revisión nueva sin aprobación; los datos guardados aún no han cambiado.';
            'draft.history.failed'='La restauración no se guardó. Abre el último borrador guardado antes de reintentar; los detalles están en Diagnóstico.';
            'draft.create'='Crear borrador de concepto'; 'draft.create.hint'='Crea un borrador local en Ideas, vinculado a la investigación de este nicho. Sin generación ni publicación.';
            'draft.created'='Borrador creado: {0}'; 'draft.exists'='Ya existe un borrador de esta misma investigación: {0}'; 'draft.count'='{0} borrador(es) local(es) de este nicho';
            'draft.state'='Borrador de investigación'; 'draft.meta'='Borrador local de investigación · revisión {0} · no está en el servidor';
            'draft.next'='Revisa el borrador: escribe el gancho y la dirección visual en Editar y luego elige MANTENER / EDITAR / REGENERAR / OMITIR. Arte: Exportar brief (sin envío) e importar la imagen final.';
            'draft.missing'='Falta antes del arte: {0}.'; 'draft.missing.hook'='gancho'; 'draft.missing.visual'='dirección visual';
            'draft.provenance'='Procedencia: {0} · puntuación {1} · confianza {2}% · instantánea {3} · {4} nota(s) vinculada(s)';
            'generation.server.fullbrief.blocked'='Configura un proveedor local para generar el brief completo aprobado. La generación del servidor está bloqueada hasta que conserve todos los campos del brief.';
            'brief.approval.approve'='Aprobar idea y diseño'; 'brief.approval.cancel'='Cancelar';
            'brief.approval.title'='Aprobar idea y diseño';
            'brief.approval.summary'="¿Aprobar tanto la IDEA como el CONCEPTO DE DISEÑO de este brief completo guardado?`n`nRevisión: {0}`nSHA-256 del brief completo: {1}`n`n{2}`n`nLa aprobación solo cubre este contenido exacto. Cualquier cambio requiere aprobar de nuevo. CONSERVAR no equivale a aprobar. El envío de pago necesita la confirmación de generación por separado.";
            'draft.generate.blocked'='Configura un proveedor local para generar un brief aprobado, o exporta el brief e importa el arte. Los borradores no se envían al servidor.';
            'draft.saved'='Revisión {0} del borrador guardada localmente. Las decisiones anteriores del propietario ya no aplican.'; 'draft.unchanged'='No hay cambios.';
            'draft.need.niche'='Selecciona un nicho primero.'; 'draft.need.live'='Se requiere investigación en vivo. No se crea un borrador con datos ausentes.'; 'draft.need.title'='El título no puede estar vacío.';
            'queue.draft'='Borrador de investigación'; 'draft.live.blocked'='Este es un borrador local de investigación. Las acciones del servidor no están disponibles.'
        }
    }
    foreach($loc in $texts.Keys){
        if($null -eq $script:UiText[$loc]){$script:UiText[$loc]=@{}}
        foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]}
    }
}

# ---------- pure state helpers (headless-testable) ----------
function Get-ResearchDraftList($State) {
    if($null -eq $State){return @()}
    $p=$State.PSObject.Properties['research_drafts']; if($null -eq $p -or $null -eq $p.Value){return @()}
    return @($p.Value)
}
function ConvertTo-PlainArray($Items) { $list=New-Object System.Collections.ArrayList; foreach($i in @($Items)){if($null -ne $i){[void]$list.Add($i)}}; return ,($list.ToArray()) }
function Set-PlainArrayProperty($Object,[string]$Name,$Items) {
    $arr=ConvertTo-PlainArray $Items
    if($null -eq $Object.PSObject.Properties[$Name]){$Object|Add-Member -NotePropertyName $Name -NotePropertyValue $null -Force}
    $Object.PSObject.Properties[$Name].Value=$arr
}
function Set-ResearchDraftList($State,$Drafts) { Set-PlainArrayProperty $State 'research_drafts' $Drafts }
function Get-ResearchDraft([string]$ConceptKey,$State=$null) {
    if([string]::IsNullOrWhiteSpace($ConceptKey)){return $null}
    if($null -eq $State){$State=Read-LocalCoreState}
    foreach($d in (Get-ResearchDraftList $State)){if([string](Get-PropertyValue $d 'concept_key') -eq $ConceptKey -and [string](Get-PropertyValue $d 'status') -eq 'draft'){return $d}}
    return $null
}
function Test-ResearchDraftKey([string]$ConceptKey) { return (-not [string]::IsNullOrWhiteSpace($ConceptKey) -and $ConceptKey.StartsWith($script:ResearchDraftKeyPrefix)) }
function Test-CurrentIsResearchDraft {
    if($null -eq $script:Current){return $false}
    return [bool](Get-PropertyValue $script:Current 'local_research_draft')
}
function Get-DiscoverNicheIdentity($Niche) {
    foreach($f in @('niche_id','id','niche_key','key','slug')){
        $v=Get-PropertyValue $Niche $f
        if($null -ne $v -and -not [string]::IsNullOrWhiteSpace([string]$v)){return [pscustomobject]@{field=$f;value=[string]$v;name=[string](Get-PropertyValue $Niche 'name')}}
    }
    $name=([string](Get-PropertyValue $Niche 'name')).Trim()
    if([string]::IsNullOrWhiteSpace($name)){return $null}
    return [pscustomobject]@{field='name_sha256';value=(Get-StringSha256Hex $name.ToLowerInvariant());name=$name}
}
function Get-ResearchDraftStableJson($Object) {
    # Display-only properties are UI decorations, not research evidence.
    if($null -eq $Object){return 'null'}
    $copy=[ordered]@{}
    foreach($p in ($Object.PSObject.Properties | Sort-Object Name)){if($p.Name -in @('score_label','meta_label')){continue};$copy[$p.Name]=$p.Value}
    return ($copy | ConvertTo-Json -Depth 12 -Compress)
}
function Get-DiscoverNotesForNiche($Snapshot,$Niche,$Identity) {
    # Only notes that the snapshot explicitly links to this niche count as evidence. No fuzzy matching.
    $out=@(); if($null -eq $Snapshot -or $null -eq $Identity){return @()}
    $nameLc=([string]$Identity.name).Trim().ToLowerInvariant()
    foreach($n in @(Get-PropertyValue $Snapshot 'notes')){
        if($null -eq $n){continue}; $hit=$false
        foreach($f in @('niche_id','niche_key','niche_slug')){$v=[string](Get-PropertyValue $n $f);if($v -and $Identity.field -ne 'name_sha256' -and $v -eq [string]$Identity.value){$hit=$true}}
        foreach($f in @('niche_name','niche')){$v=([string](Get-PropertyValue $n $f)).Trim().ToLowerInvariant();if($v -and $nameLc -and $v -eq $nameLc){$hit=$true}}
        if($hit){$out+=[pscustomobject]@{note_id=[string](Get-PropertyValue $n 'id');topic=[string](Get-PropertyValue $n 'topic');conclusion=[string](Get-PropertyValue $n 'conclusion');created_at=[string](Get-PropertyValue $n 'created_at');note_sha256=(Get-StringSha256Hex (Get-ResearchDraftStableJson $n))}}
    }
    return @($out | Select-Object -First 8)
}
function New-ResearchDraftContent($Niche,$Notes) {
    $name=([string](Get-PropertyValue $Niche 'name')).Trim()
    $summary=([string](Get-PropertyValue $Niche 'research_summary')).Trim()
    $audience=([string](Get-PropertyValue $Niche 'audience')).Trim()
    $count=0;try{$count=[int](Get-PropertyValue $Niche 'concept_count')}catch{}
    $conclusions=@($Notes|Where-Object{-not[string]::IsNullOrWhiteSpace($_.conclusion)}|Select-Object -First 3|ForEach-Object{('- '+$_.topic+': '+$_.conclusion)})
    $conceptText=$summary;if($conclusions.Count){$conceptText=($summary+"`n`nSource notes (not independently verified):`n"+($conclusions-join"`n")).Trim()}
    $purchase=''
    $sourceCount=Get-ForgeSourceConceptCountText (Get-PropertyValue $Niche 'concept_count')
    $diff='The source snapshot reports '+$sourceCount+' concept records. This count does not measure demand, competition or originality. Differentiation of a new creative concept still needs review.'
    # Hook and visual direction are creative choices; they are intentionally left empty, never invented here.
    return [ordered]@{title=$name;hook='';concept_text=$conceptText;target_buyer=$audience;purchase_reason=$purchase;differentiation=$diff;visual_direction_text='';production_spec=[pscustomobject]@{}}
}
function Get-ResearchDraftContentHash([string]$ConceptKey,$Fields) {
    $m=[ordered]@{concept_key=$ConceptKey}; foreach($f in $script:ResearchDraftContentFields){$m[$f]=[string](Get-PropertyValue ([pscustomobject]$Fields) $f)}
    $spec=Get-ForgeProductionSpec $Fields;if($null -eq $spec){$spec=[pscustomobject]@{}};if(-not($spec -is [pscustomobject] -or $spec -is [System.Collections.IDictionary])){throw 'Production spec must be a JSON object.'};$m['production_spec']=$spec
    return (Get-ForgeBriefSha256 $m)
}
function New-ResearchDraftRevision([string]$ConceptKey,[int]$RevisionNo,$Fields,[string]$Reason,$EvidenceContext=$null) {
    $marker=[string](Get-PropertyValue $Fields '__forge_rejection_id');if($marker){Assert-ForgeRejectedSaveBinding $marker $ConceptKey ([string](Read-ForgeRejectedProposal $marker).record.binding.revision_id) $Fields $Reason}
    if($Reason-and$Reason.StartsWith('local_ai_',[StringComparison]::OrdinalIgnoreCase)){Assert-ForgeAIFieldsForSave $Fields $EvidenceContext}
    $hash=Get-ResearchDraftContentHash $ConceptKey $Fields
    $rev=[ordered]@{revision_no=$RevisionNo;revision_id=('rdrev-{0}-{1}-{2}' -f $ConceptKey.Substring($script:ResearchDraftKeyPrefix.Length),$RevisionNo,$hash.Substring(0,12));revision_hash=$hash;created_at=[DateTime]::UtcNow.ToString('o');reason=$Reason}
    foreach($f in $script:ResearchDraftContentFields){$rev[$f]=[string](Get-PropertyValue ([pscustomobject]$Fields) $f)}
    $spec=Get-ForgeProductionSpec $Fields;if($null -eq $spec){$spec=[pscustomobject]@{}};$rev['production_spec']=((ConvertTo-ForgeBriefCanonicalJson $spec)|ConvertFrom-Json -DateKind String)
    $rev['owner_language_review']=Get-ForgeOwnerLanguageReview $Fields
    return [pscustomobject]$rev
}
function New-ResearchConceptDraft($Niche,$Snapshot,$LoadedAtUtc,[string]$BackendVersion='') {
    if($null -eq $Niche){throw 'NO_NICHE: Select a niche first.'}
    if($null -eq $Snapshot){throw 'NO_LIVE_RESEARCH: Live research snapshot is required.'}
    $identity=Get-DiscoverNicheIdentity $Niche; if($null -eq $identity){throw 'NO_NICHE_IDENTITY: The selected niche has no id or name.'}
    $rowJson=Get-ResearchDraftStableJson $Niche; $rowSha=Get-StringSha256Hex $rowJson
    $packet=Get-PropertyValue $Snapshot 'research_packet';$sourceSha=[string](Get-PropertyValue $packet 'source_sha256')
    # Imported source identity is the archived byte SHA, never recomputed freshness/display metadata.
    # Missing/invalid packet SHAs cannot enter a row-only fallback. Older valid imported drafts need no new field.
    $evidenceSha=if($null-ne$packet){''}else{Get-ForgeBriefSha256 ([ordered]@{notes=(Get-PropertyValue $Snapshot 'notes');sources=(Get-PropertyValue $Snapshot 'sources')})}
    $s=Read-LocalCoreState
    foreach($d in (Get-ResearchDraftList $s)){
        $p=Get-PropertyValue $d 'provenance'
        if([string](Get-PropertyValue $d 'status') -ne 'draft'){continue}
        $priorPacket=Get-PropertyValue $p 'research_packet';$priorSha=[string](Get-PropertyValue $priorPacket 'source_sha256');$sameEvidence=$false
        if($null-ne$packet){$sameNiche=([string](Get-PropertyValue $p 'niche_identity_field')-ceq$identity.field-and[string](Get-PropertyValue $p 'niche_identity')-ceq$identity.value);$sameEvidence=($sameNiche-and$sourceSha-cmatch'^[0-9a-f]{64}$'-and$priorSha-cmatch'^[0-9a-f]{64}$'-and$sourceSha-ceq$priorSha)}
        elseif($null-eq$priorPacket){$sameEvidence=([string](Get-PropertyValue $p 'niche_row_sha256')-ceq$rowSha-and$evidenceSha-and[string](Get-PropertyValue $p 'evidence_snapshot_sha256')-ceq$evidenceSha)}
        if($sameEvidence){return [pscustomobject]@{created=$false;draft=$d}}
    }
    $notes=@(Get-DiscoverNotesForNiche $Snapshot $Niche $identity)
    $fields=New-ResearchDraftContent $Niche $notes
    $key=$script:ResearchDraftKeyPrefix+([Guid]::NewGuid().ToString('N').Substring(0,24))
    $rev=New-ResearchDraftRevision $key 1 $fields 'created_from_discover_research'
    $loaded=''; if($null -ne $LoadedAtUtc){try{$loaded=([datetime]$LoadedAtUtc).ToUniversalTime().ToString('o')}catch{$loaded=[string]$LoadedAtUtc}}
    $sources=@(); foreach($x in @(Get-PropertyValue $Snapshot 'sources') | Select-Object -First 16){if($null -eq $x){continue};$sources+=[pscustomobject]@{source_id=[string](Get-PropertyValue $x 'id');name=[string](Get-PropertyValue $x 'name');source_class=[string](Get-PropertyValue $x 'source_class');url=[string](Get-PropertyValue $x 'url');authority_level=(Get-PropertyValue $x 'authority_level');last_checked_at=[string](Get-PropertyValue $x 'last_checked_at')}}
    $provenance=[pscustomobject]@{
        origin='discover_research'; contract=[string]$(if(Get-PropertyValue $Snapshot 'contract'){Get-PropertyValue $Snapshot 'contract'}else{'forge.discover_snapshot.v1'})
        snapshot_loaded_at=$loaded; backend_version=$BackendVersion
        niche_identity_field=$identity.field; niche_identity=$identity.value; niche_name=$identity.name
        niche_row_sha256=$rowSha; evidence_snapshot_sha256=$evidenceSha; niche_row=($rowJson | ConvertFrom-Json)
        score_total=(Get-PropertyValue $Niche 'score_total'); score_confidence=(Get-PropertyValue $Niche 'score_confidence'); category=[string](Get-PropertyValue $Niche 'category'); audience=[string](Get-PropertyValue $Niche 'audience'); concept_count_at_snapshot=(Get-PropertyValue $Niche 'concept_count')
        evidence_notes=@($notes); evidence_note_match='explicit_niche_link_only'; evidence_note_link_available=[bool](@(Get-PropertyValue $Snapshot 'notes') | Where-Object { $null -ne $_ -and ($null -ne $_.PSObject.Properties['niche_key'] -or $null -ne $_.PSObject.Properties['niche_id'] -or $null -ne $_.PSObject.Properties['niche_name']) } | Select-Object -First 1)
        snapshot_sources=@($sources); snapshot_sources_scope='snapshot_wide_context_not_niche_specific';research_verified=$false;research_packet=(Get-PropertyValue $Snapshot 'research_packet')
    }
    $draft=[pscustomobject]@{
        schema=$script:ResearchDraftSchema; concept_key=$key; status='draft'; created_at=$rev.created_at; updated_at=$rev.created_at
        niche_name=$identity.name; current_revision_no=1; current_revision_id=$rev.revision_id; current_revision_hash=$rev.revision_hash
        revisions=@($rev); provenance=$provenance
        authority=[pscustomobject]@{scope='server_and_paid_actions_only; local owner gates (exact local accept, local package) keep their own existing checks';server_concept=$false;backend_mutation=$false;generation_authorized=$false;paid_provider_authorized=$false;accept_authorized=$false;publication_authorized=$false;external_submission_authorized=$false}
    }
    Set-ResearchDraftList $s (@(Get-ResearchDraftList $s)+@($draft))
    Write-LocalCoreState $s
    return [pscustomobject]@{created=$true;draft=$draft}
}
function Get-ResearchDraftCurrentFields($Draft) {
    $revs=@(Get-PropertyValue $Draft 'revisions'); $no=[int](Get-PropertyValue $Draft 'current_revision_no')
    foreach($r in $revs){if([int](Get-PropertyValue $r 'revision_no') -eq $no){return $r}}
    if($revs.Count){return $revs[$revs.Count-1]}; return $null
}
function Get-ResearchDraftHistory($Draft) {
    # Detached view rows: adding display aliases must never decorate saved history.
    $rows=@()
    foreach($revision in @(Get-PropertyValue $Draft 'revisions')){
        if($null-eq$revision){continue}
        $row=ConvertFrom-Json -DateKind String (ConvertTo-Json -InputObject $revision -Depth 60 -Compress)
        Add-OrSetProperty $row 'id' ([string](Get-PropertyValue $revision 'revision_id'))
        Add-OrSetProperty $row 'content_hash' ([string](Get-PropertyValue $revision 'revision_hash'))
        Add-OrSetProperty $row 'revision_kind' ([string](Get-PropertyValue $revision 'reason'))
        Add-OrSetProperty $row 'display' ('Revision {0} · {1}' -f $row.revision_no,$row.created_at)
        $rows+=,$row
    }
    return @($rows|Sort-Object revision_no -Descending)
}
function Get-ResearchDraftRestoreSource($Draft,[string]$SourceRevisionId,[string]$ExpectedRevisionId) {
    if($null-eq$Draft){throw 'DRAFT_NOT_FOUND: The research draft no longer exists.'}
    if([string](Get-PropertyValue $Draft 'current_revision_id')-cne$ExpectedRevisionId){throw 'DRAFT_STALE: This draft changed in another window. Reopen it before restoring.'}
    if(!$SourceRevisionId-or$SourceRevisionId-ceq$ExpectedRevisionId){throw 'DRAFT_RESTORE_SOURCE: Select an older saved revision.'}
    $matches=@((Get-PropertyValue $Draft 'revisions')|Where-Object{[string](Get-PropertyValue $_ 'revision_id')-ceq$SourceRevisionId})
    if($matches.Count-ne1){throw 'DRAFT_RESTORE_SOURCE: The selected saved revision is missing or ambiguous. Nothing was restored.'}
    $source=$matches[0];$hash=Get-ResearchDraftContentHash ([string](Get-PropertyValue $Draft 'concept_key')) $source
    if($hash-cne[string](Get-PropertyValue $source 'revision_hash')){throw 'DRAFT_RESTORE_SOURCE: The historical content hash does not match. Nothing was restored.'}
    return (ConvertFrom-Json -DateKind String (ConvertTo-Json -InputObject $source -Depth 60 -Compress))
}
function Save-ResearchDraftRevision([string]$ConceptKey,$Fields,[string]$Reason,[string]$ExpectedRevisionId,$EvidenceContext=$null,[string]$SourceRevisionId='') {
    $marker=[string](Get-PropertyValue $Fields '__forge_rejection_id');if($marker){Assert-ForgeRejectedSaveBinding $marker $ConceptKey $ExpectedRevisionId $Fields $Reason}
    if($Reason-and$Reason.StartsWith('local_ai_',[StringComparison]::OrdinalIgnoreCase)){Assert-ForgeAIFieldsForSave $Fields $EvidenceContext}
    $s=Read-LocalCoreState; $d=Get-ResearchDraft $ConceptKey $s; if($null -eq $d){throw 'DRAFT_NOT_FOUND: The research draft no longer exists.'}
    if([string](Get-PropertyValue $d 'current_revision_id') -ne $ExpectedRevisionId){throw 'DRAFT_STALE: This draft changed in another window. Reopen it before saving.'}
    $restoreSource=$null;if($SourceRevisionId){$restoreSource=Get-ResearchDraftRestoreSource $d $SourceRevisionId $ExpectedRevisionId}
    $t=([string](Get-PropertyValue ([pscustomobject]$Fields) 'title')).Trim(); if([string]::IsNullOrWhiteSpace($t)){throw 'DRAFT_TITLE_REQUIRED: Title cannot be empty.'}
    $newHash=Get-ResearchDraftContentHash $ConceptKey $Fields
    if($null-eq$restoreSource-and$newHash -eq [string](Get-PropertyValue $d 'current_revision_hash')){return [pscustomobject]@{saved=$false;draft=$d}}
    $no=[int](Get-PropertyValue $d 'current_revision_no')+1
    $rev=New-ResearchDraftRevision $ConceptKey $no $Fields $(if([string]::IsNullOrWhiteSpace($Reason)){'owner_edit'}else{$Reason}) -EvidenceContext $EvidenceContext
    if($null-ne$restoreSource){Add-OrSetProperty $rev 'source_revision_id' $SourceRevisionId;Add-OrSetProperty $rev 'source_revision_hash' ([string]$restoreSource.revision_hash)}
    Set-PlainArrayProperty $d 'revisions' (@(Get-PropertyValue $d 'revisions')+@($rev))
    Add-OrSetProperty $d 'current_revision_no' $no; Add-OrSetProperty $d 'current_revision_id' $rev.revision_id; Add-OrSetProperty $d 'current_revision_hash' $rev.revision_hash; Add-OrSetProperty $d 'updated_at' $rev.created_at
    if($null-ne$EvidenceContext){Set-ForgeDraftResearchEvidence $d $Fields $EvidenceContext}
    # Commit revision and revocation atomically: UI refresh/reopen may fail after this write.
    # Historical review/receipts and artwork files survive; none grants authority to the new revision.
    $lc=Get-LocalCoreConcept $ConceptKey $s
    if($null-ne$lc){
        $null=Preserve-ForgeLocalReviewHistory $lc 'research_revision_changed'
        Add-OrSetProperty $lc 'brief_approval' $null;Add-OrSetProperty $lc 'active_acceptance' $null
        foreach($artwork in @(Get-PropertyValue $lc 'artwork')){Add-OrSetProperty $artwork 'accepted' $false}
        Add-OrSetProperty $lc 'checks' (New-LocalCoreChecks $rev.revision_id);Add-OrSetProperty $lc 'publication' $null
        Invalidate-LocalCorePackages $lc 'research_revision_changed'
        Add-OrSetProperty $lc 'owner_decision' 'UNDECIDED';Add-OrSetProperty $lc 'owner_decision_revision_id' $rev.revision_id;Add-OrSetProperty $lc 'owner_decision_revision_hash' $rev.revision_hash;Add-OrSetProperty $lc 'owner_decision_at' ''
    }
    Write-LocalCoreState $s
    return [pscustomobject]@{saved=$true;draft=$d}
}
function ConvertTo-ResearchDraftConcept($Draft) {
    $r=Get-ResearchDraftCurrentFields $Draft; $p=Get-PropertyValue $Draft 'provenance'
    return [pscustomobject]@{
        concept_key=[string](Get-PropertyValue $Draft 'concept_key'); title=[string](Get-PropertyValue $r 'title'); hook=[string](Get-PropertyValue $r 'hook')
        niche_name=[string](Get-PropertyValue $p 'niche_name'); concept_text=[string](Get-PropertyValue $r 'concept_text'); target_buyer=[string](Get-PropertyValue $r 'target_buyer')
        purchase_reason=[string](Get-PropertyValue $r 'purchase_reason'); differentiation=[string](Get-PropertyValue $r 'differentiation'); visual_direction_text=[string](Get-PropertyValue $r 'visual_direction_text')
        current_revision_no=[int](Get-PropertyValue $Draft 'current_revision_no'); current_revision_id=[string](Get-PropertyValue $Draft 'current_revision_id'); current_content_hash=[string](Get-PropertyValue $Draft 'current_revision_hash')
        current_revision_accepted=$false; workflow_state=$script:ResearchDraftWorkflowState; production_spec=$(if($null -ne (Get-PropertyValue $r 'production_spec')){Get-PropertyValue $r 'production_spec'}else{[pscustomobject]@{}}); concept_status='draft'
        score_total=(Get-PropertyValue $p 'score_total'); is_local_draft=$true
    }
}
function Get-ResearchDraftQueueItems($State=$null) {
    if($null -eq $State){try{$State=Read-LocalCoreState}catch{Write-AppLog 'WARN' ('Research drafts unavailable: '+$_.Exception.Message);throw}}
    $items=@()
    foreach($d in (Get-ResearchDraftList $State)){
        if([string](Get-PropertyValue $d 'status') -ne 'draft'){continue}
        $c=ConvertTo-ResearchDraftConcept $d
        $items+=[pscustomobject]@{concept_key=$c.concept_key;title=$c.title;hook=$c.hook;niche_name=$c.niche_name;concept_text=$c.concept_text;target_buyer=$c.target_buyer;purchase_reason=$c.purchase_reason;differentiation=$c.differentiation;visual_direction_text=$c.visual_direction_text;workflow_state=$script:ResearchDraftWorkflowState;score_total=$c.score_total;is_local_draft=$true;meaning=''}
    }
    return @($items)
}
function Merge-ResearchDraftsIntoQueue($Items,$State=$null) {
    $base=@($Items | Where-Object {$null -ne $_}); $seen=@{}; foreach($i in $base){$seen[[string](Get-PropertyValue $i 'concept_key')]=$true}
    $out=@($base); foreach($d in (Get-ResearchDraftQueueItems $State)){if(-not $seen.ContainsKey([string]$d.concept_key)){$out+=$d}}
    return @($out)
}
function Get-ResearchDraftMissing($Concept) {
    $m=@(); if([string]::IsNullOrWhiteSpace([string](Get-PropertyValue $Concept 'hook'))){$m+=(Get-UiText 'draft.missing.hook' 'hook')}
    if([string]::IsNullOrWhiteSpace([string](Get-PropertyValue $Concept 'visual_direction_text'))){$m+=(Get-UiText 'draft.missing.visual' 'visual direction')}
    return @($m)
}
function Get-ResearchDraftProvenanceText($Draft) {
    $origin=Get-PropertyValue (Get-PropertyValue $Draft 'provenance') 'origin'
    if($null-ne(Get-PropertyValue (Get-PropertyValue $Draft 'provenance') 'research_packet')){return (Get-ResearchReviewWarning $Draft)+"`r`n`r`n"+(Format-ResearchEvidenceRows (Get-PropertyValue (Get-PropertyValue $Draft 'provenance') 'research_packet'))}
    if($origin-eq'local_ai'){return 'Локальный AI-черновик Qwen. Идея и дизайн предложены моделью; исследования рынка, продажи и права не подтверждены.'}
    $p=Get-PropertyValue $Draft 'provenance'; $score=Get-PropertyValue $p 'score_total'; $conf=Get-PropertyValue $p 'score_confidence'
    $scoreText=Format-ForgeUnverifiedAssessmentValue $score;$confText=Format-ForgeUnverifiedAssessmentValue $conf
    return ((Get-UiText 'draft.provenance' 'Source context: {0} | unverified source score {1}, confidence field {2} | loaded {3} | {4} linked notes. Not a demand estimate.') -f [string](Get-PropertyValue $p 'niche_name'),$scoreText,$confText,[string](Get-PropertyValue $p 'snapshot_loaded_at'),@((Get-PropertyValue $p 'evidence_notes')|Where-Object{$null-ne$_}).Count)
}

# ---------- UI glue (WPF; exercised natively only) ----------
function Set-DraftEditBoxesEditable([bool]$Editable) {
    foreach($box in @($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$ReasonBox)){if($null -ne $box){$box.IsReadOnly=(-not $Editable)}}
    if($null -ne $SpecBox){$SpecBox.IsReadOnly=(-not $Editable)}
}
function Restore-RoleEditability {
    $canEdit=Has-Cap 'edit'
    foreach($box in @($TitleBox,$HookBox,$ConceptTextBox,$BuyerBox,$PurchaseBox,$DifferentiationBox,$VisualBox,$SpecBox,$ReasonBox)){if($null -ne $box){$box.IsReadOnly=(-not $canEdit)}}
}
function Enter-ResearchDraftSection([string]$Section) {
    Enter-LocalCoreSection $Section
    foreach($tab in @($MainTabs.Items)){if($tab -is [Windows.Controls.TabItem]){if((Get-MainTabKey $tab) -in @('edit','history')){$tab.IsEnabled=$true}}}
    if($null -ne $ContextNav){$ContextNav.Visibility='Collapsed'}
    if($null -ne $script:Current -and $null -ne $ConceptMeta){$ConceptMeta.Text=(Get-UiText 'draft.meta' 'Local research draft · revision {0} · not on the server') -f [int](Get-PropertyValue $script:Current.concept 'current_revision_no')}
}
function Clear-DraftStaleConceptSurfaces {
    # A draft has no server variants, generation requests, analysis, publication or delivery state.
    foreach($l in @($VariantList,$GenerationRequestList,$RevisionList,$AuditList)){if($null -ne $l){try{$l.ItemsSource=@()}catch{}}}
    foreach($tb in @($AnalysisPurchase,$AnalysisContext,$AnalysisMeaning,$AnalysisEvidence,$AnalysisScores,$AnalysisAdvanced,$AnalysisWarnings,$CurrentRevisionPreview,$SelectedRevisionPreview,$RevisionAdvanced,$AuditAdvanced,$AuditDetail,$DeliveryStatus)){if($null -ne $tb){try{$tb.Text=''}catch{}}}
}
function Open-ResearchDraftItem($Item,[bool]$Force=$false) {
    if($null -eq $Item){return $false}
    $key=[string](Get-PropertyValue $Item 'concept_key')
    if(-not $Force -and $null -ne $script:Current -and [string](Get-PropertyValue $script:Current.concept 'concept_key') -eq $key){return}
    if(-not $Force -and ($script:Dirty -or $script:PublicationDirty) -and -not (Confirm 'Discard unsaved creative/publication edits and open another concept?')){return}
    try {
        $d=Get-ResearchDraft $key; if($null -eq $d){Show-Error 'This research draft no longer exists. Refresh the Ideas list.';return $false}
        $c=ConvertTo-ResearchDraftConcept $d
        $script:Dirty=$false; $script:PublicationDirty=$false; $script:ReviewWorkspace=$null; $script:RestoreSourceRevisionId=$null; $script:Delivery=$null; $script:Publication=$null
        $script:Current=[pscustomobject]@{concept=$c;local_research_draft=$true;draft=$d;variants=@();revisions=@(Get-ResearchDraftHistory $d);scores=@();analysis_warnings=@()}
        if(@('home','discover','portfolio','performance') -contains $script:ProductSection){$script:ProductSection='ideas'}
        $wasBusy=$script:Busy; $script:Busy=$true
        try {
            Clear-DraftStaleConceptSurfaces
            $RevisionList.ItemsSource=$script:Current.revisions
            $CurrentRevisionPreview.Text=Format-Revision (Get-ResearchDraftCurrentFields $d)
            $SelectedRevisionPreview.Text=Get-UiText 'draft.history.hint' 'Select a saved revision to compare. Restore copies it to Edit; Save creates a new unapproved revision.'
            $RestoreRevisionButton.IsEnabled=$false
            $TitleBox.Text=$c.title;$HookBox.Text=$c.hook;$ConceptTextBox.Text=$c.concept_text;$BuyerBox.Text=$c.target_buyer;$PurchaseBox.Text=$c.purchase_reason;$DifferentiationBox.Text=$c.differentiation;$VisualBox.Text=$c.visual_direction_text;$SpecBox.Text=($c.production_spec|ConvertTo-Json -Depth 60);$ReasonBox.Text=''
            if($null -ne $GenerationBriefText){$GenerationBriefText.Text=Get-GenerationBriefSummary $c}
            $ConceptTitle.Text=$c.title
            $OverviewHook.Text=$c.hook;$OverviewConcept.Text=(Format-ForgeOwnerOriginal ($c.concept_text) ([string]$c.hook));$OverviewBuyer.Text=(Format-ForgeOwnerOriginal ($c.target_buyer) ([string]$c.hook));$OverviewWhy.Text=(Format-ForgeOwnerOriginal ($c.purchase_reason) ([string]$c.hook));$OverviewDifferent.Text=(Format-ForgeOwnerOriginal ($c.differentiation) ([string]$c.hook));$OverviewVisual.Text=(Format-ForgeOwnerOriginal ($c.visual_direction_text) ([string]$c.hook));$OverviewMeaning.Text=''
            $OverviewStatus.Text=Get-UiText 'draft.state' 'Research draft'
            # Checks tab: show the draft's own reasoning instead of empty server-analysis sections.
            $dash='—'; $AnalysisPurchase.Text=if([string]$c.purchase_reason){[string]$c.purchase_reason}else{$dash}; $AnalysisContext.Text=if([string]$c.target_buyer){[string]$c.target_buyer}else{$dash}; $AnalysisMeaning.Text=if([string]$c.concept_text){[string]$c.concept_text}else{$dash}
            $OverviewWarnings.Text=(Format-ForgeOwnerLanguageReview $c)+"`n`n"+(Get-ResearchDraftProvenanceText $d)+"`n`nUnsaved edits exist only in memory. Use Save to keep them. After closing or a crash, only the last successfully saved revision can be restored."
            $missing=@(Get-ResearchDraftMissing $c); $next=Get-UiText 'draft.next' 'Review this draft.'
            if($missing.Count){$next=((Get-UiText 'draft.missing' 'Still missing before artwork: {0}.') -f ($missing -join ', '))+' '+$next}
            $OverviewNext.Text=$next
            $OverviewVisualButton.IsEnabled=$true; $OverviewEditButton.IsEnabled=$true
        } finally { $script:Busy=$wasBusy }
        Set-DraftEditBoxesEditable $true
        $null=Ensure-LocalCoreConceptFromCurrent
        Load-AuditHistory $key
        # Fill local tabs now so no surface keeps the previous concept's data.
        try{Refresh-LocalArtworkUi}catch{Write-AppLog 'WARN' ('Draft artwork surface refresh failed: '+$_.Exception.Message)}
        try{Load-LocalChecksUi}catch{Write-AppLog 'WARN' ('Draft checks surface refresh failed: '+$_.Exception.Message)}
        try{Load-LocalPublicationUi}catch{Write-AppLog 'WARN' ('Draft publication surface refresh failed: '+$_.Exception.Message)}
        Show-ProductSection $script:ProductSection
        Set-Dirty $false
        Update-OwnerDecisionControls
        return $true
    } catch {
        Write-AppLog 'ERROR' ('Research draft open failed for '+$key+': '+$_.Exception.Message)
        Show-Error ('Research draft could not be opened: '+$_.Exception.Message)
        if($null -ne $StatusText){$StatusText.Text='Draft open failed'};return $false
    }
}
function Restore-SelectedResearchDraftRevision {
    if(!(Test-CurrentIsResearchDraft)-or$script:Busy){return}
    $selected=$RevisionList.SelectedItem;if($null-eq$selected){return}
    $key=[string]$script:Current.concept.concept_key;$expected=[string]$script:Current.concept.current_revision_id
    $sourceId=[string](Get-PropertyValue $selected 'revision_id');$sourceHash=[string](Get-PropertyValue $selected 'revision_hash')
    try{
        # Confirmation does not write state or discard unsaved content on Cancel.
        $question=((Get-UiText 'draft.history.confirm' 'Copy saved revision {0} into Edit? Unsaved creative edits will be replaced. Save will create a NEW unapproved revision; history is preserved. Artwork acceptance and publication approval are not restored.') -f $selected.revision_no)
        if(!(Confirm $question)){return}
        if(!(Test-CurrentIsResearchDraft)-or[string]$script:Current.concept.concept_key-cne$key-or[string]$script:Current.concept.current_revision_id-cne$expected){throw 'The open idea changed. Nothing was restored.'}
        $source=Get-ResearchDraftRestoreSource (Get-ResearchDraft $key) $sourceId $expected
        if([string]$source.revision_hash-cne$sourceHash){throw 'The selected historical revision changed. Nothing was restored.'}
        $specJson=ConvertTo-ForgeBriefCanonicalJson (Get-ForgeProductionSpec $source)
        $TitleBox.Text=[string]$source.title;$HookBox.Text=[string]$source.hook;$ConceptTextBox.Text=[string]$source.concept_text;$BuyerBox.Text=[string]$source.target_buyer;$PurchaseBox.Text=[string]$source.purchase_reason;$DifferentiationBox.Text=[string]$source.differentiation;$VisualBox.Text=[string]$source.visual_direction_text;$SpecBox.Text=$specJson
        $ReasonBox.Text=('Restore from revision {0}' -f $source.revision_no);$script:RestoreSourceRevisionId=$sourceId
        Set-Dirty $true;$null=Select-MainTab 'Edit';Update-MainTabUi
        $StatusText.Text=Get-UiText 'draft.history.staged' 'Historical content copied to Edit. Save to create a new unapproved revision; no saved state has changed yet.'
    }catch{Write-AppLog 'WARN' ('Draft restore refused: '+$_.Exception.Message);Show-Error (Get-UiText 'draft.history.failed' 'Restore was not saved. Reopen the latest saved draft before retrying; technical details are in Diagnostics.')}
}
function Save-CurrentResearchDraftRevision {
    if(-not(Test-CurrentIsResearchDraft)){return}
    $c=$script:Current.concept;$key=[string]$c.concept_key;$expected=[string]$c.current_revision_id;$expectedHash=[string]$c.current_content_hash
    $sourceId=[string]$script:RestoreSourceRevisionId;$reason=[string]$ReasonBox.Text
    $fields=[ordered]@{title=([string]$TitleBox.Text).Trim();hook=[string]$HookBox.Text;concept_text=[string]$ConceptTextBox.Text;target_buyer=[string]$BuyerBox.Text;purchase_reason=[string]$PurchaseBox.Text;differentiation=[string]$DifferentiationBox.Text;visual_direction_text=[string]$VisualBox.Text}
    try{$fields.production_spec=ConvertFrom-ForgeProductionSpecJson ([string]$SpecBox.Text)}catch{Show-Error 'Спецификация должна быть корректным JSON-объектом. Исходные поля сохранены.';return}
    if([string]::IsNullOrWhiteSpace($fields.title)){Show-Error 'Название не может быть пустым.';return}
    if($script:PublicationDirty){if(-not(Confirm 'Новая творческая ревизия отменит текущий контекст публикации и несохранённые метаданные. Продолжить?')){return}}
    $committed=$false
    try{
        if(!(Test-CurrentIsResearchDraft)-or[string]$script:Current.concept.concept_key-cne$key-or[string]$script:Current.concept.current_revision_id-cne$expected-or[string]$script:Current.concept.current_content_hash-cne$expectedHash){throw 'The open draft changed during save confirmation. Nothing was saved.'}
        $r=Save-ResearchDraftRevision $key $fields $reason $expected -SourceRevisionId $sourceId
        if(-not$r.saved){Set-Dirty $false;$StatusText.Text='Изменений для сохранения нет.';return}
        $committed=$true;Set-PublicationDirty $false;Set-Dirty $false
        Refresh-ResearchDraftQueue
        $opened=@(Open-ResearchDraftItem ([pscustomobject]@{concept_key=$key}) $true)
        if(-not(@($opened|Where-Object {$_-is[bool]-and$_}).Count)){throw 'DRAFT_REOPEN_FAILED_AFTER_COMMIT'}
        Select-MainTab 'Overview';Update-MainTabUi
        $StatusText.Text=('Ревизия {0} сохранена и открыта; оригиналы не переведены автоматически. Язык пояснений указан в обзоре.' -f [int]$r.draft.current_revision_no)
    }catch{
        if($committed){
            $script:Current=$null
            try{Clear-DraftStaleConceptSurfaces}catch{}
            try{Update-OwnerDecisionControls}catch{}
            $StatusText.Text='Локальная ревизия сохранена, но обновление интерфейса не завершилось. Старая карточка не доступна для решений; заново откройте её из очереди. Не повторяйте сохранение вслепую.'
            Write-AppLog 'WARN' 'Research draft committed but UI reload failed; stale action context cleared.'
        }else{
            $StatusText.Text='Сохранение ревизии не подтверждено. Поля редактора сохранены; проверьте актуальную версию перед повтором.'
            Show-Error $_.Exception.Message
        }
    }
}
function Refresh-ResearchDraftQueue {
    $server=@($script:Queue | Where-Object {-not [bool](Get-PropertyValue $_ 'is_local_draft')})
    $script:Queue=@(Add-QueueDisplayProperties (Merge-ResearchDraftsIntoQueue $server))
    Apply-Filter
    if(Get-Command Refresh-AutoResearchCardsFromSavedDrafts -ErrorAction SilentlyContinue){Refresh-AutoResearchCardsFromSavedDrafts}
}
function Update-DiscoverDraftControls {
    if($null -eq $DiscoverCreateDraftButton){return}
    $DiscoverCreateDraftButton.Content=Get-UiText 'draft.create' 'Create concept draft'
    $DiscoverCreateDraftButton.ToolTip=Get-UiText 'draft.create.hint' 'Creates a local draft in Ideas, bound to this niche''s research.'
    $n=$null; if($null -ne $DiscoverNicheList){$n=$DiscoverNicheList.SelectedItem}
    $DiscoverCreateDraftButton.IsEnabled=($null -ne $n -and $null -ne $script:DiscoverSnapshot -and -not $script:Busy -and (-not $script:OfflineMode -or [string](Get-PropertyValue $script:DiscoverSnapshot 'origin')-eq'local_import'))
    if($null -ne $DiscoverDraftStatusText){
        if($null -eq $n){$DiscoverDraftStatusText.Text='';return}
        $count=0; try{$id=Get-DiscoverNicheIdentity $n; foreach($d in (Get-ResearchDraftList (Read-LocalCoreState))){$p=Get-PropertyValue $d 'provenance';if([string](Get-PropertyValue $d 'status') -eq 'draft' -and [string](Get-PropertyValue $p 'niche_identity') -eq [string]$id.value){$count++}}}catch{}
        $DiscoverDraftStatusText.Text=if($count -gt 0){(Get-UiText 'draft.count' '{0} local draft(s) from this niche') -f $count}else{Get-UiText 'draft.create.hint' ''}
    }
}
function Invoke-DiscoverCreateDraft {
    $n=$null; if($null -ne $DiscoverNicheList){$n=$DiscoverNicheList.SelectedItem}
    if($null -eq $n){Show-Error (Get-UiText 'draft.need.niche' 'Select a niche first.');return}
    if($null -eq $script:DiscoverSnapshot -or ($script:OfflineMode-and[string](Get-PropertyValue $script:DiscoverSnapshot 'origin')-ne'local_import')){Show-Error (Get-UiText 'draft.need.live' 'Live research is required.');return}
    if(($script:Dirty -or $script:PublicationDirty) -and -not (Confirm 'Discard unsaved creative/publication edits and open another concept?')){return}
    try {
        $r=New-ResearchConceptDraft $n $script:DiscoverSnapshot $script:DiscoverLoadedAt ([string]$script:BackendVersion)
        $key=[string](Get-PropertyValue $r.draft 'concept_key')
        Write-AppLog 'INFO' ('Research draft '+$(if($r.created){'created'}else{'reused'})+': '+$key+' niche='+[string](Get-PropertyValue (Get-PropertyValue $r.draft 'provenance') 'niche_identity'))
        Refresh-ResearchDraftQueue
        $script:Dirty=$false; $script:PublicationDirty=$false
        $script:ProductSection='ideas'
        Open-ResearchDraftItem ([pscustomobject]@{concept_key=$key}) $true
        $StatusText.Text=if($r.created){(Get-UiText 'draft.created' 'Draft created: {0}') -f [string](Get-PropertyValue $r.draft 'niche_name')}else{(Get-UiText 'draft.exists' 'A draft from this exact research already exists: {0}') -f [string](Get-PropertyValue $r.draft 'niche_name')}
    } catch { Write-AppLog 'ERROR' ('Research draft creation failed: '+$_.Exception.Message); Show-Error ('Draft was not created: '+$_.Exception.Message) }
}

function Restore-DynamicSurfacesAfterLocale {
    try{ if(Get-Command Update-ListingHints -ErrorAction SilentlyContinue){ Update-ListingHints } }catch{}
    if($script:ProductSection -eq 'portfolio'){try{Update-PortfolioPipelineSurface}catch{}}
    # Apply-StaticLocaleUi rewrites every TextBlock with the text captured at startup ("—", "Select a niche"...).
    # Re-render the live surfaces from current data so a language switch never shows stale placeholders.
    if($null -ne $script:DiscoverSnapshot -and $null -ne $DiscoverNicheList){
        $selId=''; try{$cur=$DiscoverNicheList.SelectedItem;if($null -ne $cur){$i=Get-DiscoverNicheIdentity $cur;if($null -ne $i){$selId=[string]$i.value}}}catch{}
        Render-DiscoverSnapshot $script:DiscoverSnapshot $selId
        if($null -ne $DiscoverStatusText -and $null -ne $script:DiscoverLoadedAt){$DiscoverStatusText.Text=('{0} · {1:HH:mm} UTC' -f (Get-UiText 'discover.ready' 'Live research loaded'),[datetime]$script:DiscoverLoadedAt)}
        Update-DiscoverDraftControls
    }
    if((Test-CurrentIsResearchDraft) -and -not ($script:Dirty -or $script:PublicationDirty)){
        $key=[string](Get-PropertyValue $script:Current.concept 'concept_key'); $section=$script:ProductSection
        Open-ResearchDraftItem ([pscustomobject]@{concept_key=$key}) $true
        if($section -ne $script:ProductSection -and $section -in @('discover','home','portfolio','performance')){Show-ProductSection $section}
    }
}
