; FlowPy Installer — Inno Setup Script
; TurcoDevelopStudio / FlowPy
;
; Build with:  iscc installer\flowpy.iss
; Requires PyInstaller output in dist\FlowPy\ first.

#define AppName        "FlowPy"
#ifndef AppVersion
  #define AppVersion    "1.0.0"
#endif
#define AppPublisher    "TurcoDevelopStudio"
#define AppURL          "https://turcodevelopstudio.netlify.app"
#define AppExeName      "FlowPy.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\dist
OutputBaseFilename=FlowPy-Setup-v{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\FlowPy\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\FlowPy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
const
  UninstallRegKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1';

function InitializeSetup(): Boolean;
var
  InstalledVersion: String;
begin
  Result := True;
  if RegQueryStringValue(HKCU, UninstallRegKey, 'DisplayVersion', InstalledVersion) then
  begin
    WizardForm.WelcomeLabel2.Caption :=
      'Setup will update FlowPy from version ' + InstalledVersion +
      ' to {#AppVersion}.' + #13#10 + #13#10 +
      'Your plugins and settings are kept.';
  end;
end;
