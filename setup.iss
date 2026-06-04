[Setup]
AppName=FlowTrack
AppVersion=1.0
AppPublisher=Zainy Zihar
AppPublisherURL=https://github.com/hasnizihar/FlowTrack
DefaultDirName={autopf}\FlowTrack
DefaultGroupName=FlowTrack
AllowNoIcons=yes
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=FlowTrack_Setup
SetupIconFile=traffic_analysis_gui\assets\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\FlowTrack.exe"; DestDir: "{app}"; Flags: ignoreversion
; Note: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\FlowTrack"; Filename: "{app}\FlowTrack.exe"
Name: "{group}\{cm:UninstallProgram,FlowTrack}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\FlowTrack"; Filename: "{app}\FlowTrack.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FlowTrack.exe"; Description: "{cm:LaunchProgram,FlowTrack}"; Flags: nowait postinstall skipifsilent
