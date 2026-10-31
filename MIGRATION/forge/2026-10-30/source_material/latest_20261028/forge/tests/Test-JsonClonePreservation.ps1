# PROPOSAL ONLY: not executed during preparation. Run only in a separately
# authorized, already-installed PowerShell 7.5+ runner, in a fresh -NoProfile
# process. No installation, network, model, real workspace or approval issuance.
# An external supervisor must enforce a timeout and require: process exit 0,
# a new receipt for this invocation, receipt.status == PASS, and matching source
# hashes. Timeout, crash, nonzero exit, missing receipt, BLOCKED or FAIL fails the
# run. A killed host cannot guarantee a receipt. The switch below acknowledges
# that requirement; it does not implement or prove external supervision.
# Scope: five clone sites in four actual functions, with real canonical JSON,
# spec and content/brief hash helpers. Missing bootstrap and owner-language
# boundaries are explicitly labeled below. This is NOT a full module import,
# strict-parser, language-review, approval, source-capture or full-stack test.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ModuleRoot,
    [switch]$ExternalSupervisorConfirmed
)

$ErrorActionPreference = 'Stop'
$script:ScopeLabel = 'five JSON clone sites; actual extracted functions; synthetic unapproved fixtures'
$script:Checks = New-Object 'System.Collections.Generic.List[object]'
$script:Sources = [ordered]@{}
$script:LoadedFunctions = New-Object 'System.Collections.Generic.List[object]'
$script:Controls = New-Object 'System.Collections.Generic.List[object]'
$script:CheckCount = 0
$script:LanguageReviewCalls = 0
$script:ExpectedFunctionCount = 15
$started = [DateTime]::UtcNow.ToString('o')
$runId = [Guid]::NewGuid().ToString('N')
$runRoot = Join-Path ([IO.Path]::GetTempPath()) ('forge-json-clone-preservation-' + $runId)
if (Test-Path -LiteralPath $runRoot) { throw 'Fresh test root already exists; refusing reuse.' }
[void][IO.Directory]::CreateDirectory($runRoot)
if ((Get-Item -LiteralPath $runRoot -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Fresh test root is redirected; refusing use.'
}
$receiptPath = Join-Path $runRoot 'receipt.json'
$blocked = $false
$status = 'FAIL'
$runtime = [ordered]@{
    ps_version=[string]$PSVersionTable.PSVersion; ps_edition=[string]$PSVersionTable.PSEdition;
    platform=[Environment]::OSVersion.Platform.ToString(); timezone=[TimeZoneInfo]::Local.Id;
    convert_from_json_command_type=''; convert_from_json_module=''; date_kind_available=$false;
    external_supervisor_acknowledged=[bool]$ExternalSupervisorConfirmed
}

function Get-TestBytesHash([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Get-TestTextHash([string]$Text) { return Get-TestBytesHash ([Text.Encoding]::UTF8.GetBytes($Text)) }
function Get-TestJson($Value) { return ConvertTo-Json -InputObject $Value -Depth 60 -Compress }
function Assert-Test([bool]$Condition, [string]$Message) {
    $script:CheckCount++
    if (!$Condition) { throw ('CHECK_FAILED: ' + $Message) }
}
function Invoke-TestCase([string]$Name, [scriptblock]$Body) {
    try {
        & $Body
        $script:Checks.Add([pscustomobject]@{name=$Name; status='PASS'; detail=''})
        Write-Host ('PASS: ' + $Name)
    } catch {
        $script:Checks.Add([pscustomobject]@{name=$Name; status='FAIL'; detail=$_.Exception.Message})
        Write-Host ('FAIL: ' + $Name + ': ' + $_.Exception.Message)
    }
}
function Get-TestThrownMessage([scriptblock]$Body) {
    try { $null = & $Body } catch { return $_.Exception.Message }
    throw 'CHECK_FAILED: expected an exception, but the call returned.'
}
function Assert-TestValuePreserved($Expected, $Actual, [string]$Path) {
    if ($null -eq $Expected) {
        Assert-Test ($null -eq $Actual) ($Path + ': null remains null')
    } elseif ($Expected -is [string]) {
        Assert-Test ($Actual -is [string]) ($Path + ': JSON string must remain a string, not a date or number')
        Assert-Test ($Expected -ceq $Actual) ($Path + ': exact case-sensitive string lexeme')
        $beforeBytes=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Expected))
        $afterBytes=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$Actual))
        Assert-Test ($beforeBytes -ceq $afterBytes) ($Path + ': exact UTF-8 string bytes')
    } elseif ($Expected -is [bool]) {
        Assert-Test ($Actual -is [bool] -and $Expected -eq $Actual) ($Path + ': boolean type and value')
    } elseif ($Expected -is [Array]) {
        Assert-Test ($Actual -is [Array]) ($Path + ': array shape, including empty and singleton arrays')
        Assert-Test ($Expected.Count -eq $Actual.Count) ($Path + ': array length')
        for ($i=0; $i -lt $Expected.Count; $i++) {
            Assert-TestValuePreserved $Expected[$i] $Actual[$i] ($Path + '[' + $i + ']')
        }
    } elseif ($Expected -is [Collections.IDictionary] -or $Expected -is [pscustomobject]) {
        Assert-Test ($Actual -is [Collections.IDictionary] -or $Actual -is [pscustomobject]) ($Path + ': object shape')
        $expectedKeys=@(if ($Expected -is [Collections.IDictionary]) { $Expected.Keys } else { $Expected.PSObject.Properties.Name })
        $actualKeys=@(if ($Actual -is [Collections.IDictionary]) { $Actual.Keys } else { $Actual.PSObject.Properties.Name })
        Assert-Test ($expectedKeys.Count -eq $actualKeys.Count) ($Path + ': property count')
        foreach ($key in $expectedKeys) {
            Assert-Test ($actualKeys -ccontains [string]$key) ($Path + ': exact property name ' + $key)
            Assert-TestValuePreserved (Get-ForgeBriefValue $Expected $key) (Get-ForgeBriefValue $Actual $key) ($Path + '.' + $key)
        }
    } else {
        $isNumber=($Actual -is [byte] -or $Actual -is [sbyte] -or $Actual -is [int16] -or $Actual -is [uint16] -or $Actual -is [int32] -or $Actual -is [uint32] -or $Actual -is [int64] -or $Actual -is [uint64] -or $Actual -is [single] -or $Actual -is [double] -or $Actual -is [decimal])
        Assert-Test $isNumber ($Path + ': number must not become a string, date or boolean')
        Assert-Test ([decimal]$Expected -eq [decimal]$Actual) ($Path + ': numeric value')
    }
}
function Assert-TestCanonicalEqual($Expected, $Actual, [string]$Message) {
    Assert-TestValuePreserved $Expected $Actual $Message
    Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $Expected) -ceq (ConvertTo-ForgeBriefCanonicalJson $Actual)) ($Message + ': real canonical JSON bytes')
    Assert-Test ((Get-ForgeBriefSha256 $Expected) -ceq (Get-ForgeBriefSha256 $Actual)) ($Message + ': real canonical SHA-256')
}

# Explicit missing-bootstrap adapters, not replacements for production spec,
# canonicalization, revision hash, brief hash or the functions under test.
# The original Get-PropertyValue/Get-ByteSha256Hex bootstrap bodies are absent
# from this authorized source set. Property lookup delegates to the ACTUAL
# extracted Get-ForgeBriefValue; byte hashing is a standard SHA-256 test adapter.
function Get-PropertyValue($Object, [string]$Name) { return ,(Get-ForgeBriefValue $Object $Name) }
function Get-ByteSha256Hex([byte[]]$Bytes) { return Get-TestBytesHash $Bytes }
function Get-ForgeOwnerLanguageReview($Fields) {
    # Missing OwnerLanguage boundary only: no language-review validity claim.
    $script:LanguageReviewCalls++
    return [pscustomobject]@{schema='test.synthetic_language_boundary.v1'; status='UNREVIEWED'; approved=$false}
}
# Unexpected authority/save paths fail rather than silently acquire authority.
function Assert-ForgeRejectedSaveBinding { throw 'TEST_BOUNDARY_STOP: rejected-save binding is outside this test' }
function Read-ForgeRejectedProposal { throw 'TEST_BOUNDARY_STOP: source/proposal reads are forbidden' }
function Assert-ForgeAIFieldsForSave { throw 'TEST_BOUNDARY_STOP: AI validation is outside this test' }

function New-TestDateFixture {
    return [pscustomobject][ordered]@{
        utc='2026-02-03T04:05:06Z'; positive_offset='2026-02-03T04:05:06.1234000+05:45';
        negative_offset='2026-02-03T04:05:06.1200-07:30'; fractional_utc='2026-02-03T04:05:06.1234567Z';
        explicit_zero_offset='2026-02-03T04:05:06.0000000+00:00'; no_zone='2026-02-03T04:05:06.1200';
        date_only='2026-02-03'; number=42; numeric_string='42'; decimal_number=17.25;
        large_integer=[long]9007199254740991; bool_value=$false; bool_string='false'; null_value=$null;
        nested=[pscustomobject][ordered]@{
            dates=[object[]]@('2026-02-03T04:05:06.1234000+05:45','2026-02-03T04:05:06Z','2026-02-03T04:05:06.1200-07:30');
            sequence=[object[]]@(42,'42',$false,'false',$null,[pscustomobject]@{at='2026-02-03T04:05:06.1234567Z'});
            singleton=[object[]]@('2026-02-03T04:05:06.0000000+00:00'); empty=[object[]]@()
        }
    }
}
function New-TestFields {
    return [pscustomobject][ordered]@{
        concept_key='rd-synthetic-date-clone'; niche_name='2026-02-03T04:05:06.1234000+05:45';
        title='2026-02-03T04:05:06Z'; hook='SYNTHETIC UNAPPROVED';
        concept_text='Synthetic clone fixture, not production input.'; target_buyer='test-only';
        purchase_reason='not an approved decision'; differentiation='synthetic';
        visual_direction_text='No generation or publication is authorized.'; production_spec=(New-TestDateFixture)
    }
}
function New-TestExpectedBrief($Fields) {
    # Independent expected envelope, never a call to the snapshot function.
    return [pscustomobject][ordered]@{
        schema='forge.approved_generation_brief.v1'; concept_key=$Fields.concept_key;
        niche_name=$Fields.niche_name; title=$Fields.title; hook=$Fields.hook; concept_text=$Fields.concept_text;
        target_buyer=$Fields.target_buyer; purchase_reason=$Fields.purchase_reason;
        differentiation=$Fields.differentiation; visual_direction_text=$Fields.visual_direction_text;
        production_spec=$Fields.production_spec
    }
}
function New-TestLocalConcept {
    $checks=New-LocalCoreChecks
    $checks.ip.state='blocked'
    $checks.ip.note='2026-02-03T04:05:06.1234000+05:45'
    $checks.ip.evidence_refs=@('synthetic-not-evidence','2026-02-03T04:05:06.1200-07:30')
    Add-OrSetProperty $checks.ip 'synthetic_fixture' (New-TestDateFixture)
    return [pscustomobject][ordered]@{
        concept_key='rd-synthetic-date-clone'; source_revision_id='synthetic-unapproved-revision'; source_revision_hash=('a'*64);
        generation_brief_snapshot=(New-TestExpectedBrief (New-TestFields)); generation_brief_sha256=('b'*64);
        publication=[pscustomobject][ordered]@{listing_title='SYNTHETIC NOT FOR PUBLICATION'; saved_at='2026-02-03T04:05:06.1200-07:30'; fixture=(New-TestDateFixture)};
        checks=$checks;
        active_acceptance=[pscustomobject][ordered]@{schema='test.synthetic_unapproved_acceptance.v1'; approved=$false; at='2026-02-03T04:05:06.0000000+00:00'; fixture=(New-TestDateFixture)};
        brief_approval=[pscustomobject][ordered]@{schema='test.synthetic_unapproved.v1'; approval_id='synthetic-not-an-approval'; decision='NOT_APPROVED'; explicit_owner_action=$false; idea_approved=$false; design_concept_approved=$false; at='2026-02-03T04:05:06.1234000+05:45'; fixture=(New-TestDateFixture)};
        owner_decision='EDIT'; owner_decision_revision_id='synthetic-unapproved-revision'; owner_decision_revision_hash=('a'*64); owner_decision_at='2026-02-03T04:05:06.1234567Z';
        artwork=[object[]]@([pscustomobject][ordered]@{id='synthetic-revocation-control'; accepted=$true; source_revision_hash=('a'*64); integrity_check=[pscustomobject]@{synthetic=$true}; at='2026-02-03T04:05:06.1200-07:30'; fixture=(New-TestDateFixture)});
        packages=[object[]]@([pscustomobject][ordered]@{id='synthetic-revocation-control'; valid=$true; at='2026-02-03T04:05:06.1234000+05:45'; fixture=(New-TestDateFixture)})
    }
}
function New-TestExpectedHistoryContext($Lc) {
    # Property order matches the source payload so its NON-canonical context
    # hash can be checked before/after cloning with the real string hash helper.
    return [pscustomobject][ordered]@{
        concept_key=$Lc.concept_key; source_revision_id=$Lc.source_revision_id; source_revision_hash=$Lc.source_revision_hash;
        brief_snapshot=$Lc.generation_brief_snapshot; brief_sha256=$Lc.generation_brief_sha256;
        publication=$Lc.publication; checks=$Lc.checks; active_acceptance=$Lc.active_acceptance;
        owner_decision=$Lc.owner_decision; owner_decision_revision_id=$Lc.owner_decision_revision_id;
        owner_decision_revision_hash=$Lc.owner_decision_revision_hash; owner_decision_at=$Lc.owner_decision_at
    }
}
function New-TestExpectedLegacy($Lc) {
    return [pscustomobject][ordered]@{
        schema='forge.legacy_v1_content.v1'; history_only=$true; artwork=$Lc.artwork; packages=$Lc.packages;
        source_revision_id=$Lc.source_revision_id; source_revision_hash=$Lc.source_revision_hash;
        publication=$Lc.publication; checks=$Lc.checks; active_acceptance=$Lc.active_acceptance;
        brief_approval=$Lc.brief_approval; owner_decision=$Lc.owner_decision;
        owner_decision_revision_id=$Lc.owner_decision_revision_id; owner_decision_revision_hash=$Lc.owner_decision_revision_hash;
        owner_decision_at=$Lc.owner_decision_at
    }
}
function Get-TestObjectExcept($Value, [string[]]$Exclude) {
    $out=[ordered]@{}
    foreach ($property in $Value.PSObject.Properties) {
        if ($Exclude -cnotcontains $property.Name) { $out[$property.Name]=$property.Value }
    }
    return [pscustomobject]$out
}
function Get-TestObservedScalar($Value) {
    $kind=if ($null -eq $Value) { 'null' } else { $Value.GetType().FullName }
    $text=if ($null -eq $Value) { $null } else { [string]$Value }
    $roundtrip=if ($Value -is [DateTime] -or $Value -is [DateTimeOffset]) { $Value.ToString('o',[Globalization.CultureInfo]::InvariantCulture) } else { $null }
    return [pscustomobject]@{
        clr_type=$kind; actual_text=$text; date_roundtrip_text=$roundtrip;
        canonical_json=(ConvertTo-ForgeBriefCanonicalJson $Value);
        actual_text_utf8_sha256=$(if ($null -eq $text) { $null } else { Get-TestTextHash $text })
    }
}

try {
    $fromJson=Get-Command ConvertFrom-Json -ErrorAction Stop
    $toJson=Get-Command ConvertTo-Json -ErrorAction Stop
    $runtime.convert_from_json_command_type=[string]$fromJson.CommandType
    $runtime.convert_from_json_module=$fromJson.ModuleName
    $runtime.date_kind_available=$fromJson.Parameters.ContainsKey('DateKind')
    if (!$ExternalSupervisorConfirmed) {
        $blocked=$true; throw 'BLOCKED: a separately authorized externally supervised runner is required.'
    }
    if ($PSVersionTable.PSVersion -lt [version]'7.5' -or !$runtime.date_kind_available) {
        $blocked=$true; throw 'BLOCKED: installed PowerShell 7.5+ and ConvertFrom-Json -DateKind are required. No fallback or installation is permitted.'
    }
    if ($fromJson.CommandType -ne 'Cmdlet' -or $fromJson.ModuleName -cne 'Microsoft.PowerShell.Utility' -or $toJson.CommandType -ne 'Cmdlet' -or $toJson.ModuleName -cne 'Microsoft.PowerShell.Utility') {
        $blocked=$true; throw 'BLOCKED: JSON cmdlets are shadowed or are not the installed Microsoft.PowerShell.Utility cmdlets.'
    }
    Assert-Test ($runtime.date_kind_available) 'Installed DateKind parameter is available.'
    $ModuleRoot=(Resolve-Path -LiteralPath $ModuleRoot).ProviderPath
    $copyRoot=Join-Path $runRoot 'exact-module-copies'
    [void][IO.Directory]::CreateDirectory($copyRoot)
    $targets=[ordered]@{
        'Forge.BriefApproval.ps1'=@('Get-ForgeBriefValue','Get-ForgeProductionSpec','ConvertTo-ForgeBriefCanonicalJson','Get-ForgeBriefSha256','New-ForgeGenerationBriefSnapshot');
        'Forge.ResearchDrafts.ps1'=@('Get-ResearchDraftContentHash','New-ResearchDraftRevision');
        'Forge.LocalCore.ps1'=@('Get-StringSha256Hex','Add-OrSetProperty','New-LocalCoreState','New-LocalCoreCheckRecord','New-LocalCoreChecks','Invalidate-LocalCorePackages','Preserve-ForgeLocalReviewHistory','Convert-LocalCoreStateToV2')
    }
    foreach ($fileName in $targets.Keys) {
        $path=Join-Path $ModuleRoot $fileName
        $item=Get-Item -LiteralPath $path -Force
        Assert-Test ($item -is [IO.FileInfo] -and !($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) ('Ordinary source file: '+$fileName)
        $bytes=[IO.File]::ReadAllBytes($path)
        $copyPath=Join-Path $copyRoot $fileName
        [IO.File]::WriteAllBytes($copyPath,$bytes)
        $script:Sources[$fileName]=[pscustomobject]@{
            path=$path; before_sha256=(Get-TestBytesHash $bytes); after_sha256='';
            copied_path=$copyPath; copied_before_sha256=(Get-TestBytesHash ([IO.File]::ReadAllBytes($copyPath))); copied_after_sha256=''
        }
        Assert-Test ($script:Sources[$fileName].before_sha256 -ceq $script:Sources[$fileName].copied_before_sha256) ('Byte-exact owned source copy: '+$fileName)
        $tokens=$null; $parseErrors=$null
        $ast=[Management.Automation.Language.Parser]::ParseFile($copyPath,[ref]$tokens,[ref]$parseErrors)
        Assert-Test (@($parseErrors).Count -eq 0) ('Source parses: '+$fileName)
        foreach ($name in $targets[$fileName]) {
            $definitions=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object {$_.Name -ceq $name})
            Assert-Test ($definitions.Count -eq 1) ('Exactly one source function: '+$name)
            $definition=$definitions[0]
            # Evaluate only the exact named function definition from the owned
            # copy, NEVER the module's top-level bootstrap/dot-source chain.
            . ([scriptblock]::Create($definition.Extent.Text))
            $loaded=Get-Command -Name $name -CommandType Function
            Assert-Test ($loaded.ScriptBlock.Ast.Extent.Text -ceq $definition.Body.Extent.Text) ('Exact source body loaded: '+$name)
            $script:LoadedFunctions.Add([pscustomobject]@{
                name=$name; source=$path; parsed_owned_copy=$copyPath;
                definition_sha256=(Get-TestTextHash $definition.Extent.Text); body_sha256=(Get-TestTextHash $loaded.ScriptBlock.Ast.Extent.Text);
                source_start_line=$definition.Extent.StartLineNumber
            })
        }
    }
    Assert-Test ($script:LoadedFunctions.Count -eq $script:ExpectedFunctionCount) 'All fifteen actual source functions are loaded.'
    # Required bootstrap constants are copied from ResearchDrafts, not evaluated
    # via its top-level statements. These are fixture-domain bootstrap values.
    $script:ResearchDraftContentFields=@('title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text')
    $script:ResearchDraftKeyPrefix='rd-'

    Invoke-TestCase 'Real canonical/spec/hash helpers and bootstrap SHA adapter have known vectors' {
        $value=[pscustomobject][ordered]@{b='7'; a=7}
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $value) -ceq '{"a":7,"b":"7"}') 'Canonical property order and number/string distinction.'
        Assert-Test ((Get-ForgeBriefSha256 $value) -ceq '7c9d87a50894a7f0771bc8ce8eb3577c86fd93db3938820e7c9146f492af4d75') 'Real brief SHA-256 known vector.'
        Assert-Test ((Get-StringSha256Hex 'abc') -ceq 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad') 'Actual string helper plus explicitly missing-bootstrap byte adapter known vector.'
        $fields=New-TestFields
        Assert-Test ([object]::ReferenceEquals((Get-ForgeProductionSpec $fields),$fields.production_spec)) 'Real spec accessor is in use.'
    }
    Invoke-TestCase 'Site 1: revision spec clone preserves lexemes, types, order, input and actual revision hash' {
        $fields=New-TestFields; $before=ConvertTo-ForgeBriefCanonicalJson $fields
        $expectedHash=Get-ResearchDraftContentHash $fields.concept_key $fields
        $beforeReviewCalls=$script:LanguageReviewCalls
        $revision=New-ResearchDraftRevision $fields.concept_key 3 $fields 'synthetic_owner_edit_unapproved'
        Assert-TestCanonicalEqual $fields.production_spec $revision.production_spec 'revision.production_spec'
        Assert-Test ($revision.revision_hash -ceq $expectedHash) 'Stored revision hash equals pre-clone real content hash.'
        Assert-Test ($revision.revision_hash -ceq (Get-ResearchDraftContentHash $fields.concept_key $revision)) 'Stored revision hash equals post-clone recomputation using the real helper.'
        Assert-Test ($revision.revision_id -ceq ('rdrev-synthetic-date-clone-3-'+$expectedHash.Substring(0,12))) 'Revision identity retains the expected hash binding.'
        Assert-Test ($script:LanguageReviewCalls -eq $beforeReviewCalls+1 -and !$revision.owner_language_review.approved) 'Only the labeled UNREVIEWED language boundary ran.'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $fields) -ceq $before) 'Revision creation does not mutate input.'
        Assert-Test (![object]::ReferenceEquals($fields.production_spec,$revision.production_spec)) 'Spec root is detached.'
        $revision.production_spec.nested.dates[0]='changed-only-in-clone'
        $revision.production_spec.nested.sequence[5].at='changed-only-in-clone'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $fields) -ceq $before) 'Nested clone edits do not alias input objects or arrays.'
    }
    Invoke-TestCase 'Site 2: brief clone preserves the exact expected envelope and real brief hash' {
        $fields=New-TestFields; $before=ConvertTo-ForgeBriefCanonicalJson $fields
        $expected=New-TestExpectedBrief $fields
        $expectedJson=ConvertTo-ForgeBriefCanonicalJson $expected
        $expectedHash=Get-ForgeBriefSha256 $expected
        $brief=New-ForgeGenerationBriefSnapshot $fields
        Assert-TestCanonicalEqual $expected $brief 'brief'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $brief) -ceq $expectedJson) 'Brief canonical bytes equal the exact expected pre-clone envelope.'
        Assert-Test ((Get-ForgeBriefSha256 $brief) -ceq $expectedHash) 'Brief hash is exactly the expected pre-clone hash.'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $fields) -ceq $before) 'Brief creation does not mutate input.'
        Assert-Test (![object]::ReferenceEquals($fields.production_spec.nested,$brief.production_spec.nested)) 'Nested brief spec is detached.'
        $brief.production_spec.nested.dates[1]='changed-only-in-brief'
        $brief.production_spec.nested.sequence[5].at='changed-only-in-brief'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $fields) -ceq $before) 'Nested brief edits do not alias input.'
    }
    Invoke-TestCase 'Site 3: history payload clone preserves all values and exact context/id hashes' {
        $lc=New-TestLocalConcept; $before=ConvertTo-ForgeBriefCanonicalJson $lc
        $expected=New-TestExpectedHistoryContext (New-TestLocalConcept)
        $expectedContextHash=Get-StringSha256Hex (Get-TestJson $expected)
        $expectedApprovalHash=Get-StringSha256Hex (Get-TestJson $lc.brief_approval)
        $expectedId='review-'+(Get-StringSha256Hex ($expectedContextHash+'|'+$expectedApprovalHash))
        Assert-Test (Preserve-ForgeLocalReviewHistory $lc 'synthetic_snapshot_only') 'A new synthetic historical entry is captured.'
        Assert-Test ($lc.review_history -is [Array] -and $lc.review_history.Count -eq 1) 'History remains an array.'
        $entry=$lc.review_history[0]
        Assert-Test ($entry.history_only -is [bool] -and $entry.history_only -and $entry.schema -ceq 'forge.local_review_history.v1') 'Historical marker is explicit, not authority.'
        Assert-TestCanonicalEqual $expected (Get-TestObjectExcept $entry.payload @('brief_approval')) 'history.payload'
        Assert-Test ($entry.context_sha256 -ceq $expectedContextHash -and $entry.id -ceq $expectedId) 'History context and identity hash bind the exact uncoerced payload and approval fixture.'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson (Get-TestObjectExcept $lc @('review_history'))) -ceq $before) 'Only the documented review_history append changes the input root.'
        $lc.publication.fixture.nested.dates[0]='changed-current-publication'
        $lc.generation_brief_snapshot.production_spec.nested.sequence[5].at='changed-current-brief'
        Assert-TestCanonicalEqual $expected (Get-TestObjectExcept $entry.payload @('brief_approval')) 'history remains detached after current-input edits'
    }
    Invoke-TestCase 'Site 4: historical unapproved approval clone preserves values without granting authority' {
        $lc=New-TestLocalConcept; $expected=(New-TestLocalConcept).brief_approval
        $beforeApproval=ConvertTo-ForgeBriefCanonicalJson $lc.brief_approval
        Assert-Test (Preserve-ForgeLocalReviewHistory $lc 'synthetic_approval_copy_only') 'Synthetic history entry created.'
        $saved=$lc.review_history[0].payload.brief_approval
        Assert-TestCanonicalEqual $expected $saved 'history.payload.brief_approval'
        Assert-Test ($saved.schema -ceq 'test.synthetic_unapproved.v1' -and $saved.decision -ceq 'NOT_APPROVED' -and !$saved.explicit_owner_action -and !$saved.idea_approved -and !$saved.design_concept_approved) 'No real approval record or approval authority is manufactured.'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $lc.brief_approval) -ceq $beforeApproval) 'Capturing history does not mutate the current approval fixture.'
        Assert-Test (![object]::ReferenceEquals($saved.fixture.nested,$lc.brief_approval.fixture.nested)) 'Approval nested objects are detached.'
        $saved.fixture.nested.dates[0]='changed-only-in-history'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $lc.brief_approval) -ceq $beforeApproval) 'Editing historical approval does not alias current input.'
    }
    Invoke-TestCase 'History duplicate capture preserves existing bytes and does not create authority' {
        $lc=New-TestLocalConcept
        Assert-Test (Preserve-ForgeLocalReviewHistory $lc 'synthetic_first') 'Initial history captured.'
        $before=ConvertTo-ForgeBriefCanonicalJson $lc
        Assert-Test (!(Preserve-ForgeLocalReviewHistory $lc 'synthetic_duplicate')) 'Unchanged input deduplicates.'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $lc) -ceq $before) 'Duplicate capture does not change existing history or current values.'
    }
    foreach ($badHistory in @('scalar','invalid_entry')) {
        Invoke-TestCase ('History malformed-input fail-closed guard: '+$badHistory) {
            $lc=New-TestLocalConcept
            $bad=if ($badHistory -ceq 'scalar') { 'not-an-array' } else { [object[]]@([pscustomobject]@{schema='test.invalid_history'; history_only=$false}) }
            # Preserve singleton array shape through assignment explicitly.
            if ($badHistory -ceq 'invalid_entry') { $bad=[object[]]@([pscustomobject]@{schema='test.invalid_history'; history_only=$false}) }
            Add-OrSetProperty $lc 'review_history' $bad
            $before=ConvertTo-ForgeBriefCanonicalJson $lc
            $message=Get-TestThrownMessage { Preserve-ForgeLocalReviewHistory $lc 'must_not_overwrite' }
            $expectedMessage=if ($badHistory -ceq 'scalar') { 'Saved local review history is malformed;' } else { 'Saved local review history could not be verified;' }
            Assert-Test ($message.StartsWith($expectedMessage)) 'Existing malformed-history refusal remains explicit.'
            Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $lc) -ceq $before) 'Refusal does not overwrite current or historical input.'
        }
    }
    Invoke-TestCase 'Site 5: legacy snapshot preserves exact values while real migration revokes current authority' {
        $lc=New-TestLocalConcept
        $expected=New-TestExpectedLegacy (New-TestLocalConcept)
        $expectedLegacyJson=ConvertTo-ForgeBriefCanonicalJson $expected
        $expectedBriefJson=ConvertTo-ForgeBriefCanonicalJson $lc.generation_brief_snapshot
        $state=[pscustomobject][ordered]@{
            schema='forge.local_core.v1'; updated_at='2026-02-03T04:05:06.1234000+05:45'; concepts=[object[]]@($lc);
            sales_imports=[object[]]@(); research_drafts=[object[]]@();
            publication_receipts=[object[]]@([pscustomobject]@{id='synthetic-revocation-control'; lineage_verified=$true; at='2026-02-03T04:05:06.1200-07:30'});
            sales_rows=[object[]]@([pscustomobject]@{id='synthetic-revocation-control'; linked=$true; linked_product_key='synthetic'; at='2026-02-03T04:05:06.1234567Z'})
        }
        $result=Convert-LocalCoreStateToV2 $state
        Assert-Test ([object]::ReferenceEquals($state,$result)) 'Migration is intentionally in-place, not an input-immutability claim.'
        Assert-Test ($result.schema -ceq 'forge.local_core.v2' -and $result.state_revision -eq 0 -and $result.last_write_id -ceq '') 'Existing v2 migration envelope retained.'
        Assert-TestCanonicalEqual $expected $lc.legacy_v1_content 'legacy snapshot'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $lc.legacy_v1_content) -ceq $expectedLegacyJson) 'Archived pre-revocation values are byte-identical under real canonicalization.'
        Assert-Test ($lc.legacy_v1_content.history_only -is [bool] -and $lc.legacy_v1_content.history_only) 'Legacy snapshot is history only.'
        Assert-Test ($null -eq $lc.brief_approval -and $null -eq $lc.active_acceptance -and $null -eq $lc.publication) 'Current approval, acceptance and publication are revoked.'
        Assert-Test ($lc.approval_recovery_review_required -is [bool] -and $lc.approval_recovery_review_required -and $lc.approval_recovery_source -ceq 'legacy_v1_migration') 'Fresh review remains required after migration.'
        Assert-Test ($lc.source_revision_hash -ceq '' -and $lc.legacy_listing_restore_pending) 'Legacy lineage does not retain current authority.'
        foreach ($art in $lc.artwork) {
            Assert-Test ($art.accepted -is [bool] -and !$art.accepted -and $art.source_revision_hash -ceq '' -and $null -eq $art.integrity_check) 'Real migration revokes artwork acceptance, lineage and integrity.'
        }
        foreach ($package in $lc.packages) {
            Assert-Test ($package.valid -is [bool] -and !$package.valid -and $package.invalidation_reason -ceq 'v1_state_migrated_without_exact_lineage_binding') 'Real package invalidation remains fail closed.'
        }
        Assert-TestCanonicalEqual (New-LocalCoreChecks) $lc.checks 'real reset check records'
        Assert-Test (!$lc.checks.ip.legal_clearance) 'Reset checks do not imply legal clearance.'
        Assert-Test (!$result.publication_receipts[0].lineage_verified -and !$result.sales_rows[0].linked -and $result.sales_rows[0].linked_product_key -ceq '') 'Receipt/sales current lineage is revoked.'
        Assert-Test ($result.updated_at -is [string] -and $result.updated_at -ceq '2026-02-03T04:05:06.1234000+05:45') 'Unrelated existing state timestamp lexeme stays unchanged.'
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $lc.generation_brief_snapshot) -ceq $expectedBriefJson) 'Unchanged generation brief remains intact.'
        Assert-Test ($lc.legacy_v1_content.artwork[0].accepted -and $lc.legacy_v1_content.packages[0].valid) 'Historical synthetic pre-revocation flags survive without becoming current authority.'
        Assert-Test (![object]::ReferenceEquals($lc.legacy_v1_content.artwork[0].fixture.nested,$lc.artwork[0].fixture.nested)) 'Archived nested artwork is detached.'
        $lc.artwork[0].fixture.nested.dates[0]='changed-only-in-current-artwork'
        $lc.packages[0].fixture.nested.sequence[5].at='changed-only-in-current-package'
        Assert-TestCanonicalEqual $expected $lc.legacy_v1_content 'legacy remains detached after current edits'
        $beforeRepeat=ConvertTo-ForgeBriefCanonicalJson $state
        $null=Convert-LocalCoreStateToV2 $state
        Assert-Test ((ConvertTo-ForgeBriefCanonicalJson $state) -ceq $beforeRepeat) 'Already-v2 conversion does not replace historical values or restore authority.'
    }
    Invoke-TestCase 'Actual default ConvertFrom-Json control records observed types, text and hashes without assumed drift' {
        $fields=New-TestFields
        $spec=$fields.production_spec
        $inputJson=ConvertTo-ForgeBriefCanonicalJson $spec
        # Intentionally the installed DEFAULT parser, with no DateKind argument.
        $defaultSpec=ConvertFrom-Json -InputObject $inputJson -ErrorAction Stop
        $observations=New-Object 'System.Collections.Generic.List[object]'
        foreach ($name in @('utc','positive_offset','negative_offset','fractional_utc','explicit_zero_offset','no_zone','date_only','number','numeric_string','decimal_number','large_integer','bool_value','bool_string','null_value')) {
            $before=Get-TestObservedScalar (Get-ForgeBriefValue $spec $name)
            $after=Get-TestObservedScalar (Get-ForgeBriefValue $defaultSpec $name)
            $observations.Add([pscustomobject]@{path=('production_spec.'+$name); before=$before; default_result=$after; type_changed=($before.clr_type -cne $after.clr_type); canonical_json_changed=($before.canonical_json -cne $after.canonical_json)})
        }
        for ($i=0; $i -lt $spec.nested.dates.Count; $i++) {
            $before=Get-TestObservedScalar $spec.nested.dates[$i]
            $after=Get-TestObservedScalar $defaultSpec.nested.dates[$i]
            $observations.Add([pscustomobject]@{path=('production_spec.nested.dates['+$i+']'); before=$before; default_result=$after; type_changed=($before.clr_type -cne $after.clr_type); canonical_json_changed=($before.canonical_json -cne $after.canonical_json)})
        }
        $defaultFields=New-TestFields; $defaultFields.production_spec=$defaultSpec
        $expectedBrief=New-TestExpectedBrief $fields
        $briefInputJson=ConvertTo-ForgeBriefCanonicalJson $expectedBrief
        $defaultBrief=ConvertFrom-Json -InputObject $briefInputJson -ErrorAction Stop
        $beforeSpecHash=Get-ForgeBriefSha256 $spec; $afterSpecHash=Get-ForgeBriefSha256 $defaultSpec
        $beforeRevisionHash=Get-ResearchDraftContentHash $fields.concept_key $fields
        $afterRevisionHash=Get-ResearchDraftContentHash $fields.concept_key $defaultFields
        $beforeBriefHash=Get-ForgeBriefSha256 $expectedBrief; $afterBriefHash=Get-ForgeBriefSha256 $defaultBrief
        $changedTypes=@($observations | Where-Object {$_.type_changed}).Count
        $changedText=@($observations | Where-Object {$_.canonical_json_changed}).Count
        $control=[pscustomobject][ordered]@{
            name='installed_default_parser_same_synthetic_fixture'; date_kind_argument_used=$false;
            outcome=$(if ($changedTypes -gt 0 -or $changedText -gt 0 -or $beforeSpecHash -cne $afterSpecHash -or $beforeRevisionHash -cne $afterRevisionHash -or $beforeBriefHash -cne $afterBriefHash) {'OBSERVED_DIFFERENCE'} else {'NO_DIFFERENCE_OBSERVED'});
            input_spec_canonical_json=$inputJson; default_spec_canonical_json=(ConvertTo-ForgeBriefCanonicalJson $defaultSpec);
            input_brief_canonical_json=$briefInputJson; default_brief_canonical_json=(ConvertTo-ForgeBriefCanonicalJson $defaultBrief);
            spec_hash_before=$beforeSpecHash; spec_hash_after=$afterSpecHash; spec_hash_changed=($beforeSpecHash -cne $afterSpecHash);
            revision_hash_before=$beforeRevisionHash; revision_hash_after=$afterRevisionHash; revision_hash_changed=($beforeRevisionHash -cne $afterRevisionHash);
            brief_hash_before=$beforeBriefHash; brief_hash_after=$afterBriefHash; brief_hash_changed=($beforeBriefHash -cne $afterBriefHash);
            changed_type_count=$changedTypes; changed_canonical_text_count=$changedText; observations=@($observations.ToArray());
            interpretation='Observed installed-runtime behavior only. No simulated drift; no requirement that an old/default clone must fail on every runtime.'
        }
        $script:Controls.Add($control)
        Assert-Test ($observations.Count -eq 17) 'Actual default-parser observations cover scalars and nested date-array values.'
        Assert-Test ($defaultSpec -is [pscustomobject] -and $defaultBrief -is [pscustomobject]) 'Both real default parser calls returned object roots.'
        Assert-TestCanonicalEqual (New-TestDateFixture) $spec 'default control does not mutate original fixture'
        Write-Host ('DEFAULT CONTROL: '+$control.outcome+'; changed types='+$changedTypes+'; changed canonical scalar text='+$changedText+'; spec/revision/brief hash changed='+$control.spec_hash_changed+'/'+$control.revision_hash_changed+'/'+$control.brief_hash_changed)
        foreach ($observation in $observations) {
            Write-Host ('OBSERVED '+$observation.path+': '+$observation.before.clr_type+' '+$observation.before.canonical_json+' -> '+$observation.default_result.clr_type+' '+$observation.default_result.canonical_json)
        }
        Write-Host ('OBSERVED spec hash: '+$beforeSpecHash+' -> '+$afterSpecHash)
        Write-Host ('OBSERVED revision hash: '+$beforeRevisionHash+' -> '+$afterRevisionHash)
        Write-Host ('OBSERVED brief hash: '+$beforeBriefHash+' -> '+$afterBriefHash)
    }
} catch {
    $caseStatus=if ($blocked) { 'BLOCKED' } else { 'FAIL' }
    $script:Checks.Add([pscustomobject]@{name='Harness setup or unexpected execution failure'; status=$caseStatus; detail=$_.Exception.Message})
    Write-Host ($caseStatus+': '+$_.Exception.Message)
} finally {
    foreach ($fileName in @($script:Sources.Keys)) {
        Invoke-TestCase ('Source and owned copy bytes unchanged: '+$fileName) {
            $source=$script:Sources[$fileName]
            $source.after_sha256=Get-TestBytesHash ([IO.File]::ReadAllBytes($source.path))
            $source.copied_after_sha256=Get-TestBytesHash ([IO.File]::ReadAllBytes($source.copied_path))
            Assert-Test ($source.after_sha256 -ceq $source.before_sha256) 'Source module bytes must remain unchanged.'
            Assert-Test ($source.copied_after_sha256 -ceq $source.before_sha256) 'Owned exact source copy must remain unchanged.'
        }
    }
    $failed=@($script:Checks | Where-Object {$_.status -ceq 'FAIL'}).Count
    $status=if ($blocked) { 'BLOCKED' } elseif ($failed -eq 0 -and $script:LoadedFunctions.Count -eq $script:ExpectedFunctionCount -and $script:Controls.Count -eq 1 -and $script:CheckCount -gt 0) { 'PASS' } else { 'FAIL' }
    $receipt=[ordered]@{
        schema='forge.json_clone_preservation_test_receipt.v1'; run_id=$runId; status=$status;
        scope=$script:ScopeLabel; started_at=$started; completed_at=[DateTime]::UtcNow.ToString('o'); runtime=$runtime;
        module_root=$ModuleRoot; fresh_owned_test_root=$runRoot; explicit_check_count=$script:CheckCount;
        sources=@($script:Sources.Values); loaded_functions=@($script:LoadedFunctions.ToArray());
        cases=@($script:Checks.ToArray()); failed_cases=$failed; default_parser_controls=@($script:Controls.ToArray());
        target_sites=@('New-ResearchDraftRevision.production_spec','New-ForgeGenerationBriefSnapshot.brief','Preserve-ForgeLocalReviewHistory.payload','Preserve-ForgeLocalReviewHistory.brief_approval','Convert-LocalCoreStateToV2.legacy');
        real_helpers=@('Get-ForgeBriefValue','Get-ForgeProductionSpec','ConvertTo-ForgeBriefCanonicalJson','Get-ForgeBriefSha256','Get-ResearchDraftContentHash','Get-StringSha256Hex','Add-OrSetProperty','New-LocalCoreState','New-LocalCoreCheckRecord','New-LocalCoreChecks','Invalidate-LocalCorePackages');
        dependency_doubles=@('Missing bootstrap Get-PropertyValue delegates to actual Get-ForgeBriefValue.','Missing bootstrap Get-ByteSha256Hex uses SHA-256 test primitive; actual Get-StringSha256Hex remains extracted.','ResearchDraftContentFields and ResearchDraftKeyPrefix bootstrap constants.','Missing Get-ForgeOwnerLanguageReview returns a labeled synthetic UNREVIEWED response.','Unexpected proposal/rejected-save/AI-validation boundary calls throw.');
        limitations=@('No full module import or full-stack claim; the twelve missing dependency files and Workbench remain unavailable and are never fetched or substituted.','Strict JSON syntax/parser and owner-language correctness are not tested.','No real approval record, real state write, model, PC, source capture, network, installation, export, publication, remote or CI action.','Revision and brief inputs are immutable; history intentionally appends review_history, and legacy migration intentionally revokes authority in place.','Only the five named clone sites are covered; other default-parser clone sites are not changed or covered by a blanket guarantee.','Default-parser differences are actual observations from this invocation, not guaranteed on every runtime.','External supervisor must treat timeout, crash, nonzero exit, missing receipt or non-PASS receipt as failure.','This receipt applies only to this invocation and its recorded exact module bytes.')
    }
    # Fresh CreateNew receipt: no old PASS can be reused. Unsupported runtimes
    # get BLOCKED, not a fallback parser, auto-install or fabricated test result.
    $stream=[IO.File]::Open($receiptPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {
        $bytes=[Text.Encoding]::UTF8.GetBytes((ConvertTo-Json -InputObject $receipt -Depth 60))
        $stream.Write($bytes,0,$bytes.Length)
    } finally { $stream.Dispose() }
    Write-Host ('Receipt: '+$receiptPath)
    Write-Host ('Scope: '+$script:ScopeLabel)
}
if ($status -cne 'PASS') { throw ('JSON clone preservation checks '+$status+'; fresh receipt: '+$receiptPath) }
Write-Host ('PASS: '+$script:CheckCount+' explicit checks; '+$script:Checks.Count+' cases. No full-stack claim.')
