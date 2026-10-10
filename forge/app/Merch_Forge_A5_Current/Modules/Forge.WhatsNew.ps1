# Merch Forge · "What's new" card on Home after an update
# Shown once per version (until "Got it"), in the UI language; non-modal so it never blocks anything.
$script:WhatsNewPath = Join-Path $PSScriptRoot '..\Data\Forge.WhatsNew.json'
$script:WhatsNewData = $null

function Register-WhatsNewUiText {
    if($null -eq $script:UiText){return}
    $texts=@{ en=@{'wn.title'="What's new in Merch Forge {0}";'wn.ok'='Got it'}; ru=@{'wn.title'='Что нового в Merch Forge {0}';'wn.ok'='Понятно'}; es=@{'wn.title'='Novedades de Merch Forge {0}';'wn.ok'='Entendido'} }
    foreach($loc in $texts.Keys){ if($null -eq $script:UiText[$loc]){$script:UiText[$loc]=@{}}; foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]} }
}
function Get-WhatsNewSeenPath { return (Join-Path $script:StateRoot 'whats-new-seen.txt') }
function Get-WhatsNewData {
    if($null -eq $script:WhatsNewData){ try{ $script:WhatsNewData=Get-Content -LiteralPath $script:WhatsNewPath -Raw -Encoding UTF8 | ConvertFrom-Json }catch{ $script:WhatsNewData=$false } }
    if($script:WhatsNewData -eq $false){ return $null }; return $script:WhatsNewData
}
function Test-WhatsNewDue {
    $d=Get-WhatsNewData; if($null -eq $d){ return $false }
    $ver=[string](Get-PropertyValue $d 'version'); if([string]::IsNullOrWhiteSpace($ver)){ return $false }
    $seen=''; try{ $seen=([string](Get-Content -LiteralPath (Get-WhatsNewSeenPath) -Raw -ErrorAction Stop)).Trim() }catch{}
    return ($seen -ne $ver)
}
function Update-WhatsNewCard {
    if($null -eq $WhatsNewCard){return}
    try {
        if(-not (Test-WhatsNewDue)){ $WhatsNewCard.Visibility='Collapsed'; return }
        $d=Get-WhatsNewData; $loc=if(@('en','ru','es') -contains [string]$script:Locale){[string]$script:Locale}else{'en'}
        $items=@(Get-PropertyValue (Get-PropertyValue $d 'items') $loc); if($items.Count -eq 0){ $items=@(Get-PropertyValue (Get-PropertyValue $d 'items') 'en') }
        $shortVer=([string](Get-PropertyValue $d 'version') -split '-')[0]
        $WhatsNewTitle.Text=(Get-UiText 'wn.title' "What's new in Merch Forge {0}") -f $shortVer
        $WhatsNewText.Text=(@($items | ForEach-Object { '• '+[string]$_ })) -join [Environment]::NewLine
        $WhatsNewDismissButton.Content=Get-UiText 'wn.ok' 'Got it'
        $WhatsNewCard.Visibility='Visible'
    } catch { Write-AppLog 'WARN' ("What's new card failed: "+$_.Exception.Message) }
}
function Dismiss-WhatsNew {
    try { $d=Get-WhatsNewData; if($null -ne $d){ Ensure-Dir $script:StateRoot; [IO.File]::WriteAllText((Get-WhatsNewSeenPath),[string](Get-PropertyValue $d 'version'),(New-Object Text.UTF8Encoding($false))) } } catch { Write-AppLog 'WARN' ("What's new could not be saved: "+$_.Exception.Message) }
    if($null -ne $WhatsNewCard){ $WhatsNewCard.Visibility='Collapsed' }
}
