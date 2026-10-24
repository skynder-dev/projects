using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using System.Reflection;
using System.Runtime.InteropServices;
public static class TestOutcome {
 static readonly JavaScriptSerializer J=new JavaScriptSerializer{MaxJsonLength=8388608};
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
 [return:MarshalAs(UnmanagedType.I1)]
 static extern bool CreateSymbolicLink(string link,string target,int flags);
 static void Link(string link,string target,bool directory){
  int flags=directory?1:0;
  if(!CreateSymbolicLink(link,target,flags|2)&&!CreateSymbolicLink(link,target,flags))throw new InvalidOperationException("Windows owned-link test prerequisite unavailable; containment is NOT qualified. Error "+Marshal.GetLastWin32Error());
 }
 static MethodInfo Private(string name){var method=typeof(AnalysisOutcomePresentation).GetMethod(name,BindingFlags.Static|BindingFlags.NonPublic);if(method==null)throw new Exception("Required snapshot reader method missing: "+name);return method;}
 static string Digest(byte[] raw){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(raw)).Replace("-","").ToLowerInvariant();}
 static string root;static int tests;static string Id=new string('a',64);
 static Dictionary<string,object> O(params object[] a){var d=new Dictionary<string,object>();for(int i=0;i<a.Length;i+=2)d[(string)a[i]]=a[i+1];return d;}
 static string H(string p){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(File.ReadAllBytes(p))).Replace("-","").ToLowerInvariant();}
 static void Write(string p,object x){Directory.CreateDirectory(Path.GetDirectoryName(p));File.WriteAllText(p,J.Serialize(x),new UTF8Encoding(false));}
 sealed class F{public string Root,Input,Result,Metrics;public Dictionary<string,object> Job;}
 static F Fixture(string name,object hypotheses,string state="completed_needs_review",string finish="stop"){
  var f=new F{Root=Path.Combine(root,name),Input="analysis-inputs/"+Id+".json",Result="analysis-results/"+Id+".json",Metrics="analysis-results/"+Id+"-metrics.json"};Directory.CreateDirectory(f.Root);
  Write(Path.Combine(f.Root,f.Input),O("input_sha256",Id,"schema","SYNTHETIC_PRESENTATION_FIXTURE","request",O("format",O("properties",O("hypotheses",O("type","array","minItems",0,"maxItems",3))))));
  string raw=Path.Combine(f.Root,"runs/synthetic/raw.json");Write(raw,O("synthetic",true,"hypotheses",hypotheses));
  Write(Path.Combine(f.Root,f.Result),O("model_output",O("source_job",Id,"hypotheses",hypotheses),"raw_response_sha256",H(raw),"raw_response_retained_in_run","runs/synthetic/raw.json"));
  Write(Path.Combine(f.Root,f.Metrics),O("source_job",Id,"status","VALIDATED_MODEL_OUTPUT","model_calls",1,"finish_reason",finish));
  f.Job=O("status",state,"input_file",f.Input,"input_file_sha256",H(Path.Combine(f.Root,f.Input)),"analysis_result",f.Result,"result_file_sha256",H(Path.Combine(f.Root,f.Result)),"analysis_metrics",f.Metrics);
  Write(Path.Combine(f.Root,"analysis-queue.json"),O("jobs",O(Id,f.Job)));return f;
 }
 static void Check(bool x,string name){if(!x)throw new Exception("FAILED "+name);tests++;Console.WriteLine("PASS "+name);}
 static AnalysisOutcomePresentation.Entry Inspect(F f){return AnalysisOutcomePresentation.Inspect(f.Root,Id,f.Job);}
 static Dictionary<string,string> Snapshot(F f){return Directory.GetFiles(f.Root,"*",SearchOption.AllDirectories).ToDictionary(p=>p,p=>H(p));}
 public static int Main(string[] args){Console.OutputEncoding=new UTF8Encoding(false);try{
  root=Path.GetFullPath(args[0]);Directory.CreateDirectory(root);
  var empty=Fixture("empty",new object[0]);var before=Snapshot(empty);var e=Inspect(empty);
  Check(e.Kind=="completed_empty"&&e.Message==AnalysisOutcomePresentation.EmptyMessage,"completed-empty exact truthful status");
  string normalized=e.Text.Replace('\\','/');Check(normalized.Contains(empty.Input)&&normalized.Contains(empty.Result)&&normalized.Contains("SHA256")&&normalized.Contains("runs/synthetic/raw.json"),"lineage raw/hash references retained");
  Check(AnalysisOutcomePresentation.Load(empty.Root).Length==1&&AnalysisOutcomePresentation.Load(empty.Root)[0].Kind=="completed_empty","history contains an outcome even with zero cards");
  Check(AnalysisOutcomePresentation.Current(empty.Root,O("analysis_job",Id)).Kind=="completed_empty","current job selects same empty outcome");
  var after=Snapshot(empty);Check(before.Count==after.Count&&before.All(k=>after[k.Key]==k.Value),"presentation never changes raw result input metrics queue");
  var one=Fixture("one",new object[]{O("title","SYNTHETIC ONE CARD")});Check(Inspect(one).Kind=="completed_with_hypotheses"&&!Inspect(one).Message.Contains("не сообщила причину"),"one-card remains distinct and count retained");
  foreach(string state in new[]{"failed","cancelled","awaiting_authorized_executor","running"}){var f=Fixture(state,new object[0],state);string expected=state=="awaiting_authorized_executor"?"not_started":state;Check(Inspect(f).Kind==expected,"state "+state+" is not abstention");}
  var length=Fixture("length",new object[0],"completed_needs_review","length");Check(Inspect(length).Kind=="truncated","length never promoted to successful empty");
  var noStop=Fixture("no-stop",new object[0],"completed_needs_review","");Check(Inspect(noStop).Kind=="unconfirmed","missing completion evidence not successful empty");
  var altered=Fixture("altered",new object[0]);File.AppendAllText(Path.Combine(altered.Root,altered.Result)," ");Check(Inspect(altered).Kind=="unconfirmed","changed result hash rejected");
  var wrong=Fixture("wrong-id",new object[0]);Write(Path.Combine(wrong.Root,wrong.Metrics),O("source_job",new string('b',64),"status","VALIDATED_MODEL_OUTPUT","model_calls",1,"finish_reason","stop"));Check(Inspect(wrong).Kind=="unconfirmed","receipt cannot cross source revision");
  var outside=Fixture("outside",new object[0]);outside.Job["analysis_result"]="../other.json";Check(Inspect(outside).Kind=="unconfirmed","path escape rejected");
  var badArray=Fixture("bad-array",O());Check(Inspect(badArray).Kind=="unconfirmed","missing/invalid hypotheses not successful empty");
  var reason=Fixture("extra-reason",new object[0]);Write(Path.Combine(reason.Root,reason.Result),O("model_output",O("source_job",Id,"hypotheses",new object[0],"reason","SYNTHETIC unexpected field")));reason.Job["result_file_sha256"]=H(Path.Combine(reason.Root,reason.Result));Check(Inspect(reason).Kind=="unconfirmed","unsupported rationale is not inferred or hidden");
  var min3=Fixture("min-three",new object[0]);Write(Path.Combine(min3.Root,min3.Input),O("input_sha256",Id,"request",O("format",O("properties",O("hypotheses",O("minItems",3))))));min3.Job["input_file_sha256"]=H(Path.Combine(min3.Root,min3.Input));Check(Inspect(min3).Kind=="unconfirmed","old non-abstaining schema not reclassified");
  string direct=AnalysisOutcomePresentation.DirectNote(O("status","completed","hypotheses",new object[0]));Check(direct.Contains("требует подтверждения")&&!direct.Contains("модель не сообщила причину"),"unbound direct empty remains unconfirmed");
  Write(Path.Combine(empty.Root,"analysis-queue.json"),O("jobs",new object[0]));Check(AnalysisOutcomePresentation.Load(empty.Root).Single().Kind=="unconfirmed","corrupt history does not look empty or successful");
  var rejected=Fixture("reviewer-repro",new object[0]);Write(Path.Combine(rejected.Root,rejected.Metrics),O("source_job",Id,"status","MODEL_OUTPUT_NEEDS_REVIEW","model_calls",1,"finish_reason","stop","strict_validation_error","SYNTHETIC invalid original JSON/schema","abstained",false,"raw_output_cards",3));Check(Inspect(rejected).Kind=="unconfirmed","reviewer invalid raw projection is not successful empty");
  foreach(string key in new[]{"strict_validation_error","validation_error","validation_errors","parse_error","parse_errors","abstained","raw_output_cards","output_cards"}){
   var negative=Fixture("marker-"+key,new object[0]);var receipt=O("source_job",Id,"status","MODEL_OUTPUT_NEEDS_REVIEW","model_calls",1,"finish_reason","stop");receipt[key]=key=="abstained"?(object)false:key.EndsWith("cards")?(object)3:(object)"SYNTHETIC error";Write(Path.Combine(negative.Root,negative.Metrics),receipt);Check(Inspect(negative).Kind=="unconfirmed","individual negative marker "+key);
  }
  var validReview=Fixture("valid-semantic-pending",new object[0]);Write(Path.Combine(validReview.Root,validReview.Metrics),O("source_job",Id,"status","MODEL_OUTPUT_NEEDS_REVIEW","model_calls",1,"finish_reason","stop","strict_validation_error","","parse_errors",new object[0],"abstained",true,"raw_output_cards",0,"output_cards",0));Check(Inspect(validReview).Kind=="completed_empty","structurally valid empty still allowed pending semantic review");
  foreach(string location in new[]{"job","saved"}){
   var negative=Fixture("location-"+location,new object[0]);if(location=="job")negative.Job["parse_error"]="SYNTHETIC error";else{string path=Path.Combine(negative.Root,negative.Result);var saved=J.DeserializeObject(File.ReadAllText(path)) as Dictionary<string,object>;saved["validation_error"]="SYNTHETIC error";Write(path,saved);negative.Job["result_file_sha256"]=H(path);}Check(Inspect(negative).Kind=="unconfirmed","negative evidence on "+location);
  }
  foreach(string which in new[]{"input","metrics"}){
   var large=Fixture("oversize-"+which,new object[0]);string path=Path.Combine(large.Root,which=="input"?large.Input:large.Metrics);
   using(var file=new FileStream(path,FileMode.Create,FileAccess.Write,FileShare.None))file.SetLength(LocalJson.Limit+1L);
   var rejectedLarge=Inspect(large);Check(rejectedLarge.Kind=="unconfirmed"&&rejectedLarge.Text.Contains("bounded size"),"oversize "+which+" rejected before hashing/parsing");
  }
  var linkedFile=Fixture("linked-file",new object[0]);string originalInput=Path.Combine(linkedFile.Root,linkedFile.Input),ownedFile=Path.Combine(root,"owned-outside-input.json");File.Move(originalInput,ownedFile);string outsideHash=H(ownedFile);Link(originalInput,ownedFile,false);
  var linkedFileResult=Inspect(linkedFile);Check(linkedFileResult.Kind=="unconfirmed"&&linkedFileResult.Text.Contains("Reparse")&&H(ownedFile)==outsideHash,"file symlink outside fixture rejected; owned target unchanged");
  var linkedDirectory=Fixture("linked-directory",new object[0]);string originalDirectory=Path.Combine(linkedDirectory.Root,"analysis-results"),ownedDirectory=Path.Combine(root,"owned-outside-results");Directory.Move(originalDirectory,ownedDirectory);Link(originalDirectory,ownedDirectory,true);
  var linkedDirectoryResult=Inspect(linkedDirectory);Check(linkedDirectoryResult.Kind=="unconfirmed"&&linkedDirectoryResult.Text.Contains("Reparse"),"directory reparse outside fixture rejected");
  var linkedRoot=Fixture("root-target",new object[0]);string rootAlias=Path.Combine(root,"root-alias");Link(rootAlias,linkedRoot.Root,true);
  var linkedRootResult=AnalysisOutcomePresentation.Inspect(rootAlias,Id,linkedRoot.Job);Check(linkedRootResult.Kind=="unconfirmed"&&linkedRootResult.Text.Contains("Reparse"),"reparse workspace root rejected before evidence reads");
  var coherent=Fixture("snapshot-coherence",new object[0]);string coherentInput=Path.Combine(coherent.Root,coherent.Input);
  object snapshot=Private("ReadSnapshot").Invoke(null,new object[]{coherent.Root,coherentInput,H(coherentInput)});Type snapshotType=snapshot.GetType();byte[] snapshotBytes=(byte[])snapshotType.GetField("Bytes").GetValue(snapshot);string snapshotDigest=(string)snapshotType.GetField("Digest").GetValue(snapshot);var snapshotData=(Dictionary<string,object>)snapshotType.GetField("Data").GetValue(snapshot);
  Check(snapshotDigest==Digest(snapshotBytes)&&J.Serialize(snapshotData)==J.Serialize(LocalJson.ParseObject(LocalJson.Decode(snapshotBytes))),"checked hash and parsed JSON use the same bounded buffer");
  Write(coherentInput,O("input_sha256",new string('b',64),"schema","SYNTHETIC REPLACEMENT"));Check(snapshotDigest!=H(coherentInput)&&(string)snapshotData["input_sha256"]==Id,"later path replacement cannot change retained snapshot/provenance");
  using(var opened=new FileStream(coherentInput,FileMode.Open,FileAccess.Read,FileShare.Read)){
   bool mismatchRejected=false;try{Private("VerifyOpenedPath").Invoke(null,new object[]{opened,Path.Combine(coherent.Root,"different-owned-path.json")});}catch(TargetInvocationException ex){mismatchRejected=ex.InnerException is InvalidDataException;}
   Check(mismatchRejected,"opened handle path must match expected path before byte access");
  }
  Console.WriteLine("TOTAL "+tests+" SYNTHETIC presentation checks; no GUI/model/production writes");return 0;
 }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}}
}
