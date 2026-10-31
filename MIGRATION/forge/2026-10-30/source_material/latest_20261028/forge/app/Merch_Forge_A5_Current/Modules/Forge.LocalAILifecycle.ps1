# Presentation of acknowledged/uncertain local saves, never model/owner approval.
function Set-ForgeLocalAISavedPresentation($Saved,[string]$OriginalResponse='') {
 if($null-eq$Saved-or$Saved.saved-isnot[bool]-or!$Saved.saved){throw 'Acknowledged save receipt required'}
 $draft=Get-PropertyValue $Saved 'draft';$key=[string](Get-PropertyValue $draft 'concept_key')
 $script:LastLocalAISaveReceipt=[pscustomobject]@{schema='forge.local_ai_save_outcome.v1';outcome='saved';saved=$true;at_utc=[DateTime]::UtcNow.ToString('o');concept_key=$key;revision_id=[string](Get-PropertyValue $draft 'current_revision_id');original_response=$OriginalResponse;ui_refresh_failed=$false;approved=$false;publication_authorized=$false}
 $script:LastRejectedLocalAIResponse=$null
 try {
  Refresh-ResearchDraftQueue
  Open-ResearchDraftItem ([pscustomobject]@{concept_key=$key}) $true
  $LocalAIStatus.Text='Непроверенный черновик сохранён для редактирования. Одобрение идеи, печати и публикации не создавалось.'
 } catch {
  $script:LastLocalAISaveReceipt.ui_refresh_failed=$true
  $LocalAIStatus.Text='Непроверенный черновик сохранён, но отображение не обновилось. Найдите его в списке черновиков; повторный модельный запрос не нужен.'
  try{Write-AppLog 'WARN' 'Unapproved local AI draft saved; UI refresh failed after commit.'}catch{}
 }
}
function Set-ForgeLocalAIStorageUncertain($Request,[string]$OriginalResponse,$ErrorObject) {
 $script:LastLocalAISaveReceipt=[pscustomobject]@{schema='forge.local_ai_save_outcome.v1';outcome='uncertain';saved=$null;at_utc=[DateTime]::UtcNow.ToString('o');concept_key=[string](Get-PropertyValue $Request 'Key');expected_revision=[string](Get-PropertyValue $Request 'Revision');original_response=$OriginalResponse;error_type=$ErrorObject.GetType().FullName;approved=$false;publication_authorized=$false;automatic_retry=$false}
 $script:LastRejectedLocalAIResponse=$null
 $LocalAIStatus.Text='Результат сохранения не подтверждён. Проверьте список и версии черновиков перед повтором; исходный ответ сохранён в диагностике, автоматического повтора нет.'
 try{Write-AppLog 'WARN' 'Local AI save completion uncertain; inspect current draft state before any retry.'}catch{}
}
