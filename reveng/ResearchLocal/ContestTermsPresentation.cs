using System;using System.IO;using System.Linq;using System.Text;using System.Collections;using System.Collections.Generic;using System.Globalization;using System.Text.RegularExpressions;
// Contests (owner's idea, 31.10.2026) in the window: the sealed collector result as contest_terms.py wrote it to
// contest-terms-view.json (payload_json + payload_sha256), shown as quoted terms only. Read-only: no network, no model,
// no ranking, no candidate; a hash mismatch or unknown schema shows a refusal, never partial data.
public static class ContestTermsPresentation {
 public const string FileName="contest-terms-view.json",Schema="contest-terms-view-v1",PayloadSchema="contest-terms-v2";
 static string S(Dictionary<string,object>d,string k){object v;return d!=null&&d.TryGetValue(k,out v)&&v!=null?Convert.ToString(v,CultureInfo.InvariantCulture):"";}
 static Dictionary<string,object>D(object v){return v as Dictionary<string,object>??new Dictionary<string,object>();}
 static Dictionary<string,object>D(Dictionary<string,object>d,string k){object v;return d!=null&&d.TryGetValue(k,out v)?D(v):new Dictionary<string,object>();}
 static IEnumerable<object>A(object v){if(v is IEnumerable&&!(v is string)&&!(v is IDictionary))foreach(var x in(IEnumerable)v)yield return x;}
 static IEnumerable<Dictionary<string,object>>Rows(Dictionary<string,object>d,string k){object v;if(d!=null&&d.TryGetValue(k,out v))foreach(var x in A(v)){var row=x as Dictionary<string,object>;if(row!=null)yield return row;}}
 static string Number(object v){if(v==null)return "";double x;try{x=Convert.ToDouble(v,CultureInfo.InvariantCulture);}catch(Exception){return "не число";}if(Double.IsNaN(x)||Double.IsInfinity(x)||Math.Abs(x)>=1e15)return "вне диапазона";var f=(NumberFormatInfo)CultureInfo.InvariantCulture.NumberFormat.Clone();f.NumberGroupSeparator=" ";return x.ToString(x==Math.Floor(x)?"#,##0":"#,##0.##",f);}
 public static string Money(Dictionary<string,object>p){if(p==null||p.Count==0)return "";string amount=Number(p.ContainsKey("amount")?p["amount"]:null),currency=S(p,"currency");if(amount=="")return "";return amount+(currency==""?"":" "+currency);}
 static string Classification(Dictionary<string,object>r){switch(S(r,"classification")){
  case "contest_terms_found":return "условия найдены: срок и приз процитированы со страницы";
  case "partial_terms":return "часть условий найдена; остальное на странице не найдено";
  case "not_found_in_checked_source":return "в проверенном тексте страницы условий не найдено";
  case "source_unavailable":return "источник недоступен: "+S(r,"error");
  default:return "неизвестный статус: "+S(r,"classification");}}
 static string Deadline(string status){switch(status){case "open":return "открыт";case "closed":return "закрыт";default:return "не найден";}}
 static string Identity(string how){switch(how){case "declared_canonical_matches":return "объявленный canonical совпадает";case "exact_url_no_redirect_no_canonical_declared":return "точный адрес без редиректов, canonical не объявлен";case "":return "не установлена";default:return how;}}
 static string Origin(Dictionary<string,object>r){if(S(r,"origin")=="aggregator_lead"){var lead=D(r,"lead");var listed=new List<string>();if(S(lead,"listed_deadline")!="")listed.Add("срок "+S(lead,"listed_deadline"));string prize=Money(D(lead,"listed_prize"));if(prize!="")listed.Add("приз "+prize);return "лид из вторичного списка ("+S(r,"seed")+")"+(listed.Count>0?"; в списке: "+String.Join(", ",listed)+" - подсказка списка, не условие":"");}return "ручной поиск ассистента ("+S(r,"seed")+"), не автономная находка RevEng";}
 // The owner's swipes on RevEng's phone cards, as Forge's phone sync records them (card id -> like/now/nope); read-only,
 // empty when the phone link is not on this PC or the file cannot be read.
 public static Dictionary<string,string> PhoneDecisions(){var o=new Dictionary<string,string>();try{string f=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"MerchForge","phone-sync","decisions.json");if(!File.Exists(f))return o;foreach(var p in LocalJson.ReadObject(f))if(p.Key.StartsWith("rv_",StringComparison.Ordinal))o[p.Key]=S(D(p.Value),"verdict");}catch(Exception ex){if(ex is OutOfMemoryException)throw;}return o;}
 public static string CardId(string key){string id="rv_c_"+Regex.Replace(key??"","[^A-Za-z0-9_.-]","_");return id.Length>79?id.Substring(0,79):id;}
 static string Verdict(string v){switch(v){case "like":return "копать";case "now":return "отложено";case "nope":return "убрано";default:return "";}}
 public static string Describe(string root){
  string path=Path.Combine(root,FileName);
  if(!File.Exists(path))return "КОНКУРСЫ: сохранённого сбора нет.\r\nНажмите «Собрать условия конкурсов»: программа прочитает страницы организаторов и вторичный список своим ограниченным способом (robots.txt, HTTPS, без редиректов, без модели) и покажет процитированные условия здесь. Сеть сейчас не включалась.";
  try{
   var wrap=LocalJson.ReadObject(path);if(S(wrap,"schema")!=Schema)throw new InvalidDataException("Unknown contest view schema: "+S(wrap,"schema"));
   string payload=S(wrap,"payload_json");if(payload==""||payload.Length>LocalJson.Limit||ProvenanceAudit.Sha(payload)!=S(wrap,"payload_sha256"))throw new InvalidDataException("Contest view payload hash mismatch");
   var data=LocalJson.ParseObject(payload);if(S(data,"schema")!=PayloadSchema)throw new InvalidDataException("Unknown contest payload schema: "+S(data,"schema"));
   return Render(data,PhoneDecisions());
  }catch(Exception ex){if(ex is OutOfMemoryException)throw;return "КОНКУРСЫ: сохранённый сбор не прочитан: "+ex.Message+"\r\nПоказывать нечего; старые данные не подменяются. Сеть и модель не запускались.";}
 }
 public static string Render(Dictionary<string,object>data){return Render(data,null);}
 public static string Render(Dictionary<string,object>data,Dictionary<string,string>decisions){
  var b=new StringBuilder("КОНКУРСЫ: условия, процитированные со страниц организаторов\r\n");
  b.AppendLine("Это возможности с призом и сроком, не оценка и не кандидат: вне общего рейтинга. Участие, допуск, судейство и выплата не подтверждены. Ничего не отправлялось и не публиковалось.");
  var records=Rows(data,"records").ToList();
  b.AppendLine("Сбор: "+S(data,"collected_at")+" | запросов к страницам: "+S(data,"source_requests")+" | запросов к модели: "+S(data,"model_requests")+" | лидов за проход не больше: "+S(data,"lead_limit_per_run"));
  b.AppendLine("Открытых по заявленному сроку: "+records.Count(r=>S(r,"deadline_status")=="open")+" | закрытых: "+records.Count(r=>S(r,"deadline_status")=="closed")+" | срок не найден: "+records.Count(r=>S(r,"deadline_status")!="open"&&S(r,"deadline_status")!="closed"&&S(r,"classification")!="source_unavailable")+" | источник недоступен: "+records.Count(r=>S(r,"classification")=="source_unavailable"));
  int n=0;
  foreach(var r in records){n++;b.AppendLine();
   b.AppendLine(n+". "+S(r,"title")+(S(r,"organizer")!=""?" - "+S(r,"organizer"):"")+" ["+S(r,"key")+"]");
   string mine;if(decisions!=null&&decisions.TryGetValue(CardId(S(r,"key")),out mine)&&Verdict(mine)!="")b.AppendLine("Ваше решение с телефона: "+Verdict(mine));
   b.AppendLine("Откуда: "+Origin(r));
   b.AppendLine("Страница: "+S(r,"source_url"));
   b.AppendLine("Статус: "+Classification(r));
   if(S(r,"classification")=="source_unavailable"){b.AppendLine("Вывода об этом конкурсе нет. Недоступность источника не означает, что конкурса нет.");continue;}
   b.AppendLine("Заявленный срок: "+(S(r,"declared_deadline")==""?"на странице не найден":S(r,"declared_deadline"))+" - "+Deadline(S(r,"deadline_status"))+" (дата со страницы, не дата проверки; отсчёт по дню сбора "+S(data,"today")+")");
   string prize=Money(D(r,"prize"));b.AppendLine("Приз: "+(prize==""?"на странице не найден":prize+" - как написано на странице, не проверено"));
   var fee=D(r,"fee");string feeText=fee.Count==0?"на странице не найден":Number(fee.ContainsKey("amount")?fee["amount"]:null)=="0"?"бесплатно - как написано на странице":Money(fee)+" - как написано на странице";b.AppendLine("Взнос: "+feeText);
   var length=A(r.ContainsKey("length_minutes")?r["length_minutes"]:null).Select(x=>Number(x)).ToArray();
   b.AppendLine("Длительность: "+(length.Length==2?(length[0]==length[1]?length[0]:length[0]+"-"+length[1])+" мин":"не найдена")+" | обязательный инструмент: "+(S(r,"required_tool")==""?"не найден":S(r,"required_tool")));
   var facts=Rows(r,"facts").ToList();if(facts.Count>0){b.AppendLine("Цитаты со страницы (не длиннее 14 слов):");foreach(var f in facts)b.AppendLine("  "+S(f,"id")+" ["+S(f,"kind")+"]: "+S(f,"quote"));}
   var unproven=A(r.ContainsKey("unproven")?r["unproven"]:null).Select(x=>Convert.ToString(x)).ToArray();if(unproven.Length>0)b.AppendLine("На странице не найдено: "+String.Join(", ",unproven));
   b.AppendLine("Проверено: "+S(r,"observed_at")+" | личность страницы: "+Identity(S(r,"source_identity"))+" | SHA256 ответа: "+S(r,"response_sha256"));
  }
  var pairs=Rows(data,"compatible").ToList();b.AppendLine();
  b.AppendLine("ОДНА РАБОТА, НЕСКОЛЬКО КОНКУРСОВ (совпадение по длительности и инструменту; эксклюзивность и премьеру проверять вручную):");
  if(pairs.Count==0)b.AppendLine("  пар с общей длительностью среди открытых конкурсов нет");
  foreach(var p in pairs){var keys=A(p.ContainsKey("contests")?p["contests"]:null).Select(x=>Convert.ToString(x)).ToArray();var shared=A(p.ContainsKey("shared_length_minutes")?p["shared_length_minutes"]:null).Select(x=>Number(x)).ToArray();var warn=A(p.ContainsKey("check_exclusivity_terms_of")?p["check_exclusivity_terms_of"]:null).Select(x=>Convert.ToString(x)).ToArray();
   b.AppendLine("  "+String.Join(" + ",keys)+": общая длительность "+(shared.Length==2?shared[0]+"-"+shared[1]+" мин":"?")+(S(p,"required_tool")!=""?" | инструмент: "+S(p,"required_tool"):"")+(warn.Length>0?" | проверить эксклюзивность: "+String.Join(", ",warn):""));}
  b.AppendLine();b.AppendLine("ВТОРИЧНЫЕ СПИСКИ (агрегаторы): только подсказки; условия берутся со страницы организатора");
  var listings=D(data,"listings");if(listings.Count==0)b.AppendLine("  вторичные списки в этом сборе не читались");
  foreach(var entry in listings){var item=D(entry.Value);var leads=Rows(item,"leads").ToList();
   b.AppendLine("  "+S(item,"title")+" | "+S(item,"source_url")+" | "+(S(item,"classification")=="source_unavailable"?"недоступен: "+S(item,"error"):S(item,"classification")=="listing_read"?"прочитан":S(item,"classification")));
   if(leads.Count==0)continue;
   b.AppendLine("  Ссылок на организаторов: "+leads.Count+" | проверено на страницах организаторов: "+leads.Count(l=>S(l,"status")=="checked_on_organizer_page")+" | уже среди ручных семян: "+leads.Count(l=>S(l,"status")=="already_seeded")+" | не проверено в этот проход: "+leads.Count(l=>S(l,"status").StartsWith("not_checked")));
   int shown=0;foreach(var l in leads){if(S(l,"status")=="checked_on_organizer_page"||S(l,"status")=="already_seeded")continue;if(shown==40){b.AppendLine("    ... и ещё "+(leads.Count(x=>S(x,"status").StartsWith("not_checked"))-shown)+"; следующий проход берёт ближайшие по сроку");break;}shown++;
    b.AppendLine("    не проверен"+(S(l,"status").EndsWith("_listed_date_passed")?" (дата в списке прошла)":"")+": "+S(l,"text")+" | "+S(l,"url")+(S(l,"listed_deadline")!=""?" | в списке: "+S(l,"listed_deadline"):""));}
  }
  b.AppendLine();b.AppendLine("Доступный сейчас шаг: открыть страницу организатора по ссылке и прочитать правила самому. Отправка работы, оплата взноса, регистрация и публикация этим экраном не выполняются и не разрешаются.");
  return b.ToString();
 }
}
