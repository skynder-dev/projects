# Explicit local owner review receipt only; never owner/product/artwork approval.
function Get-ForgeSemanticReviewBinding($Draft) {
 $hold=Get-PropertyValue $Draft 'semantic_review_hold';if($null-eq$hold){throw 'SEMANTIC_REVIEW_HOLD_REQUIRED'}
 $fields=Get-ResearchDraftCurrentFields $Draft;$concept=ConvertTo-ResearchDraftConcept $Draft
 $source=[string](Get-PropertyValue (Get-PropertyValue $Draft.provenance 'research_packet') 'source_sha256')
 if($source-cnotmatch'^[0-9a-f]{64}$'){throw 'SEMANTIC_REVIEW_SOURCE_REQUIRED'}
 return [pscustomobject][ordered]@{concept_key=$Draft.concept_key;revision_id=$Draft.current_revision_id;revision_hash=$Draft.current_revision_hash;full_brief_sha256=(Get-ForgeBriefSha256 (New-ForgeGenerationBriefSnapshot $concept));source_sha256=$source;hold_sha256=(Get-ForgeBriefSha256 $hold)}
}
function Get-ForgeSemanticReviewSnapshot([string]$ConceptKey) {
 if($script:Dirty-or$script:PublicationDirty){throw 'SEMANTIC_REVIEW_UNSAVED_EDITS'}
 $s=Read-LocalCoreState;$d=Get-ResearchDraft $ConceptKey $s;if($null-eq$d){throw 'SEMANTIC_REVIEW_DRAFT_MISSING'}
 $binding=Get-ForgeSemanticReviewBinding $d
 if($null-ne$script:Current-and[string]$script:Current.concept.concept_key-cne$ConceptKey){throw 'SEMANTIC_REVIEW_VISIBLE_CONTEXT_CHANGED'}
 $previousCurrent=$script:Current;$previousSnapshot=$script:DiscoverSnapshot
 try{$script:Current=[pscustomobject]@{concept=(ConvertTo-ResearchDraftConcept $d);draft=$d;local_research_draft=$true};$script:DiscoverSnapshot=$null;$evidence=Get-ResearchEvidenceContext;if($null-eq$evidence-or$evidence.packet.source_sha256-cne$binding.source_sha256){throw 'SEMANTIC_REVIEW_SOURCE_CHANGED'};Assert-ForgeCanonicalHeldFields (Get-ResearchDraftCurrentFields $d) $evidence}finally{$script:Current=$previousCurrent;$script:DiscoverSnapshot=$previousSnapshot}
 return [pscustomobject]@{schema='forge.semantic_review_snapshot.v1';binding=$binding;binding_sha256=(Get-ForgeBriefSha256 $binding);state_revision=$s.state_revision;last_write_id=$s.last_write_id;full_saved_brief=(New-ForgeGenerationBriefSnapshot (ConvertTo-ResearchDraftConcept $d));source_records=$evidence.selected_records;original_hold=$d.semantic_review_hold;meaning_verified=$false}
}
function Record-ForgeSemanticReview {
 param([Parameter(Mandatory=$true)]$Snapshot,[Parameter(Mandatory=$true)][ValidateSet('NEEDS_EDIT','REJECTED','REVIEWED_FOR_NEXT_REVIEW_STAGE')][string]$Outcome,[Parameter(Mandatory=$true)][string]$OwnerNote,[Parameter(Mandatory=$true)][string]$OwnerIntent)
 if($OwnerIntent-cne'RECORD_EXPLICIT_SEMANTIC_REVIEW'){throw 'SEMANTIC_REVIEW_EXPLICIT_INTENT_REQUIRED'}
 if([string]::IsNullOrWhiteSpace($OwnerNote)-or$OwnerNote.Length-gt1000){throw 'SEMANTIC_REVIEW_NOTE_REQUIRED'}
 if($Snapshot.schema-cne'forge.semantic_review_snapshot.v1'-or$Snapshot.binding_sha256-cne(Get-ForgeBriefSha256 $Snapshot.binding)){throw 'SEMANTIC_REVIEW_SNAPSHOT_INVALID'}
 $fresh=Get-ForgeSemanticReviewSnapshot ([string]$Snapshot.binding.concept_key)
 if($fresh.binding_sha256-cne$Snapshot.binding_sha256-or$fresh.state_revision-ne$Snapshot.state_revision-or$fresh.last_write_id-cne$Snapshot.last_write_id){throw 'SEMANTIC_REVIEW_STALE: saved revision/source/HOLD/state changed'}
 $s=Read-LocalCoreState
 if($s.state_revision-ne$Snapshot.state_revision-or$s.last_write_id-cne$Snapshot.last_write_id){throw 'SEMANTIC_REVIEW_STALE: concurrent state changed'}
 $d=Get-ResearchDraft $Snapshot.binding.concept_key $s
 if((Get-ForgeBriefSha256 (Get-ForgeSemanticReviewBinding $d))-cne$Snapshot.binding_sha256){throw 'SEMANTIC_REVIEW_STALE: draft changed'}
 $receipt=[pscustomobject]@{schema='forge.semantic_review_receipt.v1';id=('semreview-'+[guid]::NewGuid().ToString('N'));binding=$fresh.binding;binding_sha256=$fresh.binding_sha256;outcome=$Outcome;owner_note=$OwnerNote;owner_intent=$OwnerIntent;reviewed_at=[datetime]::UtcNow.ToString('o');origin='explicit_local_owner_review';machine_meaning_verified=$false;rights_verified=$false;demand_verified=$false;print_quality_verified=$false;generation_authorized=$false;publication_authorized=$false}
 Set-PlainArrayProperty $d 'semantic_reviews' (@(Get-PropertyValue $d 'semantic_reviews')+@($receipt))
 Write-LocalCoreState $s
 return [pscustomobject]@{recorded=$true;receipt=$receipt;owner_or_artwork_approval_created=$false}
}
function Test-ForgeSemanticReviewCurrent($Draft) {
 # Caller-supplied state is never authoritative for current receipt or brief.
 $suppliedBinding=Get-ForgeSemanticReviewBinding $Draft
 $state=Read-LocalCoreState;$persisted=Get-ResearchDraft ([string]$Draft.concept_key) $state
 if($null-eq$persisted){return $false}
 $binding=Get-ForgeSemanticReviewBinding $persisted;$sha=Get-ForgeBriefSha256 $binding
 if((Get-ForgeBriefSha256 $suppliedBinding)-cne$sha){return $false}
 $reviews=@(Get-PropertyValue $persisted 'semantic_reviews'|Where-Object{$null-ne$_})
 if(!$reviews.Count){return $false};$last=$reviews[-1]
 if($last.schema-cne'forge.semantic_review_receipt.v1'-or$last.outcome-cne'REVIEWED_FOR_NEXT_REVIEW_STAGE'-or$last.owner_intent-cne'RECORD_EXPLICIT_SEMANTIC_REVIEW'-or[string]::IsNullOrWhiteSpace($last.owner_note)-or$last.binding_sha256-cne$sha-or(Get-ForgeBriefSha256 $last.binding)-cne$sha){return $false}
 $archive=Join-Path (Join-Path $script:StateRoot 'research-import-v1') ($binding.source_sha256+'.source.json')
 if((Get-FileSha256Hex $archive)-cne$binding.source_sha256){return $false}
 $fresh=Get-ForgeSemanticReviewSnapshot $persisted.concept_key
 # Snapshot read revalidates source/freshness/guards. Refuse a concurrent write
 # between receipt read and fresh snapshot, including a new negative receipt.
 if($fresh.binding_sha256-cne$sha-or$fresh.state_revision-ne$state.state_revision-or$fresh.last_write_id-cne$state.last_write_id){return $false}
 return $true
}
