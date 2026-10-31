"""Source/order/integrity checks only; no PowerShell parsing or runtime execution."""
from pathlib import Path
import hashlib,json,re,unittest
HERE=Path(__file__).resolve().parent;TESTS=HERE.parent;APP=TESTS.parent/'app/Merch_Forge_A5_Current'
def text(p):return p.read_text(encoding='utf-8-sig')
def fn(s,n):
 m=re.search(r'^function '+re.escape(n)+r'\b',s,re.M);assert m,n
 nxt=re.search(r'^function ',s[m.end():],re.M)
 return s[m.start():m.end()+nxt.start() if nxt else len(s)]
CORE=text(APP/'Modules/Forge.LocalCore.ps1');IMPORT=fn(CORE,'Import-LocalPublicationReceiptFromPath')
class HistoricalReceiptStatic(unittest.TestCase):
 def test_historical_branch_requires_real_boolean_and_recorded_ready(self):
  self.assertIn("[string](Get-PropertyValue $packageMatch 'status') -ne 'READY_FOR_MANUAL_UPLOAD'",IMPORT)
  self.assertIn("$historicalPackage=Test-LocalPackageBoolean $packageMatch 'valid' $false",IMPORT)
  self.assertIn("if(!$historicalPackage-and!(Test-LocalPackageBoolean $packageMatch 'valid' $true))",IMPORT)
  self.assertNotIn('invalidated_at',IMPORT)
 def test_all_archive_identity_date_and_conflict_gates_precede_confirmation(self):
  confirm=IMPORT.index("Confirm $question 'Record historical publication receipt'")
  for token in ('Read-LocalCheckEvidencePayload $Path','Get-LocalReadyPackageZipAuthority $packagePath $packageMatch $conceptKey','Published package bytes are missing','print_production_sha256 does not match','lineage does not match','preupload_gate_sha256 does not match',"$channel -ne 'amazon_merch'",'$marketplace -ne',"$published -gt [DateTime]::UtcNow.AddMinutes(10)",'$published -lt $packageCreated.AddMinutes(-10)','$published -gt $profileValidUntil','This publication receipt was already imported','This exact published product/package binding is already recorded','Get-LocalPublicationReceiptBindingDecision','The conflicting receipt was not imported'):
   self.assertLess(IMPORT.index(token),confirm,token)
 def test_cancel_is_before_mutation_and_dialog_is_owner_attestation_not_inference(self):
  append=IMPORT.index('$s.publication_receipts=@($s.publication_receipts)+@($receipt)')
  self.assertLess(IMPORT.index("if(!(Confirm $question 'Record historical publication receipt'))"),append)
  self.assertIn("saved records were not changed.';return}",IMPORT)
  self.assertIn('Confirm that the supplied receipt records an actual publication you are reporting',IMPORT)
  self.assertIn('Forge verifies archive lineage, not external publication',IMPORT)
 def test_receipt_and_archive_are_rehashed_after_dialog_before_write(self):
  confirm=IMPORT.index('Confirm $question');fence=IMPORT.index('(Get-FileSha256Hex $Path)-cne$fileSha-or(Get-FileSha256Hex $packagePath)-cne$packageSha')
  self.assertLess(confirm,fence);self.assertLess(fence,IMPORT.index('$s.publication_receipts=@('))
  self.assertEqual(1,IMPORT.count('Write-LocalCoreState $s'))
 def test_historical_import_cannot_restore_current_authority_or_dispatch(self):
  for token in ('Invalidate-LocalCorePackages','active_acceptance=','checks=','brief_approval=','valid=$true','Set-LocalExactAcceptance','New-ForgeBriefApprovalRecord','Invoke-ForgeApi','Start-Process','Build-LocalAmazonPackage','Invoke-LocalCheckAutomation'):
   self.assertNotIn(token,IMPORT)
  self.assertIn('historical_package_at_import=$historicalPackage',IMPORT)
  self.assertIn("publication_evidence_kind='owner_attested_external';independent_publication_verification=$false",IMPORT)
  self.assertIn('try{Update-LocalCoreBusinessSurfaces}catch',IMPORT)
  self.assertIn('needs attention; refresh to verify saved history',IMPORT)
 def test_extended_native_suite_keeps_actual_zip_and_importer_with_matching_pins(self):
  suite=text(TESTS/'Test-PipelinePackageAuthority.ps1');pins=json.loads(text(TESTS/'PipelinePackageAuthority.sources.json'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  for name in ('Import-LocalPublicationReceiptFromPath','Read-LocalCheckEvidencePayload','Get-LocalPublicationReceiptBindingDecision','Get-LocalReadyPackageZipAuthority','Test-LocalPackageArtworkTechnical'):
   self.assertIn(name,pins['expected_loaded_functions'])
  self.assertIn('Parser]::ParseFile',suite);self.assertIn('. ([scriptblock]::Create($definition.Extent.Text))',suite)
  self.assertNotRegex(suite,r'(?m)^function (?:Import-LocalPublicationReceiptFromPath|Read-LocalCheckEvidencePayload|Get-LocalReadyPackageZipAuthority)\b')
  for row in pins['application_sources']:self.assertEqual(row['sha256'],sha(APP/row['path']),row['path'])
  for row in pins['test_sources']:self.assertEqual(row['sha256'],sha(TESTS/row['path']),row['path'])
if __name__=='__main__':unittest.main()
