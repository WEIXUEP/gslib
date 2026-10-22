@echo off
setlocal
set "GENERATOR=NMake Makefiles JOM"
set "BUILD_NAME=msvc-jom"
if /i "%~1"=="nmake" (
  set "GENERATOR=NMake Makefiles"
  set "BUILD_NAME=msvc-nmake"
) else if not "%~1"=="" if /i not "%~1"=="jom" (
  echo Usage: %~nx0 [jom^|nmake] [ON^|OFF]
  exit /b 1
)

set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
  echo Visual Studio Installer was not found.
  exit /b 1
)
for /f "usebackq delims=" %%I in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VS_DIR=%%I"
if not defined VS_DIR (
  echo Install the Visual Studio C++ build tools.
  exit /b 1
)
call "%VS_DIR%\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
if errorlevel 1 exit /b 1
set "PATH=%VS_DIR%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%PATH%"

where cmake >nul 2>nul
if errorlevel 1 (
  echo Install CMake or enable the Visual Studio CMake tools component.
  exit /b 1
)
if "%BUILD_NAME%"=="msvc-jom" (
  where jom >nul 2>nul
  if errorlevel 1 (
    echo Add jom.exe to PATH or use: %~nx0 nmake
    exit /b 1
  )
)

for %%I in ("%~dp0..") do set "SOURCE_DIR=%%~fI"
set "BUILD_DIR=%SOURCE_DIR%\build\%BUILD_NAME%"
if "%~2"=="" (
  if not defined GSLIB_CODE_PROTETION set "GSLIB_CODE_PROTETION=OFF"
) else (
  set "GSLIB_CODE_PROTETION=%~2"
)
cmake -S "%SOURCE_DIR%" -B "%BUILD_DIR%" -G "%GENERATOR%" -DCMAKE_C_COMPILER=cl -DCMAKE_BUILD_TYPE=Release -DMPI=ON -DNBC=ON -DBUILD_TESTING=ON -DGSLIB_CODE_PROTETION=%GSLIB_CODE_PROTETION% -DCMAKE_INSTALL_PREFIX="%BUILD_DIR%/install"
if errorlevel 1 exit /b 1
if "%BUILD_NAME%"=="msvc-jom" (
  cmake --build "%BUILD_DIR%" --parallel
) else (
  cmake --build "%BUILD_DIR%"
)
if errorlevel 1 exit /b 1
ctest --test-dir "%BUILD_DIR%" --output-on-failure
if errorlevel 1 exit /b 1
cmake --install "%BUILD_DIR%"
exit /b %errorlevel%
