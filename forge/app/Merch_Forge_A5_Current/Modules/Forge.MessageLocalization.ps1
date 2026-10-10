# Merch Forge · runtime message localization
# Status bar, busy banner, error and confirmation texts are produced in English in many places (literals, templates,
# concatenations). Instead of touching every call site, known English templates are translated where they are shown.
# Data: Data\Forge.MessageTranslations.json ({en, ru, es}; {0}.. mark variable parts that are carried over unchanged).
$script:MessageExact = @{}
$script:MessagePatterns = @()
$script:TranslatingUiMessage = $false

function Initialize-MessageTranslations {
    $script:MessageExact = New-Object 'System.Collections.Generic.Dictionary[string,object]'
    $script:MessagePatterns = @()
    $path = Join-Path (Split-Path -Parent $script:ModuleRoot) 'Data\Forge.MessageTranslations.json'
    if(-not (Test-Path -LiteralPath $path -PathType Leaf)){ return }
    try { $j = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json } catch { Write-AppLog 'WARN' ('Message translations unreadable: '+$_.Exception.Message); return }
    foreach($e in @(Get-PropertyValue $j 'entries')){
        $en = [string](Get-PropertyValue $e 'en'); if([string]::IsNullOrEmpty($en)){continue}
        if($en -match '\{\d+\}'){
            $rx = '^' + ([regex]::Escape($en) -replace '\\\{(\d+)\}','(?<p$1>[\s\S]*?)') + '$'
            $script:MessagePatterns += [pscustomobject]@{ rx = (New-Object System.Text.RegularExpressions.Regex($rx,[System.Text.RegularExpressions.RegexOptions]::Singleline)); entry = $e }
        } else { $script:MessageExact[$en] = $e }
    }
}
function Translate-UiMessage([string]$Text) {
    if([string]::IsNullOrEmpty($Text)){ return $Text }
    $loc = [string]$script:Locale; if($loc -notin @('ru','es')){ return $Text }
    $hit = $null
    if($null -ne $script:MessageExact -and $script:MessageExact.TryGetValue($Text,[ref]$hit)){ $v=[string](Get-PropertyValue $hit $loc); if($v){ return $v }; return $Text }
    foreach($p in @($script:MessagePatterns)){
        $m = $p.rx.Match($Text); if(-not $m.Success){ continue }
        $out = [string](Get-PropertyValue $p.entry $loc); if([string]::IsNullOrEmpty($out)){ return $Text }
        for($i=0; $i -lt 10; $i++){ $g=$m.Groups['p'+$i]; if($g.Success){ $out = $out.Replace('{'+$i+'}', $g.Value) } }
        return $out
    }
    return $Text
}
function Register-MessageLocalizationSinks {
    $dpd = [System.ComponentModel.DependencyPropertyDescriptor]::FromProperty([System.Windows.Controls.TextBlock]::TextProperty,[System.Windows.Controls.TextBlock])
    foreach($tb in @($StatusText,$BusyText,$LocalCoreStatusText)){
        if($null -eq $tb){ continue }
        $dpd.AddValueChanged($tb,[EventHandler]{
            param($sender,$e)
            if($script:TranslatingUiMessage){ return }
            $script:TranslatingUiMessage = $true
            try { $cur=[string]$sender.Text; $n = Translate-UiMessage $cur; if($n -ne $cur){ $sender.Text = $n } } catch {} finally { $script:TranslatingUiMessage = $false }
        })
    }
}
