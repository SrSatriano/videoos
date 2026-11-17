$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root "data\logs"
$VenvPath = Join-Path $Root ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$PythonwExe = Join-Path $VenvPath "Scripts\pythonw.exe"
$PipExe = Join-Path $VenvPath "Scripts\pip.exe"
$PytestExe = Join-Path $VenvPath "Scripts\pytest.exe"
$UvicornExe = Join-Path $VenvPath "Scripts\uvicorn.exe"
$NpmCache = Join-Path $Root ".npm-cache"
$AllowDockerReset = $env:VIDEO_OS_ALLOW_DOCKER_RESET -in @("1", "true", "TRUE", "yes", "YES", "sim", "SIM")
$ForceCleanStart = $env:VIDEO_OS_FORCE_CLEAN_START -in @("1", "true", "TRUE", "yes", "YES", "sim", "SIM")
$NoOpenWindow = $env:VIDEO_OS_NO_OPEN -in @("1", "true", "TRUE", "yes", "YES", "sim", "SIM")
$PreflightOnly = $env:VIDEO_OS_PREFLIGHT_ONLY -in @("1", "true", "TRUE", "yes", "YES", "sim", "SIM")
$DefaultApiPort = 8010
$DefaultWebPort = 5174

function Get-DotEnvValue {
    param([string]$Name)

    $EnvPath = Join-Path $Root ".env"
    if (-not (Test-Path $EnvPath)) {
        return $null
    }

    foreach ($Line in (Get-Content -LiteralPath $EnvPath)) {
        if ($Line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.+?)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Get-ConfiguredInt {
    param(
        [string]$Name,
        [int]$DefaultValue
    )

    $RawValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($RawValue)) {
        $RawValue = Get-DotEnvValue $Name
    }

    $Parsed = 0
    if ([int]::TryParse($RawValue, [ref]$Parsed) -and $Parsed -gt 0) {
        return $Parsed
    }
    return $DefaultValue
}

function Initialize-VideoOSRuntimeEnv {
    $ApiPort = Get-ConfiguredInt "VIDEO_OS_API_PORT" $DefaultApiPort
    $WebPort = Get-ConfiguredInt "VIDEO_OS_WEB_PORT" $DefaultWebPort
    $ExpectedApiUrl = "http://127.0.0.1:$ApiPort"
    $ExpectedCors = "http://127.0.0.1:$WebPort,http://localhost:$WebPort"

    $env:VIDEO_OS_API_PORT = [string]$ApiPort
    $env:VIDEO_OS_WEB_PORT = [string]$WebPort
    $env:VITE_API_URL = $ExpectedApiUrl
    $env:VIDEO_OS_CORS_ORIGINS = $ExpectedCors

    return @{
        ApiPort = $ApiPort
        WebPort = $WebPort
        ApiUrl = $ExpectedApiUrl
        CorsOrigins = $ExpectedCors
    }
}

function Update-PythonToolPaths {
    $script:PythonExe = Join-Path $script:VenvPath "Scripts\python.exe"
    $script:PythonwExe = Join-Path $script:VenvPath "Scripts\pythonw.exe"
    $script:PipExe = Join-Path $script:VenvPath "Scripts\pip.exe"
    $script:PytestExe = Join-Path $script:VenvPath "Scripts\pytest.exe"
    $script:UvicornExe = Join-Path $script:VenvPath "Scripts\uvicorn.exe"

    if ((-not (Test-Path $script:PythonExe)) -and (Test-Path $script:PythonwExe)) {
        $script:PythonExe = $script:PythonwExe
    }
}

function Get-FrontendDependencyMarker {
    $PackageLock = Join-Path $Root "frontend\package-lock.json"
    if (Test-Path $PackageLock) {
        return $PackageLock
    }
    return (Join-Path $Root "frontend\package.json")
}

function Test-ExecutableAvailable {
    param([string]$Command)

    if ([string]::IsNullOrWhiteSpace($Command)) {
        return $false
    }
    if ($Command.Contains("\") -or $Command.Contains("/")) {
        return (Test-Path $Command)
    }
    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

function Get-ToolVersion {
    param(
        [string]$Command,
        [string[]]$Arguments = @("--version")
    )

    if (-not (Test-ExecutableAvailable $Command)) {
        return "INDISPONIVEL"
    }

    try {
        $Output = & $Command @Arguments 2>&1
        if ($LASTEXITCODE -eq 0 -and $Output) {
            return (($Output | Select-Object -First 1).ToString().Trim())
        }
    } catch {
        return "INDISPONIVEL"
    }
    return "INDISPONIVEL"
}

function Get-PythonRuntimeVersion {
    $Version = Get-ToolVersion $PythonExe @("--version")
    if ($Version -ne "INDISPONIVEL") {
        return $Version
    }

    $CfgFile = Join-Path $VenvPath "pyvenv.cfg"
    if (Test-Path $CfgFile) {
        foreach ($Line in (Get-Content -LiteralPath $CfgFile)) {
            if ($Line -match "^\s*version\s*=\s*(.+?)\s*$") {
                return "Python $($Matches[1].Trim()) (pyvenv.cfg)"
            }
        }
    }
    return "INDISPONIVEL"
}

function Get-PythonBootstrapCandidates {
    $Candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:VIDEO_OS_PYTHON_BOOTSTRAP)) {
        $Candidates += $env:VIDEO_OS_PYTHON_BOOTSTRAP
    }
    $Candidates += (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
    $Candidates += (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe")
    $Candidates += "python"
    $Candidates += "py"
    return $Candidates
}

function New-VideoOSVenv {
    param([string]$TargetPath)

    foreach ($Candidate in (Get-PythonBootstrapCandidates)) {
        if ([string]::IsNullOrWhiteSpace($Candidate)) {
            continue
        }

        if ($Candidate -eq "python") {
            if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
                continue
            }
            & python -m venv $TargetPath
        } elseif ($Candidate -eq "py") {
            if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
                continue
            }
            & py -3 -m venv $TargetPath
        } else {
            if (-not (Test-Path $Candidate)) {
                continue
            }
            & $Candidate -m venv $TargetPath
        }

        if ($LASTEXITCODE -eq 0) {
            Update-PythonToolPaths
            if (Test-Path $script:PipExe) {
                return $true
            }
        }
    }

    return $false
}

function Normalize-ProcessEnvironment {
    $Vars = [Environment]::GetEnvironmentVariables("Process")
    $PathKeys = @($Vars.Keys | Where-Object { [string]$_ -ieq "PATH" })
    if ($PathKeys.Count -le 1) {
        return
    }

    $PathValue = [Environment]::GetEnvironmentVariable("PATH", "Process")
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        $PathValue = [string]$Vars[$PathKeys[0]]
    }

    foreach ($Key in $PathKeys) {
        [Environment]::SetEnvironmentVariable([string]$Key, $null, "Process")
    }
    [Environment]::SetEnvironmentVariable("Path", $PathValue, "Process")
}

function Write-Step($Text) {
    Write-Host ""
    Write-Host $Text -ForegroundColor Cyan
}

function Fail($Text) {
    Write-Host ""
    Write-Host $Text -ForegroundColor Red
    Read-Host "Pressione ENTER para sair"
    exit 1
}

function Require-File($RelativePath) {
    $Path = Join-Path $Root $RelativePath
    if (-not (Test-Path $Path)) {
        Fail "Arquivo obrigatorio ausente: $RelativePath"
    }
    $Size = (Get-Item $Path).Length
    if ($Size -eq 0) {
        Fail "Arquivo obrigatorio esta vazio ou corrompido (0 bytes): $RelativePath"
    }
}

function Test-DockerImageOutdated($ServiceName, $ImageName) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return "UNKNOWN"
    }
    $CreatedStr = & docker inspect --format="{{.Created}}" $ImageName 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($CreatedStr)) {
        return "NOVA"
    }

    $ImageTime = [DateTime]::MinValue
    if ([DateTime]::TryParse($CreatedStr, [ref]$ImageTime)) {
        $FilesToCheck = @()
        if ($ServiceName -eq "api" -or $ServiceName -eq "worker") {
            $FilesToCheck += (Join-Path $Root "backend\requirements.txt")
            $FilesToCheck += (Join-Path $Root "backend\Dockerfile")
        } elseif ($ServiceName -eq "web") {
            $FilesToCheck += (Join-Path $Root "frontend\package.json")
            $FilesToCheck += (Join-Path $Root "frontend\Dockerfile")
        }
        $FilesToCheck += (Join-Path $Root "docker-compose.yml")

        foreach ($File in $FilesToCheck) {
            if (Test-Path $File) {
                $FileTime = (Get-Item $File).LastWriteTime
                if ($FileTime -gt $ImageTime) {
                    return "DESATUALIZADA"
                }
            }
        }
        return "ATUALIZADA"
    }
    return "UNKNOWN"
}

function Invoke-PreFlightAudit {
    Update-PythonToolPaths
    Write-Host "==========================================" -ForegroundColor Gray
    Write-Host "     Pre-Flight Audit (Auditoria Pre-Voo)  " -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Gray
    
    $FilesOk = $true
    $Required = @("docker-compose.yml", "backend\requirements.txt", "backend\app\main.py", "frontend\package.json", "frontend\src\App.tsx")
    foreach ($File in $Required) {
        $Path = Join-Path $Root $File
        if (-not (Test-Path $Path)) {
            Write-Host "[ERRO] Arquivo ausente: $File" -ForegroundColor Red
            $FilesOk = $false
        } else {
            $Size = (Get-Item $Path).Length
            if ($Size -eq 0) {
                Write-Host "[ERRO] Arquivo vazio ou corrompido: $File" -ForegroundColor Red
                $FilesOk = $false
            }
        }
    }
    if ($FilesOk) {
        Write-Host "[OK] Arquivos essenciais do sistema: INTEGROS" -ForegroundColor Green
    } else {
        Fail "Auditoria de arquivos falhou. O sistema contem arquivos ausentes ou vazios."
    }

    $requirementsPath = Join-Path $Root "backend\requirements.txt"
    $pythonStatus = "NAO INSTALADO"
    if ((Test-Path $PythonExe) -and (Test-Path $PipExe)) {
        & $PipExe show fastapi *> $null
        if ($LASTEXITCODE -ne 0) {
            $pythonStatus = "NAO INSTALADO"
        } else {
            $pythonStatus = "ATUALIZADO"
            $cfgFile = Join-Path $VenvPath "pyvenv.cfg"
            if (Test-Path $cfgFile) {
                $reqTime = (Get-Item $requirementsPath).LastWriteTime
                $cfgTime = (Get-Item $cfgFile).LastWriteTime
                if ($reqTime -gt $cfgTime) {
                    $pythonStatus = "DESATUALIZADO (sera atualizado)"
                }
            }
        }
    }
    $pythonColor = "Yellow"
    if ($pythonStatus -eq "ATUALIZADO") { $pythonColor = "Green" }
    Write-Host "[INFO] Status das dependencias Python: $pythonStatus" -ForegroundColor $pythonColor
    Write-Host "[INFO] Versao Python runtime: $(Get-PythonRuntimeVersion)" -ForegroundColor Gray

    $nodeModules = Join-Path $Root "frontend\node_modules"
    $dependencyMarker = Get-FrontendDependencyMarker
    $nodeStatus = "NAO INSTALADO"
    if ((Test-Path $nodeModules) -and (Test-Path (Join-Path $nodeModules "react")) -and (Test-Path (Join-Path $nodeModules "vite"))) {
        $nodeStatus = "ATUALIZADO"
        $modulesTime = (Get-Item $nodeModules).LastWriteTime
        $markerTime = (Get-Item $dependencyMarker).LastWriteTime
        if ($markerTime -gt $modulesTime) {
            $nodeStatus = "DESATUALIZADO (sera atualizado)"
        }
    }
    $nodeColor = "Yellow"
    if ($nodeStatus -eq "ATUALIZADO") { $nodeColor = "Green" }
    Write-Host "[INFO] Status das dependencias Node: $nodeStatus" -ForegroundColor $nodeColor
    Write-Host "[INFO] Versao Node: $(Get-ToolVersion "node" @("--version"))" -ForegroundColor Gray
    Write-Host "[INFO] Versao npm: $(Get-ToolVersion "npm.cmd" @("--version"))" -ForegroundColor Gray

    $preflightApiPort = Get-ConfiguredInt "VIDEO_OS_API_PORT" $DefaultApiPort
    $preflightWebPort = Get-ConfiguredInt "VIDEO_OS_WEB_PORT" $DefaultWebPort
    $apiPortStatus = Get-PortStatusLabel $preflightApiPort
    $webPortStatus = Get-PortStatusLabel $preflightWebPort
    $apiPortColor = if ($apiPortStatus -eq "LIVRE") { "Green" } else { "Yellow" }
    $webPortColor = if ($webPortStatus -eq "LIVRE") { "Green" } else { "Yellow" }
    Write-Host "[INFO] Porta API esperada ($preflightApiPort): $apiPortStatus" -ForegroundColor $apiPortColor
    Write-Host "[INFO] Porta Web esperada ($preflightWebPort): $webPortStatus" -ForegroundColor $webPortColor

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "[INFO] Docker CLI: $(Get-ToolVersion "docker" @("--version"))" -ForegroundColor Gray
        docker version --format "{{.Server.Version}}" *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Engine do Docker Desktop: ONLINE" -ForegroundColor Green
            $ApiImgStatus = Test-DockerImageOutdated "api" "sistemadeedio-api"
            $WebImgStatus = Test-DockerImageOutdated "web" "sistemadeedio-web"
            $WorkerImgStatus = Test-DockerImageOutdated "worker" "sistemadeedio-worker"

            $apiImgColor = "Yellow"
            if ($ApiImgStatus -eq "ATUALIZADA") { $apiImgColor = "Green" }
            $webImgColor = "Yellow"
            if ($WebImgStatus -eq "ATUALIZADA") { $webImgColor = "Green" }
            $workerImgColor = "Yellow"
            if ($WorkerImgStatus -eq "ATUALIZADA") { $workerImgColor = "Green" }

            Write-Host "[INFO] Imagem Docker API (sistemadeedio-api): $ApiImgStatus" -ForegroundColor $apiImgColor
            Write-Host "[INFO] Imagem Docker Web (sistemadeedio-web): $WebImgStatus" -ForegroundColor $webImgColor
            Write-Host "[INFO] Imagem Docker Worker (sistemadeedio-worker): $WorkerImgStatus" -ForegroundColor $workerImgColor
        } else {
            Write-Host "[INFO] Engine do Docker Desktop: OFFLINE (usando modo local)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[INFO] Docker Desktop: NAO INSTALADO (usando modo local)" -ForegroundColor Yellow
    }
    Write-Host "==========================================" -ForegroundColor Gray
    Write-Host ""
}



function Invoke-Checked($Command, $Arguments, $WorkingDirectory = $Root) {
    Push-Location $WorkingDirectory
    try {
        & $Command @Arguments
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        return $true
    }
    finally {
        Pop-Location
    }
}

function Test-CanBindPort($Port) {
    $Listener = $null
    try {
        $Listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $Listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $Listener) {
            $Listener.Stop()
        }
    }
}

function Get-PortStatusLabel($Port) {
    if (Test-CanBindPort $Port) {
        return "LIVRE"
    }
    return "OCUPADA"
}

function Get-UsablePort($Candidates) {
    foreach ($Port in $Candidates) {
        if (Test-CanBindPort $Port) {
            return $Port
        }
    }

    $Listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    try {
        $Listener.Start()
        return ([System.Net.IPEndPoint]$Listener.LocalEndpoint).Port
    }
    finally {
        $Listener.Stop()
    }
}

function Get-PreferredPort {
    param(
        [int]$PreferredPort,
        [int[]]$Candidates,
        [string]$ServiceName,
        [int]$ContainerPort
    )

    $ExistingPort = Get-ComposePort $ServiceName $ContainerPort
    if ($ExistingPort -eq $PreferredPort) {
        return $PreferredPort
    }
    if (Test-CanBindPort $PreferredPort) {
        return $PreferredPort
    }

    $AllCandidates = @($PreferredPort) + $Candidates
    foreach ($Port in ($AllCandidates | Select-Object -Unique)) {
        if ($Port -eq $PreferredPort) {
            continue
        }
        if (Test-CanBindPort $Port) {
            return $Port
        }
    }

    return (Get-UsablePort $Candidates)
}

function Test-VideoOSProcess($ProcessInfo) {
    if ($ProcessInfo.ProcessId -eq $PID) {
        return $false
    }

    $ProcessName = [string]$ProcessInfo.Name
    if ($ProcessName -notmatch "python|node|electron") {
        return $false
    }

    $CommandLine = [string]$ProcessInfo.CommandLine
    if ([string]::IsNullOrWhiteSpace($CommandLine)) {
        return $false
    }

    $RootMatch = $CommandLine.IndexOf($Root, [StringComparison]::OrdinalIgnoreCase) -ge 0
    $VideoOSMatch = $CommandLine -match "app\.main:app|vite|VideoOS|electron\\main\.cjs"
    return ($RootMatch -and $VideoOSMatch)
}

function Stop-VideoOSLocalProcesses {
    $Processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { Test-VideoOSProcess $_ }

    foreach ($ProcessInfo in $Processes) {
        try {
            Stop-Process -Id $ProcessInfo.ProcessId -Force -ErrorAction Stop
            Write-Host "Processo local do Video OS finalizado: $($ProcessInfo.ProcessId)"
        }
        catch {
            Write-Host "Nao foi possivel finalizar processo local $($ProcessInfo.ProcessId)"
        }
    }
}

function Test-DockerEngine {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return $false
    }

    docker version --format "{{.Server.Version}}" *> $null
    return ($LASTEXITCODE -eq 0)
}

function Wait-DockerEngine($Seconds) {
    $Deadline = (Get-Date).AddSeconds($Seconds)
    do {
        if (Test-DockerEngine) {
            return $true
        }
        Start-Sleep -Seconds 3
    } while ((Get-Date) -lt $Deadline)

    return $false
}

function Restart-DockerDesktop {
    if (-not $AllowDockerReset) {
        Write-Host "Docker nao respondeu. Reset pesado desativado para preservar outros containers/WSL." -ForegroundColor Yellow
        Write-Host "Para permitir manutencao pesada, rode com VIDEO_OS_ALLOW_DOCKER_RESET=1." -ForegroundColor Yellow
        return
    }
    Write-Host "Docker nao respondeu. Reiniciando Docker Desktop e WSL..." -ForegroundColor Yellow
    Get-Process "Docker Desktop", "com.docker.backend", "docker", "docker-compose" -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
    wsl --shutdown *> $null
    Start-Sleep -Seconds 8

    $DockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Test-Path $DockerDesktop) {
        Start-Process -FilePath $DockerDesktop -WindowStyle Hidden
    }
}

function Docker-Ready($Seconds) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return $false
    }

    if (Test-DockerEngine) {
        return $true
    }

    $DockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Test-Path $DockerDesktop) {
        Start-Process -FilePath $DockerDesktop -WindowStyle Hidden
    }

    if (Wait-DockerEngine $Seconds) {
        return $true
    }

    if ($AllowDockerReset) {
        Restart-DockerDesktop
        return (Wait-DockerEngine 180)
    }

    return $false
}

function Stop-DockerQuiet {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return
    }
    if (-not (Test-DockerEngine)) {
        return
    }
    if (-not $ForceCleanStart) {
        Write-Host "Mantendo containers Docker existentes. Use `$env:VIDEO_OS_FORCE_CLEAN_START='1'; .\VideoOS.cmd para recriar o Video OS." -ForegroundColor DarkGray
        return
    }
    $env:COMPOSE_BAKE = "false"
    docker compose down --remove-orphans *> (Join-Path $LogDir "compose.down.log")
}

function Get-ComposePort($Service, $ContainerPort) {
    if (-not (Test-DockerEngine)) {
        return $null
    }

    $Output = & docker compose port $Service $ContainerPort 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Output)) {
        return $null
    }

    $Line = ($Output | Select-Object -First 1).Trim()
    if ($Line -match ":(\d+)$") {
        return [int]$Matches[1]
    }
    return $null
}

function Test-DockerContainerOutdated {
    param([string]$ServiceName)

    if (-not (Test-DockerEngine)) {
        return $true
    }

    $ContainerId = @(& docker compose ps -q $ServiceName 2>$null) | Select-Object -First 1
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($ContainerId)) {
        return $true
    }

    $CreatedStr = & docker inspect --format="{{.Created}}" $ContainerId 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($CreatedStr)) {
        return $true
    }

    $Created = [DateTime]::MinValue
    if (-not [DateTime]::TryParse($CreatedStr, [ref]$Created)) {
        return $true
    }
    $CreatedUtc = $Created.ToUniversalTime()

    $FilesToCheck = @(
        (Join-Path $Root ".env"),
        (Join-Path $Root "docker-compose.yml")
    )
    if ($ServiceName -eq "api" -or $ServiceName -eq "worker") {
        $FilesToCheck += (Join-Path $Root "backend\requirements.txt")
        $FilesToCheck += (Join-Path $Root "backend\app\services\social.py")
        $FilesToCheck += (Join-Path $Root "backend\Dockerfile")
    } elseif ($ServiceName -eq "web") {
        $FilesToCheck += (Join-Path $Root "frontend\src\api.ts")
        $FilesToCheck += (Join-Path $Root "frontend\src\components\CaptureDesk.tsx")
        $FilesToCheck += (Join-Path $Root "frontend\package.json")
        $FilesToCheck += (Join-Path $Root "frontend\package-lock.json")
        $FilesToCheck += (Join-Path $Root "frontend\Dockerfile")
    }

    foreach ($File in $FilesToCheck) {
        if ((Test-Path $File) -and ((Get-Item $File).LastWriteTimeUtc -gt $CreatedUtc)) {
            return $true
        }
    }

    return $false
}

function Test-ExistingDockerStack {
    param(
        [int]$ExpectedApiPort,
        [int]$ExpectedWebPort,
        [string]$ExpectedApiUrl
    )

    $ApiPort = Get-ComposePort "api" 8000
    $WebPort = Get-ComposePort "web" 5173
    if (-not $ApiPort -or -not $WebPort) {
        return $null
    }

    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:$ApiPort/api/system/health" -UseBasicParsing -TimeoutSec 3 *> $null
        Invoke-WebRequest -Uri "http://127.0.0.1:$WebPort" -UseBasicParsing -TimeoutSec 3 *> $null

        $PortAligned = ($ApiPort -eq $ExpectedApiPort -and $WebPort -eq $ExpectedWebPort)
        $WebEnvAligned = $false
        try {
            $ApiSource = (Invoke-WebRequest -Uri "http://127.0.0.1:$WebPort/src/api.ts" -UseBasicParsing -TimeoutSec 3).Content
            $WebEnvAligned = ($ApiSource -like "*$ExpectedApiUrl*")
        }
        catch {
            $WebEnvAligned = $false
        }
        if (-not $WebEnvAligned) {
            $WebContainerId = @(& docker compose ps -q web 2>$null) | Select-Object -First 1
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($WebContainerId)) {
                $WebEnvRaw = @(& docker inspect --format="{{range .Config.Env}}{{println .}}{{end}}" $WebContainerId 2>$null)
                if ($LASTEXITCODE -eq 0) {
                    $WebEnvAligned = ($WebEnvRaw -contains "VITE_API_URL=$ExpectedApiUrl")
                }
            }
        }

        $ContainersFresh = -not (
            (Test-DockerContainerOutdated "api") -or
            (Test-DockerContainerOutdated "worker") -or
            (Test-DockerContainerOutdated "web")
        )

        return @{
            ApiPort = $ApiPort
            WebPort = $WebPort
            PortAligned = $PortAligned
            WebEnvAligned = $WebEnvAligned
            ContainersFresh = $ContainersFresh
            IsCurrent = ($PortAligned -and $WebEnvAligned -and $ContainersFresh)
        }
    }
    catch {
        return $null
    }
}

function Wait-Url($Url, $Name, $Seconds) {
    Write-Host "Aguardando $Name responder..."
    $Deadline = (Get-Date).AddSeconds($Seconds)
    do {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 *> $null
            return $true
        }
        catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $Deadline)

    return $false
}

function Open-AppWindow($Url) {
    if ($NoOpenWindow) {
        Write-Host "VIDEO_OS_NO_OPEN=1 ativo. Janela nao sera aberta; URL pronta: $Url" -ForegroundColor Yellow
        return
    }

    $ElectronBin = Join-Path $Root "frontend\node_modules\.bin\electron.cmd"
    $ElectronMain = Join-Path $Root "frontend\electron\main.cjs"
    if ((-not (Test-Path $ElectronBin)) -and (Test-Path $ElectronMain) -and (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        Write-Host "Electron desktop nao encontrado no node_modules. Instalando dependencias frontend..." -ForegroundColor Yellow
        Invoke-Checked "npm.cmd" @("install", "--cache", $NpmCache, "--no-audit") (Join-Path $Root "frontend") *> $null
    }
    if ((Test-Path $ElectronBin) -and (Test-Path $ElectronMain)) {
        $env:VIDEO_OS_DESKTOP_URL = $Url
        $ElectronOut = Join-Path $LogDir "electron.desktop.log"
        $ElectronErr = Join-Path $LogDir "electron.desktop.err.log"
        Remove-Item -Force -ErrorAction SilentlyContinue $ElectronOut, $ElectronErr
        try {
            # Inicia o processo passando -PassThru para monitorar seu status
            $Proc = Start-Process -FilePath $ElectronBin `
                -ArgumentList @("electron\main.cjs", "--video-os-url=$Url") `
                -WorkingDirectory (Join-Path $Root "frontend") `
                -RedirectStandardOutput $ElectronOut `
                -RedirectStandardError $ElectronErr `
                -PassThru `
                -ErrorAction Stop
            
            # Aguarda 2 segundos para checar se o Electron permaneceu ativo
            Start-Sleep -Seconds 2
            if ($Proc.HasExited) {
                Write-Host "Electron fechou inesperadamente com codigo de saida $($Proc.ExitCode). Caindo para Edge app..." -ForegroundColor Yellow
                Write-Host "Log do Electron: $ElectronErr" -ForegroundColor Yellow
                if ((Test-Path $ElectronErr) -and ((Get-Item $ElectronErr).Length -gt 0)) {
                    Get-Content -LiteralPath $ElectronErr -Tail 8
                }
            } else {
                Write-Host "Abrindo Video OS Desktop em Electron..." -ForegroundColor Green
                Write-Host "Logs do Electron: $ElectronOut / $ElectronErr" -ForegroundColor DarkGray
                return
            }
        }
        catch {
            Write-Host "Electron nao abriu. Vou cair para Edge app." -ForegroundColor Yellow
            Write-Host "Log do Electron: $ElectronErr" -ForegroundColor Yellow
        }
    }

    $Candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
    )
    $Edge = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($Edge) {
        Start-Process -FilePath $Edge -ArgumentList @("--app=$Url", "--new-window")
        return
    }
    Start-Process $Url
}

function Prepare-Dirs {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "data") *> $null
    New-Item -ItemType Directory -Force -Path $LogDir *> $null
    New-Item -ItemType Directory -Force -Path $NpmCache *> $null
}

function Run-DockerMode {
    $Runtime = Initialize-VideoOSRuntimeEnv
    $DesiredApiPort = [int]$Runtime.ApiPort
    $DesiredWebPort = [int]$Runtime.WebPort
    $ForceRecreateDockerStack = $false

    $ApiImgStatus = Test-DockerImageOutdated "api" "sistemadeedio-api"
    $WebImgStatus = Test-DockerImageOutdated "web" "sistemadeedio-web"
    $WorkerImgStatus = Test-DockerImageOutdated "worker" "sistemadeedio-worker"
    $NeedsBuild = ($ApiImgStatus -ne "ATUALIZADA" -or $WebImgStatus -ne "ATUALIZADA" -or $WorkerImgStatus -ne "ATUALIZADA")

    if (-not $ForceCleanStart -and -not $NeedsBuild) {
        $Existing = Test-ExistingDockerStack $DesiredApiPort $DesiredWebPort $Runtime.ApiUrl
        if ($Existing -and $Existing.IsCurrent) {
            Write-Step "[4/7] Modo Docker: stack existente detectada"
            Write-Host "Video OS ja esta rodando em Docker. Nao vou reiniciar containers." -ForegroundColor Green
            Open-AppWindow "http://127.0.0.1:$($Existing.WebPort)"
            Write-Host ""
            Write-Host "Sistema aberto sem reiniciar Docker: http://127.0.0.1:$($Existing.WebPort)" -ForegroundColor Green
            Write-Host "API: http://127.0.0.1:$($Existing.ApiPort)"
            Write-Host "Para recriar apenas o Video OS: `$env:VIDEO_OS_FORCE_CLEAN_START='1'; .\VideoOS.cmd"
            return
        }
        elseif ($Existing) {
            Write-Step "[4/7] Modo Docker: stack existente defasada"
            Write-Host "Stack ativa em API $($Existing.ApiPort), Web $($Existing.WebPort), mas nao esta alinhada com a atualizacao atual." -ForegroundColor Yellow
            Write-Host "Portas esperadas: API $DesiredApiPort, Web $DesiredWebPort; VITE_API_URL esperado: $($Runtime.ApiUrl)" -ForegroundColor Yellow
            Write-Host "Portas OK: $($Existing.PortAligned); Frontend OK: $($Existing.WebEnvAligned); Containers novos: $($Existing.ContainersFresh)" -ForegroundColor DarkYellow
            $ForceRecreateDockerStack = $true
        }
    }

    Write-Step "[4/7] Modo Docker: validando Compose"
    $env:COMPOSE_BAKE = "false"
    $env:DOCKER_BUILDKIT = "0"
    $env:COMPOSE_DOCKER_CLI_BUILD = "0"
    $ApiPort = Get-PreferredPort $DesiredApiPort @(8010, 8011, 8012, 18000, 8000) "api" 8000
    $WebPort = Get-PreferredPort $DesiredWebPort @(5174, 5175, 15173, 5173) "web" 5173
    $env:VIDEO_OS_API_PORT = [string]$ApiPort
    $env:VIDEO_OS_WEB_PORT = [string]$WebPort
    $env:VITE_API_URL = "http://127.0.0.1:$ApiPort"
    $env:VIDEO_OS_CORS_ORIGINS = "http://127.0.0.1:$WebPort,http://localhost:$WebPort"
    Write-Host "Portas escolhidas: API $ApiPort, Frontend $WebPort"

    if (-not (Invoke-Checked "docker" @("compose", "config"))) {
        Fail "Falha na validacao do docker-compose.yml"
    }

    Write-Step "[5/7] Modo Docker: verificando necessidade de build"
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root "backend\.pytest_cache")
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Root "frontend\dist")

    if ($NeedsBuild) {
        Write-Host "Imagens Docker desatualizadas ou novas detectadas. Construindo..." -ForegroundColor Yellow
        if (-not (Invoke-Checked "docker" @("compose", "build", "api", "worker", "web"))) {
            Write-Host "Build Docker falhou. Vou abrir em modo local." -ForegroundColor Yellow
            Run-LocalMode
            return
        }
    } else {
        Write-Host "Imagens Docker estao atualizadas. Ignorando build (usando cache local)." -ForegroundColor Green
    }


    Write-Step "[6/7] Modo Docker: rodando verificacoes"
    if (-not (Invoke-Checked "docker" @("compose", "run", "--rm", "--no-deps", "api", "python", "-m", "pytest"))) {
        Fail "Testes do backend falharam no container."
    }
    if (-not (Invoke-Checked "docker" @("compose", "run", "--rm", "--no-deps", "web", "npm", "run", "build"))) {
        Fail "Build do frontend falhou no container."
    }

    Write-Step "[7/7] Modo Docker: subindo servicos do Video OS"
    $UpArgs = @("compose", "up", "-d", "--remove-orphans")
    if ($ForceRecreateDockerStack) {
        $UpArgs += "--force-recreate"
    }
    if (-not (Invoke-Checked "docker" $UpArgs)) {
        Write-Host "Subida Docker falhou. Vou abrir em modo local." -ForegroundColor Yellow
        Run-LocalMode
        return
    }

    if (-not (Wait-Url "http://127.0.0.1:$ApiPort/api/system/health" "API" 90)) {
        docker compose logs --tail 80 api
        Fail "API nao respondeu no modo Docker."
    }
    if (-not (Wait-Url "http://127.0.0.1:$WebPort" "Frontend" 90)) {
        docker compose logs --tail 80 web
        Fail "Frontend nao respondeu no modo Docker."
    }

    Open-AppWindow "http://127.0.0.1:$WebPort"
    Write-Host ""
    Write-Host "Sistema aberto em modo Docker: http://127.0.0.1:$WebPort" -ForegroundColor Green
    Write-Host "FFmpeg esta disponivel no container."
    Write-Host ""
    docker compose ps
    Write-Host ""
    Write-Host "Para ver logs depois: docker compose logs -f"
}

function Ensure-PythonEnv {
    Update-PythonToolPaths
    $requirementsPath = Join-Path $Root "backend\requirements.txt"
    $needsInstall = $false

    if ((-not (Test-Path $PythonExe)) -or (-not (Test-Path $PipExe))) {
        Write-Host "Criando .venv..."
        if (-not (New-VideoOSVenv $VenvPath)) {
            Fail "Nao consegui criar .venv. Instale Python 3."
        }
        Update-PythonToolPaths
        $needsInstall = $true
    } else {
        $cfgFile = Join-Path $VenvPath "pyvenv.cfg"
        if (Test-Path $cfgFile) {
            $reqTime = (Get-Item $requirementsPath).LastWriteTime
            $cfgTime = (Get-Item $cfgFile).LastWriteTime
            if ($reqTime -gt $cfgTime) {
                Write-Host "requirements.txt foi modificado. Atualizando dependencias Python..." -ForegroundColor Yellow
                $needsInstall = $true
            }
        }
    }

    if (-not $needsInstall) {
        & $PipExe show fastapi *> $null
        if ($LASTEXITCODE -ne 0) {
            $needsInstall = $true
        }
    }

    if ($needsInstall) {
        Write-Host "Instalando/Atualizando dependencias Python..."
        & $PipExe install -r $requirementsPath --cache-dir (Join-Path $Root ".pip-cache") --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org
        if ($LASTEXITCODE -ne 0) {
            Fail "Falha ao instalar dependencias Python."
        }
        if (Test-Path (Join-Path $VenvPath "pyvenv.cfg")) {
            (Get-Item (Join-Path $VenvPath "pyvenv.cfg")).LastWriteTime = Get-Date
        }
    }
}

function Ensure-FrontendEnv {
    $nodeModules = Join-Path $Root "frontend\node_modules"
    $dependencyMarker = Get-FrontendDependencyMarker
    $needsInstall = $false

    if (-not (Test-Path $nodeModules) -or -not (Test-Path (Join-Path $nodeModules "react")) -or -not (Test-Path (Join-Path $nodeModules "vite"))) {
        $needsInstall = $true
    } else {
        $modulesTime = (Get-Item $nodeModules).LastWriteTime
        $markerTime = (Get-Item $dependencyMarker).LastWriteTime
        if ($markerTime -gt $modulesTime) {
            Write-Host "Marcador de dependencias frontend modificado. Atualizando dependencias Node..." -ForegroundColor Yellow
            $needsInstall = $true
        }
    }

    if ($needsInstall) {
        Write-Host "Instalando/Atualizando dependencias frontend..."
        if (-not (Invoke-Checked "npm.cmd" @("install", "--cache", $NpmCache) (Join-Path $Root "frontend"))) {
            Fail "Falha ao instalar dependencias frontend."
        }
        if (Test-Path $nodeModules) {
            (Get-Item $nodeModules).LastWriteTime = Get-Date
        }
    }
}


function Run-LocalMode {
    Update-PythonToolPaths
    Write-Step "[4/7] Modo Local: preparando Python"
    Write-Host "OK - venv local ja garantido."

    Write-Step "[5/7] Modo Local: preparando frontend"
    Write-Host "OK - node_modules local ja garantido."

    Write-Step "[6/7] Modo Local: rodando verificacoes"
    if (Test-Path $PytestExe) {
        $pytestCommand = $PytestExe
        $pytestArgs = @()
    } else {
        $pytestCommand = $PythonExe
        $pytestArgs = @("-m", "pytest")
    }
    if (-not (Invoke-Checked $pytestCommand $pytestArgs (Join-Path $Root "backend"))) {
        Fail "Testes do backend falharam."
    }
    if (-not (Invoke-Checked "npm.cmd" @("run", "build") (Join-Path $Root "frontend"))) {
        Fail "Build do frontend falhou."
    }

    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "AVISO: FFmpeg nao esta no PATH local. Para renderizar, use Docker ou instale FFmpeg." -ForegroundColor Yellow
        Write-Host ""
    }

    Write-Step "[7/7] Modo Local: subindo API e frontend"
    Stop-VideoOSLocalProcesses
    $Runtime = Initialize-VideoOSRuntimeEnv
    $ApiPort = if (Test-CanBindPort ([int]$Runtime.ApiPort)) { [int]$Runtime.ApiPort } else { Get-UsablePort @(8010, 8011, 8012, 18000, 8000) }
    $WebPort = if (Test-CanBindPort ([int]$Runtime.WebPort)) { [int]$Runtime.WebPort } else { Get-UsablePort @(5174, 5175, 15173, 5173) }
    $env:VIDEO_OS_API_PORT = [string]$ApiPort
    $env:VIDEO_OS_WEB_PORT = [string]$WebPort
    $env:VIDEO_OS_CORS_ORIGINS = "http://127.0.0.1:$WebPort,http://localhost:$WebPort"
    $env:VITE_API_URL = "http://127.0.0.1:$ApiPort"
    Write-Host "Portas escolhidas: API $ApiPort, Frontend $WebPort"

    $ApiOut = Join-Path $LogDir "api.local.log"
    $ApiErr = Join-Path $LogDir "api.local.err.log"
    $WebOut = Join-Path $LogDir "web.local.log"
    $WebErr = Join-Path $LogDir "web.local.err.log"

    try {
        if (Test-Path $UvicornExe) {
            $apiCommand = $UvicornExe
            $apiArgs = @("app.main:app", "--host", "127.0.0.1", "--port", [string]$ApiPort)
        } else {
            $apiCommand = $PythonExe
            $apiArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", [string]$ApiPort)
        }
        Start-Process -FilePath $apiCommand `
            -ArgumentList $apiArgs `
            -WorkingDirectory (Join-Path $Root "backend") `
            -RedirectStandardOutput $ApiOut `
            -RedirectStandardError $ApiErr `
            -WindowStyle Minimized `
            -ErrorAction Stop
    }
    catch {
        Fail "Nao consegui iniciar a API local: $($_.Exception.Message)"
    }

    try {
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList @("/c", "npm.cmd run dev -- --host 127.0.0.1 --port $WebPort") `
            -WorkingDirectory (Join-Path $Root "frontend") `
            -RedirectStandardOutput $WebOut `
            -RedirectStandardError $WebErr `
            -WindowStyle Minimized `
            -ErrorAction Stop
    }
    catch {
        Fail "Nao consegui iniciar o frontend local: $($_.Exception.Message)"
    }

    if (-not (Wait-Url "http://127.0.0.1:$ApiPort/api/system/health" "API" 90)) {
        Fail "API local nao respondeu. Veja $ApiOut e $ApiErr"
    }
    if (-not (Wait-Url "http://127.0.0.1:$WebPort" "Frontend" 90)) {
        Fail "Frontend local nao respondeu. Veja $WebOut e $WebErr"
    }

    Open-AppWindow "http://127.0.0.1:$WebPort"
    Write-Host ""
    Write-Host "Sistema aberto em MODO LOCAL: http://127.0.0.1:$WebPort" -ForegroundColor Green
    Write-Host "API log: $ApiOut"
    Write-Host "Web log: $WebOut"
    Read-Host "Pressione ENTER para sair"
}

Clear-Host
Normalize-ProcessEnvironment
Initialize-VideoOSRuntimeEnv *> $null
Write-Host ""
Write-Host "=========================================="
Write-Host "  Video OS - Sistema de Edicao em Massa"
Write-Host "=========================================="
Write-Host ""

Invoke-PreFlightAudit

if ($PreflightOnly) {
    Write-Host "VIDEO_OS_PREFLIGHT_ONLY=1 ativo. Diagnostico concluido sem iniciar servicos." -ForegroundColor Yellow
    exit 0
}

Prepare-Dirs


Write-Step "[1/7] Verificando arquivos obrigatorios e ambiente local"
Require-File "docker-compose.yml"
Require-File "backend\requirements.txt"
Require-File "backend\app\main.py"
Require-File "frontend\package.json"
Require-File "frontend\src\App.tsx"
Write-Host "OK - estrutura principal encontrada."

Write-Host "Garantindo dependencias Python local..." -ForegroundColor Cyan
Ensure-PythonEnv
Write-Host "Garantindo dependencias Node local..." -ForegroundColor Cyan
Ensure-FrontendEnv

Write-Step "[2/7] Finalizando servicos antigos"
Stop-DockerQuiet
Stop-VideoOSLocalProcesses
Write-Host "OK - somente processos do Video OS foram tratados."

Write-Step "[3/7] Escolhendo modo de execucao"
Write-Host "Aguardando Docker Desktop por ate 2 minutos quando necessario..."
if (Docker-Ready 120) {
    Write-Host "Docker pronto. Vou iniciar em modo Docker." -ForegroundColor Green
    Run-DockerMode
}
else {
    Write-Host "Docker nao respondeu. Vou abrir em modo local para voce conseguir usar a interface." -ForegroundColor Yellow
    Run-LocalMode
}
