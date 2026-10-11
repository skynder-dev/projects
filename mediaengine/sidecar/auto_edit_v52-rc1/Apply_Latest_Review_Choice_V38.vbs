Set s=CreateObject("WScript.Shell")
s.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & Replace(WScript.ScriptFullName,"Apply_Latest_Review_Choice_V38.vbs","APPLY_LATEST_REVIEW_CHOICE_V38.ps1") & """",0,False
