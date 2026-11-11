. (Join-Path $PSScriptRoot 'Forge.BriefApproval.ps1')
# Client-side validator for the schema vocabulary Forge itself emits.
# Runtime schema enforcement is not treated as proof of a valid response.
function Assert-ForgeResponseNode($Value,$Schema,[string]$Path='$',[int]$Depth=0){
 if($Depth-gt20){throw 'AI_SCHEMA_CONTRACT_VIOLATION: response nesting exceeds limit'}
 function Fail([string]$Reason){throw ('AI_SCHEMA_CONTRACT_VIOLATION: '+$Path+': '+$Reason)}
 switch([string]$Schema.type){
  'object'{
   if($Value-isnot[pscustomobject]){Fail 'expected object'}
   $actual=@($Value.PSObject.Properties.Name)
   $declared=if($Schema.properties-is[Collections.IDictionary]){@($Schema.properties.Keys)}else{@($Schema.properties.PSObject.Properties.Name)}
   foreach($name in $actual){if($declared-cnotcontains$name-and$Schema.additionalProperties-eq$false){Fail ('undeclared field '+$name)}}
   foreach($name in @($Schema.required)){if($actual-cnotcontains$name){Fail ('missing field '+$name)}}
   foreach($name in $actual){if($declared-ccontains$name){Assert-ForgeResponseNode $Value.$name $Schema.properties.$name ($Path+'.'+$name) ($Depth+1)}}
  }
  'string'{
   if($Value-isnot[string]){Fail 'expected string'}
   if($null-ne$Schema.minLength-and$Value.Length-lt$Schema.minLength){Fail 'string below minLength'}
   if($null-ne$Schema.maxLength-and$Value.Length-gt$Schema.maxLength){Fail 'string exceeds maxLength'}
   if($Schema.pattern-and![regex]::IsMatch($Value,[string]$Schema.pattern)){Fail 'pattern mismatch'}
   if($null-ne$Schema.enum-and@($Schema.enum)-cnotcontains$Value){Fail 'value outside exact enum'}
  }
  'array'{
   if($Value-isnot[Array]){Fail 'expected array'}
   if($null-ne$Schema.minItems-and$Value.Count-lt$Schema.minItems){Fail 'array below minItems'}
   if($null-ne$Schema.maxItems-and$Value.Count-gt$Schema.maxItems){Fail 'array exceeds maxItems'}
   for($i=0;$i-lt$Value.Count;$i++){Assert-ForgeResponseNode $Value[$i] $Schema.items ($Path+'['+$i+']') ($Depth+1)}
  }
  default{Fail 'unsupported Forge schema type; refuse unchecked response'}
 }
}
function Assert-ForgeLocalAIWireContract([string]$Content,$Schema){
 if($Content.Length-gt24000){throw 'AI_SCHEMA_CONTRACT_VIOLATION: response exceeds bound'}
 try{$value=ConvertFrom-ForgeJsonObjectStrict $Content}catch{throw ('AI_SCHEMA_CONTRACT_VIOLATION: raw JSON rejected before schema validation: '+$_.Exception.Message)}
 Assert-ForgeResponseNode $value $Schema
 # Existing canonical parser/strict JSON parser still performs duplicate-key and semantic checks.
}
