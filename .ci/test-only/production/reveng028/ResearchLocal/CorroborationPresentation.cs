using System;using System.Text;using System.Collections.Generic;
// Metadata presentation only. Never authenticates people, buyers or independent demand.
public static class CorroborationPresentation {
 public static string Describe(Dictionary<string,object> value){var b=new StringBuilder();bool current=ManualHypotheses.S(value,"scope_policy")=="saved_problem_report_metadata_v2_no_independence_inference";
 b.AppendLine(current?"Сохранённые сообщения соответствующей роли (число URL, не людей и не покупателей): "+ManualHypotheses.S(value,"distinct_posts"):"Исторические счётчики без текущей перепроверки ролей (не подтверждение спроса): "+ManualHypotheses.S(value,"distinct_posts"));
 b.AppendLine("Записанных ID автора в namespace источника: "+ManualHypotheses.S(value,"public_author_ids_count")+"; это не число установленных независимых людей.");
 b.AppendLine("Независимость сообщений и людей: неизвестна. Наличие издателя источника не подтверждает покупателя; число URL/авторских ID не является рыночным спросом.");
 if(!current&&ManualHypotheses.S(value,"independence")!="")b.AppendLine("Историческая неподтверждённая метка metadata: "+ManualHypotheses.S(value,"independence"));
 foreach(var relation in ManualHypotheses.A(ManualHypotheses.V(value,"possible_shared_origins"))){var row=ManualHypotheses.D(relation);b.AppendLine("Возможное общее происхождение: "+ManualHypotheses.S(row,"from_url")+" -> "+ManualHypotheses.S(row,"referenced_report_url")+". Ссылка или цитирование не являются независимым подтверждением.");
 bool hasOrigin=false;foreach(var item in ManualHypotheses.A(ManualHypotheses.V(row,"metadata_origins"))){hasOrigin=true;var origin=ManualHypotheses.D(item);b.AppendLine("Сохранённая metadata: "+ManualHypotheses.S(origin,"metadata_field")+"["+ManualHypotheses.S(origin,"metadata_index")+"] = "+ManualHypotheses.S(origin,"saved_target_url"));b.AppendLine("E-ID записи: "+ManualHypotheses.S(origin,"evidence_id")+"; SHA256 JSON записи: "+ManualHypotheses.S(origin,"observation_json_sha256")+". Это хеш сохранённого объекта, не доказательство байтов ответа или личности автора.");}if(!hasOrigin)b.AppendLine("Происхождение link metadata в этой сохранённой метке не зафиксировано; точный snapshot неизвестен.");}
 return b.ToString();}
}
