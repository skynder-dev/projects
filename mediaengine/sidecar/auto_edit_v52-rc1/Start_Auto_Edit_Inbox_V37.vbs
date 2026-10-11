Option Explicit
Dim shell,fso,here,ps,cmd
Set shell=CreateObject("WScript.Shell")
Set fso=CreateObject("Scripting.FileSystemObject")
here=fso.GetParentFolderName(WScript.ScriptFullName)
ps=fso.BuildPath(here,"RUN_AUTO_EDIT_SUPERVISOR_V37.ps1")
cmd="powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ps & """"
shell.Run cmd,0,False
