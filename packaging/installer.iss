; Plantilla base Inno Setup para DriverSwitch GUI
; Compilar este .iss desde la carpeta packaging para usar rutas relativas.

#define MyAppName "DriverSwitch GUI"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "DriverSwitch Team"
#define MyAppExeName "DriverSwitchGUI.exe"
#define MyRootDir AddBackslash(SourcePath) + "..\\"

[Setup]
AppId={{D7B52B25-117A-4C1B-B2D0-DRIVERSWITCHGUI}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=DriverSwitchGUI-Setup
SetupIconFile={#MyRootDir}image1.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "{#MyRootDir}dist\DriverSwitchGUI\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\image1.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\image1.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; Flags: nowait postinstall skipifsilent
