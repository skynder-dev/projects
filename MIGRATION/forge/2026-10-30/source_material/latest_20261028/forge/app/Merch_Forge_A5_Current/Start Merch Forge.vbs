Option Explicit

Dim fso, shell, dir, localAppData, logDir, launchLog, readyFile, exitFile
Dim cmdPath, psPath, cmdExe, launchCommand, startTick, timeoutMs, exitCode, msg, sessionId

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

dir = fso.GetParentFolderName(WScript.ScriptFullName)
cmdPath = dir & "\MerchForgeLauncher.cmd"
psPath = dir & "\MerchForgeWorkbench.ps1"
cmdExe = ResolveNativeSystemExe("cmd.exe")

If Len(cmdExe) = 0 Then
    MsgBox "Merch Forge cannot start because the trusted Windows command host is unavailable.", 16, "Merch Forge - Missing Windows Host"
    WScript.Quit 12
End If

If Not fso.FileExists(cmdPath) Then
    MsgBox "Merch Forge cannot start because MerchForgeLauncher.cmd is missing." & vbCrLf & _
           "Re-extract the complete package and try again.", 16, "Merch Forge - Missing File"
    WScript.Quit 10
End If
If Not fso.FileExists(psPath) Then
    MsgBox "Merch Forge cannot start because MerchForgeWorkbench.ps1 is missing." & vbCrLf & _
           "Re-extract the complete package and try again.", 16, "Merch Forge - Missing File"
    WScript.Quit 11
End If

localAppData = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
logDir = localAppData & "\MerchForge\logs"
If Not fso.FolderExists(localAppData & "\MerchForge") Then fso.CreateFolder(localAppData & "\MerchForge")
If Not fso.FolderExists(logDir) Then fso.CreateFolder(logDir)

Randomize
sessionId = CStr(Year(Now)) & Right("0" & CStr(Month(Now)), 2) & Right("0" & CStr(Day(Now)), 2) & "-" & _
            Right("0" & CStr(Hour(Now)), 2) & Right("0" & CStr(Minute(Now)), 2) & Right("0" & CStr(Second(Now)), 2) & "-" & _
            Right("000000" & CStr(Int(Rnd * 1000000)), 6)

launchLog = logDir & "\MerchForge-launch-" & sessionId & ".log"
readyFile = logDir & "\MerchForge-ready-" & sessionId & ".flag"
exitFile = logDir & "\MerchForge-exit-" & sessionId & ".txt"

On Error Resume Next
If fso.FileExists(launchLog) Then fso.DeleteFile launchLog, True
If fso.FileExists(readyFile) Then fso.DeleteFile readyFile, True
If fso.FileExists(exitFile) Then fso.DeleteFile exitFile, True
On Error GoTo 0

shell.Environment("PROCESS")("MERCH_FORGE_LAUNCH_LOG") = launchLog
shell.Environment("PROCESS")("MERCH_FORGE_READY_FILE") = readyFile
shell.Environment("PROCESS")("MERCH_FORGE_EXIT_FILE") = exitFile
shell.Environment("PROCESS")("MERCH_FORGE_LAUNCH_ID") = sessionId

launchCommand = Chr(34) & cmdExe & Chr(34) & " /d /c " & Chr(34) & Chr(34) & cmdPath & Chr(34) & Chr(34)
shell.Run launchCommand, 0, False
startTick = Timer
timeoutMs = 180000

Do
    If fso.FileExists(readyFile) Then Exit Do

    If fso.FileExists(exitFile) Then
        exitCode = ReadExitCode(exitFile)
        msg = "Merch Forge did not open." & vbCrLf & vbCrLf & _
              "Exit code: " & CStr(exitCode) & vbCrLf & _
              ReadLogTail(launchLog) & vbCrLf & vbCrLf & _
              "Diagnostic log:" & vbCrLf & launchLog
        MsgBox msg, 16, "Merch Forge - Startup Error"
        WScript.Quit 1
    End If

    WScript.Sleep 250
    If ElapsedMs(startTick) > timeoutMs Then
        msg = "Merch Forge did not become ready within 3 minutes." & vbCrLf & vbCrLf & _
              ReadLogTail(launchLog) & vbCrLf & vbCrLf & _
              "Diagnostic log:" & vbCrLf & launchLog
        MsgBox msg, 16, "Merch Forge - Startup Timeout"
        WScript.Quit 2
    End If
Loop

Do
    If fso.FileExists(exitFile) Then
        exitCode = ReadExitCode(exitFile)
        If exitCode <> 0 Then
            msg = "Merch Forge closed because of an error." & vbCrLf & vbCrLf & _
                  "Exit code: " & CStr(exitCode) & vbCrLf & _
                  ReadLogTail(launchLog) & vbCrLf & vbCrLf & _
                  "Diagnostic log:" & vbCrLf & launchLog
            MsgBox msg, 16, "Merch Forge - Error"
        End If
        WScript.Quit exitCode
    End If
    WScript.Sleep 500
Loop


Function ResolveNativeSystemExe(relativePath)
    Dim root, p
    root = shell.ExpandEnvironmentStrings("%SystemRoot%")
    p = root & "\Sysnative\" & relativePath
    If fso.FileExists(p) Then ResolveNativeSystemExe = p: Exit Function
    p = root & "\System32\" & relativePath
    If fso.FileExists(p) Then ResolveNativeSystemExe = p: Exit Function
    ResolveNativeSystemExe = ""
End Function

Function ReadExitCode(path)
    On Error Resume Next
    Dim ts, s
    Set ts = fso.OpenTextFile(path, 1, False)
    s = Trim(ts.ReadAll)
    ts.Close
    If Err.Number <> 0 Or Not IsNumeric(s) Then
        Err.Clear
        ReadExitCode = 999
    Else
        ReadExitCode = CInt(s)
    End If
    On Error GoTo 0
End Function

Function ReadLogTail(path)
    On Error Resume Next
    Dim ts, s, maxChars
    maxChars = 10000
    If Not fso.FileExists(path) Then
        ReadLogTail = "No diagnostic output was captured."
        Exit Function
    End If
    Set ts = fso.OpenTextFile(path, 1, False)
    s = ts.ReadAll
    ts.Close
    If Len(s) > maxChars Then s = Right(s, maxChars)
    If Len(Trim(s)) = 0 Then s = "No diagnostic output was captured."
    ReadLogTail = s
    On Error GoTo 0
End Function

Function ElapsedMs(startSeconds)
    Dim nowSeconds, delta
    nowSeconds = Timer
    delta = nowSeconds - startSeconds
    If delta < 0 Then delta = delta + 86400
    ElapsedMs = delta * 1000
End Function
