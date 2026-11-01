using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

// Display a proposed test offer only. Never infer a sale, currency validity or profit.
public static class PriceExperimentPresentation {
 const string Withheld="Proposed offer data is malformed or too large; amount/currency withheld pending review.";

 static bool Number(object value,out string text,out bool zero){
  text=null;zero=false;
  if(!(value is byte||value is sbyte||value is short||value is ushort||value is int||value is uint||value is long||value is ulong||value is float||value is double||value is decimal))return false;
  double number=Convert.ToDouble(value,CultureInfo.InvariantCulture);
  // The native JSON reader may coerce a >64-digit integer to a short exponent.
  // Withhold extreme magnitudes rather than displaying that rounded surrogate.
  if(Double.IsNaN(number)||Double.IsInfinity(number)||number<0||number>=1e64)return false;
  text=((IFormattable)value).ToString(value is double||value is float?"R":null,CultureInfo.InvariantCulture);
  if(text.Length>64)return false;
  zero=number==0;return true;
 }

 public static string Describe(Dictionary<string,object> candidate){
  object raw;
  // Absent/null preserve the old presentation; never fill an amount or currency.
  if(candidate==null||!candidate.TryGetValue("price_experiment",out raw)||raw==null)return "";
  var offer=raw as Dictionary<string,object>;
  object status,amount,currency;
  if(offer==null||offer.Count!=3||!offer.TryGetValue("status",out status)||!offer.TryGetValue("amount",out amount)||!offer.TryGetValue("currency",out currency)||!(status is string)||(string)status!="proposed_unverified"||!(currency is string))return Withheld;
  string label=(string)currency;
  if(label.Length!=3||label[0]<'A'||label[0]>'Z'||label[1]<'A'||label[1]>'Z'||label[2]<'A'||label[2]>'Z')return Withheld;
  string number;bool displayedZero;
  if(!Number(amount,out number,out displayedZero))return Withheld;
  return "Proposed UNVERIFIED test offer: "+number+" "+label+" (unverified currency label). "+(displayedZero?"Displayed zero may reflect native numeric rounding; a free test is only a hypothesis if the original offer is exactly zero. ":"")+"Not observed price, payment, revenue or demand; no action authorized.";
 }

 public static void Append(StringBuilder text,Dictionary<string,object> candidate){
  string offer=Describe(candidate);if(offer!="")text.AppendLine(offer);
 }
}
