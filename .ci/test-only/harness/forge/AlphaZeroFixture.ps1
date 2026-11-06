function New-AlphaZeroFixtureFields {
 $fixture=[IO.File]::ReadAllText((Join-Path $PSScriptRoot '../../fixtures/forge/card.json'),[Text.Encoding]::UTF8)|ConvertFrom-Json
 $brief=$fixture.cards[0].control_state.brief
 $fields=[ordered]@{};foreach($name in @('title','hook','concept_text','target_buyer','purchase_reason','differentiation','visual_direction_text','production_spec')){$fields[$name]=$brief.$name}
 $value=$fields|ConvertTo-Json -Depth 40|ConvertFrom-Json
 $value.title='Русский "заголовок" для проверки технического токена'
 $value.concept_text=[regex]::Replace([string]$value.concept_text,'(?:Источник|Ссылка)\s+\[E1\][\s\S]*$','').Trim()
 $value.production_spec.ink_palette=@('белые чернила')
 $value.visual_direction_text='Незапечатанные области PNG прозрачные alpha=0, физическая ткань непрозрачная.'
 $value.production_spec.composition='Крупная белая надпись: '+$value.hook+'. Незапечатанные области PNG прозрачные alpha=0.'
 return $value
}
function Set-AlphaZeroFixtureToken($Fields,[string]$Token){
 $Fields.visual_direction_text='Незапечатанные области PNG прозрачные '+$Token+', непрозрачной остаётся физическая ткань.'
 $Fields.production_spec.composition='Крупная белая надпись: '+$Fields.hook+'. Незапечатанные области PNG прозрачные '+$Token+'.'
}
