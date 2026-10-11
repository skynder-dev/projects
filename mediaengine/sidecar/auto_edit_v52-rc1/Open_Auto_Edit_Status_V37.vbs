Option Explicit
Dim shell,fso,here,ps,root,status,cmd
Set shell=CreateObject("WScript.Shell")
Set fso=CreateObject("Scripting.FileSystemObject")
here=fso.GetParentFolderName(WScript.ScriptFullName)
ps=fso.BuildPath(here,"SUPERVISOR_STATUS_V37.ps1")
cmd="powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & ps & """"
shell.Run cmd,0,True
root="D:\Archivist\sidecars\auto_edit\queue"
status=fso.BuildPath(root,"SUPERVISOR_STATUS.txt")
If fso.FileExists(status) Then shell.Run "notepad.exe """ & status & """",1,False
