using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Web.Script.Serialization;

// Compile against the production wrapper.exe (ContestTermsPresentation, LocalJson, ProvenanceAudit). Synthetic view file
// only: no Forms, no network, no model. Checks that quoted terms, origins, lead statuses and refusals render as the
// window shows them, and that a hash mismatch or unknown schema shows nothing but the refusal.
public static class TestContestTermsPresentation {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer{MaxJsonLength=8388608};
 static int checks;
 static void Check(bool ok,string name){if(!ok)throw new Exception("FAILED "+name);checks++;}
 static Dictionary<string,object> Money(double amount,string currency){return new Dictionary<string,object>{{"amount",amount},{"currency",currency},{"status","proposed_unverified"}};}
 static Dictionary<string,object> Record(string key,string title,string origin,string classification,string deadline,string status){
  return new Dictionary<string,object>{{"schema","contest-terms-v2"},{"rules_version","contest-terms-rules-v1"},{"kind","official_contest_terms"},{"key",key},{"organizer","SYNTHETIC Organizer"},{"title",title},
   {"source_url","https://organizer.example/"+key},{"seed",origin=="manual_seed"?"assistant manual web search 2026-10-31":"lead from https://agg.example/ (secondary list)"},{"origin",origin},
   {"observed_at","2026-11-01T00:00:00+00:00"},{"response_sha256",new string('a',64)},{"expires",1.0},{"classification",classification},{"declared_deadline",deadline},{"deadline_status",status},
   {"facts",new object[]{new Dictionary<string,object>{{"id","K1"},{"kind","deadline"},{"quote","Submissions close on 20 November 2026"}},new Dictionary<string,object>{{"id","K2"},{"kind","prize"},{"quote","prize of US$1,000,000"}}}},
   {"prize",Money(1000000.0,"USD")},{"fee",Money(0.0,null)},{"length_minutes",new object[]{5,7}},{"required_tool","Seedance"},{"unproven",new object[]{"eligibility","format"}},
   {"automatic_admission",false},{"global_ranking","excluded"},{"source_identity","declared_canonical_matches"},{"interpretation","Terms as quoted"}};
 }
 static string Write(string root,object payloadObject,string schema="contest-terms-view-v1",string tamper=null){
  string payload=payloadObject as string??Json.Serialize(payloadObject);
  var wrap=new Dictionary<string,object>{{"schema",schema},{"written_at","2026-11-01T00:00:00+00:00"},{"payload_sha256",tamper??ProvenanceAudit.Sha(payload)},{"payload_json",payload}};
  File.WriteAllText(Path.Combine(root,ContestTermsPresentation.FileName),Json.Serialize(wrap),new UTF8Encoding(false));return payload;
 }
 public static int Main(string[] args){try{
  string root=Path.Combine(Path.GetTempPath(),"reveng-contest-view-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
  try{
   string missing=ContestTermsPresentation.Describe(root);
   Check(missing.StartsWith("КОНКУРСЫ: сохранённого сбора нет",StringComparison.Ordinal)&&missing.Contains("Сеть сейчас не включалась"),"missing view file explains without inventing data");
   var seed=Record("billion_ai_film_2027","AI Film Award 2027","manual_seed","contest_terms_found","2026-11-20","open");
   var lead=Record("lead-0123456789ab","Organizer site","aggregator_lead","partial_terms","2026-12-01","open");lead["prize"]=Money(2500.0,"EUR");lead["fee"]=Money(10.0,"USD");lead["length_minutes"]=new object[]{10,10};lead["required_tool"]=null;
   lead["lead"]=new Dictionary<string,object>{{"aggregator","agg"},{"listed_deadline","2026-11-20"},{"listed_prize",Money(5000.0,"USD")},{"listed_text","Organizer site"}};
   var closed=Record("old_contest","Closed Festival","manual_seed","contest_terms_found","2026-10-01","closed");
   var down=Record("waiff_cannes_2027","WAIFF Cannes 2027","manual_seed","source_unavailable",null,"unknown");down["error"]="HTTPError: HTTP Error 403: Forbidden";down["facts"]=new object[0];down["prize"]=null;down["fee"]=null;down["length_minutes"]=null;down["required_tool"]=null;down["unproven"]=new object[0];
   var listing=new Dictionary<string,object>{{"title","SYNTHETIC listing"},{"source_url","https://agg.example/"},{"classification","listing_read"},{"role","secondary_lead_list"},{"leads",new object[]{
    new Dictionary<string,object>{{"url","https://organizer.example/lead-0123456789ab"},{"text","Organizer site"},{"status","checked_on_organizer_page"},{"listed_deadline","2026-11-20"}},
    new Dictionary<string,object>{{"url","https://organizer.example/billion_ai_film_2027"},{"text","AI Film Award 2027"},{"status","already_seeded"},{"listed_deadline","2026-11-20"}},
    new Dictionary<string,object>{{"url","https://four.example/"},{"text","Four Festival"},{"status","not_checked_this_run_lead_limit"},{"listed_deadline",null}},
    new Dictionary<string,object>{{"url","https://three.example/"},{"text","Three Festival"},{"status","not_checked_this_run_lead_limit_listed_date_passed"},{"listed_deadline","2026-10-01"}}}}};
   var payload=new Dictionary<string,object>{{"schema","contest-terms-v2"},{"collected_at","2026-11-01T00:00:00+00:00"},{"today","2026-11-01"},{"records",new object[]{seed,lead,closed,down}},
    {"compatible",new object[]{new Dictionary<string,object>{{"contests",new object[]{"billion_ai_film_2027","lead-0123456789ab"}},{"shared_length_minutes",new object[]{5,7}},{"required_tool","Seedance"},{"check_exclusivity_terms_of",new object[]{"billion_ai_film_2027"}}}}},
    {"listings",new Dictionary<string,object>{{"agg",listing}}},{"lead_limit_per_run",8},{"source_requests",8},{"model_requests",0}};
   string text=Write(root,payload);string rendered=ContestTermsPresentation.Describe(root);
   Check(rendered.StartsWith("КОНКУРСЫ: условия, процитированные со страниц организаторов",StringComparison.Ordinal),"heading");
   Check(rendered.Contains("вне общего рейтинга")&&rendered.Contains("не оценка и не кандидат")&&rendered.Contains("Участие, допуск, судейство и выплата не подтверждены"),"boundaries stated");
   Check(rendered.Contains("запросов к страницам: 8 | запросов к модели: 0 | лидов за проход не больше: 8"),"run counters");
   Check(rendered.Contains("Открытых по заявленному сроку: 2 | закрытых: 1 | срок не найден: 0 | источник недоступен: 1"),"status counts");
   Check(rendered.Contains("1. AI Film Award 2027 - SYNTHETIC Organizer [billion_ai_film_2027]")&&rendered.Contains("Откуда: ручной поиск ассистента (assistant manual web search 2026-10-31), не автономная находка RevEng"),"seed origin is manual search, not RevEng discovery");
   Check(rendered.Contains("Заявленный срок: 2026-11-20 - открыт (дата со страницы, не дата проверки; отсчёт по дню сбора 2026-11-01)"),"declared deadline with its meaning");
   Check(rendered.Contains("Приз: 1 000 000 USD - как написано на странице, не проверено"),"prize grouped, invariant, unverified");
   Check(rendered.Contains("Взнос: бесплатно - как написано на странице"),"zero fee shown as stated");
   Check(rendered.Contains("Длительность: 5-7 мин | обязательный инструмент: Seedance"),"length and tool");
   Check(rendered.Contains("K1 [deadline]: Submissions close on 20 November 2026")&&rendered.Contains("K2 [prize]: prize of US$1,000,000"),"quotes shown verbatim");
   Check(rendered.Contains("На странице не найдено: eligibility, format"),"unproven kinds listed");
   Check(rendered.Contains("личность страницы: объявленный canonical совпадает | SHA256 ответа: "+new string('a',64)),"identity and response hash");
   Check(rendered.Contains("2. Organizer site - SYNTHETIC Organizer [lead-0123456789ab]")&&rendered.Contains("Откуда: лид из вторичного списка (lead from https://agg.example/ (secondary list)); в списке: срок 2026-11-20, приз 5 000 USD - подсказка списка, не условие"),"lead origin keeps listing hints apart from terms");
   Check(rendered.Contains("Приз: 2 500 EUR - как написано на странице, не проверено")&&rendered.Contains("Взнос: 10 USD - как написано на странице")&&rendered.Contains("Длительность: 10 мин | обязательный инструмент: не найден"),"lead terms come from the organizer page");
   Check(rendered.Contains("Статус: часть условий найдена; остальное на странице не найдено"),"partial classification");
   Check(rendered.Contains("3. Closed Festival")&&rendered.Contains("Заявленный срок: 2026-10-01 - закрыт"),"closed deadline");
   Check(rendered.Contains("4. WAIFF Cannes 2027")&&rendered.Contains("Статус: источник недоступен: HTTPError: HTTP Error 403: Forbidden")&&rendered.Contains("Недоступность источника не означает, что конкурса нет."),"unavailable source stays a non-conclusion");
   int unavailable=rendered.IndexOf("4. WAIFF Cannes 2027",StringComparison.Ordinal);int afterUnavailable=rendered.IndexOf("ОДНА РАБОТА",StringComparison.Ordinal);
   Check(unavailable>0&&afterUnavailable>unavailable&&!rendered.Substring(unavailable,afterUnavailable-unavailable).Contains("Приз:"),"no prize line is invented for an unavailable source");
   Check(rendered.Contains("billion_ai_film_2027 + lead-0123456789ab: общая длительность 5-7 мин | инструмент: Seedance | проверить эксклюзивность: billion_ai_film_2027"),"one work many contests pair with its warning");
   Check(rendered.Contains("SYNTHETIC listing | https://agg.example/ | прочитан")&&rendered.Contains("Ссылок на организаторов: 4 | проверено на страницах организаторов: 1 | уже среди ручных семян: 1 | не проверено в этот проход: 2"),"listing counters");
   Check(rendered.Contains("не проверен: Four Festival | https://four.example/")&&rendered.Contains("не проверен (дата в списке прошла): Three Festival | https://three.example/ | в списке: 2026-10-01"),"unchecked leads listed with their listing date");
   Check(!rendered.Contains("не проверен: Organizer site")&&!rendered.Contains("не проверен: AI Film Award 2027"),"checked and seeded leads are not listed as unchecked");
   Check(rendered.Contains("Отправка работы, оплата взноса, регистрация и публикация этим экраном не выполняются и не разрешаются."),"no action authorized");
   Check(!rendered.Contains("рекоменд")&&!rendered.Contains("победител")&&!rendered.Contains("балл"),"no recommendation, winner or score vocabulary");
   Check(Json.Serialize(payload)==text,"payload object unchanged by rendering");
   string swiped=ContestTermsPresentation.Render(payload,new Dictionary<string,string>{{"rv_c_billion_ai_film_2027","like"},{"rv_c_old_contest","nope"}});
   Check(swiped.Contains("[billion_ai_film_2027]\r\nВаше решение с телефона: копать")&&swiped.Contains("Ваше решение с телефона: убрано")&&!rendered.Contains("Ваше решение с телефона"),"phone decisions shown next to their contest only");
   seed["rules_pages"]=new object[]{new Dictionary<string,object>{{"url","https://organizer.example/rules"},{"classification","partial_terms"},{"facts",new object[]{new Dictionary<string,object>{{"id","K1"},{"kind","eligibility"},{"quote","Open to filmmakers worldwide"}}}}},new Dictionary<string,object>{{"url","https://organizer.example/faq"},{"classification","not_checked_this_run_budget"},{"facts",new object[0]}}};
   seed["filled_from"]=new Dictionary<string,object>{{"length_minutes","https://organizer.example/rules"}};
   string deep=ContestTermsPresentation.Render(payload,null);
   Check(deep.Contains("ПРАВИЛА, дочитаны по вашему «копать»:")&&deep.Contains("K1 [eligibility]: Open to filmmakers worldwide")&&deep.Contains("faq - не прочитано: лимит запросов прохода")&&deep.Contains("Поле length_minutes взято со страницы правил: https://organizer.example/rules"),"rules pages and filled fields shown");
   Check(ContestTermsPresentation.CardId("lead-0123456789ab")=="rv_c_lead-0123456789ab"&&ContestTermsPresentation.CardId("a b/c")=="rv_c_a_b_c","card ids match phone_cards.py");
   Write(root,payload,"contest-terms-view-v1",new string('0',64));string refused=ContestTermsPresentation.Describe(root);
   Check(refused.StartsWith("КОНКУРСЫ: сохранённый сбор не прочитан: Contest view payload hash mismatch",StringComparison.Ordinal)&&!refused.Contains("AI Film Award")&&refused.Contains("старые данные не подменяются"),"hash mismatch shows refusal only");
   Write(root,payload,"contest-terms-view-v0");refused=ContestTermsPresentation.Describe(root);
   Check(refused.Contains("Unknown contest view schema: contest-terms-view-v0")&&!refused.Contains("AI Film Award"),"unknown wrapper schema refused");
   var other=new Dictionary<string,object>(payload);other["schema"]="contest-terms-v1";Write(root,other);refused=ContestTermsPresentation.Describe(root);
   Check(refused.Contains("Unknown contest payload schema: contest-terms-v1")&&!refused.Contains("AI Film Award"),"unknown payload schema refused");
   File.WriteAllText(Path.Combine(root,ContestTermsPresentation.FileName),"{not json",new UTF8Encoding(false));refused=ContestTermsPresentation.Describe(root);
   Check(refused.StartsWith("КОНКУРСЫ: сохранённый сбор не прочитан: ",StringComparison.Ordinal),"invalid JSON refused");
   var empty=new Dictionary<string,object>{{"schema","contest-terms-v2"},{"collected_at","2026-11-01T00:00:00+00:00"},{"today","2026-11-01"},{"records",new object[0]},{"compatible",new object[0]},{"listings",new Dictionary<string,object>()},{"lead_limit_per_run",8},{"source_requests",0},{"model_requests",0}};
   Write(root,empty);string none=ContestTermsPresentation.Describe(root);
   Check(none.Contains("Открытых по заявленному сроку: 0")&&none.Contains("пар с общей длительностью среди открытых конкурсов нет")&&none.Contains("вторичные списки в этом сборе не читались"),"empty collection renders without errors");
   var previous=System.Threading.Thread.CurrentThread.CurrentCulture;try{System.Threading.Thread.CurrentThread.CurrentCulture=new System.Globalization.CultureInfo("ru-RU");Check(ContestTermsPresentation.Money(Money(1234.5,"USD"))=="1 234.5 USD","locale does not change number meaning");}finally{System.Threading.Thread.CurrentThread.CurrentCulture=previous;}
   Check(ContestTermsPresentation.Money(Money(Double.NaN,"USD"))=="вне диапазона USD"&&ContestTermsPresentation.Money(null)=="","non-finite amount withheld, missing offer empty");
  }finally{try{Directory.Delete(root,true);}catch{}}
  Console.WriteLine("PASS "+checks+" native contest view assertions; synthetic only; no GUI/model/network");return 0;
 }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}}
}
