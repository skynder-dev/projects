using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Runtime.InteropServices;

// Read-only job presentation. No candidate, decision, raw or queue writes.
public static class AnalysisOutcomePresentation {
 public const string EmptyMessage="Гипотеза не предложена; модель не сообщила причину; это не оценка рынка";
 public sealed class Entry {
  public string JobId,Kind,Message,Text;
  public override string ToString(){return "AI-задание | "+Message+" | "+JobId.Substring(0,Math.Min(12,JobId.Length));}
 }
 static Dictionary<string,object> D(object x){return x as Dictionary<string,object>??new Dictionary<string,object>();}
 static string S(Dictionary<string,object> d,string k){return d.ContainsKey(k)&&d[k]!=null?Convert.ToString(d[k]):"";}
 // Rejected raw output may have been projected into an empty imported array.
 static bool PresentError(object value){
  if(value==null)return false;
  if(value is string)return !String.IsNullOrWhiteSpace((string)value);
  if(value is bool)return (bool)value;
  var array=value as object[];if(array!=null)return array.Length>0;
  var map=value as Dictionary<string,object>;if(map!=null)return map.Count>0;
  return true;
 }
 static string EmptyConflict(Dictionary<string,object> data){
  foreach(string key in new[]{"strict_validation_error","validation_error","validation_errors","parse_error","parse_errors"})
   if(data.ContainsKey(key)&&PresentError(data[key]))return "Explicit "+key;
  if(data.ContainsKey("abstained")&&(!(data["abstained"] is bool)||!(bool)data["abstained"]))return "Contradictory abstained marker";
  foreach(string key in new[]{"raw_output_cards","output_cards"})
   if(data.ContainsKey(key)&&(!(data[key] is int)||(int)data[key]!=0))return "Contradictory "+key+" count";
  return "";
 }
 static void ValidateRawPointer(Dictionary<string,object> saved){
  object value;if(!saved.TryGetValue("raw_response_retained_in_run",out value)||value==null)return;
  var pointer=value as string;
  if(pointer=="")return; // Optional/legacy reference remains optional, not raw-byte proof.
  if(pointer==null||pointer!=pointer.Trim()||pointer.StartsWith("/")||pointer.StartsWith("\\")||pointer.IndexOfAny(new[]{'<','>',':','"','|','?','*'})>=0||pointer.Any(Char.IsControl))throw new InvalidDataException("Malformed or outside raw evidence pointer");
  foreach(string part in pointer.Replace('\\','/').Split('/')){
   if(part==""||part=="."||part==".."||part.EndsWith(".")||part.EndsWith(" ")||Regex.IsMatch(part,@"^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)",RegexOptions.IgnoreCase))throw new InvalidDataException("Malformed or outside raw evidence pointer");
  }
  // Lexical reference validation only: never resolve/open/hash the target.
 }
 sealed class Snapshot {
  public string Path,Digest;
  public byte[] Bytes;
  public Dictionary<string,object> Data;
 }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
 static extern uint GetFinalPathNameByHandle(IntPtr handle,StringBuilder path,uint length,uint flags);
 static void RejectReparseAncestors(string path){
  for(string current=path;current!=null;current=System.IO.Path.GetDirectoryName(current))
   if((File.GetAttributes(current)&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException("Reparse evidence paths are not supported");
 }
 static string LocalRoot(string root){
  string full=System.IO.Path.GetFullPath(root);
  if(full.StartsWith(@"\\",StringComparison.Ordinal)||full.StartsWith("//",StringComparison.Ordinal))throw new InvalidDataException("Network evidence roots are not supported");
  RejectReparseAncestors(full);
  if(!Directory.Exists(full))throw new InvalidDataException("Local evidence root is missing");
  return full.TrimEnd(System.IO.Path.DirectorySeparatorChar,System.IO.Path.AltDirectorySeparatorChar);
 }
 static string LocalPath(string root,string path){
  string fullRoot=LocalRoot(root),full=System.IO.Path.GetFullPath(path);
  if(full.StartsWith(@"\\",StringComparison.Ordinal)||full.StartsWith("//",StringComparison.Ordinal)||!full.StartsWith(fullRoot+System.IO.Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Evidence path is outside the local root");
  RejectReparseAncestors(full);return full;
 }
 static void VerifyOpenedPath(FileStream file,string expected){
  if(Environment.OSVersion.Platform!=PlatformID.Win32NT)throw new InvalidDataException("Opened evidence path verification requires the Windows target");
  var finalPath=new StringBuilder(32768);uint count=GetFinalPathNameByHandle(file.SafeFileHandle.DangerousGetHandle(),finalPath,(uint)finalPath.Capacity,0);
  if(count==0||count>=finalPath.Capacity)throw new InvalidDataException("Opened evidence path could not be verified");
  string actual=finalPath.ToString();
  if(actual.StartsWith(@"\\?\UNC\",StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Opened evidence handle resolves to a network path");
  if(actual.StartsWith(@"\\?\",StringComparison.Ordinal))actual=actual.Substring(4);
  if(actual.StartsWith(@"\\",StringComparison.Ordinal)||!System.IO.Path.GetFullPath(actual).Equals(expected,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Opened evidence handle resolves outside its expected local path");
 }
 static Snapshot ReadSnapshot(string root,string path,string expectedDigest){
  string full=LocalPath(root,path);
  using(var file=new FileStream(full,FileMode.Open,FileAccess.Read,FileShare.Read)){
   // Validate the opened handle before reading: path prechecks alone miss a
   // junction swap. No file write/delete sharing is granted during this read.
   VerifyOpenedPath(file,full);
   if(file.Length>LocalJson.Limit)throw new InvalidDataException("Evidence JSON exceeds the bounded size limit");
   byte[] raw=new byte[(int)file.Length];int offset=0;
   while(offset<raw.Length){int count=file.Read(raw,offset,raw.Length-offset);if(count==0)throw new EndOfStreamException("Partial evidence JSON read");offset+=count;}
   if(file.ReadByte()!=-1)throw new InvalidDataException("Evidence JSON changed while reading");
   VerifyOpenedPath(file,full);LocalPath(root,full);
   string digest;using(var hash=SHA256.Create())digest=BitConverter.ToString(hash.ComputeHash(raw)).Replace("-","").ToLowerInvariant();
   if(expectedDigest!=null&&(!Regex.IsMatch(expectedDigest,"^[0-9a-fA-F]{64}$")||!digest.Equals(expectedDigest,StringComparison.OrdinalIgnoreCase)))throw new InvalidDataException("Hash связанного файла не совпадает");
   // Hash, parser, and displayed provenance all use this one bounded snapshot.
   return new Snapshot{Path=full,Digest=digest,Bytes=raw,Data=LocalJson.ParseObject(LocalJson.Decode(raw))};
  }
 }
 static Snapshot BoundSnapshot(string root,string relative,string expected,string expectedDigest){
  if(relative.Replace('\\','/')!=expected)throw new InvalidDataException("Путь результата не соответствует заданию");
  return ReadSnapshot(root,Path.Combine(root,relative),expectedDigest);
 }
 static Entry Make(string id,string kind,string message,string detail){return new Entry{JobId=id,Kind=kind,Message=message,Text=message+"\r\nЗадание: "+id+"\r\n"+detail+"\r\nИсходные файлы не изменены. Это событие задания, не карточка и не решение владельца; последующая проверка остаётся доступна."};}
 public static Entry Inspect(string root,string id,Dictionary<string,object> job){
  string state=S(job,"status");
  if(state=="failed")return Make(id,"failed","Анализ завершился ошибкой",S(job,"error"));
  if(state=="cancelled"||state=="canceled")return Make(id,"cancelled","Анализ отменён","");
  if(state=="truncated"||state=="incomplete")return Make(id,"truncated","Ответ модели не завершён","");
  if(state=="awaiting_authorized_executor")return Make(id,"not_started","Анализ ещё не запущен","");
  if(state=="stale_sources")return Make(id,"stale_preparation","Вход устарел; новый анализ не запущен","");
  if(state=="superseded_preparation")return Make(id,"superseded","Подготовленный вход заменён; это не новый результат",S(job,"superseded_by"));
  if(state=="running")return Make(id,"running","Анализ выполняется","");
  if(state!="completed_verified"&&state!="completed_needs_review")return Make(id,"unconfirmed","Завершение анализа не подтверждено",state);
  try{
   LocalRoot(root);DecisionStore.RequirePublicationComplete(root);
   if(!String.IsNullOrWhiteSpace(S(job,"recovery_warning")))throw new InvalidDataException("Native recovery warning prevents confirmed completion");
   if(job.ContainsKey("recovered_result_structurally_valid")&&(!(job["recovered_result_structurally_valid"] is bool)||!(bool)job["recovered_result_structurally_valid"]))throw new InvalidDataException("Native recovered result is structurally invalid or unconfirmed");
   if(!Regex.IsMatch(id,"^[0-9a-f]{64}$"))throw new InvalidDataException("Неверный идентификатор задания");
   var input=BoundSnapshot(root,S(job,"input_file"),"analysis-inputs/"+id+".json",S(job,"input_file_sha256"));
   var inputData=input.Data;if(S(inputData,"input_sha256")!=id)throw new InvalidDataException("Вход относится к другой ревизии");
   var result=BoundSnapshot(root,S(job,"analysis_result"),"analysis-results/"+id+".json",S(job,"result_file_sha256"));
   var saved=result.Data;ValidateRawPointer(saved);var model=D(saved.ContainsKey("model_output")?saved["model_output"]:null);
   if(model.Count!=2||model.Keys.Any(k=>k!="source_job"&&k!="hypotheses"))throw new InvalidDataException("Форма сохранённого вывода не соответствует контракту");
   if(S(model,"source_job")!=id)throw new InvalidDataException("Вывод относится к другому входу");
   var values=model.ContainsKey("hypotheses")?model["hypotheses"] as object[]:null;
   if(values==null)throw new InvalidDataException("hypotheses не является массивом");
   if(values.Length==0){var request=D(inputData.ContainsKey("request")?inputData["request"]:null);var format=D(request.ContainsKey("format")?request["format"]:null);var properties=D(format.ContainsKey("properties")?format["properties"]:null);var list=D(properties.ContainsKey("hypotheses")?properties["hypotheses"]:null);if(!list.ContainsKey("minItems")||!(list["minItems"] is int)||(int)list["minItems"]!=0)throw new InvalidDataException("Схема исходного запроса не подтверждает допустимость пустого ответа");}
   var metrics=BoundSnapshot(root,S(job,"analysis_metrics"),"analysis-results/"+id+"-metrics.json",null);var receipt=metrics.Data;
   if(S(receipt,"source_job")!=id)throw new InvalidDataException("Receipt относится к другому входу");
   if(values.Length==0){
    foreach(var evidenceRecord in new[]{job,saved,receipt}){
     string conflict=EmptyConflict(evidenceRecord);
     if(conflict!="")return Make(id,"unconfirmed","Пустой результат не подтверждён: имеются ошибки проверки или противоречивые markers",conflict+"\r\nReceipt: "+metrics.Path+"\r\nSHA256: "+metrics.Digest);
    }
   }
   string finish=S(receipt,"finish_reason");if(finish=="")finish=S(receipt,"done_reason");
   if(finish=="length")return Make(id,"truncated","Ответ модели не завершён","Receipt: "+metrics.Path+"\r\nSHA256: "+metrics.Digest);
   bool one=receipt.ContainsKey("model_calls")&&receipt["model_calls"] is int&&(int)receipt["model_calls"]==1;
   if(!one||finish!="stop"||(S(receipt,"status")!="VALIDATED_MODEL_OUTPUT"&&S(receipt,"status")!="MODEL_OUTPUT_NEEDS_REVIEW"))throw new InvalidDataException("Нет подтверждения завершённого единственного ответа");
   string evidence="Вход: "+input.Path+"\r\nSHA256: "+input.Digest+"\r\nРезультат: "+result.Path+"\r\nSHA256: "+result.Digest+"\r\nReceipt: "+metrics.Path+"\r\nSHA256: "+metrics.Digest+"\r\nRaw SHA256 (сохранённая ссылка): "+S(saved,"raw_response_sha256")+"\r\nRaw pointer (исходное значение): "+S(saved,"raw_response_retained_in_run");
   return values.Length==0?Make(id,"completed_empty",EmptyMessage,evidence):Make(id,"completed_with_hypotheses","Гипотезы предложены: "+values.Length+"; требуется отдельная проверка",evidence);
  }catch(Exception e){if(e is OutOfMemoryException)throw;return Make(id,"unconfirmed","Завершение анализа не подтверждено",e.Message);}
 }
 public static Entry[] Load(string root){
  try{LocalRoot(root);string p=Path.Combine(root,"analysis-queue.json");if(!File.Exists(p))return new Entry[0];var q=ReadSnapshot(root,p,null).Data;var jobs=q.ContainsKey("jobs")?q["jobs"] as Dictionary<string,object>:null;if(jobs==null)throw new InvalidDataException("Реестр заданий не является объектом");return jobs.OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>Inspect(root,x.Key,D(x.Value))).ToArray();}
  catch(Exception e){if(e is OutOfMemoryException)throw;return new[]{Make("queue","unconfirmed","Состояние AI-заданий недоступно",e.Message)};}
 }
 public static Entry Current(string root,Dictionary<string,object> result){
  string id=S(result,"analysis_job");if(id=="")return null;
  try{LocalRoot(root);var q=ReadSnapshot(root,Path.Combine(root,"analysis-queue.json"),null).Data;var jobs=D(q.ContainsKey("jobs")?q["jobs"]:null);var seen=new HashSet<string>();
   for(int i=0;i<6;i++){if(!seen.Add(id)||!jobs.ContainsKey(id))throw new InvalidDataException("Связь заданий отсутствует или зациклена");var job=D(jobs[id]);string next=S(job,"superseded_by");if(next!=""){id=next;continue;}return Inspect(root,id,job);}throw new InvalidDataException("Слишком длинная связь заданий");
  }catch(Exception e){if(e is OutOfMemoryException)throw;return Make(id,"unconfirmed","Состояние AI-задания недоступно",e.Message);}
 }
 public static string DirectNote(Dictionary<string,object> result){
  var a=result.ContainsKey("hypotheses")?result["hypotheses"] as object[]:null;
  return S(result,"analysis_job")==""&&S(result,"status")=="completed"&&a!=null&&a.Length==0?"Пустой сохранённый результат; завершение модели требует подтверждения; это не оценка рынка":"";
 }
}
