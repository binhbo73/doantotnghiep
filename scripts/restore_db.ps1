<#
Simple PostgreSQL restore script for Windows PowerShell.
Usage:
  .\restore_db.ps1 [-EnvFile pathToEnv] [-DumpFile path]

Behavior:
  - Loads DB credentials from an env file (default: backend/.env.local then backend/.env)
  - Prompts for dump file if not provided (defaults to latest in backups/)
  - Uses `pg_restore` to restore the custom-format dump into the configured DB
  - After restore, optionally runs Django `dumpdata` to show the restored content

Security / safety:
  - Do NOT run this against production DB without a verified plan. Prefer restoring into a staging or local DB first.
#>

param(
    [string]$EnvFile = "backend/.env.local",
    [string]$DumpFile = ""
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

if (-not (Get-Command pg_restore -ErrorAction SilentlyContinue)) {
    Write-Error "pg_restore not found in PATH. Install PostgreSQL client tools and ensure pg_restore is in PATH."
    exit 1
}

if (-not $DumpFile -or -not (Test-Path $DumpFile)) {
    $backups = Get-ChildItem -Path backups -Filter "*.dump" -File | Sort-Object LastWriteTime -Descending
    if ($backups.Count -eq 0) { Write-Error "No dump files found in backups/ and no DumpFile provided."; exit 1 }
    Write-Host "Available dumps (newest first):"
    $i = 0
    $backups | ForEach-Object { $i++; Write-Host "$i) $($_.FullName)" }
    $choice = Read-Host "Enter number to restore (default 1)"
    if (-not $choice) { $choice = 1 }
    $sel = $backups[[int]$choice - 1]
    $DumpFile = $sel.FullName
}

Write-Host "Restoring $DumpFile into database $DB_NAME ..."

$timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$logfile = "backups/restore_$timestamp.log"

$origEnv = $env:PGPASSWORD
try {
    if ($DB_PASS) { $env:PGPASSWORD = $DB_PASS }
    # Restore note:
    #   - The safe test restore done in this workspace was executed inside the Docker container `rag_postgres`.
    #   - `restore_test_YYYYMMDD_HHMMSS` is a temporary database name used only for validation, not a backup file.
    Write-Host "Restore log: $logfile"
    & pg_restore --clean --no-owner -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME $DumpFile 2>&1 | Tee-Object -FilePath $logfile -Append
    if ($LASTEXITCODE -ne 0) { throw "pg_restore failed with exit code $LASTEXITCODE" }
    Write-Host "Restore completed."
} catch {
    Write-Error "Restore error: $_"
} finally {
    if ($null -ne $origEnv) { $env:PGPASSWORD = $origEnv } else { Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue }
}

# Optionally run Django dumpdata to show restored content
if (Test-Path "backend/manage.py") {
    Write-Host "Running Django dumpdata to generate restored_snapshot.json (this may take time)..."
    & python backend/manage.py dumpdata --indent 2 > restored_snapshot.json
    if ($LASTEXITCODE -eq 0) { Write-Host "Wrote restored_snapshot.json" } else { Write-Warning "dumpdata returned exit code $LASTEXITCODE" }
}

Write-Host "Done. Verify data carefully before re-enabling production traffic."
