using System;using System.IO;using System.Linq;using System.Text;using System.Collections;using System.Collections.Generic;using System.Security.Cryptography;
// Read-only reconciliation. No clocks for ordering, no process probing or repair.
public static class AttemptPublication {
 const string Schema="reveng-collection-attempt-v1";const int MaxRuns=256;
 static string S(Dictionary<string,object>d,string k){object v;return d.TryGetValue(k,out v)&&v!=null?Convert.ToString(v):"";}
 static string Hash(byte[]b){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant();}
 static bool SamePath(string a,string b){if(String.IsNullOrEmpty(a)||String.IsNullOrEmpty(b))return false;return String.Equals(Path.GetFullPath(a).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar),Path.GetFullPath(b).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar),StringComparison.OrdinalIgnoreCase);}
 static void Local(string p){p=Path.GetFullPath(p);if(p.StartsWith(@"\\"))throw new InvalidDataException("Local journal only");for(var d=new DirectoryInfo(Path.GetDirectoryName(p));d!=null;d=d.Parent)if(d.Exists&&(d.Attributes&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException("Reparse journal directory");if(File.Exists(p)&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)throw new InvalidDataException("Reparse journal file");}
 static byte[] Bytes(string p){Local(p);return LocalJson.ReadBytes(p,LocalJson.Limit);}
 static Dictionary<string,object> Read(string p){return LocalJson.ParseObject(LocalJson.Decode(Bytes(p)));}
 static string Run(string root,string relative){string p=Path.GetFullPath(Path.Combine(root,relative));if(!SamePath(Path.GetDirectoryName(p),Path.Combine(root,"runs")))throw new InvalidDataException("Attempt outside owned runs");Local(Path.Combine(p,"result.json"));return p;}
 static string Relative(string root,string p){return p.Substring(Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar).Length+1).Replace('\\','/');}
 static string[] Dirs(string root){string runs=Path.Combine(root,"runs");Local(Path.Combine(runs,"_boundary"));if(!Directory.Exists(runs))return new string[0];var dirs=Directory.GetDirectories(runs);if(dirs.Length>MaxRuns)throw new InvalidDataException("Run scan limit; latest publication unknown");foreach(var d in dirs)Local(Path.Combine(d,"_boundary"));return dirs;}
 static Dictionary<string,object> Unknown(string note,List<object> scoped){return new Dictionary<string,object>{{"status","collection_publication_uncertain"},{"note",note},{"hypotheses",new object[0]},{"unpublished_attempts",scoped.ToArray()},{"local_result_errors",new object[]{new Dictionary<string,object>{{"file","attempt_publication"},{"reason",note}}}},{"reopen_context","PUBLICATION_UNCERTAIN_NO_OLD_SUCCESS_FALLBACK"}};}
 static object Scope(string root,string file){try{var raw=Bytes(file);var data=LocalJson.ParseObject(LocalJson.Decode(raw));return new Dictionary<string,object>{{"run_file",Relative(root,file)},{"sha256",Hash(raw)},{"recorded_status",S(data,"status")},{"source_errors",data.ContainsKey("source_errors")?data["source_errors"]:new object[0]}};}catch(Exception ex){if(ex is OutOfMemoryException)throw;return new Dictionary<string,object>{{"run_file",Relative(root,file)},{"recorded_status","UNREADABLE"},{"source_errors",new object[0]},{"read_error",ex.GetType().Name}};}}
 public static Dictionary<string,object> Select(string root){
  try{
   root=Path.GetFullPath(root);
   string marker=Path.Combine(root,"current-collection-attempt.json"),pointer=Path.Combine(root,"latest-discovery.json");Local(marker);
   if(Directory.GetFiles(root,".collection-attempt-*.tmp").Length>0)return Unknown("Найдена незавершённая durable-регистрация попытки; старый успех не является последним подтверждённым результатом.",new List<object>());
   if(!File.Exists(marker)){
    string published="";if(File.Exists(pointer))try{var p=Read(pointer);published=Path.GetFullPath(Path.Combine(root,S(p,"file")));if(Path.GetFileName(published)!="result.json"||!SamePath(Path.GetDirectoryName(Path.GetDirectoryName(published)),Path.Combine(root,"runs")))return null;}catch{return null;}
    var others=new List<object>();foreach(var dir in Dirs(root)){string f=Path.Combine(dir,"result.json");if(File.Exists(f)&&!SamePath(f,published))others.Add(Scope(root,f));}
    if(others.Count>0)return Unknown("Старый журнал не фиксирует начало попыток: есть результаты вне опубликованного указателя. Их порядок/последняя публикация не установлены; не выбираем старый успех автоматически.",others);return null;
   }
   var current=Read(marker);if(S(current,"schema")!=Schema||!System.Text.RegularExpressions.Regex.IsMatch(S(current,"attempt_id"),"^[0-9a-f]{32}$"))throw new InvalidDataException("Invalid attempt marker");
   string home=Run(root,S(current,"run_directory")),file=Path.Combine(home,"result.json");var prior=current.ContainsKey("preexisting_results")?current["preexisting_results"]as Dictionary<string,object>:null;if(prior==null)throw new InvalidDataException("Missing pre-attempt snapshot");
   var found=new Dictionary<string,string>();var changed=new List<object>();foreach(var dir in Dirs(root)){string f=Path.Combine(dir,"result.json");if(SamePath(f,file)||!File.Exists(f))continue;string rel=Relative(root,f),hash=Hash(Bytes(f));found[rel]=hash;if(!prior.ContainsKey(rel)||!String.Equals(Convert.ToString(prior[rel]),hash,StringComparison.OrdinalIgnoreCase))changed.Add(Scope(root,f));}
   if(prior.Keys.Any(k=>!found.ContainsKey(k))||changed.Count>0)return Unknown("История результатов изменилась после регистрации текущей попытки; публикация неоднозначна, включая возможного старого writer.",changed);
   if(!File.Exists(file))return new Dictionary<string,object>{{"status","collection_attempt_incomplete"},{"note","Начало новой попытки записано, результата ещё нет. Активна она или прервана — не установлено; старый успех не подставляется."},{"collection_attempt_id",S(current,"attempt_id")},{"hypotheses",new object[0]},{"reopen_context","REGISTERED_ATTEMPT_WITHOUT_RESULT"}};
   byte[] bytes=Bytes(file);var result=LocalJson.ParseObject(LocalJson.Decode(bytes));if(S(result,"collection_attempt_id")!=S(current,"attempt_id"))throw new InvalidDataException("Result token differs from current attempt");
   bool terminal=S(result,"status")!=""&&S(result,"status")!="running";bool publishedCurrent=false;
   if(File.Exists(pointer))try{var p=Read(pointer);publishedCurrent=SamePath(Path.Combine(root,S(p,"file")),file)&&S(p,"collection_attempt_id")==S(current,"attempt_id")&&String.Equals(S(p,"sha256"),Hash(bytes),StringComparison.OrdinalIgnoreCase);}catch{publishedCurrent=false;}
   if(!terminal||!publishedCurrent){
    result["recorded_status"]=S(result,"status");if(!terminal)result["status"]="collection_attempt_incomplete";else if(S(result,"status")=="completed")result["status"]="collection_publication_incomplete";
    result["hypotheses"]=new object[0];result["publication_state"]="RESULT_NOT_FULLY_PUBLISHED";result["reopen_context"]="LATEST_REGISTERED_ATTEMPT_UNPUBLISHED";
    var notes=new List<object>();if(result.ContainsKey("local_result_errors")&&result["local_result_errors"]is IEnumerable&&!(result["local_result_errors"]is string))foreach(var x in(IEnumerable)result["local_result_errors"])notes.Add(x);
    notes.Add(new Dictionary<string,object>{{"file",Relative(root,file)},{"reason","Последняя зарегистрированная попытка не полностью опубликована. Сохранённый статус: "+S(result,"recorded_status")+". Не подставляем старый успешный pointer и не ремонтируем файлы автоматически."}});result["local_result_errors"]=notes.ToArray();return result;
   }
   result["reopen_context"]="VERIFIED_REGISTERED_ATTEMPT_AND_PUBLICATION";return result;
  }catch(Exception ex){if(ex is OutOfMemoryException)throw;return Unknown("Журнал попыток не удалось проверить: "+ex.GetType().Name+": "+ex.Message,new List<object>());}
 }
}
