# ============================================================
#  ATLAS — Full Stack Launcher
#  Opens each service in its own Windows Terminal tab.
#  Run from the repo root: .\start_atlas.ps1
# ============================================================

param(
    [switch]$Demo,          # also open fault script terminals
    [switch]$Replay,        # use --replay flag on fault scripts (instant, no sleep)
    [string]$BackendPort = "8000",
    [string]$FrontendPort = "5173"
)

$Root = $PSScriptRoot

# ── Colour helpers ────────────────────────────────────────────────────────────
function Write-Header($text) {
    Write-Host ""
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "  $('─' * ($text.Length))" -ForegroundColor DarkCyan
}

function Write-Step($label, $value) {
    Write-Host "  " -NoNewline
    Write-Host $label.PadRight(22) -ForegroundColor DarkGray -NoNewline
    Write-Host $value -ForegroundColor White
}

function Write-Ok($text)   { Write-Host "  ✓ $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "  ⚠ $text" -ForegroundColor Yellow }
function Write-Err($text)  { Write-Host "  ✗ $text" -ForegroundColor Red }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
Write-Header "ATLAS Pre-flight Checks"

# Python
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.(1[1-9]|[2-9]\d)") {
            $python = $cmd
            Write-Ok "Python  → $ver ($cmd)"
            break
        }
    } catch {}
}
if (-not $python) {
    Write-Err "Python 3.11+ not found. Install from https://python.org"
    exit 1
}

# Node / npm
try {
    $nodeVer = node --version 2>&1
    Write-Ok "Node.js → $nodeVer"
} catch {
    Write-Err "Node.js not found. Install from https://nodejs.org"
    exit 1
}

# .env
if (-not (Test-Path "$Root\.env")) {
    Write-Err ".env not found at repo root. Copy .env.example and fill in values."
    exit 1
}
Write-Ok ".env    → found"

# ui/node_modules
if (-not (Test-Path "$Root\ui\node_modules")) {
    Write-Warn "ui/node_modules missing — running npm install..."
    Push-Location "$Root\ui"
    npm install --silent
    Pop-Location
    Write-Ok "npm install complete"
}

# ── Detect terminal launcher ──────────────────────────────────────────────────
$wtAvailable = $null -ne (Get-Command "wt" -ErrorAction SilentlyContinue)
$wtAvailable = $wtAvailable -and (wt --version 2>&1) -notmatch "not recognized"

# ── Build tab commands ────────────────────────────────────────────────────────
# Each entry: [Title, WorkingDir, Command]
$tabs = [System.Collections.Generic.List[hashtable]]::new()

$tabs.Add(@{
    Title = "ATLAS Backend"
    Dir   = $Root
    Cmd   = "$python -m uvicorn backend.main:app --host 0.0.0.0 --port $BackendPort --reload --log-level info"
    Color = "oneHalfDark"
})

$tabs.Add(@{
    Title = "Mock PaymentAPI"
    Dir   = $Root
    Cmd   = "$python data/mock_services/mock_payment_api.py"
    Color = "oneHalfDark"
})

$tabs.Add(@{
    Title = "ATLAS Frontend"
    Dir   = "$Root\ui"
    Cmd   = "npm run dev -- --port $FrontendPort"
    Color = "oneHalfDark"
})

if ($Demo) {
    $replayFlag = if ($Replay) { " --replay" } else { "" }

    $tabs.Add(@{
        Title = "Fault: FinanceCore"
        Dir   = $Root
        Cmd   = "$python data/fault_scripts/financecore_cascade.py$replayFlag"
        Color = "oneHalfDark"
    })

    $tabs.Add(@{
        Title = "Fault: RetailMax"
        Dir   = $Root
        Cmd   = "$python data/fault_scripts/retailmax_redis_oom.py$replayFlag"
        Color = "oneHalfDark"
    })
}

# ── Launch ────────────────────────────────────────────────────────────────────
Write-Header "Launching Services"

if ($wtAvailable) {
    # Windows Terminal — all tabs in one window
    Write-Ok "Windows Terminal detected — opening tabbed session"

    # Build wt argument string — semicolons must be literal in the argument list
    $wtParts = @()
    $wtParts += "new-tab --title `"$($tabs[0].Title)`" --startingDirectory `"$($tabs[0].Dir)`" powershell -NoExit -Command `"$($tabs[0].Cmd -replace '"','\"')`""

    for ($i = 1; $i -lt $tabs.Count; $i++) {
        $t = $tabs[$i]
        $wtParts += "; new-tab --title `"$($t.Title)`" --startingDirectory `"$($t.Dir)`" powershell -NoExit -Command `"$($t.Cmd -replace '"','\"')`""
    }

    $wtArgString = $wtParts -join " "
    Start-Process "wt" -ArgumentList $wtArgString
} else {
    # Fallback — separate PowerShell windows
    Write-Warn "Windows Terminal not found — opening separate PowerShell windows"

    foreach ($t in $tabs) {
        $escapedCmd = $t.Cmd -replace '"', '\"'
        Start-Process powershell -ArgumentList @(
            "-NoExit",
            "-Command",
            "Set-Location '$($t.Dir)'; `$host.UI.RawUI.WindowTitle = '$($t.Title)'; $escapedCmd"
        )
        Start-Sleep -Milliseconds 300
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Header "ATLAS is starting"
Write-Step "Backend API"    "http://localhost:$BackendPort"
Write-Step "API Docs"       "http://localhost:$BackendPort/docs"
Write-Step "Frontend"       "http://localhost:$FrontendPort"
Write-Step "Mock PaymentAPI" "http://localhost:8001/actuator/health"
Write-Step "WebSocket logs" "ws://localhost:$BackendPort/ws/logs/FINCORE_UK_001"
Write-Step "WebSocket inc." "ws://localhost:$BackendPort/ws/incidents/FINCORE_UK_001"
Write-Step "WebSocket act." "ws://localhost:$BackendPort/ws/activity"

if ($Demo) {
    Write-Host ""
    Write-Warn "Demo mode: fault scripts will start immediately."
    Write-Warn "Wait ~30s for backend to be ready before fault scripts fire."
}

Write-Host ""
Write-Host "  Usage:" -ForegroundColor DarkGray
Write-Host "    .\start_atlas.ps1              # backend + mock + frontend" -ForegroundColor DarkGray
Write-Host "    .\start_atlas.ps1 -Demo        # + fault scripts (real-time)" -ForegroundColor DarkGray
Write-Host "    .\start_atlas.ps1 -Demo -Replay # + fault scripts (instant)" -ForegroundColor DarkGray
Write-Host ""
