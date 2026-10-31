#!/usr/bin/env python3
"""Offline structural checks, not a PowerShell parser or a WPF runtime pass."""
from pathlib import Path
import collections
import hashlib
import json
import re
import unittest
import xml.etree.ElementTree as ET

FORGE = Path(__file__).resolve().parents[1]
APP = FORGE / 'app' / 'Merch_Forge_A5_Current'
MODULES = APP / 'Modules'
TEXT = (APP / 'MerchForgeWorkbench.ps1').read_text(encoding='utf-8-sig')
XAML = re.search(r"\[xml\]\$xaml=@'\n(.*?)\n'@", TEXT, re.S).group(1)
XML = ET.fromstring(XAML)
NAME = '{http://schemas.microsoft.com/winfx/2006/xaml}Name'
ELEMENTS = {e.attrib[NAME]: e for e in XML.iter() if NAME in e.attrib}
PARENTS = {child: parent for parent in XML.iter() for child in parent}
CONTROL_TYPES = {
    'LocalEntryButton': 'Button', 'LocalEntryStatus': 'TextBlock',
    'LocalAIPanel': 'StackPanel', 'LocalAIPrompt': 'TextBox', 'LocalAIStatus': 'TextBlock',
    'LocalAICreateButton': 'Button', 'LocalAIReviseButton': 'Button',
    'LocalAICanonicalHoldButton': 'Button', 'LocalAICancelButton': 'Button',
}

def block(name):
    return TEXT.split('# BEGIN NEW WORKBENCH RECONCILIATION ' + name + '\n', 1)[1].split(
        '# END NEW WORKBENCH RECONCILIATION ' + name, 1)[0]

def source(name):
    return (MODULES / name).read_text(encoding='utf-8-sig')

def commands(text):
    return '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('#'))

class WorkbenchReconciliationStatic(unittest.TestCase):
    def test_direct_entry_runtime_refuses_before_state_or_wpf(self):
        self.assertTrue(TEXT.startswith('#requires -Version 7.5\n'))
        runtime = block('RUNTIME')
        self.assertIn("$PSVersionTable.PSEdition -cne 'Core'", runtime)
        self.assertIn("$PSVersionTable.PSVersion -lt [version]'7.5.0'", runtime)
        self.assertIn("$forgeJsonCommand.Parameters.ContainsKey('DateKind')", runtime)
        self.assertIn('Microsoft.PowerShell.Utility\\ConvertFrom-Json', runtime)
        self.assertIn('-DateKind String', runtime)
        self.assertIn('$forgeRuntimeProbe.instant -isnot [string]', runtime)
        self.assertLess(TEXT.index('# END NEW WORKBENCH RECONCILIATION RUNTIME'), TEXT.index('Add-Type -AssemblyName PresentationFramework'))
        self.assertLess(TEXT.index('# END NEW WORKBENCH RECONCILIATION RUNTIME'), TEXT.index('$script:StateRoot ='))
        self.assertNotIn('catch', commands(runtime))

    def test_backend_mobile_integration_is_not_loaded(self):
        backend = commands(source('Forge.BackendStatus.ps1'))
        self.assertNotIn('Forge.MobileRelayHook.ps1', backend)
        self.assertNotIn('Start-ForgeMobileSyncIfAuthorized', backend)
        self.assertIn('$script:LocalApproveBriefButton = $null', block('STATE'))
        self.assertNotIn('LocalApproveBriefButton', ELEMENTS)

    def test_hosted_harness_uses_real_xaml_modules_and_bounded_events(self):
        harness = (FORGE / 'tests' / 'Test-WorkbenchReconciliationWpf.ps1').read_text()
        self.assertIn('[Management.Automation.Language.Parser]::ParseFile($workbenchPath', harness)
        self.assertIn('[Management.Automation.Language.Parser]::ParseFile($module.FullName', harness)
        self.assertIn('[Windows.Markup.XamlReader]::Load($reader)', harness)
        self.assertIn("Get-ReconciliationBlock 'BINDINGS'", harness)
        self.assertIn("Get-ReconciliationBlock 'INITIALIZATION'", harness)
        self.assertNotRegex(harness, r'(?m)^\s*\.\s+\$workbenchPath')
        self.assertNotIn('.ShowDialog(', harness)
        for call in ('Invoke-RestMethod ', 'Invoke-WebRequest ', '.PostAsync(', 'Initialize-LocalCore', 'Initialize-AutoResearchUi'):
            self.assertNotIn(call, commands(harness))
        self.assertNotRegex(harness, r'(?m)^function (?:New-ForgeLocalAIJsonRequest|Start-ForgeLocalAIRequest|Save-Forge|Get-ResearchEvidenceContext)')
        self.assertIn('$Window.Close()', harness)
        self.assertIn('Click-Control $LocalAICancelButton', harness)
        self.assertIn('Click-Control $SemanticReviewCancel', harness)
        self.assertIn('$RejectedAIEditor.Text=', harness)

    def test_hosted_harness_pins_inputs_and_exclusively_claims_private_root(self):
        harness = (FORGE / 'tests' / 'Test-WorkbenchReconciliationWpf.ps1').read_text()
        for token in ('[string]$RunId', '[string]$EvidenceParent', '[string]$ExpectedTestSha256', '[string]$ExpectedInputManifestSha256',
                      'CreateDirectoryW', '[IO.FileMode]::CreateNew', '[IO.FileShare]::None',
                      '$acl.SetAccessRuleProtection($true,$false)', 'ReparsePoint', 'ownership.json'):
            self.assertIn(token, harness)
        self.assertIn("'forge-workbench-wiring-'+$RunId", harness)
        self.assertIn("'receipt-'+$RunId+'.json'", harness)
        self.assertIn("Copy-ForgeWiringInput 'harness' $PSCommandPath", harness)
        self.assertIn("Copy-ForgeWiringInput 'input_manifest'", harness)
        self.assertIn("$sealedInputs.candidate_workbench_sha256", harness)

    def test_hosted_harness_executes_copies_and_rehashes_originals_after_cleanup(self):
        harness = (FORGE / 'tests' / 'Test-WorkbenchReconciliationWpf.ps1').read_text()
        self.assertLess(harness.index('$AppRoot=$copiedApp;'), harness.index('[Management.Automation.Language.Parser]::ParseFile($workbenchPath'))
        self.assertLess(harness.index('$AppRoot=$copiedApp;'), harness.index("$script:ModuleRoot=Join-Path $AppRoot 'Modules'"))
        final = harness.split('# Quiesce UI first;', 1)[1]
        self.assertLess(final.index('$script:Window.Close()'), final.index('Read-ForgeWiringBytes $snapshot.original_path'))
        self.assertIn('Read-ForgeWiringBytes $snapshot.copy_path', final)
        self.assertIn('$script:ForgeWiringExpectedInputs=49', harness)
        self.assertIn("Original/copied module inventory changed", final)
        self.assertIn('$script:ForgeWiringOwnershipOk-and$integrityOk', final)

    def test_hosted_harness_never_publishes_pass_before_final_checks_or_deletes_evidence(self):
        harness = (FORGE / 'tests' / 'Test-WorkbenchReconciliationWpf.ps1').read_text()
        before, final = harness.split('# Quiesce UI first;', 1)
        self.assertNotRegex(before, r"(?:status|ForgeWiringStatus)\s*=\s*'PASS'")
        self.assertLess(final.index('$integrityOk='), final.index("$script:ForgeWiringStatus='PASS'"))
        self.assertLess(final.index("$script:ForgeWiringStatus='PASS'"), final.index('Write-ForgeWiringNewFile $script:ForgeWiringReceiptPath'))
        for forbidden in ('Remove-Item', '[IO.Directory]::Delete', '[IO.File]::Delete', 'Move-Item', '[IO.FileMode]::Create,'):
            self.assertNotIn(forbidden, commands(harness))
        self.assertIn("{'FAIL'}else{'BLOCKED'}", harness)
        self.assertIn('evidence_retained=$true', final)
        self.assertTrue(harness.rstrip().endswith('exit $script:ForgeWiringExitCode'))

    def test_full_xaml_has_unique_names(self):
        names = [e.attrib[NAME] for e in XML.iter() if NAME in e.attrib]
        self.assertGreater(len(names), 200)
        self.assertEqual([], [k for k, v in collections.Counter(names).items() if v != 1])

    def test_real_typed_controls_and_panel_mount(self):
        for name, tag in CONTROL_TYPES.items():
            self.assertEqual(ELEMENTS[name].tag.split('}')[1], tag)
        self.assertIs(PARENTS[ELEMENTS['LocalAIStatus']], ELEMENTS['LocalAIPanel'])
        self.assertIs(PARENTS[ELEMENTS['LocalAIPanel']], next(e for e in ELEMENTS['LocalAIExpander'] if e.tag.endswith('ScrollViewer')))

    def test_panel_is_pinned_outside_navigated_pages(self):
        expander = ELEMENTS['LocalAIExpander']
        self.assertEqual(expander.attrib['Grid.Row'], '1')
        page_grid = PARENTS[ELEMENTS['HomeLandingScroll']]
        self.assertEqual(page_grid.attrib['Grid.Row'], '2')
        self.assertIs(PARENTS[page_grid], PARENTS[expander])
        rows = list(PARENTS[expander])[0]
        self.assertEqual([e.attrib['Height'] for e in rows], ['Auto', 'Auto', '*'])

    def test_initial_controls_are_inert_and_bounded(self):
        self.assertEqual(ELEMENTS['LocalAIExpander'].attrib['IsExpanded'], 'False')
        self.assertEqual(ELEMENTS['LocalAICancelButton'].attrib['IsEnabled'], 'False')
        self.assertEqual(ELEMENTS['LocalAIPrompt'].attrib['MaxLength'], '4000')
        self.assertNotIn('Text', ELEMENTS['LocalAIPrompt'].attrib)
        self.assertIn('No request sent', ELEMENTS['LocalAIStatus'].attrib['Text'])
        for name in CONTROL_TYPES:
            self.assertFalse({'Click', 'Loaded', 'TextChanged'} & set(ELEMENTS[name].attrib))

    def test_script_bindings_exact_once_before_initialization(self):
        bindings = block('BINDINGS')
        for name in CONTROL_TYPES:
            self.assertEqual(len(re.findall(r'\$script:' + name + r"\s*=\s*X '" + name + "'", TEXT)), 1)
            self.assertIn(name, bindings)
        self.assertLess(TEXT.index('# END NEW WORKBENCH RECONCILIATION BINDINGS'), TEXT.index('# BEGIN NEW WORKBENCH RECONCILIATION INITIALIZATION'))
        self.assertIn('[object]::ReferenceEquals($script:LocalAIStatus.Parent,$script:LocalAIPanel)', bindings)

    def test_required_state_precedes_imports_under_strictmode(self):
        state = block('STATE')
        self.assertLess(TEXT.index('Set-StrictMode -Version 2.0'), TEXT.index('# BEGIN NEW WORKBENCH RECONCILIATION STATE'))
        self.assertLess(TEXT.index('# END NEW WORKBENCH RECONCILIATION STATE'), TEXT.index(". (Join-Path $script:ModuleRoot"))
        for name in ('LocalAIRequest', 'LocalAITimer', 'VisionReviewRequest', 'UnsavedGuardWindow',
                     'LastCanonicalResponse', 'LastLocalAISaveReceipt', 'LastRejectedLocalAIResponse',
                     'SemanticReviewDisplayedSnapshot', 'LastSemanticReviewUiReceipt', 'AutoResearchProcess', 'AutoResearchTimer'):
            self.assertRegex(state, r'\$script:' + name + r'\s*=\s*\$null')
        self.assertRegex(state, r'\$script:CanonicalDesignExperiment\s*=\s*\$false')
        self.assertRegex(state, r'\$script:RejectedAIEditDirty\s*=\s*\$false')

    def test_review_mount_sentinels_are_not_predeclared(self):
        self.assertNotRegex(TEXT, r'\$script:(?:RejectedAIExpander|SemanticReviewExpander)\s*=')
        for filename, sentinel in [('Forge.RejectedAI.ps1', 'RejectedAIExpander'), ('Forge.SemanticReviewUI.ps1', 'SemanticReviewExpander')]:
            self.assertIn('Get-Variable ' + sentinel + ' -Scope Script', source(filename))
            self.assertIn('$parent=$LocalAIStatus.Parent', source(filename))
            self.assertIn('$parent-isnot[Windows.Controls.Panel]', source(filename))

    def test_available_import_closure_is_real_and_complete(self):
        pending = [TEXT]
        imported = set()
        pattern = r"(?m)^\. \(Join-Path \$(?:script:ModuleRoot|PSScriptRoot) '([^']+\.ps1)'\)"
        while pending:
            for name in re.findall(pattern, pending.pop()):
                self.assertTrue((MODULES / name).is_file(), name)
                if name not in imported:
                    imported.add(name)
                    pending.append(source(name))
        self.assertEqual(imported, {p.name for p in MODULES.glob('*.ps1')})
        self.assertTrue({'Forge.LocalAI.ps1', 'Forge.AutoResearch.ps1', 'Forge.PublicSignals.ps1',
                         'Forge.ResearchImport.ps1', 'Forge.PublicEvidence.ps1', 'Forge.Economics.ps1'} <= imported)
        self.assertNotIn('Forge.MobileRelayHook.ps1', imported)

    def test_module_bytes_match_sealed_input_manifest(self):
        manifest = json.loads((FORGE / 'tests' / 'WorkbenchReconciliationInputs.json').read_text())
        self.assertEqual({p.name for p in MODULES.glob('*.ps1')}, set(manifest['module_sha256']))
        for name, expected in manifest['module_sha256'].items():
            self.assertEqual(hashlib.sha256((MODULES / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual(manifest['base_workbench_sha256'], '5aed878eabcbf48e5c1092792c0b72fb80272a1b45b72d146dc895ed1f949d0d')

    def test_no_automatic_research_model_or_source_start_added(self):
        init = commands(block('INITIALIZATION'))
        self.assertEqual(init.strip().splitlines(), [
            'Initialize-ForgeLocalAIUI',
            '$script:LocalAICanonicalHoldButton.Add_Click({Invoke-ForgeWorkbenchCanonicalHold})',
            '$script:LocalEntryButton.Add_Click({Invoke-ForgeWorkbenchLocalEntry})',
            'Show-ForgeWorkbenchGenerationUnavailable',
            'Initialize-ForgeUnsavedCloseGuard $Window'])
        code = commands(TEXT)
        for forbidden in ('Initialize-AutoResearchUi', 'Start-AutoResearch', 'Invoke-ForgePublicSignalsRefresh',
                          'Invoke-ForgeNicheEvidenceRefresh', 'Invoke-ForgeNicheDiscovery',
                          'Start-ForgeMobileSyncIfAuthorized', 'Refresh-ForgePublicSignalsSummary'):
            self.assertNotIn(forbidden, code)
        self.assertEqual(len(re.findall(r'(?m)^Initialize-ForgeLocalAIUI\s*$', TEXT)), 1)
        self.assertLess(TEXT.index('Initialize-ForgeLocalAIUI\n'), TEXT.index('$Window.Add_ContentRendered'))

    def test_poll_timer_only_completes_an_existing_request(self):
        local_ai = source('Forge.LocalAI.ps1')
        self.assertIn('$script:LocalAITimer.Add_Tick({Complete-ForgeLocalAIRequest})', local_ai)
        self.assertIn('if($null-eq$request-or!$request.Task.IsCompleted){return}', local_ai)
        self.assertIn('$Window.Add_Closed({$script:LocalAITimer.Stop();Stop-ForgeLocalAIRequest})', local_ai)

    def test_explicit_canonical_action_not_global_default(self):
        self.assertIn('(new)', ELEMENTS['LocalAICanonicalHoldButton'].attrib['Content'])
        self.assertIn('HOLD', ELEMENTS['LocalAICanonicalHoldButton'].attrib['Content'])
        self.assertEqual(ELEMENTS['LocalAICanonicalHoldButton'].attrib['IsEnabled'], '{Binding IsEnabled, ElementName=LocalAIReviseButton, Mode=OneWay}')
        action = TEXT.split('function Invoke-ForgeWorkbenchCanonicalHold {', 1)[1].split('\nfunction Refresh-Workbench', 1)[0]
        self.assertIn('if($null -ne $script:LocalAIRequest){return}', action)
        self.assertIn('if(-not (Test-CurrentIsResearchDraft))', action)
        self.assertIn('Start-ForgeLocalAIRequest $true', action)
        self.assertRegex(action, r'finally\s*\{\s*\$script:CanonicalDesignExperiment=\$false')
        self.assertEqual(TEXT.count('$script:CanonicalDesignExperiment=$true'), 1)
        for forbidden in ('Save-', 'Approve-', 'Record-ForgeSemanticReview', 'Invoke-ForgePublic', 'Start-AutoResearch'):
            self.assertNotIn(forbidden, action)

    def test_single_close_guard_with_rejected_copy_warning(self):
        self.assertNotRegex(TEXT, r'\$Window\.(?:Add_Closing|add_Closing)\(')
        self.assertEqual(TEXT.count('Initialize-ForgeUnsavedCloseGuard $Window'), 1)
        layout = source('Forge.UI.Layout.ps1')
        self.assertIn('[object]::ReferenceEquals($script:UnsavedGuardWindow,$HostWindow)', layout)
        self.assertEqual(layout.lower().count('.add_closing('), 1)
        self.assertIn('rejected-proposal edits that could not be retained', layout)
        self.assertIn('Close and discard unsaved creative/publication edits?', layout)
        self.assertIn('$EventArgs.Cancel=$true;return', layout)

    def test_local_entry_is_explicit_and_backend_connect_unchanged(self):
        self.assertIn('no backend', ELEMENTS['LocalEntryButton'].attrib['Content'])
        self.assertIs(PARENTS[ELEMENTS['LocalEntryButton']], PARENTS[ELEMENTS['ConnectButton']])
        self.assertIn('$ConnectButton.Add_Click({Connect-Workbench $false})', TEXT)
        action = TEXT.split('function Invoke-ForgeWorkbenchLocalEntry {', 1)[1].split('function Show-ForgeWorkbenchGenerationUnavailable', 1)[0]
        self.assertIn('if($script:Busy){return}', action)
        self.assertIn('if($script:Dirty -or $script:PublicationDirty)', action)
        self.assertIn('Enter-LocalWorkbench', action)
        self.assertIn('No backend fallback was attempted', action)
        for forbidden in ('Connect-Workbench', 'Load-EncryptedOwnerKey', 'Invoke-ForgeApi', 'Start-ForgeLocalAIRequest', 'Start-AutoResearch'):
            self.assertNotIn(forbidden, action)
        self.assertEqual(len(re.findall(r'(?m)^\s*Enter-LocalWorkbench\s*$', TEXT)), 1)
        refresh = TEXT.split('function Refresh-Workbench {', 1)[1].split('\n$publicationBoxes=', 1)[0]
        route = "if($script:ConnectionState -ceq 'Local'){$null=Refresh-LocalWorkbench;return}"
        self.assertIn(route, refresh)
        self.assertLess(refresh.index(route), refresh.index('Connect-Workbench'))

    def test_generation_ui_and_startup_are_inert(self):
        code = commands(TEXT)
        self.assertIn('$GenerateButton.Add_Click({Show-ForgeWorkbenchGenerationUnavailable})', code)
        self.assertIn('$CancelGenerationButton.Add_Click({Show-ForgeWorkbenchGenerationUnavailable})', code)
        self.assertNotIn('Queue-Generation', code)
        self.assertNotIn('Cancel-Generation', code)
        self.assertIn('$null=Initialize-GenerationWorkerBridge;', code)
        self.assertNotIn('Sync-LocalGenerationResults', code)
        self.assertIn('Generation unavailable', ELEMENTS['GenerateButton'].attrib['Content'])
        self.assertIn('Cancellation unavailable', ELEMENTS['CancelGenerationButton'].attrib['Content'])
        self.assertIn('Generation unavailable', ELEMENTS['GenerationUnavailableNotice'].attrib['Text'])
        action = TEXT.split('function Show-ForgeWorkbenchGenerationUnavailable {', 1)[1].split('\n}', 1)[0]
        self.assertIn('Get-LocalGenerationCapability', action)
        for forbidden in ('Confirm ', 'Queue-', 'Cancel-', 'Save-', 'Start-', 'Sync-'):
            self.assertNotIn(forbidden, action)
        bridge = source('Forge.GenerationWorkerBridge.ps1')
        initializer = bridge.split('function Initialize-GenerationWorkerBridge {', 1)[1].split('\n}', 1)[0]
        self.assertEqual(commands(initializer).strip(), 'return (Get-LocalGenerationCapability)')
        sync = bridge.split('function Sync-LocalGenerationResults', 1)[1].split('\n}', 1)[0]
        self.assertIn("throw (New-LocalGenerationUnavailableError 'result_import')", sync)

    def test_canonical_hold_and_authority_guard_unchanged(self):
        canonical = source('Forge.CanonicalDesignPrototype.ps1')
        self.assertIn("schema='forge.semantic_hold.v1';status='PENDING';meaning_verified=$false", canonical)
        self.assertIn("Add-OrSetProperty $rev 'semantic_review_hold' $hold", canonical)
        self.assertIn("Add-OrSetProperty $d 'semantic_review_hold' $hold", canonical)
        self.assertIn("Add-OrSetProperty $lc 'brief_approval' $null", canonical)
        self.assertNotIn('Record-ForgeSemanticReview', commands(TEXT))

if __name__ == '__main__':
    unittest.main(verbosity=2)
