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
function Translate-UiMessage([string]$Text,[int]$Depth=0) {
    if([string]::IsNullOrEmpty($Text)){ return $Text }
    $loc = [string]$script:Locale; if($loc -notin @('ru','es')){ return $Text }
    $hit = $null
    if($null -ne $script:MessageExact -and $script:MessageExact.TryGetValue($Text,[ref]$hit)){ $v=[string](Get-PropertyValue $hit $loc); if($v){ return $v }; return $Text }
    foreach($p in @($script:MessagePatterns)){
        $m = $p.rx.Match($Text); if(-not $m.Success){ continue }
        $out = [string](Get-PropertyValue $p.entry $loc); if([string]::IsNullOrEmpty($out)){ return $Text }
        # Variable parts may themselves be known messages (e.g. 'Draft was not created: <inner error>').
        for($i=0; $i -lt 10; $i++){ $g=$m.Groups['p'+$i]; if($g.Success){ $val=$g.Value; if($Depth -lt 3){ $val=Translate-UiMessage $val ($Depth+1) }; $out = $out.Replace('{'+$i+'}', $val) } }
        return $out
    }
    return $Text
}
function Test-KnownUiMessage([string]$Text) {
    # A message written for people (it is in the translation table) is shown as-is instead of a generic error.
    # Server/network failures keep the friendly generic mapping.
    if([string]::IsNullOrWhiteSpace($Text)){ return $false }
    if($Text -match 'HTTP [0-9]{3}|API_ERROR|EMPTY_RESPONSE|timed out|unable to connect|name resolution|No such host'){ return $false }
    $hit=$null; if($null -ne $script:MessageExact -and $script:MessageExact.TryGetValue($Text,[ref]$hit)){ return $true }
    foreach($p in @($script:MessagePatterns)){ $en=[string](Get-PropertyValue $p.entry 'en'); if($en.StartsWith('{0}')){ continue }; if($p.rx.IsMatch($Text)){ return $true } }
    return $false
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
