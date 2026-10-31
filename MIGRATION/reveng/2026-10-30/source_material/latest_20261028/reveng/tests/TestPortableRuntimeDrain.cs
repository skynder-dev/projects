// In-process actual helper probes only. No Python/Process/Forms/model/network call.
// Supply the actual all-source wrapper.exe as a reference; not a substitute Run.
using System;
using System.IO;
using System.Diagnostics;
using System.Threading.Tasks;
public static class TestPortableRuntimeDrain {
 static int checks;
 static void Check(bool value,string name){checks++;if(!value)throw new Exception("FAIL "+name);}
 static T Expect<T>(Action action,string name) where T:Exception {try{action();}catch(T ex){checks++;return ex;}throw new Exception("FAIL expected "+typeof(T).Name+" "+name);}
 sealed class ChunkReader:TextReader {
  readonly string value;readonly int chunk;int offset;
  public ChunkReader(string value,int chunk){this.value=value;this.chunk=chunk;}
  public override Task<int> ReadAsync(char[] buffer,int index,int count){int n=Math.Min(Math.Min(chunk,count),value.Length-offset);value.CopyTo(offset,buffer,index,n);offset+=n;return Task.FromResult(n);}
 }
 sealed class NeverReader:TextReader {
  readonly TaskCompletionSource<int> pending=new TaskCompletionSource<int>();
  public override Task<int> ReadAsync(char[] buffer,int index,int count){return pending.Task;}
 }
 sealed class BrokenReader:TextReader {
  public override Task<int> ReadAsync(char[] buffer,int index,int count){var failed=new TaskCompletionSource<int>();failed.SetException(new IOException("SYNTHETIC stream failure"));return failed.Task;}
 }
 sealed class CloseReader:TextReader {
  public bool Closed;readonly bool fail;readonly TaskCompletionSource<bool> release;
  public CloseReader(bool fail=false,TaskCompletionSource<bool> release=null){this.fail=fail;this.release=release;}
  protected override void Dispose(bool disposing){if(release!=null)release.Task.GetAwaiter().GetResult();Closed=true;if(fail)throw new IOException("SYNTHETIC close failure");base.Dispose(disposing);}
 }
 sealed class OwnedHandle:IDisposable {
  readonly Func<bool> readersClosed;readonly bool fail;public bool Disposed;public readonly TaskCompletionSource<bool> Finished=new TaskCompletionSource<bool>();
  public OwnedHandle(Func<bool> readersClosed,bool fail=false){this.readersClosed=readersClosed;this.fail=fail;}
  public void Dispose(){if(!readersClosed())throw new InvalidOperationException("SYNTHETIC process disposal before readers");Disposed=true;Finished.SetResult(true);if(fail)throw new IOException("SYNTHETIC process-handle disposal failure");}
 }
 public static int Main(){try{
  string unicode="SYNTHETIC \u041f\u0440\u0438\u0432\u0435\u0442 \ud83d\ude00\n";
  Check(PortableRuntime.ReadBoundedAsync(new StringReader(""),1).GetAwaiter().GetResult()=="","empty EOF");
  Check(PortableRuntime.ReadBoundedAsync(new ChunkReader(unicode,1),unicode.Length).GetAwaiter().GetResult()==unicode,"split UTF-16 chunks unchanged");
  string largest=new string('x',PortableRuntime.MaxCapturedCharacters-2)+"\ud83d\ude00";
  Check(PortableRuntime.ReadBoundedAsync(new ChunkReader(largest,4093),PortableRuntime.MaxCapturedCharacters).GetAwaiter().GetResult()==largest,"largest supported receipt accepted exactly");
  Expect<InvalidDataException>(()=>PortableRuntime.ReadBoundedAsync(new StringReader("12345"),4).GetAwaiter().GetResult(),"no successful truncated output");
  Expect<IOException>(()=>PortableRuntime.ReadBoundedAsync(new BrokenReader(),100).GetAwaiter().GetResult(),"actual reader failure");
  Expect<ArgumentOutOfRangeException>(()=>PortableRuntime.ReadBoundedAsync(new StringReader(""),0).GetAwaiter().GetResult(),"zero limit rejected");
  Expect<ArgumentOutOfRangeException>(()=>PortableRuntime.ReadBoundedAsync(new StringReader(""),Int32.MaxValue).GetAwaiter().GetResult(),"unsupported limit cannot overflow");
  string[] complete=PortableRuntime.DrainOutput(Task.FromResult(unicode),Task.FromResult("SYNTHETIC stderr"),0);
  Check(complete[0]==unicode&&complete[1]=="SYNTHETIC stderr","both completed streams unchanged");
  var never=new TaskCompletionSource<string>();var watch=Stopwatch.StartNew();
  Expect<TimeoutException>(()=>PortableRuntime.DrainOutput(never.Task,Task.FromResult(""),0),"incomplete stdout no Result wait");
  Check(watch.ElapsedMilliseconds<1000,"bounded controlled stdout drain");
  Expect<TimeoutException>(()=>PortableRuntime.DrainOutput(Task.FromResult(""),never.Task,0),"incomplete stderr no Result wait");
  Expect<TimeoutException>(()=>PortableRuntime.DrainOutput(PortableRuntime.ReadBoundedAsync(new NeverReader(),100),Task.FromResult(""),0),"actual pending TextReader no Result wait");
  var faulted=new TaskCompletionSource<string>();faulted.SetException(new IOException("SYNTHETIC read fault"));
  Expect<AggregateException>(()=>PortableRuntime.DrainOutput(faulted.Task,Task.FromResult(""),0),"faulted task not success");
  var cancelled=new TaskCompletionSource<string>();cancelled.SetCanceled();
  Expect<AggregateException>(()=>PortableRuntime.DrainOutput(Task.FromResult(""),cancelled.Task,0),"cancelled task not success");
  Expect<ArgumentOutOfRangeException>(()=>PortableRuntime.DrainOutput(Task.FromResult(""),Task.FromResult(""),-1),"infinite timeout forbidden");
  var closeOut=new CloseReader();var closeError=new CloseReader();
  Check(PortableRuntime.CloseOwnedHandles(closeOut,closeError,null,1000)&&closeOut.Closed&&closeError.Closed,"actual reader closure");
  Check(!PortableRuntime.CloseOwnedHandles(new CloseReader(true),null,null,1000),"reader close failure is not confirmed");
  var release=new TaskCompletionSource<bool>();var pendingClose=new CloseReader(false,release);
  try{Check(!PortableRuntime.CloseOwnedHandles(pendingClose,null,null,0),"blocked close returns bounded unconfirmed");}finally{release.SetResult(true);}
  Expect<ArgumentOutOfRangeException>(()=>PortableRuntime.CloseOwnedHandles(null,null,null,-1),"infinite close wait forbidden");
  var orderedOut=new CloseReader();var orderedError=new CloseReader();var handle=new OwnedHandle(()=>orderedOut.Closed&&orderedError.Closed);
  Check(PortableRuntime.CloseOwnedHandles(orderedOut,orderedError,handle,1000)&&handle.Disposed,"owned handle disposed only after both reader tasks");
  var failedHandle=new OwnedHandle(()=>true,true);
  Check(!PortableRuntime.CloseOwnedHandles(null,null,failedHandle,1000)&&failedHandle.Disposed,"owned handle disposal failure remains unconfirmed");
  var failedReader=new CloseReader(true);var afterFault=new OwnedHandle(()=>failedReader.Closed);
  Check(!PortableRuntime.CloseOwnedHandles(failedReader,null,afterFault,1000)&&afterFault.Disposed,"owned handle closure attempted after reader fault");
  var releaseOrdered=new TaskCompletionSource<bool>();var blockedReader=new CloseReader(false,releaseOrdered);var afterPending=new OwnedHandle(()=>blockedReader.Closed);
  try{Check(!PortableRuntime.CloseOwnedHandles(blockedReader,null,afterPending,0)&&!afterPending.Disposed,"pending reader cannot trigger concurrent owned handle disposal");}finally{releaseOrdered.SetResult(true);}
  Check(afterPending.Finished.Task.Wait(1000),"owned handle continuation completes after reader release");
  var unknown=new PortableRuntime.CompletionUnconfirmedException("SYNTHETIC missing receipt",false,new TimeoutException());
  var exited=new PortableRuntime.CompletionUnconfirmedException("SYNTHETIC process exited",true,new IOException());
  Check(!unknown.ProcessExitConfirmed&&exited.ProcessExitConfirmed,"owned exit status distinguished from commit outcome");
  foreach(string prefix in new[]{"Экспорт не выполнен: ","Ревью не записано: ","Экспорт идеи не выполнен: ","Response was NOT imported: ","Цитата не сохранена: ","Источник/реестр не загружен: "}){
   foreach(var ex in new[]{unknown,exited}){string message=PortableRuntime.FailureMessage(ex,prefix,"SYNTHETIC definite-failure suffix");Check(!message.Contains(prefix)&&!message.Contains("definite-failure suffix")&&message.Contains("Данные могли сохраниться")&&message.Contains("автоматического повтора нет"),"uncertain caller message "+prefix);}
  }
  Check(PortableRuntime.FailureMessage(new IOException("SYNTHETIC before start"),"PREFIX "," SUFFIX")=="PREFIX SYNTHETIC before start SUFFIX","ordinary pre-start failure wording preserved");
  Console.WriteLine("PASS "+checks+" in-process runtime reader/drain assertions; Process/Windows/WPF/GUI execution NOT_TESTED");return 0;
 }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}}
}
