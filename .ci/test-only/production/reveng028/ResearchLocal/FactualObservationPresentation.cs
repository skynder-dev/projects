using System;using System.Text;using System.Collections;using System.Collections.Generic;using System.Security.Cryptography;using System.Globalization;using System.Text.RegularExpressions;
// Literal observations only. No price arithmetic, buyer inference or economic score.
public static class FactualObservationPresentation {
 static string S(Dictionary<string,object>d,string k){object v;return d.TryGetValue(k,out v)&&v!=null?Convert.ToString(v):"";}
 static Dictionary<string,object> D(object x){return x as Dictionary<string,object>??new Dictionary<string,object>();}
 static object V(Dictionary<string,object>d,string k){object x;return d.TryGetValue(k,out x)?x:null;}
 static IEnumerable<object>A(object x){if(x is IEnumerable&&!(x is string)&&!(x is IDictionary))foreach(var item in(IEnumerable)x)yield return item;}
 static string Hash(string t){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(new UTF8Encoding(false,true).GetBytes(t))).Replace("-","").ToLowerInvariant();}
 public static string Price(Dictionary<string,object> p){var b=new StringBuilder("Цена — буквальное наблюдение, не оплата клиента и не доход.\r\n");bool bound=false;try{var c=D(V(p,"context_citation"));int a=Convert.ToInt32(V(c,"price_start")),z=Convert.ToInt32(V(c,"price_end"));bound=!String.IsNullOrWhiteSpace(S(p,"displayed_price"))&&a>=0&&z>a&&!(V(c,"price_start")is bool)&&!(V(c,"price_end")is bool)&&Hash(S(p,"context"))==S(c,"text_sha256")&&ProvenanceAudit.Slice(S(p,"context"),a,z)==S(p,"displayed_price");}catch{bound=false;}
  b.AppendLine(S(p,"provider")+": "+S(p,"displayed_price")+" | currency literal: "+S(p,"currency")).AppendLine(S(p,"context"));
  b.AppendLine(bound?"Привязка: EXACT_SAVED_CONTEXT_ONLY; не аутентификация HTTP ответа":"Привязка: LEGACY_OR_UNVERIFIED_CONTEXT; цену не домысливаем");
  string role=S(p,"amount_role");if(role==""){string literal=S(p,"displayed_price"),context=S(p,"context");var roles=new HashSet<string>();if(literal!="")foreach(Match match in Regex.Matches(context,Regex.Escape(literal))){string before=context.Substring(Math.Max(0,match.Index-35),Math.Min(35,match.Index)),after=context.Substring(match.Index+match.Length);string value="unclassified_amount_not_verified_base_tariff";if(Regex.IsMatch(before,@"\bSave\s*$",RegexOptions.IgnoreCase))value="savings_not_subscription";else if(Regex.IsMatch(after,@"^\s+per\s+(?:credit card|Amex)\s+transaction\b",RegexOptions.IgnoreCase))value="transaction_fee_not_subscription";else if(Regex.IsMatch(before,@"\bAdd users for\s*$",RegexOptions.IgnoreCase)&&Regex.IsMatch(after,@"^\s+each\b",RegexOptions.IgnoreCase))value="additional_user_charge_not_base_plan";roles.Add(value);}if(roles.Count==1)foreach(string value in roles)role=value;}
  if(role!="")b.AppendLine("Amount role: "+role);
  b.AppendLine("Comparison basis unknown: currency, billing commitment, seats, included functions and limits must match before comparing prices.");
  foreach(var item in A(V(p,"nearby_conditions"))){var condition=D(item);bool exact=false;try{var c=D(V(p,"context_citation"));int offset=Convert.ToInt32(V(c,"source_start"));exact=bound&&ProvenanceAudit.Slice(S(p,"context"),Convert.ToInt32(V(condition,"start"))-offset,Convert.ToInt32(V(condition,"end"))-offset)==S(condition,"quote");}catch{}if(exact)b.AppendLine("Nearby source wording (not assigned to this amount/plan): "+S(condition,"quote"));}
  if(S(p,"free_plan_status")!="")b.AppendLine(S(p,"free_plan_status"));
  var span=D(V(p,"citation"));if(bound)b.AppendLine("Source codepoint ["+S(span,"start")+","+S(span,"end")+") | text SHA256: "+S(p,"source_text_sha256"));
  b.AppendLine("Source: "+S(p,"source_url")).AppendLine("Capture: "+EvidenceDates.Display(V(p,"observed_at"))+" | response SHA256: "+S(p,"response_sha256"));
  DateTimeOffset at;string stamp=S(p,"observed_at");bool recent=Regex.IsMatch(stamp,@"(?:Z|[+-]\d{2}:\d{2})$")&&DateTimeOffset.TryParse(stamp,CultureInfo.InvariantCulture,DateTimeStyles.None,out at)&&at<=DateTimeOffset.UtcNow&&(DateTimeOffset.UtcNow-at).TotalHours<=24;
  b.AppendLine(recent?"Снимок в пределах24ч; актуальность тарифа/рынка всё равно не доказана":"Историческое наблюдение или дата неизвестна/будущая; не считать текущим тарифом");
  if(S(p,"extraction_truncated")=="True")b.AppendLine("Извлечение ограничено: найдено "+S(p,"extraction_total_matches")+", сохранено "+S(p,"extraction_returned")+"; отсутствие остальных цен не утверждается");
  b.AppendLine("План, регион, налоги, обязательство и соответствие задаче требуют отдельной проверки.");return b.ToString();
 }
 public static string Captures(Dictionary<string,object> row){var b=new StringBuilder();var old=D(V(row,"source_profile"));var active=D(V(row,"plan_feature_mapping"));if(S(row,"plan_and_assessment_capture_relation")=="DIFFERENT_CAPTURES_DO_NOT_MERGE"||S(old,"observed_at")!=""&&S(active,"observed_at")!=""&&S(old,"observed_at")!=S(active,"observed_at"))b.AppendLine("Суждение и тарифный mapping относятся к разным фиксациям; старое суждение не обновлено.");if(S(row,"assessment_state")!="")b.AppendLine(S(row,"assessment_state"));
  b.AppendLine("Assessment source: "+S(old,"source_url")+" | "+S(old,"observed_at"));
  var observations=new List<object>();foreach(var x in A(V(row,"plan_mapping_observations")))observations.Add(x);if(observations.Count==0&&active.Count>0)observations.Add(active);
  foreach(var entry in observations){var capture=D(entry);b.AppendLine("Отдельное ценовое наблюдение: "+S(capture,"source_url")+" | "+S(capture,"observed_at")+" | response SHA256: "+S(capture,"response_sha256"));var seen=new HashSet<string>();foreach(var item in A(V(capture,"links"))){var link=D(item);string value=S(link,"plan")+" | "+S(link,"displayed_price")+" | "+S(link,"billing");if(seen.Add(value))b.AppendLine(value);}}
  if(S(row,"plan_capture_state")!="")b.AppendLine(S(row,"plan_capture_state"));return b.ToString();
 }
 public static string LatestSourceCapture(Dictionary<string,object> row){var b=new StringBuilder();var doc=D(V(row,"plan_evidence_source_profile"));if(doc.Count==0)return "";var mapping=D(V(row,"plan_feature_mapping"));
  if(S(doc,"source_url")!=S(mapping,"source_url")||S(doc,"observed_at")!=S(mapping,"observed_at")||S(doc,"response_sha256")==""||S(doc,"response_sha256")!=S(mapping,"response_sha256"))return "NEW_SOURCE_CAPTURE_QUARANTINED: profile/mapping identity differs.\r\n";
  b.AppendLine("New plan/source capture: literal evidence, assessment not renewed.").AppendLine("Source: "+S(doc,"source_url")).AppendLine("Capture: "+S(doc,"observed_at")+" | response SHA256: "+S(doc,"response_sha256"));
  var scope=D(V(doc,"price_scope"));var ids=new HashSet<string>();foreach(var x in A(V(doc,"facts")))ids.Add(S(D(x),"id"));
  foreach(string key in new[]{"monthly","yearly","currency","tax","subscription_unit","per_seat","addons","trial"}){var field=D(V(scope,key));bool bound=false;foreach(var id in A(V(field,"evidence_ids")))if(ids.Contains(Convert.ToString(id)))bound=true;b.AppendLine("New capture "+key+": "+(S(field,"status")=="observed"&&bound?S(field,"value"):"unknown"));}
  foreach(var x in A(V(mapping,"page_conditions"))){var condition=D(x);b.AppendLine("Page condition: "+S(condition,"kind")+" | "+S(condition,"quote"));}
  var promo=D(V(mapping,"promotion_terms"));if(promo.Count>0)b.AppendLine("Displayed promotion terms: "+S(promo,"status")+" | "+S(promo,"start_date")+" to "+S(promo,"end_date")).AppendLine(S(promo,"quote"));
  b.AppendLine("No current offer, customer, task equivalence, price advantage or business readiness inferred.");return b.ToString();
 }

}
