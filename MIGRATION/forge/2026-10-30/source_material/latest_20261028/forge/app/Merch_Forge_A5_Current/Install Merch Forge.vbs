Option Explicit

Dim fso, shell, sourceDir, localAppData, installRoot, appDir, stageDir, backupDir, nextBackupDir, lockDir, previousAuthorityPath
Dim desktopPath, shortcutPath, sc, target, rc, msg
Dim sourceGeneration, lockedCurrentGeneration, currentGenerationBeforeSwap, lockedCurrentIdentity, currentIdentityBeforeSwap
Dim lockOwned
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
lockOwned = False

sourceDir = fso.GetParentFolderName(WScript.ScriptFullName)
localAppData = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
installRoot = localAppData & "\Programs\MerchForge"
appDir = installRoot & "\app"
stageDir = installRoot & "\app.new"
backupDir = installRoot & "\app.previous"
nextBackupDir = installRoot & "\app.previous.next"
lockDir = installRoot & "\install.lock"
previousAuthorityPath = installRoot & "\app.previous.authority.txt"

If Not fso.FileExists(sourceDir & "\integrity.json") Or Not fso.FileExists(sourceDir & "\candidate_manifest.json") Or Not fso.FileExists(sourceDir & "\MerchForgeLauncher.cmd") Or Not fso.FileExists(sourceDir & "\MerchForgeWorkbench.ps1") Or Not fso.FileExists(sourceDir & "\MerchForgePreflight.ps1") Then
    MsgBox "Merch Forge is not fully extracted." & vbCrLf & vbCrLf & _
           "Do not run Install Merch Forge.vbs from inside the ZIP." & vbCrLf & _
           "Right-click the ZIP, choose Extract All, then run this installer from the extracted Merch_Forge_A5_Current folder." & vbCrLf & vbCrLf & _
           "Current folder:" & vbCrLf & sourceDir, 48, "Merch Forge - Extract First"
    WScript.Quit 18
End If

rc = VerifyPackage(sourceDir)
If rc <> 0 Then
    MsgBox "This Merch Forge package did not pass its startup preflight." & vbCrLf & vbCrLf & _
           "Preflight code: " & CStr(rc) & vbCrLf & _
           IntegrityMeaning(rc) & vbCrLf & vbCrLf & _
           "Folder checked:" & vbCrLf & sourceDir & vbCrLf & vbCrLf & _
           "Installation was stopped. If this folder was reused from an older build, extract the ZIP again into a new empty folder.", 16, "Merch Forge - Install"
    WScript.Quit rc
End If


sourceGeneration = ReadInstallerGeneration(sourceDir)
If Not IsValidGeneration(sourceGeneration) Then
    MsgBox "This Merch Forge package does not contain a valid guarded installer generation." & vbCrLf & vbCrLf & _
           "Installation was stopped before the current installation was changed.", 16, "Merch Forge - Install"
    WScript.Quit 21
End If

If LCase(fso.GetAbsolutePathName(sourceDir)) <> LCase(fso.GetAbsolutePathName(appDir)) Then
    EnsureFolder fso.GetParentFolderName(installRoot)
    EnsureFolder installRoot

    rc = AcquireInstallLock(sourceGeneration)
    If rc <> 0 Then
        MsgBox "Another Merch Forge install/update transaction is active or an earlier transaction left a lock." & vbCrLf & vbCrLf & _
               "For safety, this installer will not delete or bypass the lock automatically." & vbCrLf & _
               "Current installation was not changed." & vbCrLf & vbCrLf & _
               "Lock folder:" & vbCrLf & lockDir, 16, "Merch Forge - Safe Update Stop"
        WScript.Quit 23
    End If

    lockedCurrentIdentity = ReadInstallIdentity(appDir)
    lockedCurrentGeneration = ReadInstallerGeneration(appDir)
    rc = CheckDowngrade(sourceGeneration, lockedCurrentGeneration)
    If rc <> 0 Then
        ReleaseInstallLock
        MsgBox "This package is older than the currently installed guarded Merch Forge generation." & vbCrLf & vbCrLf & _
               "Downgrade was blocked before the current installation was changed." & vbCrLf & _
               "Source generation: " & sourceGeneration & vbCrLf & _
               "Installed generation: " & lockedCurrentGeneration, 16, "Merch Forge - Downgrade Blocked"
        WScript.Quit 22
    End If

    rc = PreparePreviousAuthority()
    If rc <> 0 Then
        ReleaseInstallLock
        MsgBox "A Merch Forge recovery/authority state already exists and cannot be proven safe for automatic replacement." & vbCrLf & vbCrLf & _
               "For safety, this update stopped without changing the current installation." & vbCrLf & _
               "Recovery folder:" & vbCrLf & backupDir & vbCrLf & _
               "Authority marker:" & vbCrLf & previousAuthorityPath, 16, "Merch Forge - Safe Update Stop"
        WScript.Quit rc
    End If

    If fso.FolderExists(nextBackupDir) Then
        ReleaseInstallLock
        MsgBox "An unfinished Merch Forge transaction backup still exists." & vbCrLf & vbCrLf & _
               "It will not be deleted automatically." & vbCrLf & _
               "Current installation was not changed." & vbCrLf & vbCrLf & _
               "Transaction backup:" & vbCrLf & nextBackupDir, 16, "Merch Forge - Safe Update Stop"
        WScript.Quit 24
    End If

    On Error Resume Next
    If fso.FolderExists(stageDir) Then fso.DeleteFolder stageDir, True
    On Error GoTo 0

    On Error Resume Next
    Err.Clear
    fso.CreateFolder stageDir
    If Err.Number <> 0 Then
        Dim stageErrNumber, stageErrDescription
        stageErrNumber = Err.Number
        stageErrDescription = Err.Description
        Err.Clear
        On Error GoTo 0
        FailInstallDetailed "Could not create the installation staging folder.", 11, stageErrNumber, stageErrDescription, stageDir
    End If
    On Error GoTo 0

    CopySourceContents sourceDir, stageDir

    rc = VerifyPackage(stageDir)
    If rc <> 0 Then
        DeleteOwnedStage
        ReleaseInstallLock
        MsgBox "The copied application did not pass its startup preflight." & vbCrLf & _
               "Preflight code: " & CStr(rc) & vbCrLf & IntegrityMeaning(rc) & vbCrLf & vbCrLf & _
               "Your current installation was not changed.", 16, "Merch Forge - Install"
        WScript.Quit 13
    End If


    currentIdentityBeforeSwap = ReadInstallIdentity(appDir)
    currentGenerationBeforeSwap = ReadInstallerGeneration(appDir)
    If currentIdentityBeforeSwap <> lockedCurrentIdentity Then
        DeleteOwnedStage
        ReleaseInstallLock
        MsgBox "The installed Merch Forge authority changed while this update was preparing." & vbCrLf & vbCrLf & _
               "This transaction was stopped instead of overwriting a newer or different installation.", 16, "Merch Forge - Stale Update Blocked"
        WScript.Quit 25
    End If
    rc = CheckDowngrade(sourceGeneration, currentGenerationBeforeSwap)
    If rc <> 0 Then
        DeleteOwnedStage
        ReleaseInstallLock
        MsgBox "The installed Merch Forge generation advanced while this update was preparing." & vbCrLf & vbCrLf & _
               "The stale package was blocked before the current installation was changed.", 16, "Merch Forge - Stale Update Blocked"
        WScript.Quit 22
    End If

    On Error Resume Next
    Err.Clear
    If fso.FolderExists(appDir) Then fso.MoveFolder appDir, nextBackupDir
    If Err.Number <> 0 Then
        Dim moveOldErr
        moveOldErr = Err.Description
        Err.Clear
        On Error GoTo 0
        DeleteOwnedStage
        ReleaseInstallLock
        MsgBox "Could not prepare the existing installation for update." & vbCrLf & vbCrLf & _
               moveOldErr & vbCrLf & vbCrLf & _
               "The current installation was not replaced.", 16, "Merch Forge - Safe Update Stop"
        WScript.Quit 14
    End If
    Err.Clear
    fso.MoveFolder stageDir, appDir
    If Err.Number <> 0 Then
        Dim activateErr
        activateErr = Err.Description
        Err.Clear
        If fso.FolderExists(nextBackupDir) And Not fso.FolderExists(appDir) Then fso.MoveFolder nextBackupDir, appDir
        On Error GoTo 0
        ReleaseInstallLock
        MsgBox "Could not activate the new Merch Forge installation." & vbCrLf & vbCrLf & _
               activateErr & vbCrLf & vbCrLf & _
               "The previous installation was restored when possible.", 16, "Merch Forge - Safe Update Rollback"
        WScript.Quit 15
    End If
    On Error GoTo 0

    rc = VerifyPackage(appDir)
    If rc <> 0 Then
        RollbackActivatedApp
        MsgBox "The installed application did not pass its startup preflight." & vbCrLf & _
               "Preflight code: " & CStr(rc) & vbCrLf & IntegrityMeaning(rc) & vbCrLf & vbCrLf & _
               "The previous installation was restored when possible.", 16, "Merch Forge - Install"
        WScript.Quit 16
    End If


    rc = FinalizePreviousGood(currentGenerationBeforeSwap)
    If rc <> 0 Then
        ReleaseInstallLock
        MsgBox "The new Merch Forge installation passed validation, but recovery authority could not be finalized safely." & vbCrLf & vbCrLf & _
               "No recovery folder was silently discarded. A later installer will stop until this state is reconciled.", 16, "Merch Forge - Recovery Attention"
        WScript.Quit rc
    End If

    ReleaseInstallLock
End If

If Not fso.FileExists(appDir & "\Start Merch Forge.vbs") Then
    MsgBox "Merch Forge is installed, but its start helper is missing. Run the installer again from a trusted package.", 16, "Merch Forge - Install"
    WScript.Quit 17
End If

desktopPath = shell.SpecialFolders("Desktop")
shortcutPath = desktopPath & "\Merch Forge.lnk"
target = ResolveNativeSystemExe("wscript.exe")
If Len(target) = 0 Then
    MsgBox "The trusted Windows Script Host is unavailable. Installation was stopped before creating the desktop shortcut.", 16, "Merch Forge - Install"
    WScript.Quit 20
End If
Set sc = shell.CreateShortcut(shortcutPath)
sc.TargetPath = target
sc.Arguments = Chr(34) & appDir & "\Start Merch Forge.vbs" & Chr(34)
sc.WorkingDirectory = appDir
sc.Description = "Merch Forge Workbench"
sc.IconLocation = shell.ExpandEnvironmentStrings("%SystemRoot%\System32\shell32.dll,167")
sc.Save

MsgBox "Merch Forge is installed for this Windows account. Use the Merch Forge desktop shortcut to open it.", 64, "Merch Forge - Install"

Function VerifyPackage(folderPath)
    Dim launcher, cmdExe, cmd
    launcher = folderPath & "\MerchForgeLauncher.cmd"
    If Not fso.FileExists(launcher) Then
        VerifyPackage = 85
        Exit Function
    End If
    cmdExe = ResolveNativeSystemExe("cmd.exe")
    If Len(cmdExe) = 0 Then
        VerifyPackage = 89
        Exit Function
    End If
    cmd = Chr(34) & cmdExe & Chr(34) & " /d /c " & Chr(34) & Chr(34) & launcher & Chr(34) & " --verify-only" & Chr(34)
    VerifyPackage = shell.Run(cmd, 0, True)
End Function

Function IntegrityMeaning(code)
    Select Case CInt(code)
        Case 41: IntegrityMeaning = "A PowerShell runtime file contains a parser error."
        Case 42: IntegrityMeaning = "PowerShell 7.5 or newer is required at the native Program Files PowerShell 7 location. No runtime was installed or substituted."
        Case 43: IntegrityMeaning = "MerchForgePreflight.ps1 is missing."
        Case 44: IntegrityMeaning = "The PowerShell runtime file set is incomplete."
        Case 45: IntegrityMeaning = "The Workbench XAML block is malformed or missing."
        Case 46: IntegrityMeaning = "The Workbench XAML failed native WPF loading."
        Case 50: IntegrityMeaning = "The selected runtime must be PowerShell Core 7.5 or newer with exact JSON string preservation. No legacy-host or parser fallback is permitted."
        Case 80: IntegrityMeaning = "integrity.json is missing."
        Case 81: IntegrityMeaning = "integrity.json could not be parsed."
        Case 82: IntegrityMeaning = "The integrity algorithm is not SHA-256."
        Case 83: IntegrityMeaning = "The package file list is incomplete or duplicated."
        Case 84: IntegrityMeaning = "An unsafe package path was detected."
        Case 85: IntegrityMeaning = "A required package file is missing."
        Case 86: IntegrityMeaning = "A required file has the wrong size."
        Case 87: IntegrityMeaning = "A required file has the wrong SHA-256 hash."
        Case 89: IntegrityMeaning = "The trusted Windows command host is unavailable."
        Case 90: IntegrityMeaning = "The launcher did not receive verify-only mode correctly."
        Case 99: IntegrityMeaning = "The unified startup preflight failed unexpectedly."
        Case Else: IntegrityMeaning = "The verifier returned an unexpected code."
    End Select
End Function


Function ResolveNativeSystemExe(relativePath)
    Dim root, p
    root = shell.ExpandEnvironmentStrings("%SystemRoot%")
    p = root & "\Sysnative\" & relativePath
    If fso.FileExists(p) Then ResolveNativeSystemExe = p: Exit Function
    p = root & "\System32\" & relativePath
    If fso.FileExists(p) Then ResolveNativeSystemExe = p: Exit Function
    ResolveNativeSystemExe = ""
End Function


Function ReadManifestString(folderPath, fieldName)
    Dim manifestPath, ts, text, re, matches
    ReadManifestString = ""
    manifestPath = folderPath & "\candidate_manifest.json"
    If Not fso.FileExists(manifestPath) Then Exit Function
    On Error Resume Next
    Set ts = fso.OpenTextFile(manifestPath, 1, False)
    If Err.Number <> 0 Then Err.Clear: On Error GoTo 0: Exit Function
    text = ts.ReadAll
    ts.Close
    On Error GoTo 0
    Set re = New RegExp
    re.Global = False
    re.IgnoreCase = True
    re.Pattern = """" & fieldName & """\s*:\s*""([^""]*)"""
    Set matches = re.Execute(text)
    If matches.Count > 0 Then ReadManifestString = matches(0).SubMatches(0)
End Function

Function ReadInstallerGeneration(folderPath)
    ReadInstallerGeneration = ReadManifestString(folderPath, "installer_generation")
End Function

Function IsValidGeneration(value)
    Dim re
    Set re = New RegExp
    re.Global = False
    re.Pattern = "^[0-9]{20}$"
    IsValidGeneration = re.Test(value)
End Function

Function CheckDowngrade(sourceGen, installedGen)
    CheckDowngrade = 0
    If Len(installedGen) = 0 Then Exit Function
    If Not IsValidGeneration(installedGen) Then CheckDowngrade = 22: Exit Function
    If StrComp(sourceGen, installedGen, 0) < 0 Then CheckDowngrade = 22
End Function

Function ReadInstallIdentity(folderPath)
    Dim gen, pkg, wb
    If Not fso.FolderExists(folderPath) Then ReadInstallIdentity = "ABSENT": Exit Function
    gen = ReadInstallerGeneration(folderPath)
    pkg = ReadManifestString(folderPath, "package_name")
    wb = ReadManifestString(folderPath, "workbench_sha256")
    ReadInstallIdentity = "PRESENT|" & gen & "|" & pkg & "|" & wb
End Function

Function AcquireInstallLock(sourceGen)
    Dim marker, ts
    AcquireInstallLock = 23
    If fso.FolderExists(lockDir) Then Exit Function
    On Error Resume Next
    Err.Clear
    fso.CreateFolder lockDir
    If Err.Number <> 0 Then Err.Clear: On Error GoTo 0: Exit Function
    marker = lockDir & "\authority.txt"
    Set ts = fso.CreateTextFile(marker, True, False)
    If Err.Number <> 0 Then
        Err.Clear
        fso.DeleteFolder lockDir, True
        On Error GoTo 0
        Exit Function
    End If
    ts.WriteLine "MERCH_FORGE_INSTALL_LOCK_V1"
    ts.WriteLine "source_generation=" & sourceGen
    ts.Close
    On Error GoTo 0
    lockOwned = True
    AcquireInstallLock = 0
End Function

Sub ReleaseInstallLock()
    If Not lockOwned Then Exit Sub
    On Error Resume Next
    If fso.FolderExists(lockDir) Then fso.DeleteFolder lockDir, True
    On Error GoTo 0
    lockOwned = False
End Sub

Function ReadPreviousAuthorityMode()
    Dim ts, firstLine, secondLine
    ReadPreviousAuthorityMode = ""
    If Not fso.FileExists(previousAuthorityPath) Then Exit Function
    On Error Resume Next
    Set ts = fso.OpenTextFile(previousAuthorityPath, 1, False)
    If Err.Number <> 0 Then Err.Clear: On Error GoTo 0: Exit Function
    firstLine = ""
    secondLine = ""
    If Not ts.AtEndOfStream Then firstLine = ts.ReadLine
    If Not ts.AtEndOfStream Then secondLine = ts.ReadLine
    ts.Close
    On Error GoTo 0
    If firstLine <> "MERCH_FORGE_PREVIOUS_AUTHORITY_V1" Then Exit Function
    If LCase(Left(secondLine, 5)) <> "mode=" Then Exit Function
    ReadPreviousAuthorityMode = LCase(Mid(secondLine, 6))
End Function

Function IsFolderEmpty(path)
    Dim folder
    IsFolderEmpty = False
    If Not fso.FolderExists(path) Then Exit Function
    Set folder = fso.GetFolder(path)
    IsFolderEmpty = (folder.Files.Count = 0 And folder.SubFolders.Count = 0)
End Function

Function WritePreviousAuthority(modeValue, generationValue)
    Dim ts
    WritePreviousAuthority = False
    On Error Resume Next
    Err.Clear
    Set ts = fso.CreateTextFile(previousAuthorityPath, True, False)
    If Err.Number <> 0 Then Err.Clear: On Error GoTo 0: Exit Function
    ts.WriteLine "MERCH_FORGE_PREVIOUS_AUTHORITY_V1"
    ts.WriteLine "mode=" & modeValue
    If Len(generationValue) = 0 Then generationValue = "legacy_or_none"
    ts.WriteLine "generation=" & generationValue
    ts.Close
    If Err.Number = 0 Then WritePreviousAuthority = True Else Err.Clear
    On Error GoTo 0
End Function

Function PreparePreviousAuthority()
    Dim modeValue
    PreparePreviousAuthority = 0
    If fso.FolderExists(backupDir) Then
        modeValue = ReadPreviousAuthorityMode()
        If modeValue <> "sentinel" And modeValue <> "previous_good" Then PreparePreviousAuthority = 19: Exit Function
        If modeValue = "sentinel" And Not IsFolderEmpty(backupDir) Then PreparePreviousAuthority = 19: Exit Function
        If modeValue = "previous_good" And Not fso.FolderExists(appDir) Then PreparePreviousAuthority = 19: Exit Function
        Exit Function
    End If
    If fso.FileExists(previousAuthorityPath) Then PreparePreviousAuthority = 19: Exit Function
    On Error Resume Next
    Err.Clear
    fso.CreateFolder backupDir
    If Err.Number <> 0 Then Err.Clear: On Error GoTo 0: PreparePreviousAuthority = 19: Exit Function
    On Error GoTo 0
    If Not WritePreviousAuthority("sentinel", "") Then PreparePreviousAuthority = 26
End Function

Function FinalizePreviousGood(previousGeneration)
    FinalizePreviousGood = 0
    If fso.FolderExists(nextBackupDir) Then
        On Error Resume Next
        Err.Clear
        If fso.FolderExists(backupDir) Then fso.DeleteFolder backupDir, True
        If Err.Number <> 0 Then Err.Clear: On Error GoTo 0: FinalizePreviousGood = 27: Exit Function
        fso.MoveFolder nextBackupDir, backupDir
        If Err.Number <> 0 Then Err.Clear: On Error GoTo 0: FinalizePreviousGood = 27: Exit Function
        On Error GoTo 0
        If Not WritePreviousAuthority("previous_good", previousGeneration) Then FinalizePreviousGood = 27
    Else
        If Not fso.FolderExists(backupDir) Then
            On Error Resume Next
            Err.Clear
            fso.CreateFolder backupDir
            If Err.Number <> 0 Then Err.Clear: On Error GoTo 0: FinalizePreviousGood = 27: Exit Function
            On Error GoTo 0
        End If
        If Not WritePreviousAuthority("sentinel", "") Then FinalizePreviousGood = 27
    End If
End Function

Sub RollbackActivatedApp()
    On Error Resume Next
    If fso.FolderExists(appDir) Then fso.DeleteFolder appDir, True
    If fso.FolderExists(nextBackupDir) Then fso.MoveFolder nextBackupDir, appDir
    On Error GoTo 0
    ReleaseInstallLock
End Sub

Sub DeleteOwnedStage()
    On Error Resume Next
    If fso.FolderExists(stageDir) Then fso.DeleteFolder stageDir, True
    On Error GoTo 0
End Sub

Sub CopySourceContents(srcPath, dstPath)
    Dim srcFolder, fileItem, folderItem, targetPath, copyErrNumber, copyErrDescription

    On Error Resume Next
    Set srcFolder = fso.GetFolder(srcPath)
    If Err.Number <> 0 Then
        copyErrNumber = Err.Number
        copyErrDescription = Err.Description
        Err.Clear
        On Error GoTo 0
        FailInstallDetailed "Could not read the extracted Merch Forge folder.", 12, copyErrNumber, copyErrDescription, srcPath
    End If
    On Error GoTo 0

    For Each fileItem In srcFolder.Files
        targetPath = fso.BuildPath(dstPath, fileItem.Name)
        On Error Resume Next
        Err.Clear
        fso.CopyFile fileItem.Path, targetPath, True
        If Err.Number <> 0 Then
            copyErrNumber = Err.Number
            copyErrDescription = Err.Description
            Err.Clear
            On Error GoTo 0
            FailInstallDetailed "Could not copy application file: " & fileItem.Name, 12, copyErrNumber, copyErrDescription, targetPath
        End If
        On Error GoTo 0
    Next

    For Each folderItem In srcFolder.SubFolders
        targetPath = fso.BuildPath(dstPath, folderItem.Name)
        On Error Resume Next
        Err.Clear
        fso.CopyFolder folderItem.Path, targetPath, True
        If Err.Number <> 0 Then
            copyErrNumber = Err.Number
            copyErrDescription = Err.Description
            Err.Clear
            On Error GoTo 0
            FailInstallDetailed "Could not copy application folder: " & folderItem.Name, 12, copyErrNumber, copyErrDescription, targetPath
        End If
        On Error GoTo 0
    Next
End Sub

Sub FailInstallDetailed(text, code, errNumber, errDescription, failingPath)
    DeleteOwnedStage
    ReleaseInstallLock
    MsgBox text & vbCrLf & vbCrLf & _
           "Windows error: " & CStr(errNumber) & vbCrLf & _
           errDescription & vbCrLf & vbCrLf & _
           "Path:" & vbCrLf & failingPath, 16, "Merch Forge - Install"
    WScript.Quit code
End Sub

Sub EnsureFolder(path)
    If Len(path) = 0 Then Exit Sub
    If fso.FolderExists(path) Then Exit Sub
    EnsureFolder fso.GetParentFolderName(path)
    If Not fso.FolderExists(path) Then fso.CreateFolder path
End Sub

Sub FailInstall(text, code)
    DeleteOwnedStage
    ReleaseInstallLock
    MsgBox text, 16, "Merch Forge - Install"
    WScript.Quit code
End Sub
