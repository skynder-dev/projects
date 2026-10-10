# Merch Forge · listing text hints (Publish tab)
# Live, advisory warnings while the owner types: Amazon Merch field lengths and wording that marketplace rules
# usually reject. Nothing is blocked or changed automatically; the owner's Confirm-checks step stays the authority.

$script:ListingLimits = [ordered]@{
    title       = @{min=3;  max=60}
    brand       = @{min=3;  max=50}
    bullet1     = @{min=0;  max=256}
    bullet2     = @{min=0;  max=256}
    description = @{min=75; max=2000}
}
# Phrases that marketplace listing rules commonly reject (claims of status, sales talk, reviews, Amazon itself).
$script:ListingRiskPhrases = @('officially licensed','official','licensed','best seller','best-seller','bestseller','#1','number one','free shipping','on sale','discount','limited time','guarantee','guaranteed','100%','premium quality','high quality','top quality','amazon prime','amazon','5 star','five star')

function Register-ListingHintsUiText {
    if($null -eq $script:UiText){return}
    $texts=@{
        en=@{ 'lst.f.title'='Title'; 'lst.f.brand'='Brand'; 'lst.f.bullet1'='Bullet 1'; 'lst.f.bullet2'='Bullet 2'; 'lst.f.description'='Description'; 'lst.f.keywords'='Keywords';
              'lst.long'='{0}: {1} characters, Amazon allows {2}.'; 'lst.short'='{0}: {1} characters, Amazon needs at least {2}.'; 'lst.word'='{0}: "{1}" is usually rejected in listings (claims, sales talk or Amazon itself).';
              'lst.html'='{0}: remove HTML tags.'; 'lst.emoji'='{0}: remove emoji and special symbols.'; 'lst.samebullets'='Bullet 1 and Bullet 2 are the same.'; 'lst.ok'='Listing text fits Amazon limits. Hints only - nothing is blocked.' }
        ru=@{ 'lst.f.title'='Название'; 'lst.f.brand'='Бренд'; 'lst.f.bullet1'='Пункт 1'; 'lst.f.bullet2'='Пункт 2'; 'lst.f.description'='Описание'; 'lst.f.keywords'='Ключевые слова';
              'lst.long'='{0}: {1} симв., Amazon разрешает {2}.'; 'lst.short'='{0}: {1} симв., Amazon требует не меньше {2}.'; 'lst.word'='{0}: «{1}» обычно не пропускают в карточках (обещания, реклама или упоминание Amazon).';
              'lst.html'='{0}: уберите HTML-теги.'; 'lst.emoji'='{0}: уберите эмодзи и спецсимволы.'; 'lst.samebullets'='Пункт 1 и пункт 2 одинаковые.'; 'lst.ok'='Текст карточки укладывается в лимиты Amazon. Это только подсказки — ничего не блокируется.' }
        es=@{ 'lst.f.title'='Título'; 'lst.f.brand'='Marca'; 'lst.f.bullet1'='Viñeta 1'; 'lst.f.bullet2'='Viñeta 2'; 'lst.f.description'='Descripción'; 'lst.f.keywords'='Palabras clave';
              'lst.long'='{0}: {1} caracteres, Amazon permite {2}.'; 'lst.short'='{0}: {1} caracteres, Amazon pide al menos {2}.'; 'lst.word'='{0}: "{1}" suele rechazarse en las fichas (promesas, publicidad o mencionar Amazon).';
              'lst.html'='{0}: quita las etiquetas HTML.'; 'lst.emoji'='{0}: quita emojis y símbolos especiales.'; 'lst.samebullets'='La viñeta 1 y la viñeta 2 son iguales.'; 'lst.ok'='El texto de la ficha cabe en los límites de Amazon. Solo son sugerencias: nada se bloquea.' }
    }
    foreach($loc in $texts.Keys){ if($null -eq $script:UiText[$loc]){$script:UiText[$loc]=@{}}; foreach($k in $texts[$loc].Keys){$script:UiText[$loc][$k]=$texts[$loc][$k]} }
}

function Get-ListingIssues($Fields) {
    # Pure. $Fields: title, brand, bullet1, bullet2, description, keywords (strings). Returns @(@{field;kind;args}).
    $out=New-Object System.Collections.Generic.List[object]
    foreach($f in @('title','brand','bullet1','bullet2','description','keywords')){
        $v=[string](Get-PropertyValue $Fields $f); $len=$v.Trim().Length
        if($script:ListingLimits.Contains($f)){
            $lim=$script:ListingLimits[$f]
            if($len -gt $lim.max){ $out.Add([pscustomobject]@{field=$f;kind='long';args=@($len,$lim.max)}) }
            elseif($len -gt 0 -and $len -lt $lim.min){ $out.Add([pscustomobject]@{field=$f;kind='short';args=@($len,$lim.min)}) }
        }
        if(-not $v){continue}
        if($f -ne 'keywords'){
            foreach($p in $script:ListingRiskPhrases){
                $rx='(?<![\w#])'+[regex]::Escape($p)+'s?(?!\w)'
                if([regex]::IsMatch($v,$rx,[Text.RegularExpressions.RegexOptions]::IgnoreCase)){ $out.Add([pscustomobject]@{field=$f;kind='word';args=@($p)}); break }
            }
        }
        if($v -match '<\s*/?\s*[a-zA-Z][^>]*>'){ $out.Add([pscustomobject]@{field=$f;kind='html';args=@()}) }
        if($v -match '[\uD800-\uDBFF][\uDC00-\uDFFF]' -or $v -match '[☀-➿]'){ $out.Add([pscustomobject]@{field=$f;kind='emoji';args=@()}) }
    }
    $b1=([string](Get-PropertyValue $Fields 'bullet1')).Trim(); $b2=([string](Get-PropertyValue $Fields 'bullet2')).Trim()
    if($b1 -and $b1 -eq $b2){ $out.Add([pscustomobject]@{field='bullet2';kind='samebullets';args=@()}) }
    return $out.ToArray()
}
function Format-ListingIssue($Issue) {
    $label=Get-UiText ('lst.f.'+$Issue.field) $Issue.field
    $tpl=Get-UiText ('lst.'+$Issue.kind) ''
    return ('• '+[string]::Format([Globalization.CultureInfo]::InvariantCulture,$tpl,[object[]](@($label)+@($Issue.args))))
}
function Update-ListingHints {
    if($null -eq $PublicationListingHints){return}
    try {
        $f=[pscustomobject]@{title=[string]$PublicationTitleBox.Text;brand=[string]$PublicationBrandBox.Text;bullet1=[string]$PublicationBullet1Box.Text;bullet2=[string]$PublicationBullet2Box.Text;description=[string]$PublicationDescriptionBox.Text;keywords=[string]$PublicationKeywordsBox.Text}
        $issues=@(Get-ListingIssues $f)
        $any=(@($f.PSObject.Properties | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.Value) }).Count -gt 0)
        $PublicationListingHints.Text=if($issues.Count){(@($issues | ForEach-Object { Format-ListingIssue $_ })) -join [Environment]::NewLine}elseif($any){Get-UiText 'lst.ok' ''}else{''}
        $PublicationListingHints.Visibility=if([string]::IsNullOrWhiteSpace($PublicationListingHints.Text)){'Collapsed'}else{'Visible'}
    } catch { Write-AppLog 'WARN' ('Listing hints failed: '+$_.Exception.Message) }
}
