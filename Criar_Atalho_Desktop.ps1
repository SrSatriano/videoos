# ==============================================================================
# Script de Criação do Atalho de Desktop do Video OS
# ==============================================================================
param(
    [string]$ShortcutName = "Video OS.lnk"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Garantir que o icone existe
$IconPath = Join-Path $ProjectRoot "icon.ico"
if (-not (Test-Path $IconPath)) {
    $PublicIcon = Join-Path $ProjectRoot "frontend\public\icon.ico"
    if (Test-Path $PublicIcon) {
        Copy-Item $PublicIcon $IconPath -Force
    }
}

# 2. Localizar pasta da Area de Trabalho
$DesktopPath = [Environment]::GetFolderPath('Desktop')
if (-not (Test-Path $DesktopPath)) {
    throw "Area de trabalho nao encontrada em: $DesktopPath"
}

$ShortcutFile = Join-Path $DesktopPath $ShortcutName
$TargetCmd = Join-Path $ProjectRoot "VideoOS.cmd"

if (-not (Test-Path $TargetCmd)) {
    throw "Arquivo inicializador VideoOS.cmd nao encontrado em: $TargetCmd"
}

# 3. Criar atalho WScript.Shell
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutFile)
$Shortcut.TargetPath = $TargetCmd
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.Description = "Video OS - Sistema de Edicao de Videos em Massa"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
}
$Shortcut.Save()

# 4. Validar criacao
if (Test-Path $ShortcutFile) {
    Write-Host "Atalho criado com sucesso na Area de Trabalho!" -ForegroundColor Green
    Write-Host "Arquivo: $ShortcutFile" -ForegroundColor Cyan
    Write-Host "Destino: $TargetCmd" -ForegroundColor Gray
    Write-Host "Icone:   $IconPath" -ForegroundColor Gray
} else {
    throw "Falha ao gravar o atalho na Area de Trabalho."
}
