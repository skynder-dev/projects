Option Explicit
Dim fso, shell, baseDir, startPath, preflightPath, wscriptExe
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
startPath = baseDir & "\Merch_Forge_A5_Current\Start Merch Forge.vbs"
preflightPath = baseDir & "\Merch_Forge_A5_Current\MerchForgePreflight.ps1"
If Not fso.FileExists(startPath) Or Not fso.FileExists(preflightPath) Then
  MsgBox "Merch Forge 073 is not fully extracted." & vbCrLf & vbCrLf & _
         "Use Extract All, then run this entrypoint from the extracted folder.", 16, "Merch Forge - Extract First"
  WScript.Quit 2
End If
wscriptExe = ResolveNativeSystemExe("wscript.exe")
If Len(wscriptExe) = 0 Then
  MsgBox "The trusted Windows Script Host is unavailable.", 16, "Merch Forge - Missing Windows Host"
  WScript.Quit 44
End If
shell.Run Chr(34) & wscriptExe & Chr(34) & " " & Chr(34) & startPath & Chr(34), 1, False
Function ResolveNativeSystemExe(relativePath)
  Dim root, p
  root = shell.ExpandEnvironmentStrings("%SystemRoot%")
  p = root & "\Sysnative\" & relativePath
  If fso.FileExists(p) Then ResolveNativeSystemExe = p: Exit Function
  p = root & "\System32\" & relativePath
  If fso.FileExists(p) Then ResolveNativeSystemExe = p: Exit Function
  ResolveNativeSystemExe = ""
End Function
