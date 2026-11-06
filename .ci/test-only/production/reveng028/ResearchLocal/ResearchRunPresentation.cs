using System;using System.IO;using System.Text;using System.Linq;using System.Collections;using System.Collections.Generic;using System.Security.Cryptography;
// Pure file-selection/text helpers. No Forms, app Main, processes or HTTP.
public static class ResearchRunPresentation {
 static string S(Dictionary<string,object>d,string k){object v;return d.TryGetValue(k,out v)&&v!=null?Convert.ToString(v):"";}
 static IEnumerable<object> A(Dictionary<string,object>d,string k){object v;if(d.TryGetValue(k,out v)&&v is IEnumerable&&!(v is string)&&!(v is IDictionary))foreach(var x in (IEnumerable)v)yield return x;}
 static void Local(string path){var p=Path.GetFullPath(path);if(p.StartsWith(@"\\"))throw new InvalidDataException("Only local run files");for(var d=new DirectoryInfo(Path.GetDirectoryName(p));d!=null;d=d.Parent)if(d.Exists&&(d.Attributes&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException("Reparse run path");if(File.Exists(p)&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException("Reparse run file");}
 static Dictionary<string,object> Read(string p){Local(p);return LocalJson.ReadObject(p);}
 static Dictionary<string,object> Unavailable(Exception ex){return new Dictionary<string,object>{{"status","saved_run_unavailable"},{"note","Последний запуск не удалось проверить. Старые карточки доступны отдельно в истории; они не являются результатом этого запуска."},{"hypotheses",new object[0]},{"local_result_errors",new object[]{new Dictionary<string,object>{{"file","saved_run_selection"},{"reason",ex.GetType().Name+": "+ex.Message}}}},{"reopen_context","INVALID_RUN_POINTER_NO_SILENT_SUCCESS_FALLBACK"}};}
 public static Dictionary<string,object> LoadLatest(string root,string resultOverride){
  try{DecisionStore.RequirePublicationComplete(root);}catch(InvalidDataException ex){return Unavailable(ex);}
  if(resultOverride!=null)return Read(resultOverride);
  var attempt=AttemptPublication.Select(root);if(attempt!=null)return attempt;
  string pointer=Path.Combine(root,"latest-discovery.json");Local(pointer);
  if(File.Exists(pointer))try{
   var saved=Read(pointer);string found=Path.GetFullPath(Path.Combine(root,S(saved,"file")));string allowed=Path.GetFullPath(Path.Combine(root,"runs"))+Path.DirectorySeparatorChar;
   if(!found.StartsWith(allowed,StringComparison.OrdinalIgnoreCase)||Path.GetFileName(found)!="result.json")throw new InvalidDataException("Run pointer outside runs");Local(found);
   byte[] raw=LocalJson.ReadBytes(found,LocalJson.Limit);string hash;using(var h=SHA256.Create())hash=BitConverter.ToString(h.ComputeHash(raw)).Replace("-","");
   if(!hash.Equals(S(saved,"sha256"),StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Run pointer hash mismatch");
   var result=LocalJson.ParseObject(LocalJson.Decode(raw));result["reopen_context"]="VERIFIED_TERMINAL_RUN_POINTER_NOT_OPPORTUNITY_APPROVAL";return result;
  }catch(Exception ex){if(ex is OutOfMemoryException)throw;return Unavailable(ex);}
  string legacy=Path.Combine(root,"latest-result.json");if(!File.Exists(legacy))return null;try{var old=Read(legacy);old["reopen_context"]="LEGACY_SAVED_RESULT_LAST_COLLECTION_ATTEMPT_UNKNOWN";return old;}catch(Exception ex){if(ex is OutOfMemoryException)throw;return Unavailable(ex);}
 }
 public static string ErrorSummary(Dictionary<string,object> result){
  var b=new StringBuilder();foreach(string field in new[]{"source_errors","local_result_errors"}){
   object raw;if(!result.TryGetValue(field,out raw))continue;
   if(!(raw is IEnumerable)||raw is string||raw is IDictionary){b.AppendLine("Журнал ошибок повреждён; полнота покрытия неизвестна.");continue;}
   int n=0;foreach(var x in A(result,field)){n++;var e=x as Dictionary<string,object>;b.AppendLine(e==null?"Нечитаемая запись ошибки; данные сохранены.":S(e,"source")+S(e,"file")+" | "+S(e,"reason")+" | "+S(e,"url"));}
   if(n>0)b.AppendLine("Ошибок в "+field+": "+n+". Покрытие неполное; это не отсутствие спроса или решения.");
  }return b.ToString();
 }
 public static string Describe(Dictionary<string,object> result){
  if(result==null)return "Нет проверенного результата запуска. Возможность заработка не установлена.";
  var b=new StringBuilder("Контекст отображаемого запуска: "+S(result,"status")+" | "+S(result,"note")+"\r\n");
  b.AppendLine("Наблюдения и гипотезы не подтверждают возможность заработка, покупателя или доход.");
  if(S(result,"reopen_context")=="LEGACY_SAVED_RESULT_LAST_COLLECTION_ATTEMPT_UNKNOWN")b.AppendLine("Исторический сохранённый результат; последнее исследование не определено.");
  b.Append(ErrorSummary(result));foreach(var item in A(result,"unpublished_attempts")){var scope=item as Dictionary<string,object>;if(scope==null)continue;b.AppendLine("Отдельный неопубликованный результат: "+S(scope,"run_file")+" | "+S(scope,"recorded_status"));b.Append(ErrorSummary(scope));}return b.ToString();
 }
 public static string Status(Dictionary<string,object> result){object raw;string count=result.TryGetValue("source_errors",out raw)&&raw is IEnumerable&&!(raw is string)&&!(raw is IDictionary)?A(result,"source_errors").Count().ToString():"неизвестно";return "Ошибок источников: "+count+" | Возможность заработка не подтверждена | "+S(result,"status")+" | "+S(result,"note");}
 public static string CardLabel(Dictionary<string,object> card){return "Гипотеза · непроверено · "+S(card,"title");}
}
