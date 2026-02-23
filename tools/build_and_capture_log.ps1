# Run Unreal build and save full output to a log file so we can see the actual error.
# Usage: run from project root, or pass path to .uproject:
#   .\build_and_capture_log.ps1 "G:\ESC_Germany_Selection\sandbox5_7\sandbox5_7\sandbox5_7.uproject"

param(
    [string]$ProjectPath = "G:\ESC_Germany_Selection\sandbox5_7\sandbox5_7\sandbox5_7.uproject"
)

$uePath = "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat"
$projectDir = Split-Path -Parent $ProjectPath
$projectName = [System.IO.Path]::GetFileNameWithoutExtension($ProjectPath)
$logFile = Join-Path $projectDir "build_log.txt"

Write-Host "Building $projectName - full output -> $logFile"
& $uePath "${projectName}Editor" Win64 Development -Project="$ProjectPath" -WaitMutex -architecture=x64 2>&1 | Tee-Object -FilePath $logFile
Write-Host "Build finished. Check $logFile for errors (search for 'error ')."
