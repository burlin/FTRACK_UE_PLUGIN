@echo off
REM Build Unreal project and save full output to build_log.txt in the PROJECT folder.
REM Edit PROJECT_DIR and UPROJECT below to match your project, then run this batch from anywhere.
REM Or run from project folder: build_and_save_log.bat "G:\path\to\project.uproject"

set "PROJECT_DIR=G:\ESC_Germany_Selection\sandbox5_7\sandbox5_7"
set "UPROJECT=%PROJECT_DIR%\sandbox5_7.uproject"
set "PROJECT_NAME=sandbox5_7"
if not "%~1"=="" (
  set "UPROJECT=%~1"
  set "PROJECT_DIR=%~dp1"
  set "PROJECT_NAME=%~n1"
)
set "LOG=%PROJECT_DIR%\build_log.txt"

set "BUILD_BAT=C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat"
echo Building and logging to %LOG%
call "%BUILD_BAT%" %PROJECT_NAME%Editor Win64 Development -Project="%UPROJECT%" -WaitMutex -architecture=x64 > "%LOG%" 2>&1
echo Done. Open %LOG% and search for "error " to see the first compile error.
