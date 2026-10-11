Option Explicit
Dim shell,fso,root
Set shell=CreateObject("WScript.Shell")
Set fso=CreateObject("Scripting.FileSystemObject")
root="D:\Archivist\AutoEditOutput"
If Not fso.FolderExists(root) Then fso.CreateFolder(root)
shell.Run "explorer.exe """ & root & """",1,False
