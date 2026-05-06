<#
Simple PostgreSQL backup script for Windows PowerShell.
Usage:
  .\backup_db.ps1 [-EnvFile pathToEnv] [-OutDir path]

Behavior:
  - Loads DB credentials from an env file (default: backend/.env.local then backend/.env)
  - Uses `pg_dump` to create a compressed custom-format dump (.dump)
  - Ensures `PGPASSWORD` is set only for the duration of the command

Security notes:
  - Keep created dump files in a secure location with restricted permissions.
  - Prefer restoring to a non-production DB for verification before overwriting production.
#>

param(
    [string]$EnvFile = "backend/.env.local",
    [string]$OutDir = "backups",
    [ValidateSet("custom","plain")][string]$Format = "custom",
    [int]$KeepDays = 30,
    [string[]]$Databases = @()
)

function Load-EnvFile($path){
    $env = @{}
    if (-not (Test-Path $path)) { return $env }
    foreach ($line in Get-Content $path) {
        if ($line -match "^\s*#" -or $line -match "^\s*$") { continue }
        $parts = $line -split "=",2
        if ($parts.Count -eq 2) {
            $key = $parts[0].Trim()
            $val = $parts[1].Trim(' "')
            $env[$key] = $val
        }
    }
    return $env
}

function Get-FirstValue([string[]]$values, [string]$defaultValue) {
    foreach ($value in $values) {
        if ($null -ne $value -and $value.ToString().Trim() -ne "") {
            return $value
        }
    }
    return $defaultValue
}

# Fallback to backend/.env if .env.local missing
if (-not (Test-Path $EnvFile)) {
    $fallback = "backend/.env"
    if (Test-Path $fallback) { $EnvFile = $fallback }
}

$vars = Load-EnvFile $EnvFile

$DB_NAME = Get-FirstValue @($vars.POSTGRES_DB, $env:POSTGRES_DB) "rag_system"
$DB_USER = Get-FirstValue @($vars.POSTGRES_USER, $env:POSTGRES_USER) "postgres"
$DB_PASS = Get-FirstValue @($vars.POSTGRES_PASSWORD, $env:POSTGRES_PASSWORD) "postgres"
$DB_HOST = Get-FirstValue @($vars.POSTGRES_HOST, $env:POSTGRES_HOST) "localhost"
$DB_PORT = Get-FirstValue @($vars.POSTGRES_PORT, $env:POSTGRES_PORT) "5432"

if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "pg_dump not found in PATH and Docker is not available. Install PostgreSQL client tools or start Docker."
        exit 1
    }
}

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

function Get-FormatSwitch($fmt){
    switch ($fmt) {
        "custom" { return "-Fc" }
        "plain"  { return "-Fp" }
        default   { return "-Fc" }
    }
}

$timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$logfile = Join-Path $OutDir "backup_$timestamp.log"

if ($Databases.Count -gt 0) { $targets = $Databases } else { $targets = @($DB_NAME) }

Write-Host "Backup log: $logfile"

$origEnv = $env:PGPASSWORD
try {
    foreach ($target in $targets) {
        $outfile = Join-Path $OutDir "$($target)_$timestamp.dump"
        $fmtSwitch = Get-FormatSwitch $Format
        Write-Host "Backing up database $target to $outfile ..."

        try {
            if (Get-Command pg_dump -ErrorAction SilentlyContinue) {
                if ($DB_PASS) { $env:PGPASSWORD = $DB_PASS }
                $args = @($fmtSwitch, '-h', $DB_HOST, '-p', $DB_PORT, '-U', $DB_USER, '-d', $target, '-f', $outfile)
                & pg_dump @args 2>&1 | Tee-Object -FilePath $logfile -Append
                if ($LASTEXITCODE -ne 0) { throw "pg_dump failed for $target with exit code $LASTEXITCODE" }
            } else {
                $dockerArgs = @(
                    'compose','exec','-T'
                )
                if ($DB_PASS) {
                    $dockerArgs += @('-e', "PGPASSWORD=$DB_PASS")
                }
                $dockerArgs += @('postgres','pg_dump',$fmtSwitch,'-U',$DB_USER,'-d',$target)

                $stderrLog = Join-Path $OutDir "$($target)_$timestamp.err.log"
                $process = Start-Process -FilePath 'docker' -ArgumentList $dockerArgs -NoNewWindow -Wait -PassThru -RedirectStandardOutput $outfile -RedirectStandardError $stderrLog
                if ($process.ExitCode -ne 0) { throw "docker compose exec pg_dump failed for $target with exit code $($process.ExitCode). See $stderrLog" }
            }
            Write-Host "Backup completed: $outfile"
        } catch {
            Write-Error "Error backing up ${target}: $_"
        }
        # Restrict file permissions (best-effort on Windows)
        try {
            $acl = Get-Acl $outfile
            $acl.SetAccessRuleProtection($true, $false)
            Set-Acl -Path $outfile -AclObject $acl
        } catch { }
    }
} finally {
    if ($null -ne $origEnv) { $env:PGPASSWORD = $origEnv } else { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
}

# Cleanup old backups
try {
    if ($KeepDays -gt 0) {
        $cutoff = (Get-Date).AddDays(-1 * $KeepDays)
        Get-ChildItem -Path $OutDir -Filter "*.dump" -File | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
            Write-Host "Removing old backup: $($_.FullName)"
            Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
        }
    }
} catch { }

Write-Host "Done. Keep this file secure."
