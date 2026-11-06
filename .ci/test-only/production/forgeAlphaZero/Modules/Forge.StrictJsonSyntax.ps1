# Strict JSON and Unicode scalar policy before type-preserving conversion.
function Assert-ForgeStrictJsonSyntax([string]$Text) {
 if(-not ('ForgeStrictJsonSyntaxV1' -as [type])){
  Add-Type -TypeDefinition @'
using System;
public sealed class ForgeStrictJsonSyntaxV1 {
 string text; int at;
 ForgeStrictJsonSyntaxV1(string value) { text=value; }
 void Error() { throw new FormatException("Strict JSON syntax rejected at offset "+at); }
 void Space() { while(at<text.Length && (text[at]==' '||text[at]=='\t'||text[at]=='\r'||text[at]=='\n'))at++; }
 bool Take(char c) { if(at<text.Length && text[at]==c){at++;return true;}return false; }
 void Need(char c) { if(!Take(c))Error(); }
 void Word(string word) { foreach(char c in word)Need(c); }
 bool Digit() { return at<text.Length && text[at]>='0' && text[at]<='9'; }
 void String() {
  Need('"'); bool closed=false;var decoded=new System.Text.StringBuilder();
  while(at<text.Length){char c=text[at++];if(c=='"'){closed=true;break;}if(c<32)Error();
   if(c=='\\') { if(at>=text.Length)Error();char e=text[at++];
    if(e=='u'){int unit=0;for(int n=0;n<4;n++){if(at>=text.Length)Error();char h=text[at++];int digit=h>='0'&&h<='9'?h-'0':h>='a'&&h<='f'?h-'a'+10:h>='A'&&h<='F'?h-'A'+10:-1;if(digit<0)Error();unit=unit*16+digit;}decoded.Append((char)unit);}
    else if(e!='"'&&e!='\\'&&e!='/'&&e!='b'&&e!='f'&&e!='n'&&e!='r'&&e!='t')Error();
    else decoded.Append(e);
   }
   else decoded.Append(c);
  }
  if(!closed)Error();
  // Reject isolated UTF16 surrogates, escaped or literal. Preserve valid pairs
  // and literal U+FFFD; never silently replace or normalize string contents.
  for(int n=0;n<decoded.Length;n++){char c=decoded[n];if(char.IsHighSurrogate(c)){if(n+1>=decoded.Length||!char.IsLowSurrogate(decoded[n+1]))throw new FormatException("JSON string contains an invalid Unicode scalar");n++;}else if(char.IsLowSurrogate(c))throw new FormatException("JSON string contains an invalid Unicode scalar");}
 }
 void Number(){Take('-');if(!Take('0')){if(at>=text.Length||text[at]<'1'||text[at]>'9')Error();while(Digit())at++;}
  if(Take('.')){if(!Digit())Error();while(Digit())at++;}
  if(Take('e')||Take('E')){if(!Take('+'))Take('-');if(!Digit())Error();while(Digit())at++;}
 }
 void Value(int depth){if(depth>64)Error();Space();if(at>=text.Length)Error();char c=text[at];
  if(c=='{'){at++;Space();if(Take('}'))return;while(true){Space();String();Space();Need(':');Value(depth+1);Space();if(Take('}'))return;Need(',');}}
  else if(c=='['){at++;Space();if(Take(']'))return;while(true){Value(depth+1);Space();if(Take(']'))return;Need(',');}}
  else if(c=='"')String();else if(c=='t')Word("true");else if(c=='f')Word("false");else if(c=='n')Word("null");else Number();
 }
 public static void Validate(string value){if(value==null)throw new FormatException("Null JSON text");ForgeStrictJsonSyntaxV1 p=new ForgeStrictJsonSyntaxV1(value);p.Value(0);p.Space();if(p.at!=value.Length)p.Error();}
 // Newtonsoft may replace a valid pair split between a literal UTF16 unit and
 // an escape. Encode literal surrogate units for conversion only; raw input
 // remains untouched, and decoded scalar content is identical.
 public static string ConversionText(string value){var result=new System.Text.StringBuilder();foreach(char c in value){if(char.IsSurrogate(c))result.Append("\\u").Append(((int)c).ToString("x4"));else result.Append(c);}return result.ToString();}
}
'@
 }
 [ForgeStrictJsonSyntaxV1]::Validate($Text)
}
