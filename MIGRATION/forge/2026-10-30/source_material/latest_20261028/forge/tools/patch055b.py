import sys, os
sys.argv=[sys.argv[0], sys.argv[1]]
exec(open('/home/claude/forge/tools/patch055.py').read().split("DRAFT = ")[0])
G="if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.live.blocked' 'This is a local research draft. Live server actions are not available for it.');return}; "
patch('Modules/Forge.DomainActions.ps1', [
 ("function Prepare-DeliveryPackage {\n    ", "function Prepare-DeliveryPackage {\n    "+G),
 ("function Prepare-SocialHandoff {\n    ", "function Prepare-SocialHandoff {\n    "+G),
 ("function Prepare-OwnerPackage {\n    ", "function Prepare-OwnerPackage {\n    "+G),
 ("function Save-PublicationMetadata {\n    if($null -ne $script:Publication -and [bool](Get-PropertyValue $script:Publication 'local_core')){Save-LocalPublicationMetadata;return}\n", "function Save-PublicationMetadata {\n    if($null -ne $script:Publication -and [bool](Get-PropertyValue $script:Publication 'local_core')){Save-LocalPublicationMetadata;return}\n    "+G+"\n"),
 ("function Save-Revision {\n    ", "function Save-Revision {\n    if(Test-CurrentIsResearchDraft){Save-CurrentResearchDraftRevision;return}\n    "),
 ("function Queue-Generation {\n    ", "function Queue-Generation {\n    if(Test-CurrentIsResearchDraft){Show-Error (Get-UiText 'draft.generate.blocked' 'Research drafts cannot be generated from Forge yet. Use Export brief (no dispatch) and import the finished artwork.');return}\n    "),
 ("function Cancel-Generation {\n    ", "function Cancel-Generation {\n    "+G),
 ("function Reopen-CurrentAcceptance {\n    ", "function Reopen-CurrentAcceptance {\n    "+G),
 ("function Start-NewIteration([string]$Mode) {\n    ", "function Start-NewIteration([string]$Mode) {\n    "+G),
])
