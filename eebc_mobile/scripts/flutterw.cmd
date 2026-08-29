@echo off
set FLUTTER_ROOT=%USERPROFILE%\dev\flutter
set FLUTTER_BIN=%FLUTTER_ROOT%\bin

if not exist "%FLUTTER_BIN%\flutter.bat" (
  echo Flutter introuvable: %FLUTTER_BIN%\flutter.bat
  exit /b 1
)

set PATH=%FLUTTER_BIN%;%PATH%
call "%FLUTTER_BIN%\flutter.bat" %*
