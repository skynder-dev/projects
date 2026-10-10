Option Explicit
Dim shell, fso, p
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
p = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\MerchForge\owner.key"
If fso.FileExists(p) Then
  fso.DeleteFile p, True
  MsgBox "Saved Merch Forge access was removed from this Windows account.", 64, "Merch Forge"
Else
  MsgBox "No saved Merch Forge access was found on this Windows account.", 64, "Merch Forge"
End If
