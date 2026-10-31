using System;
using System.Collections.Generic;
using System.Web.Script.Serialization;

// References the actual application assembly; invokes only a static formatter, no Forms.
public static class TestOwnerPreferencePresentation {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
 static int checks;
 static Dictionary<string,object> O(params object[] values){var d=new Dictionary<string,object>();for(int i=0;i<values.Length;i+=2)d[(string)values[i]]=values[i+1];return d;}
 static void Check(bool ok,string name){if(!ok)throw new Exception("FAILED "+name);checks++;}
 static Dictionary<string,object> Snapshot(string binding,string choice,string status="READABLE",string scope="LOCAL_CURRENT_RESEARCH"){
  return O("projection",O("binding",binding,"current_choice",choice,"current_review_revision_hash",new string('f',64),"saved_entry",O("decision",choice??"keep","revision_hash",new string(binding=="CURRENT_EXACT_REVISION"?'f':'e',64),"note","SYNTHETIC retained note")),"status",status,"workspace_scope",scope,"snapshot_sha256",new string('a',64),"inputs",O("review-notes.json",O("state","captured","sha256",new string('b',64))),"issues",new object[0]);
 }
 public static int Main(){try{
  foreach(string choice in new[]{"keep","reject"}){
   var data=Snapshot("CURRENT_EXACT_REVISION",choice);string before=Json.Serialize(data),text=EvidenceComparison.OwnerPreferenceDescription(data);
   Check(text.Contains("Current exact-revision preference: "+choice),choice+" visible");Check(text.Contains("separate from evidence-review decisions"),choice+" not evidence approval");Check(text.Contains("SYNTHETIC retained note"),choice+" note retained");Check(Json.Serialize(data)==before,choice+" source unchanged");
  }
  foreach(string binding in new[]{"HISTORICAL_OR_UNBOUND","UNAVAILABLE_NOT_CURRENT","RECOVERY_CONFLICT_NOT_CURRENT"}){
   string text=EvidenceComparison.OwnerPreferenceDescription(Snapshot(binding,null,binding.StartsWith("UNAVAILABLE")?"UNAVAILABLE":binding.StartsWith("RECOVERY")?"RECOVERY_CONFLICT":"READABLE"));
   Check(text.Contains("No current choice is applied here.")&&!text.Contains("Current exact-revision preference:"),binding+" not applied");Check(text.Contains("SYNTHETIC retained note"),binding+" saved note inspectable");
  }
  string archived=EvidenceComparison.OwnerPreferenceDescription(Snapshot("CURRENT_EXACT_REVISION","keep","READABLE","HISTORICAL_READ_ONLY_ARCHIVE"));Check(archived.Contains("HISTORICAL ARCHIVE preference only; current workspace choices are unchanged."),"archive cannot replace current workspace choice");
  string absent=EvidenceComparison.OwnerPreferenceDescription(Snapshot("NO_SAVED_OWNER_DECISION",null,"ABSENT"));Check(absent.Contains("No saved Keep/Reject entry in the captured primary notes"),"absence explicit");
  Check(EvidenceComparison.OwnerPreferenceDescription(O())=="","unrelated card has no attached preference");
  Console.WriteLine("PASS "+checks+" SYNTHETIC native preference presentation checks; no GUI/model/network");return 0;
 }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}}
}
