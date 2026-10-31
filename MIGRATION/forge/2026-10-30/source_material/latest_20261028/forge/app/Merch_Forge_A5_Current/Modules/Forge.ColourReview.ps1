# Free text supplies review signals only; explicit HEX plan is the deterministic prototype.
function Get-ForgePositiveColourMentions([string]$Text,[ValidateSet('garment','ink')]$Side,[bool]$NoInkContext=$false){
 $found=@();$alternative=$false
 $colour='(?<colour>угольно[- ]ч[её]рн\w*|т[её]мно[- ]сер\w*|светло[- ]сер\w*|ч[её]рн\w*|графит\w*|бел\w*|красн\w*|син\w*|зел[её]н\w*|сер\w*|black|white|red|blue|green)'
 $noun=if($Side-ceq'garment'){'(?:футболк\w*|(?:цвет\s+)?одежд\w*)'}else{'(?:краск\w*|чернил\w*)'}
 $pattern=if($Side-ceq'garment'){'(?<![\p{L}\p{N}_])(?:'+$noun+'(?:\s*:\s*|\s+)(?:(?:предлагается|выбрана|будет)\s+)?(?:цвета\s+)?(?:не\s+)?'+$colour+'|'+$colour+'\s+'+$noun+')\b'}else{'(?<![\p{L}\p{N}_])'+$colour+'\b(?:\s+'+$noun+')?'}
 foreach($clause in @($Text-split'[.!?;,\r\n]+')){
  foreach($m in [regex]::Matches($clause,'(?i)'+$pattern)){
   $before=$clause.Substring(0,$m.Index);$after=$clause.Substring($m.Index+$m.Length)
   $negated=($m.Value-match'(?i)\bне\b'-or$before-match'(?i)\b(?:не\s+(?:(?:использовать|выбирать|выбрана|нужна|печатать|рекомендуется)\s+)?|без\s+)$'-or$after-match'(?i)^\s+не\s+(?:используется|использовать|выбрана|нужна|подходит|выбирается)\b')
   if($negated){continue}
   # A named unprinted space is not a positive ink, even when listed in ink_palette.
   if($Side-ceq'ink'-and$after-match'(?i)^\s+(?:пространств\w*|област\w*|space|areas?)\b'-and($NoInkContext-or$clause-match'(?i)alpha[- ]zero|никакой\s+краск|без\s+краск|незапечатан')){continue}
   $word=$m.Groups['colour'].Value
   $kind=if($word-match'(?i)^(?:угольно|ч[её]рн|графит|т[её]мно|black)'){'dark'}elseif($word-match'(?i)^(?:бел|светло|white)'){'light'}else{'other'}
   $found+=@($kind)
   if($clause-match'(?i)\b(?:или|например|возможно|либо)\b'){$alternative=$true}
  }
 }
 return [pscustomobject]@{positive=@($found|Select-Object -Unique);alternative=$alternative}
}
function Get-ForgeInkPaletteMentions($Entries){
 # An explicit no-ink element is NEVER evidence of ink, irrespective of word order.
 # Owners can supply an actual ink in a separate unambiguous array element.
 $positive=@();$alternative=$false;$mixed=$false
 foreach($entry in @($Entries)){
  if($entry-isnot[string]){continue}
  $noInk=$entry-match'(?i)alpha[- ]zero|никакой\s+краск|без\s+краск|незапечатан'
  if($noInk){
   # An ink noun outside the explicit no-ink phrase makes the element mixed.
   # This affects review only; no colour from the element can become ink evidence.
   $remaining=[regex]::Replace($entry,'(?i)никакой\s+краск\w*|без\s+краск\w*','')
   if($remaining-match'(?i)\bкраск\w*|\bчернил\w*'){$mixed=$true}
   continue
  }
  $part=Get-ForgePositiveColourMentions -Text $entry -Side ink
  $positive+=@($part.positive);if($part.alternative){$alternative=$true}
 }
 return [pscustomobject]@{positive=@($positive|Select-Object -Unique);alternative=$alternative;review_required=$mixed}
}
function Get-ForgeColourReviewIssues($Fields){
 $issues=@();$palette=@($Fields.production_spec.ink_palette)-join'. '
 foreach($clause in @($palette-split'[.!?;\r\n]+')){
  foreach($m in [regex]::Matches($clause,'(?i)(?<![\p{L}\p{N}_])(?:бел\w*\s+прозрачн\w*|прозрачн\w*\s+бел\w*|transparent\s+white)\b')){
   $before=$clause.Substring(0,$m.Index)
   if($before-notmatch'(?i)\bне\s+(?:использовать\s+)?$'){$issues+='COLOUR_TRANSPARENT_INK: alpha-zero is empty space, not transparent white ink.'}
  }
  if($clause-match'(?i)(?<![\p{L}\p{N}_])(?:ч[её]рн\w*|black)\b[^.!?]{0,70}(?:любом\s+фоне|any\s+background)'-and$clause-notmatch'(?i)\bне\s+использовать\b'){$issues+='COLOUR_UNIVERSAL_CONTRAST: universal contrast claim needs correction.'}
 }
 $g=Get-ForgePositiveColourMentions ([string]$Fields.visual_direction_text) garment
 $i=Get-ForgeInkPaletteMentions -Entries @($Fields.production_spec.ink_palette)
 $unresolvedGarment=($g.positive.Count-eq0-and([string]$Fields.visual_direction_text)-match'(?i)\bфутболк\w*\s+не\s+')
 if($i.review_required-or($i.positive.Count-eq0-or$Fields.production_spec.ink_palette-isnot[Array])-or$unresolvedGarment-or$g.alternative-or$i.alternative-or$g.positive.Count-gt1-or$g.positive-contains'other'-or$i.positive-contains'other'){
  $issues+='COLOUR_SELECTION_REVIEW_REQUIRED: free text does not establish a reliable technical pair; draft may be saved, artwork is not authorised.'
 }elseif($g.positive.Count-eq1-and$g.positive[0]-ceq'dark'-and$i.positive.Count-eq1-and$i.positive[0]-ceq'dark'){
  $issues+='COLOUR_DARK_ON_DARK: text positively names a dark pair; contrast review required, physical print suitability unverified.'
 }
 return @($issues|Select-Object -Unique)
}
function Get-ForgeSRGBLuminance([string]$Hex){
 if($Hex-cnotmatch'^#[0-9A-Fa-f]{6}$'){throw 'COLOUR_HEX_REQUIRED: use explicit #RRGGBB'}
 $channels=@();foreach($offset in @(1,3,5)){$c=[Convert]::ToInt32($Hex.Substring($offset,2),16)/255.0;$channels+=@($(if($c-le0.04045){$c/12.92}else{[Math]::Pow(($c+0.055)/1.055,2.4)}))}
 return 0.2126*$channels[0]+0.7152*$channels[1]+0.0722*$channels[2]
}
function New-ForgeTechnicalColourPlan([string]$GarmentHex,[string[]]$InkHex){
 if(!$InkHex-or$InkHex.Count-gt12){throw 'COLOUR_INKS_REQUIRED'}
 $g=Get-ForgeSRGBLuminance $GarmentHex;$ratios=@()
 foreach($ink in $InkHex){$i=Get-ForgeSRGBLuminance $ink;$ratio=([Math]::Max($g,$i)+0.05)/([Math]::Min($g,$i)+0.05);if($ratio-lt4.5){throw 'COLOUR_SCREEN_CONTRAST_LOW: owner must choose another pair; no automatic substitution'};$ratios+=@($ratio)}
 return [pscustomobject]@{schema='forge.owner_technical_colours.prototype.v1';garment_hex=$GarmentHex.ToUpperInvariant();ink_hex=@($InkHex|ForEach-Object{$_.ToUpperInvariant()});screen_contrast_ratios=$ratios;threshold=4.5;owner_selection_required=$true;print_quality_verified=$false;approval_created=$false}
}

function Get-ForgeTransparencyReviewIssues($Fields){
 # Bind an opacity mention to a local explicit subject, not to any earlier canvas word.
 # Limited textual review signal; no claim of full Russian semantic parsing.
 $design=@($Fields.visual_direction_text,$Fields.production_spec.composition,$Fields.production_spec.illustration)-join"`n"
 $canvas='незапечатан\w*\s+(?:област\w*|участк\w*|пространств\w*)|област\w*[^.!?\r\n]{0,70}не\s+покрыт\w*\s+чернил\w*|\b(?:PNG|канвас|холст|пиксели)\b'
 $physical='\b(?:ткань|футболка|одежда|материал)\b'
 $ink='\b(?:краска|чернила|буквы|текст|рисунок)\b'
 foreach($sentence in @($design-split'[.!?\r\n]+')){
  $subjects=@()
  foreach($pair in @(@('canvas',$canvas),@('physical',$physical),@('ink',$ink))){
   foreach($m in [regex]::Matches($sentence,'(?i)'+$pair[1])){$subjects+=@([pscustomobject]@{kind=$pair[0];index=$m.Index;length=$m.Length})}
  }
  $subjects=@($subjects|Sort-Object index)
  foreach($opacity in [regex]::Matches($sentence,'(?i)\b(?:непрозрачн\w*|не\s+прозрачн\w*)')){
   $before=$sentence.Substring(0,$opacity.Index)
   if($before-match'(?i)\bне\s+(?:(?:должн\w*|могут|будут)\s+)?(?:(?:быть|оставаться|остают\w*|становиться|являют\w*)\s+)?$'){continue}
   $subject=@($subjects|Where-Object{$_.index-le$opacity.Index}|Select-Object -Last 1)
   # Attributive form: "opaque white ink" belongs to the following noun, not an earlier PNG.
   $next=@($subjects|Where-Object{$_.index-ge($opacity.Index+$opacity.Length)}|Select-Object -First 1)
   if($next.Count){
    $gap=$sentence.Substring($opacity.Index+$opacity.Length,$next[0].index-$opacity.Index-$opacity.Length)
    $attributive=$gap-match'(?i)^\s*(?:[\p{L}-]+(?:ая|яя|ый|ий|ой|ое|ые|ие|ыми|ими)\s+){0,2}$'
    # Explicit postpositive subject: "opaque remains the physical fabric".
    # Commas/semicolons or arbitrary text cannot bridge this local binding.
    $postpositive=$gap-match'(?i)^\s*(?:(?:оста[её]тся|остаются|является|являются|становится|становятся|будет|будут)\s+|(?:долж(?:ен|на|но|ны)|может|могут)\s+(?:быть|оставаться)\s+)(?:только\s+)?(?:[\p{L}-]+(?:ая|яя|ый|ий|ой|ое|ые|ие|ыми|ими)\s+){0,2}$'
    if($attributive-or$postpositive){$subject=$next}
   }
   if($subject.Count-and$subject[0].kind-ceq'canvas'){
    return 'DESIGN_TRANSPARENCY_REVIEW_REQUIRED: output-canvas subject is described as opaque; resolve canvas alpha before artwork. Physical garment and ink opacity are separate.'
   }
  }
 }
}
function Get-ForgeDesignOutputReviewIssues($Fields){
 return @((Get-ForgeColourReviewIssues $Fields)) + @((Get-ForgeTransparencyReviewIssues $Fields))
}
