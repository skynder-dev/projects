# Mount inside the existing pinned LocalAI panel only. No Window, timer or auto-review.
function Clear-ForgeSemanticReviewUiBinding {
 $script:SemanticReviewDisplayedSnapshot=$null
 $script:SemanticReviewSubmit.IsEnabled=$false
 $script:SemanticReviewOutcome.SelectedIndex=-1
 # Preserve the owner's note buffer; cancel/stale submission never discards it.
}
function Initialize-ForgeSemanticReviewUI {
 if($null-ne(Get-Variable SemanticReviewExpander -Scope Script -ErrorAction SilentlyContinue)){return}
 $parent=$LocalAIStatus.Parent
 if($null-eq$parent-or$parent-isnot[Windows.Controls.Panel]){throw 'Existing pinned LocalAIStatus.Parent panel unavailable; no synthetic shell created'}
 $script:SemanticReviewExpander=New-Object Windows.Controls.Expander;$script:SemanticReviewExpander.Header='Проверка смысла сохранённой ревизии — отдельное решение владельца'
 $panel=New-Object Windows.Controls.StackPanel;$script:SemanticReviewExpander.Content=$panel
 $script:SemanticReviewOpen=New-Object Windows.Controls.Button;$script:SemanticReviewOpen.Content='Показать сохранённый brief и источники';[void]$panel.Children.Add($script:SemanticReviewOpen)
 $script:SemanticReviewView=New-Object Windows.Controls.TextBox;$script:SemanticReviewView.IsReadOnly=$true;$script:SemanticReviewView.AcceptsReturn=$true;$script:SemanticReviewView.TextWrapping='Wrap';$script:SemanticReviewView.MaxHeight=350;$script:SemanticReviewView.VerticalScrollBarVisibility='Auto';[void]$panel.Children.Add($script:SemanticReviewView)
 $script:SemanticReviewOutcome=New-Object Windows.Controls.ComboBox
 foreach($pair in @(@('NEEDS_EDIT','Нужны исправления'),@('REJECTED','Отклонено'),@('REVIEWED_FOR_NEXT_REVIEW_STAGE','Смысл проверен владельцем для следующего этапа проверки'))){$item=New-Object Windows.Controls.ComboBoxItem;$item.Tag=$pair[0];$item.Content=$pair[1];[void]$script:SemanticReviewOutcome.Items.Add($item)}
 $script:SemanticReviewOutcome.SelectedIndex=-1;[void]$panel.Children.Add($script:SemanticReviewOutcome)
 $script:SemanticReviewNote=New-Object Windows.Controls.TextBox;$script:SemanticReviewNote.AcceptsReturn=$true;$script:SemanticReviewNote.TextWrapping='Wrap';$script:SemanticReviewNote.MaxLength=1000;[void]$panel.Children.Add($script:SemanticReviewNote)
 $script:SemanticReviewSubmit=New-Object Windows.Controls.Button;$script:SemanticReviewSubmit.Content='Я проверил(а) показанную ревизию — записать выбранный исход';$script:SemanticReviewSubmit.IsEnabled=$false;[void]$panel.Children.Add($script:SemanticReviewSubmit)
 $script:SemanticReviewCancel=New-Object Windows.Controls.Button;$script:SemanticReviewCancel.Content='Отмена проверки';[void]$panel.Children.Add($script:SemanticReviewCancel)
 $script:SemanticReviewStatus=New-Object Windows.Controls.TextBlock;$script:SemanticReviewStatus.TextWrapping='Wrap';$script:SemanticReviewStatus.Text='Исход не выбран. Проверка смысла не является KEEP, разрешением генерации, приёмкой artwork или подтверждением прав и качества печати.';[void]$panel.Children.Add($script:SemanticReviewStatus)
 $script:SemanticReviewOpen.Add_Click({
  try{
   Clear-ForgeSemanticReviewUiBinding
   if($null-eq$script:Current){throw 'Choose an existing saved draft first'}
   $snapshot=Get-ForgeSemanticReviewSnapshot ([string]$script:Current.concept.concept_key)
   # Detached value snapshot: owner sees exactly the value bound to submit.
   $script:SemanticReviewDisplayedSnapshot=ConvertFrom-ForgeJsonObjectStrict ($snapshot|ConvertTo-Json -Depth 60)
   $script:SemanticReviewView.Text=($script:SemanticReviewDisplayedSnapshot|ConvertTo-Json -Depth 60)
   $script:SemanticReviewSubmit.IsEnabled=$true
   $script:SemanticReviewStatus.Text='Показаны сохранённая revision/hash, полный brief, источники и исходная связь текста с изображением/HOLD. Прочитайте их, явно выберите исход и введите примечание. Показ не создаёт решение.'
  }catch{Clear-ForgeSemanticReviewUiBinding;$script:SemanticReviewStatus.Text=$_.Exception.Message}
 })
 $script:SemanticReviewSubmit.Add_Click({
  try{
   if($null-eq$script:SemanticReviewDisplayedSnapshot){throw 'SEMANTIC_REVIEW_DISPLAY_REQUIRED'}
   $selected=$script:SemanticReviewOutcome.SelectedItem
   if($null-eq$selected){throw 'SEMANTIC_REVIEW_OUTCOME_REQUIRED: explicitly choose an outcome'}
   if([string]::IsNullOrWhiteSpace($script:SemanticReviewNote.Text)){throw 'SEMANTIC_REVIEW_NOTE_REQUIRED'}
   $script:LastSemanticReviewUiReceipt=Record-ForgeSemanticReview -Snapshot $script:SemanticReviewDisplayedSnapshot -Outcome ([string]$selected.Tag) -OwnerNote ([string]$script:SemanticReviewNote.Text) -OwnerIntent 'RECORD_EXPLICIT_SEMANTIC_REVIEW'
   Clear-ForgeSemanticReviewUiBinding
   $script:SemanticReviewStatus.Text='Явный исход проверки сохранён для показанной revision/hash. Owner decision, генерация, artwork, права и качество печати не одобрены. Новый edit требует новой проверки.'
  }catch{
   $message=$_.Exception.Message
   if($message-match'STALE|CHANGED|changed|UNSAVED|source|Source|Bound source'){Clear-ForgeSemanticReviewUiBinding}
   $script:SemanticReviewStatus.Text=$message
  }
 })
 $script:SemanticReviewCancel.Add_Click({Clear-ForgeSemanticReviewUiBinding;$script:SemanticReviewStatus.Text='Проверка отменена; решение не записано. Текст примечания сохранён в поле.'})
 [void]$parent.Children.Add($script:SemanticReviewExpander)
}
