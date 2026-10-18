; MediaEngine installer (Inno Setup 6). Built in CI from the finished package folder:
;   ISCC /DPkgName=MediaEngine-3.13.0-rc1-b20 /DAppVer=3.13.0-rc1 /DSrcDir=<pkg>\<PkgName> /DOutDir=<out> mediaengine_setup.iss
;
; Same layout as the ZIP (contract: every build is its own folder, data outside it):
;   <base>\MediaEngine-<version>-b<build>\   this build (a newer setup adds a new folder next to it)
;   <base>\MediaEngine Data\                 projects, database, caches, exports - created by the app, kept on uninstall
; <base> = D:\projects\medeng when D:\projects exists (the owner's project folder; nothing is put at the root of D:),
; else %USERPROFILE%\MediaEngine. The folder can be changed on the first Setup page.
; Per-user install, no administrator rights, nothing written outside <base> except the Start-menu shortcut
; (the app itself makes its desktop shortcut on first start). No network, no services, no autostart.

#ifndef PkgName
  #error PkgName is required
#endif
#ifndef AppVer
  #error AppVer is required
#endif
#ifndef SrcDir
  #error SrcDir is required
#endif
#ifndef OutDir
  #define OutDir "."
#endif
#ifndef Port
  #define Port "8775"
#endif

[Setup]
AppId={{6E0B7F3A-2C55-4D8E-9A41-1F7C3B9D5E20}
AppName=MediaEngine
AppVersion={#AppVer}
AppVerName=MediaEngine {#AppVer}
AppPublisher=MediaEngine (personal build)
VersionInfoVersion=3.13.0.0
DefaultDirName={code:DefaultBase}
UsePreviousAppDir=yes
DirExistsWarning=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutDir}
OutputBaseFilename={#PkgName}-Setup
SetupIconFile={#SrcDir}\MediaEngine.ico
UninstallDisplayIcon={app}\MediaEngine.ico
UninstallDisplayName=MediaEngine
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=yes
CloseApplications=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
en.DataKept=Your projects and exported videos stay in "MediaEngine Data" (they are not removed by uninstall).
ru.DataKept=Проекты и экспортированные ролики остаются в папке «MediaEngine Data» (удаление программы их не трогает).
en.Running=MediaEngine is running (maybe only in the background). Quit it: right-click its icon in the notification area next to the clock → Quit (or open it from the Start menu and press Quit at the top), then continue.
ru.Running=MediaEngine запущен (возможно, только в фоне). Закрой его: правой кнопкой по его значку в трее рядом с часами → «Выход» (или открой из меню Пуск и нажми «Выход» вверху), затем продолжай.
en.SameRunning=This very build of MediaEngine is running right now (maybe only in the background). Quit it: right-click its icon in the notification area next to the clock → Quit, then run Setup again.
ru.SameRunning=Именно эта сборка MediaEngine сейчас запущена (возможно, только в фоне). Закрой её: правой кнопкой по значку MediaEngine в трее рядом с часами → «Выход», затем запусти Setup снова.

[Files]
Source: "{#SrcDir}\*"; DestDir: "{app}\{#PkgName}"; Flags: ignoreversion recursesubdirs createallsubdirs
; one icon for the Apps list that does not depend on any single build folder
Source: "{#SrcDir}\MediaEngine.ico"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; the language chosen for Setup becomes the program's language once per Setup run (it can be switched in the program)
Root: HKCU; Subkey: "Software\MediaEngine"; ValueType: string; ValueName: "Language"; ValueData: "{language}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\MediaEngine"; ValueType: string; ValueName: "LanguageBuild"; ValueData: "{#PkgName}"; Flags: uninsdeletekey

[Icons]
Name: "{userprograms}\MediaEngine"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\{#PkgName}\Start MediaEngine.vbs"""; WorkingDir: "{app}\{#PkgName}"; IconFilename: "{app}\{#PkgName}\MediaEngine.ico"; Comment: "MediaEngine {#AppVer}"; AppUserModelID: "MediaEngine.Desktop"

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\{#PkgName}\Start MediaEngine.vbs"""; WorkingDir: "{app}\{#PkgName}"; Description: "{cm:LaunchProgram,MediaEngine}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; the whole build folder this setup made, including anything created in it at run time (the data folder
; "MediaEngine Data" next to it is never touched)
Type: filesandordirs; Name: "{app}\{#PkgName}"
; builds the program installed itself with its Update button (next to this one, same layout) and an unfinished one
Type: filesandordirs; Name: "{app}\MediaEngine-*"
Type: filesandordirs; Name: "{app}\.update-MediaEngine-*"
Type: files; Name: "{userdesktop}\MediaEngine RC.lnk"

[Code]
function DefaultBase(Param: String): String;
begin
  if DirExists('D:\projects') then
    Result := 'D:\projects\medeng'          { the owner's project folder; nothing at the root of D: }
  else
    Result := ExpandConstant('{%USERPROFILE}') + '\MediaEngine';
end;

function AppAnswers(): Boolean;
var
  ResultCode: Integer;
begin
  // the app answers on its own port while it runs; checked with the built-in PowerShell, no network beyond 127.0.0.1
  Result := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:{#Port}/api/ping | Out-Null; exit 0 } catch { exit 1 }"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function SameBuildRunning(Folder: String): Boolean;
var
  ResultCode: Integer;
  F: String;
begin
  // a NEW build goes into its own folder and can be installed while an older one runs (started, it takes over
  // from the older one); only re-installing the very build that is running would hit files in use
  F := Folder;
  StringChangeEx(F, '''', '''''', True);
  Result := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -Command "try { $p = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:{#Port}/api/ping).Content | ConvertFrom-Json; if ($p.install -eq ''' + F + ''') { exit 0 } else { exit 1 } } catch { exit 1 }"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if SameBuildRunning(ExpandConstant('{app}\{#PkgName}')) then
    Result := CustomMessage('SameRunning');
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  while Result and AppAnswers() do
    Result := (SuppressibleMsgBox(CustomMessage('Running'), mbInformation, MB_OKCANCEL, IDCANCEL) = IDOK);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := WizardForm.FinishedLabel.Caption + #13#10#13#10 + CustomMessage('DataKept');
end;
