#define AppName "Voice Changer Live"
#define AppPublisher "VoiceChanger"
#define AppExecutableName "VoiceChanger.exe"

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{9cc2e83c-0e74-429f-a7ae-c586a736c1df}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\VoiceChanger
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=VoiceChanger-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExecutableName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\VoiceChanger\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExecutableName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExecutableName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExecutableName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
