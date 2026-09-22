; Script gerado para o instalador oficial do GF Farmer
; Desenvolvido para compilação com Inno Setup 6 (ISCC.exe)

#define MyAppName "GF Farmer"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "STZ Labs"
#define MyAppExeName "GF Farmer.exe"
#define MyAppId "{{B8E17A63-84B2-4E9A-8F52-2FD5E48BE879}"

[Setup]
; Identificação do aplicativo
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Suporta instalação por usuário padrão ou para todos os usuários com elevação
PrivilegesRequiredOverridesAllowed=dialog

; Configurações de saída do instalador
OutputDir=..\dist\installer
OutputBaseFilename=GF_Farmer_Setup_v{#MyAppVersion}
SetupIconFile=..\build_assets\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compressão de alta eficiência
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Informações visuais e mensagens
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\GF Farmer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpa apenas arquivos residuais da aplicação no diretório de instalação
; O banco de dados do usuário em %LOCALAPPDATA% permanece intacto e protegido
Type: filesandordirs; Name: "{app}"
