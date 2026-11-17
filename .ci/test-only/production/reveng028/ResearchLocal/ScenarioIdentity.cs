using System;using System.Linq;using System.Reflection;
public static class ScenarioIdentity {
 static string Text(object row,string field){if(row==null)return null;var f=row.GetType().GetField(field,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance);return f==null?null:Convert.ToString(f.GetValue(row));}
 public static object Resolve(object[] rows,object tag,string name,string model,string status){
  var exact=rows.Where(row=>Object.ReferenceEquals(tag,row)).ToArray();
  if(tag!=null&&exact.Length==1)return exact[0];
  if(tag!=null&&exact.Length>1)return null;
  var matches=rows.Where(row=>Text(row,"Name")==name&&Text(row,"Model")==model&&Text(row,"Status")==status).ToArray();
  return matches.Length==1?matches[0]:null;
 }
 public static int Position(object[] rows,object tag,string name,string model,string status){var found=Resolve(rows,tag,name,model,status);return found==null?Int32.MaxValue:Array.FindIndex(rows,row=>Object.ReferenceEquals(row,found));}
}
