Option Explicit
Dim shell, fso, dir, ps, scriptPath, cmd, rc, reportPath, msg
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = dir & "\Test Image Provider.ps1"
ps = shell.ExpandEnvironmentStrings("%SystemRoot%") & "\System32\WindowsPowerShell\v1.0\powershell.exe"
If Not fso.FileExists(scriptPath) Then MsgBox "Provider doctor is missing.", 16, "Merch Forge": WScript.Quit 2
If Not fso.FileExists(ps) Then MsgBox "Windows PowerShell is unavailable.", 16, "Merch Forge": WScript.Quit 3
cmd = Chr(34) & ps & Chr(34) & " -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File " & Chr(34) & scriptPath & Chr(34)
rc = shell.Run(cmd, 0, True)
reportPath = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\MerchForge\provider-doctor.json"
If rc = 0 Then
  msg = "Provider local readiness: PASS" & vbCrLf & vbCrLf & "No network call and no image generation were performed."
  MsgBox msg, 64, "Merch Forge - Provider"
Else
  msg = "Provider local readiness: NEEDS ATTENTION" & vbCrLf & vbCrLf & "No network call and no image generation were performed." & vbCrLf & vbCrLf & "Report:" & vbCrLf & reportPath
  MsgBox msg, 48, "Merch Forge - Provider"
End If
WScript.Quit rc
