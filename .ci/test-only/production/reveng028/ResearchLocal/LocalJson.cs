using System;using System.IO;using System.Text;using System.Collections.Generic;using System.Web.Script.Serialization;
public static class LocalJson {
 public const int Limit=8388608;
 public static string TemporaryPath(string path){return Path.Combine(Path.GetDirectoryName(path),Guid.NewGuid().ToString("N").Substring(0,12)+".tmp");}
 public static string BackupPath(string path){return Path.ChangeExtension(path,".prev");}
 public static string Decode(byte[] raw){return new UTF8Encoding(false,true).GetString(raw).TrimStart('\ufeff');}
 public static byte[] ReadBytes(string path,int limit){byte[] raw;using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read|FileShare.Delete)){if(file.Length>limit)throw new InvalidDataException("Local JSON exceeds limit; existing file preserved");raw=new byte[(int)file.Length];int n=0;while(n<raw.Length){int count=file.Read(raw,n,raw.Length-n);if(count==0)throw new EndOfStreamException("Partial local JSON read");n+=count;}if(file.ReadByte()!=-1)throw new InvalidDataException("Local JSON changed while reading");}return raw;}
 public static string ReadText(string path,int limit){return Decode(ReadBytes(path,limit));}
 public static void WriteTemporary(string path,string text){byte[] raw=new UTF8Encoding(false,true).GetBytes(text);using(var file=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None)){file.Write(raw,0,raw.Length);file.Flush(true);}}
 sealed class Frame{public char Kind;public bool NeedKey;public HashSet<string>Keys=new HashSet<string>();}
 // JavaScriptSerializer accepts JavaScript extensions (single quotes, +1, 01,
 // .5, 1., Unicode whitespace). Validate JSON grammar before using that decoder.
 sealed class Grammar {
  readonly string text;int pos;
  Grammar(string raw){text=raw;}
  void Bad(){throw new InvalidDataException("Invalid JSON grammar; existing file preserved");}
  void Space(){while(pos<text.Length&&(text[pos]==' '||text[pos]=='\t'||text[pos]=='\r'||text[pos]=='\n'))pos++;}
  bool Take(char c){if(pos<text.Length&&text[pos]==c){pos++;return true;}return false;}
  void Need(char c){if(!Take(c))Bad();}
  bool Digit(){return pos<text.Length&&text[pos]>='0'&&text[pos]<='9';}
  void Digits(){if(!Digit())Bad();while(Digit())pos++;}
  void String(){Need('"');while(pos<text.Length){char c=text[pos++];if(c=='"')return;if(c<32)Bad();if(c=='\\'){if(pos>=text.Length)Bad();char e=text[pos++];if(e=='u'){for(int i=0;i<4;i++){if(pos>=text.Length||!Uri.IsHexDigit(text[pos++]))Bad();}}else if("\"\\/bfnrt".IndexOf(e)<0)Bad();}}Bad();}
  void Literal(string word){foreach(char c in word)Need(c);}
  void Value(int depth){Space();if(pos>=text.Length)Bad();char c=text[pos];
   if(c=='{'||c=='['){if(depth>=128)Bad();pos++;Space();char close=c=='{'?'}':']';if(Take(close))return;while(true){if(c=='{'){String();Space();Need(':');}Value(depth+1);Space();if(Take(close))return;Need(',');Space();}}
   if(c=='"'){String();return;}if(c=='t'){Literal("true");return;}if(c=='f'){Literal("false");return;}if(c=='n'){Literal("null");return;}
   Take('-');if(!Take('0'))Digits();if(Take('.'))Digits();if(Take('e')||Take('E')){if(!Take('+'))Take('-');Digits();}
  }
  public static void Validate(string raw){var p=new Grammar(raw);p.Value(0);p.Space();if(p.pos!=raw.Length)p.Bad();}
 }
 public static void ValidateText(string raw){new UTF8Encoding(false,true).GetByteCount(raw);Grammar.Validate(raw);var stack=new Stack<Frame>();var json=new JavaScriptSerializer{MaxJsonLength=Limit,RecursionLimit=128};
  for(int i=0;i<raw.Length;i++){char c=raw[i];if(Char.IsWhiteSpace(c))continue;
   if(c=='"'){int start=i++;for(;i<raw.Length;i++){if(raw[i]=='\\'){if(++i>=raw.Length)throw new InvalidDataException("Incomplete JSON escape");char escaped=raw[i];if(escaped=='u'){if(i+4>=raw.Length)throw new InvalidDataException("Incomplete Unicode escape");int code=Convert.ToInt32(raw.Substring(i+1,4),16);i+=4;if(code>=0xD800&&code<=0xDBFF){if(i+6>=raw.Length||raw[i+1]!='\\'||raw[i+2]!='u')throw new InvalidDataException("Unpaired high surrogate");int low=Convert.ToInt32(raw.Substring(i+3,4),16);if(low<0xDC00||low>0xDFFF)throw new InvalidDataException("Invalid surrogate pair");i+=6;}else if(code>=0xDC00&&code<=0xDFFF)throw new InvalidDataException("Unpaired low surrogate");}else if("\"\\/bfnrt".IndexOf(escaped)<0)throw new InvalidDataException("Invalid JSON escape");continue;}if(raw[i]<32)throw new InvalidDataException("Literal control in JSON string");if(raw[i]=='"')break;}if(i>=raw.Length)throw new InvalidDataException("Unclosed JSON string");string value=json.Deserialize<string>(raw.Substring(start,i-start+1));new UTF8Encoding(false,true).GetByteCount(value);if(stack.Count>0&&stack.Peek().Kind=='{'&&stack.Peek().NeedKey){var frame=stack.Peek();if(!frame.Keys.Add(value))throw new InvalidDataException("Duplicate JSON property; existing file preserved");frame.NeedKey=false;}continue;}
   if(stack.Count>0&&stack.Peek().Kind=='{'&&stack.Peek().NeedKey&&c!='}')throw new InvalidDataException("Expected quoted JSON property");
   if(c=='{'||c=='['){if(stack.Count>=128)throw new InvalidDataException("JSON nesting exceeds128 levels");stack.Push(new Frame{Kind=c,NeedKey=c=='{'});continue;}
   if(c=='}'||c==']'){if(stack.Count==0||stack.Peek().Kind!=(c=='}'?'{':'['))throw new InvalidDataException("Invalid JSON container");if(c=='}'&&stack.Peek().NeedKey&&stack.Peek().Keys.Count>0)throw new InvalidDataException("Trailing object comma");stack.Pop();continue;}
   if(c==','&&stack.Count>0&&stack.Peek().Kind=='{')stack.Peek().NeedKey=true;
  }if(stack.Count!=0)throw new InvalidDataException("Incomplete JSON container");
 }
 static void Finite(object value){if(value is double&&(Double.IsNaN((double)value)||Double.IsInfinity((double)value)))throw new InvalidDataException("Non-finite JSON number");var dict=value as Dictionary<string,object>;if(dict!=null){foreach(var item in dict.Values)Finite(item);return;}var list=value as System.Collections.IList;if(list!=null)foreach(var item in list)Finite(item);}
 public static object ParseValue(string raw){ValidateText(raw);var value=new JavaScriptSerializer{MaxJsonLength=Limit,RecursionLimit=128}.DeserializeObject(raw);Finite(value);return value;}
 public static Dictionary<string,object> ParseObject(string raw){var value=ParseValue(raw) as Dictionary<string,object>;if(value==null)throw new InvalidDataException("Expected local JSON object; existing file preserved");return value;}
 public static Dictionary<string,object> ReadObject(string path){return ParseObject(ReadText(path,Limit));}
}
