; MediaEngine installer (Inno Setup 6). Built in CI from the finished package folder:
;   ISCC /DPkgName=MediaEngine-3.13.0-rc1-b20 /DAppVer=3.13.0-rc1 /DSrcDir=<pkg>\<PkgName> /DOutDir=<out> mediaengine_setup.iss
;
; Same layout as the ZIP (contract: every build is its own folder, data outside it):
;   <base>\MediaEngine-<version>-b<build>\   this build (a newer setup adds a new folder next to it)
;   <base>\MediaEngine Data\                 projects, database, caches, exports - created by the app, kept on uninstall
; <base> = D:\MediaEngine when D:\Archivist or D:\MediaEngine exists (the owner's PC), else %USERPROFILE%\MediaEngine.
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
UninstallDisplayIcon={app}\{#PkgName}\MediaEngine.ico
UninstallDisplayName=MediaEngine
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=auto
CloseApplications=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
en.DataKept=Your projects and exported videos stay in "MediaEngine Data" (they are not removed by uninstall).
ru.DataKept=Проекты и экспортированные ролики остаются в папке «MediaEngine Data» (удаление программы их не трогает).
en.Running=MediaEngine is running. Press Quit in its window first, then continue.
ru.Running=MediaEngine запущен. Сначала нажми Quit в его окне, потом продолжай.

[Files]
Source: "{#SrcDir}\*"; DestDir: "{app}\{#PkgName}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\MediaEngine"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\{#PkgName}\Start MediaEngine.vbs"""; WorkingDir: "{app}\{#PkgName}"; IconFilename: "{app}\{#PkgName}\MediaEngine.ico"; Comment: "MediaEngine {#AppVer}"

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\{#PkgName}\Start MediaEngine.vbs"""; WorkingDir: "{app}\{#PkgName}"; Description: "{cm:LaunchProgram,MediaEngine}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; files the app may create inside a build folder at run time (the build folders themselves are removed with their files)
Type: filesandordirs; Name: "{app}\{#PkgName}\__pycache__"
Type: files; Name: "{userdesktop}\MediaEngine RC.lnk"

[Code]
function DefaultBase(Param: String): String;
begin
  if DirExists('D:\Archivist') or DirExists('D:\MediaEngine') then
    Result := 'D:\MediaEngine'
  else
    Result := ExpandConstant('{%USERPROFILE}') + '\MediaEngine';
end;

function AppAnswers(): Boolean;
var
  ResultCode: Integer;
begin
  // the app answers on its own port while it runs; checked with the built-in PowerShell, no network beyond 127.0.0.1
  Result := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8775/api/ping | Out-Null; exit 0 } catch { exit 1 }"',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
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
