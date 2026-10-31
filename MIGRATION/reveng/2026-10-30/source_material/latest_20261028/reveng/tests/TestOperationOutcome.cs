// Actual in-process caller formatting/receipt/cleanup methods, not Forms/Process.
using System;
using System.IO;
public static class TestOperationOutcome {
 static int checks;
 static void Check(bool value,string name){checks++;if(!value)throw new Exception("FAIL "+name);}
 static void Reject(Action action,string name){try{action();}catch(Exception){checks++;return;}throw new Exception("FAIL expected rejected receipt "+name);}
 public static int Main(){string folder=Path.Combine(Path.GetTempPath(),"reveng-outcome-"+Guid.NewGuid().ToString("N"));try{
  var invalid=new InvalidDataException("SYNTHETIC invalid receipt");
  string target=Path.Combine(folder,"exact-export.zip");
  string message=LocalResearchController.DescribeExportFailure(invalid,true,target);
  Check(message.Contains("не подтверждён")&&!message.Contains("Экспорт не выполнен")&&message.Contains(target),"completed export bad receipt unknown and target preserved");
  Check(LocalResearchController.WithExportDisplayWarning("SYNTHETIC confirmed export "+target,"SYNTHETIC UI failure").StartsWith("SYNTHETIC confirmed export "+target),"validated export survives later display failure");
  Check(LocalResearchController.DescribeExportFailure(invalid,false,null).StartsWith("Экспорт не выполнен"),"export pre-start refusal stays refusal");
  Check(SourceLedgerComparison.DescribeOperationFailure(invalid,true,"Response was NOT imported: ").Contains("не подтверждён"),"completed import invalid receipt unknown");
  Check(SourceLedgerComparison.DescribeOperationFailure(invalid,false,"Response was NOT imported: ").StartsWith("Response was NOT imported"),"import pre-start refusal stays refusal");
  string build=SourceLedgerComparison.DescribeOperationFailure(invalid,true,"Источник/реестр не загружен: ",". Данные не переписаны");
  Check(!build.Contains("Данные не переписаны")&&build.Contains("Данные могли сохраниться"),"completed build parse failure does not deny persisted catalog");
  Check(SourceLedgerComparison.DescribeOperationFailure(invalid,false,"Источник/реестр не загружен: ",". Данные не переписаны").Contains("Данные не переписаны"),"read-only/pre-start wording preserved");
  string saved=SourceLedgerComparison.DescribeQuoteSaveResult("{\"status\":\"SAVED_EXACT_QUOTATION_ONLY\",\"automatic_admission\":false}");
  Check(saved.Contains("цитата сохранена"),"actual valid quotation receipt");
  Reject(()=>SourceLedgerComparison.DescribeQuoteSaveResult("{\"status\":\"OTHER\",\"automatic_admission\":false}"),"unknown quotation receipt");
  Reject(()=>SourceLedgerComparison.DescribeQuoteSaveResult("{\"status\":\"SAVED_EXACT_QUOTATION_ONLY\",\"automatic_admission\":true}"),"unsafe quotation receipt");
  string warning=SourceLedgerComparison.WithRefreshWarning(saved,"SYNTHETIC view failure");
  Check(warning.StartsWith(saved)&&warning.Contains("SYNTHETIC view failure")&&!warning.Contains("Цитата не сохранена"),"known saved quote survives refresh failure");
  bool imported;
  string rejected=SourceLedgerComparison.DescribeImportResult("{\"status\":\"REJECTED_RESPONSE_NOT_IMPORTED\",\"research_imported\":false,\"automatic_admission\":false,\"semantic_PASS\":false,\"message\":\"SYNTHETIC rejected; not imported\"}",out imported);
  warning=SourceLedgerComparison.WithRefreshWarning(rejected,"SYNTHETIC view failure");
  Check(!imported&&warning.StartsWith(rejected)&&!warning.Contains("Saved as")&&!warning.Contains("Данные могли сохраниться"),"explicit rejection survives refresh failure, never invented save");
  string importedMessage=SourceLedgerComparison.DescribeImportResult("{\"status\":\"SAVED_UNVERIFIED_PROPOSAL_ONLY\",\"automatic_admission\":false,\"semantic_PASS\":false}",out imported);
  Check(imported&&SourceLedgerComparison.WithRefreshWarning(importedMessage,"SYNTHETIC view failure").StartsWith(importedMessage),"saved unverified proposal survives refresh failure");
  Reject(()=>{bool unused;SourceLedgerComparison.DescribeImportResult("{\"status\":\"OTHER\"}",out unused);},"unknown import receipt");
  string review=EvidenceComparison.DescribeReviewResult("{\"status\":\"SAVED_DECLARATION_ONLY\",\"semantic_PASS\":false,\"execution_authorized\":false}");
  Check(EvidenceComparison.WithReviewRefreshWarning(review,"SYNTHETIC comparison failure").StartsWith(review),"saved declaration survives comparison refresh failure");
  Reject(()=>EvidenceComparison.DescribeReviewResult("{\"status\":\"SAVED_DECLARATION_ONLY\",\"semantic_PASS\":true,\"execution_authorized\":false}"),"unsafe declaration receipt");
  Check(EvidenceComparison.DescribeReviewFailure(invalid,true).Contains("не подтверждён")&&!EvidenceComparison.DescribeReviewFailure(invalid,true).Contains("Ревью не записано"),"completed review invalid receipt unknown");
  Check(EvidenceComparison.DescribeReviewFailure(invalid,false).StartsWith("Ревью не записано"),"review pre-start refusal stays refusal");
  Directory.CreateDirectory(folder);string proposal=Path.Combine(folder,"exact-proposal.json");File.WriteAllText(proposal,"SYNTHETIC owned staging only");string before=File.ReadAllText(proposal);int deletes=0;
  string cleanup=SourceLedgerComparison.CleanupProposal(proposal,true,p=>{deletes++;File.Delete(p);});
  Check(deletes==0&&File.ReadAllText(proposal)==before&&cleanup.Contains(proposal),"uncertain outcome retains exact staging without delete attempt");
  cleanup=SourceLedgerComparison.CleanupProposal(proposal,false,p=>{deletes++;throw new UnauthorizedAccessException("SYNTHETIC denied cleanup");});
  Check(deletes==1&&File.ReadAllText(proposal)==before&&cleanup.Contains(proposal),"cleanup denial is warning with preserved staging, no retry");
  Check((saved+"\n"+cleanup).StartsWith(saved)&&!(saved+cleanup).Contains("Цитата не сохранена"),"cleanup warning does not erase confirmed save");
  cleanup=SourceLedgerComparison.CleanupProposal(proposal,false,p=>{throw new IOException("SYNTHETIC cleanup IO failure");});
  Check(cleanup.Contains(proposal)&&File.Exists(proposal),"IO cleanup exception contained, never reaches SaveSelected");
  Check(SourceLedgerComparison.CleanupProposal(proposal,false,File.Delete)==null&&!File.Exists(proposal),"ordinary successful staging cleanup unchanged");
  Console.WriteLine("PASS "+checks+" in-process operation-outcome assertions; Forms/Process/persistence commits NOT_TESTED");return 0;
 }catch(Exception ex){Console.Error.WriteLine(ex);return 1;}finally{if(Directory.Exists(folder))Directory.Delete(folder,true);}}
}
