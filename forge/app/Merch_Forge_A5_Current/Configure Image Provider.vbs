Option Explicit
Dim shell, fso, dir, ps, scriptPath, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = dir & "\Configure Image Provider.ps1"
ps = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"
If Not fso.FileExists(scriptPath) Then MsgBox "Provider configuration helper is missing.", 16, "Merch Forge": WScript.Quit 2
If Not fso.FileExists(ps) Then MsgBox "Windows PowerShell is unavailable.", 16, "Merch Forge": WScript.Quit 3
cmd = Chr(34) & ps & Chr(34) & " -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -File " & Chr(34) & scriptPath & Chr(34)
shell.Run cmd, 0, False
