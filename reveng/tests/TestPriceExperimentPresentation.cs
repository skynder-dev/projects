using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Web.Script.Serialization;

// Compile with the actual production formatter. No Forms, legacy binary or UI needed.
public static class TestPriceExperimentPresentation {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
 static int checks;
 static void Check(bool ok,string name){if(!ok)throw new Exception("FAILED "+name);checks++;}
 static Dictionary<string,object> Offer(object amount){return new Dictionary<string,object>{{"price_experiment",new Dictionary<string,object>{{"status","proposed_unverified"},{"amount",amount},{"currency","USD"}}}};}
 static bool Valid(string text){return text.StartsWith("Proposed UNVERIFIED test offer: ",StringComparison.Ordinal);}
 public static int Main(string[] args){try{
  var vectors=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(args[0],Encoding.UTF8));
  foreach(Dictionary<string,object> item in (IEnumerable)vectors["cases"]){
   string name=(string)item["name"],expected=(string)item["expected_status"];
   var candidate=(Dictionary<string,object>)item["candidate"];string before=Json.Serialize(candidate);
   string text=PriceExperimentPresentation.Describe(candidate);
   string actual=text==""?"absent":Valid(text)?"proposed_unverified":"malformed_untrusted_offer";
   Check(actual==expected,name+" status");
   if(expected=="proposed_unverified"){
    Check(text.IndexOf((string)item["expected_display"],StringComparison.OrdinalIgnoreCase)>=0,name+" exact proposed amount/currency");
    Check(text.Contains("unverified currency label")&&text.Contains("Not observed price, payment, revenue or demand; no action authorized."),name+" uncertainty and authority");
    Check(text.Contains("Displayed zero may reflect native numeric rounding;")==(bool)item["free_test"],name+" zero carries original-offer precision caveat");
    Check(!text.Contains("Zero means a proposed free test."),name+" parsed zero is not exact lexical proof");
   }else if(expected=="malformed_untrusted_offer")Check(text=="Proposed offer data is malformed or too large; amount/currency withheld pending review.",name+" no raw amount or currency exposed");
   var builder=new StringBuilder("existing\n");PriceExperimentPresentation.Append(builder,candidate);
   Check(builder.ToString()=="existing\n"+(text==""?"":text+Environment.NewLine),name+" actual append path");
   Check(Json.Serialize(candidate)==before,name+" source untouched");
  }
  // These cases use the same JSON reader as the actual card views, not boxed values.
  foreach(Dictionary<string,object> item in (IEnumerable)vectors["reader_precision_cases"]){
   string name=(string)item["name"];
   var candidate=Json.Deserialize<Dictionary<string,object>>((string)item["candidate_json"]);
   string before=Json.Serialize(candidate),text=PriceExperimentPresentation.Describe(candidate);
   var offer=(Dictionary<string,object>)candidate["price_experiment"];
   double decoded=Convert.ToDouble(offer["amount"],CultureInfo.InvariantCulture);
   Check(!text.Contains("Zero means a proposed free test."),name+" actual reader does not infer free");
   if(Valid(text)&&decoded==0)Check(text.Contains("Displayed zero may reflect native numeric rounding;")&&text.Contains("if the original offer is exactly zero"),name+" reader-rounded zero is explicit");
   if(decoded<0)Check(!Valid(text),name+" retained negative value withheld");
   if(Valid(text))Check(text.Contains("Not observed price, payment, revenue or demand; no action authorized."),name+" reader precision does not authorize anything");
   Check(Json.Serialize(candidate)==before,name+" decoded card unchanged");
  }
  foreach(object invalid in new object[]{Double.NaN,Double.PositiveInfinity,Double.NegativeInfinity,Single.NaN,Single.PositiveInfinity,1e64,1e100})Check(!Valid(PriceExperimentPresentation.Describe(Offer(invalid))),"nonfinite/extreme CLR number withheld");
  foreach(object number in new object[]{10L,10U,10UL,10m,10f})Check(PriceExperimentPresentation.Describe(Offer(number)).Contains("10 USD"),"native numeric type remains numeric");
  Check(PriceExperimentPresentation.Describe(Offer(-0.0)).Contains("Displayed zero may reflect native numeric rounding;"),"negative zero does not prove an exact free offer");
  Check(Valid(PriceExperimentPresentation.Describe(Offer(Double.Epsilon))),"small positive amount is not zero");
  Check(!PriceExperimentPresentation.Describe(Offer(Double.Epsilon)).Contains("Displayed zero may reflect native numeric rounding;"),"small positive amount not mislabeled as displayed zero");
  var previous=System.Threading.Thread.CurrentThread.CurrentCulture;try{System.Threading.Thread.CurrentThread.CurrentCulture=new CultureInfo("fr-FR");Check(PriceExperimentPresentation.Describe(Offer(12.5m)).Contains("12.5 USD"),"locale does not change decimal meaning");}finally{System.Threading.Thread.CurrentThread.CurrentCulture=previous;}
  Check(PriceExperimentPresentation.Describe(null)=="","null candidate unchanged");
  Console.WriteLine("PASS "+checks+" native formatter assertions; synthetic only; no GUI/model/network");return 0;
 }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}}
}
