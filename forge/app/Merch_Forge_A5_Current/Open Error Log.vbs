Option Explicit
Dim shell, fso, logDir, folder, file, newestPath, newestDate, prefix, notepadPath
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
logDir = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\MerchForge\logs"
prefix = "merchforge-launch-"
newestPath = ""

If fso.FolderExists(logDir) Then
  Set folder = fso.GetFolder(logDir)
  For Each file In folder.Files
    If LCase(Left(file.Name, Len(prefix))) = prefix And LCase(Right(file.Name, 4)) = ".log" Then
      If newestPath = "" Then
        newestPath = file.Path
        newestDate = file.DateLastModified
      ElseIf file.DateLastModified > newestDate Then
        newestPath = file.Path
        newestDate = file.DateLastModified
      End If
    End If
  Next
End If

If newestPath <> "" Then
  notepadPath = ResolveNativeSystemExe("notepad.exe")
  If Len(notepadPath) = 0 Then
    MsgBox "Windows Notepad is unavailable at the trusted system path." & vbCrLf & newestPath, 16, "Merch Forge"
  Else
    shell.Run Chr(34) & notepadPath & Chr(34) & " " & Chr(34) & newestPath & Chr(34), 1, False
  End If
Else
  MsgBox "No Merch Forge diagnostic log exists yet." & vbCrLf & _
         "Start Merch Forge once, then try again.", 64, "Merch Forge"
End If

Function ResolveNativeSystemExe(relativePath)
  Dim root, p
  root = shell.ExpandEnvironmentStrings("%SystemRoot%")
  p = root & "\Sysnative\" & relativePath
  If fso.FileExists(p) Then ResolveNativeSystemExe = p: Exit Function
  p = root & "\System32\" & relativePath
  If fso.FileExists(p) Then ResolveNativeSystemExe = p: Exit Function
  ResolveNativeSystemExe = ""
End Function
