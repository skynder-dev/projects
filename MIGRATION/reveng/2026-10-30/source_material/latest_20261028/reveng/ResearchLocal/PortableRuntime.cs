using System;using System.IO;using System.Linq;using System.Collections.Generic;using System.Diagnostics;using System.Text;using System.Threading.Tasks;using Microsoft.Win32;using System.Web.Script.Serialization;
public static class PortableRuntime {
 public static string Quote(string value){return "\""+value.Replace("\"","\\\"")+"\"";}
 static string Configured(string root,string key){string path=Path.Combine(root,"runtime-settings.json");if(!File.Exists(path))return null;var data=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(path,Encoding.UTF8));if(data==null)throw new Exception("runtime-settings.json должен содержать объект");return data.ContainsKey(key)&&data[key]!=null?Convert.ToString(data[key]):null;}
 static string ResolvePath(string root,string value){value=Environment.ExpandEnvironmentVariables(value.Trim());return Path.GetFullPath(Path.IsPathRooted(value)?value:Path.Combine(Path.GetDirectoryName(root),value));}
 static bool Usable(string path){return !String.IsNullOrEmpty(path)&&!path.StartsWith(@"\\",StringComparison.Ordinal)&&path.IndexOf("Microsoft\\WindowsApps",StringComparison.OrdinalIgnoreCase)<0&&File.Exists(path);}
 static IEnumerable<string> Registered(){foreach(var hive in new[]{Registry.CurrentUser,Registry.LocalMachine}){RegistryKey key=null;try{key=hive.OpenSubKey(@"SOFTWARE\Python\PythonCore");if(key!=null)foreach(string version in key.GetSubKeyNames().OrderByDescending(x=>x)){using(var install=key.OpenSubKey(version+@"\InstallPath")){if(install!=null){string exe=Convert.ToString(install.GetValue("ExecutablePath"));if(exe=="")exe=Path.Combine(Convert.ToString(install.GetValue(null)),"python.exe");yield return exe;}}}}finally{if(key!=null)key.Dispose();}}}
 public static string Python(string root,string purpose,out string diagnostic){
  diagnostic="";try{string value=Environment.GetEnvironmentVariable(purpose=="collect"?"REVENG_CRAWLER_PYTHON":"REVENG_PYTHON");if(String.IsNullOrWhiteSpace(value))value=Environment.GetEnvironmentVariable("REVENG_PYTHON");if(String.IsNullOrWhiteSpace(value)&&purpose=="collect")value=Configured(root,"crawler_python");if(String.IsNullOrWhiteSpace(value))value=Configured(root,"python");
   if(!String.IsNullOrWhiteSpace(value)){string path=ResolvePath(root,value);if(Usable(path))return path;diagnostic="Указанный Python не найден: "+path+". Проверьте REVENG_PYTHON или ResearchLocal/runtime-settings.json; автоматической установки нет.";return null;}
   string app=Path.GetDirectoryName(root);foreach(string relative in new[]{@"runtime\python.exe",@"runtime\python\python.exe"}){string path=Path.Combine(app,relative);if(Usable(path))return path;}
   foreach(string path in Registered())if(Usable(path))return path;
   foreach(string entry in (Environment.GetEnvironmentVariable("PATH")??"").Split(Path.PathSeparator)){if(String.IsNullOrWhiteSpace(entry))continue;string path=Path.Combine(entry.Trim().Trim('"'),"python.exe");if(Usable(path))return path;}
   diagnostic="Python 3.10+ не найден. История и сохранённые источники доступны без Python/AI; для экспорта укажите существующий интерпретатор в ResearchLocal/runtime-settings.json. Ничего не скачивается.";return null;
  }catch(Exception ex){diagnostic="Настройки локальной среды не прочитаны: "+ex.Message+". История доступна; автоматической установки нет.";return null;}
 }
 // Largest existing stdout receipt consumers (ledger/archive) accept 8,388,608
 // UTF-16 characters. This is a character limit, not an 8 MiB UTF-8 byte limit.
 public const int MaxCapturedCharacters=8388608;
 public const int DrainTimeoutMilliseconds=5000;
 public const int CleanupTimeoutMilliseconds=1000;
 public sealed class CompletionUnconfirmedException:Exception {
  public bool ProcessExitConfirmed {get;private set;}
  public CompletionUnconfirmedException(string message,bool processExitConfirmed,Exception inner):base(message,inner){ProcessExitConfirmed=processExitConfirmed;}
 }
 public static string FailureMessage(Exception ex,string confirmedFailurePrefix,string confirmedFailureSuffix=""){
  if(ex is CompletionUnconfirmedException)return "Результат локальной операции не подтверждён: "+ex.Message+" Данные могли сохраниться. Проверьте сохранённый результат перед повтором; автоматического повтора нет.";
  return confirmedFailurePrefix+ex.Message+confirmedFailureSuffix;
 }
 public static async Task<string> ReadBoundedAsync(TextReader reader,int limit){
  if(reader==null)throw new ArgumentNullException("reader");if(limit<=0||limit>MaxCapturedCharacters)throw new ArgumentOutOfRangeException("limit");
  var text=new StringBuilder(Math.Min(4096,limit));var buffer=new char[4096];
  while(true){int count=await reader.ReadAsync(buffer,0,Math.Min(buffer.Length,limit-text.Length+1)).ConfigureAwait(false);if(count==0)return text.ToString();if(count>limit-text.Length)throw new InvalidDataException("Local tool output exceeds "+limit+" UTF-16 characters; complete receipt unavailable");text.Append(buffer,0,count);}
 }
 public static string[] DrainOutput(Task<string> output,Task<string> error,int timeout){
  if(output==null||error==null)throw new ArgumentNullException("output/error");if(timeout<0)throw new ArgumentOutOfRangeException("timeout");
  if(!Task.WaitAll(new Task[]{output,error},timeout))throw new TimeoutException("Local tool output did not finish within the bounded drain interval");
  // Result is reachable only after BOTH tasks completed successfully. Faults and
  // cancellation throw from WaitAll; a descendant-held pipe cannot block here.
  return new[]{output.Result,error.Result};
 }
 static void ObserveFailure(Task task){if(task!=null)task.ContinueWith(t=>{if(t.IsFaulted){var ignored=t.Exception;}},TaskScheduler.Default);}
 public static bool CloseOwnedHandles(TextReader output,TextReader error,IDisposable process,int timeout){
  if(timeout<0)throw new ArgumentOutOfRangeException("timeout");
  var tasks=new List<Task>();
  foreach(IDisposable resource in new IDisposable[]{output,error})if(resource!=null){IDisposable owned=resource;tasks.Add(Task.Run(()=>owned.Dispose()));}
  // Dispose the Process only after reader cleanup finishes, avoiding concurrent
  // double-disposal on frameworks which also close redirected streams.
  if(process!=null){Task readers=Task.WhenAll(tasks);ObserveFailure(readers);tasks.Add(readers.ContinueWith(t=>process.Dispose(),TaskScheduler.Default));}
  try{return Task.WaitAll(tasks.ToArray(),timeout);}catch(AggregateException){return false;}
  finally{foreach(Task task in tasks)ObserveFailure(task);}
 }
 static bool StopOwned(Process process){
  try{if(process.HasExited)return true;}catch(InvalidOperationException){return false;}catch(System.ComponentModel.Win32Exception){return false;}
  try{process.Kill();}catch(InvalidOperationException){}catch(System.ComponentModel.Win32Exception){}catch(NotSupportedException){}
  try{return process.WaitForExit(CleanupTimeoutMilliseconds);}catch(InvalidOperationException){return false;}catch(System.ComponentModel.Win32Exception){return false;}catch(NotSupportedException){return false;}
 }
 public static string Run(string python,string arguments,string root,int timeout){
  if(timeout<0)throw new ArgumentOutOfRangeException("timeout");
  var info=new ProcessStartInfo(python,"-X utf8 "+arguments){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=root,RedirectStandardOutput=true,RedirectStandardError=true};
  Process process=Process.Start(info);if(process==null)throw new InvalidOperationException("Local tool process was not started");
  Task<string> output=null,error=null;TextReader outputReader=null,errorReader=null;string[] captured;bool exited=false;
  try{
   outputReader=process.StandardOutput;errorReader=process.StandardError;
   output=ReadBoundedAsync(outputReader,MaxCapturedCharacters);error=ReadBoundedAsync(errorReader,MaxCapturedCharacters);
   if(!process.WaitForExit(timeout))throw new TimeoutException("Local tool exceeded its execution deadline");exited=true;
   captured=DrainOutput(output,error,DrainTimeoutMilliseconds);int exitCode=process.ExitCode;
   // A nonzero exit is not a rollback receipt: a mutating tool may commit first.
   if(exitCode!=0)throw new InvalidOperationException(captured[0]!=""?captured[0]:captured[1]);
  }catch(Exception ex){
   bool stopped=exited||StopOwned(process);bool closed=CloseOwnedHandles(outputReader,errorReader,process,CleanupTimeoutMilliseconds);ObserveFailure(output);ObserveFailure(error);
   throw new CompletionUnconfirmedException(ex.Message+(stopped?" Завершение только запущенного этим вызовом процесса подтверждено; результат операции неизвестен.":" Завершение запущенного этим вызовом процесса не подтверждено; результат операции неизвестен.")+(closed?"":" Закрытие принадлежащих вызову потоков/дескрипторов не подтверждено."),stopped,ex);
  }
  // Dispose may itself block on a stream implementation. Never put an unbounded
  // using/finally Dispose after the timed cleanup; retain ownership, not a PID.
  if(!CloseOwnedHandles(outputReader,errorReader,process,CleanupTimeoutMilliseconds))throw new CompletionUnconfirmedException("Квитанция получена, но закрытие принадлежащих вызову потоков/дескрипторов не подтверждено.",true,null);
  return captured[0];
 }

 public static bool Check(string root,string python,string purpose,out string diagnostic){diagnostic="";try{string script=Path.Combine(root,"runtime_diagnostics.py");if(!File.Exists(script)){diagnostic="Отсутствует runtime_diagnostics.py рядом с программой; восстановите файлы локального комплекта. Автоскачивания нет.";return false;}var data=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(Run(python,Quote(script)+" --root "+Quote(root)+" --purpose "+purpose,root,10000));string key=purpose=="api"?"api_collector_available":purpose=="html"?"html_collector_available":purpose=="collect"?"collector_available":"export_available";if(data!=null&&data.ContainsKey(key)&&Convert.ToBoolean(data[key]))return true;diagnostic=data!=null&&data.ContainsKey("message")?Convert.ToString(data["message"]):"Локальная среда не прошла диагностику";return false;}catch(Exception ex){diagnostic="Локальная среда недоступна: "+ex.Message+". Ничего не устанавливается автоматически.";return false;}}
 static string ErrorJson(string message){return new JavaScriptSerializer().Serialize(new{status="diagnostic_error",message=message,history_without_AI=true,source_requests=0,model_requests=0,automatic_download=false});}
 public static string Describe(string root){string raw=Diagnose(root);try{var data=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(raw);var text=new StringBuilder("Локальная среда RevEng\r\n\r\n");if(data.ContainsKey("message"))text.AppendLine(Convert.ToString(data["message"]));if(data.ContainsKey("python"))text.AppendLine("Python: "+data["python"]+" ("+data["python_version"]+")");text.AppendLine("История и сохранённые источники не требуют AI.");if(data.ContainsKey("export_available"))text.AppendLine("Экспорт без AI: "+(Convert.ToBoolean(data["export_available"])?"инструмент найден":"инструмент недоступен"));if(data.ContainsKey("semantic_AI_readiness"))text.AppendLine("Готовность анализа: "+data["semantic_AI_readiness"]);var quality=data.ContainsKey("analysis_quality")?data["analysis_quality"] as Dictionary<string,object>:null;if(quality!=null){text.AppendLine("Сохранённая проверка атрибуции: "+quality["manual_attribution_review"]);text.AppendLine("Полезное сжатие: "+quality["semantic_compression"]+"; полных воспроизведений: "+quality["full_reproductions_after_apostrophe_substitution"]+". Это прежний запуск, не новый.");}foreach(string name in new[]{"model","executor"}){var item=data.ContainsKey(name)?data[name] as Dictionary<string,object>:null;string label=name=="model"?"Модель":"Исполнитель";text.AppendLine(label+": "+(item==null||!Convert.ToBoolean(item["configured"])?"не настроен":Convert.ToBoolean(item["exists"])?"файл найден, смысловая готовность не подтверждена":"указанный файл отсутствует"));}text.AppendLine("Автоматический AI выключен. Полезное сжатие и общая готовность анализа не доказаны; узкая проверка атрибуции не означает общего допуска.");text.AppendLine("Скачиваний, установки инструментов и новых запросов к источникам не выполнялось.");return text.ToString();}catch{return raw;}}
 public static string Diagnose(string root){string issue;string python=Python(root,"export",out issue);if(python==null)return new JavaScriptSerializer().Serialize(new{status="tools_missing",message=issue,history_without_AI=true,source_requests=0,model_requests=0,automatic_download=false});try{string script=Path.Combine(root,"runtime_diagnostics.py");if(!File.Exists(script))return ErrorJson("runtime_diagnostics.py отсутствует; просмотр не требует AI, инструменты не устанавливаются автоматически.");return Run(python,Quote(script)+" --root "+Quote(root),root,10000);}catch(Exception ex){return ErrorJson("Диагностика: "+ex.Message+". Автоматических скачиваний и запуска AI нет.");}}
}
