"""Source/order/integrity only. Not a PowerShell parser or behavioral runtime test."""
from pathlib import Path
import hashlib,json,re,unittest
HERE=Path(__file__).resolve().parent;APP=HERE.parents[1]/'app/Merch_Forge_A5_Current'
def text(p):return p.read_text(encoding='utf-8-sig')
def fn(source,name):
 m=re.search(r'^function '+re.escape(name)+r'\b',source,re.M)
 if m is None:raise ValueError(name)
 n=re.search(r'^function ',source[m.end():],re.M)
 return source[m.start():m.end()+n.start() if n else len(source)]
LOC=text(APP/'Modules/Forge.Localization.ps1');DRAFT=text(APP/'Modules/Forge.ResearchDrafts.ps1');WB=text(APP/'MerchForgeWorkbench.ps1')
SET=fn(LOC,'Set-UiLocale');RESTORE=fn(DRAFT,'Restore-DynamicSurfacesAfterLocale')
class LocaleEditPreservationStatic(unittest.TestCase):
 def test_same_locale_is_validated_then_noop_before_any_mutation(self):
  validate=SET.index('if(-not ($script:SupportedLocales -contains $v)){return $false}')
  noop=SET.index('if($v -eq $script:Locale){return $true}')
  dirty=SET.index('if($script:Dirty -or $script:PublicationDirty)')
  self.assertLess(validate,noop);self.assertLess(noop,dirty)
  for token in ('$StatusText.Text=','$script:Locale=$v','Save-UiLocale $v','Apply-LocaleUi'):
   self.assertLess(noop,SET.index(token))
 def test_different_locale_keeps_dirty_refusal_and_clean_persist_contract(self):
  self.assertIn("$StatusText.Text=Get-UiText 'locale.dirty' 'Save or discard current edits before changing UI language.'\n        return $false",SET)
  self.assertIn('$script:Locale=$v; if($Persist){Save-UiLocale $v}; Apply-LocaleUi; return $true',SET)
  self.assertNotIn('-and $v -ne',SET)
 def test_helper_reopens_only_if_both_editors_clean(self):
  guard='if((Test-CurrentIsResearchDraft) -and -not ($script:Dirty -or $script:PublicationDirty))'
  self.assertIn(guard,RESTORE);self.assertLess(RESTORE.index(guard),RESTORE.index('Open-ResearchDraftItem'))
  self.assertEqual(1,RESTORE.count('Open-ResearchDraftItem'))
  self.assertIn('Open-ResearchDraftItem ([pscustomobject]@{concept_key=$key}) $true',RESTORE)
  self.assertIn('Show-ProductSection $section',RESTORE)
 def test_startup_still_explicitly_applies_without_setter(self):
  init=fn(LOC,'Initialize-UiLocale')
  self.assertIn('Sync-LanguageSelector; Apply-LocaleUi',init);self.assertNotIn('Set-UiLocale',init)
  self.assertIn("if($script:StaticLocaleRegistry.Count -eq 0){Register-StaticLocaleTree $Window}",init)
  self.assertRegex(WB,r'(?m)^Initialize-UiLocale$')
 def test_real_header_calls_setter_and_sync_and_renderer_calls_helper(self):
  for suffix,locale in [('En','en'),('Ru','ru'),('Es','es')]:
   self.assertIn("$HeaderLang"+suffix+".Add_Click({if(-not $script:LocaleChangeInProgress){if(-not (Set-UiLocale '"+locale+"' $true)){Sync-LanguageSelector}else{Sync-LanguageSelector}}})",WB)
  self.assertIn('try { Restore-DynamicSurfacesAfterLocale }',fn(LOC,'Apply-LocaleUi'))
  loader=fn(DRAFT,'Open-ResearchDraftItem')
  self.assertIn('if(-not $Force -and ($script:Dirty -or $script:PublicationDirty)',loader)
  self.assertIn('$script:Dirty=$false; $script:PublicationDirty=$false',loader)
 def test_native_tests_extract_actual_functions_with_disclosed_seams(self):
  suite=text(HERE/'Test-ForgeLocaleEditPreservation.ps1');pins=json.loads(text(HERE/'LocalePins.json'))
  self.assertIn('Set-StrictMode -Version 2.0',suite);self.assertIn('Parser]::ParseFile',suite)
  self.assertIn('. ([scriptblock]::Create($definitions[0].Extent.Text))',suite)
  self.assertEqual(['Get-PropertyValue','Set-UiLocale','Sync-LanguageSelector','Initialize-UiLocale','Test-CurrentIsResearchDraft','Restore-DynamicSurfacesAfterLocale'],pins['expected_function_names'])
  for name in pins['expected_function_names']:self.assertNotRegex(suite,r'(?m)^\s*function '+re.escape(name)+r'\b')
  self.assertIn('function Apply-LocaleUi {$script:ApplyCalls++;Restore-DynamicSurfacesAfterLocale}',suite)
  self.assertIn('function Open-ResearchDraftItem',suite)
  self.assertIn('not executed',text(HERE/'README.md'))
 def test_all_native_pins_match_exact_bytes_and_cases_are_unique(self):
  pins=json.loads(text(HERE/'LocalePins.json'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  for name,h in pins['sources'].items():self.assertEqual(h,sha(APP/name),name)
  for name,h in pins['tests'].items():self.assertEqual(h,sha(HERE/name),name)
  self.assertEqual(pins['expected_function_names'],[n for ns in pins['functions'].values() for n in ns])
  cases=pins['expected_case_names'];self.assertEqual(41,len(cases));self.assertEqual(len(cases),len(set(cases)))
  for locale in ['en','ru','es']:
   for dirty in ['clean','creative','publication','both']:self.assertIn('same_'+locale+'_'+dirty,cases)
   for dirty in ['creative','publication','both']:self.assertIn('different_'+locale+'_'+dirty+'_blocked',cases)
   self.assertIn('initialize_'+locale+'_still_applies',cases)
 def test_change_adds_no_product_state_or_publication_actions(self):
  for token in ('Write-LocalCoreState','Save-ResearchDraftRevision','Save-PublicationMetadata','Set-LocalExactAcceptance','Build-LocalAmazonPackage','Invoke-ForgeApi','Start-Process','Remove-Item'):
   self.assertNotIn(token,SET);self.assertNotIn(token,RESTORE)
if __name__=='__main__':unittest.main()
