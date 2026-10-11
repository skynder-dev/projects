Option Explicit
Dim fso, sh, here, ps, cmd
Set fso=CreateObject("Scripting.FileSystemObject")
Set sh=CreateObject("WScript.Shell")
here=fso.GetParentFolderName(WScript.ScriptFullName)
ps=fso.BuildPath(here,"APPLY_LATEST_OVERRIDE_V37.ps1")
cmd="powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File """ & ps & """"
sh.Run cmd,0,False
