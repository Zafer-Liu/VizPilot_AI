@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"
if errorlevel 1 (
  echo [ERROR] Failed to cd to script directory: "%~dp0"
  pause
  exit /b 1
)

set "APP_FILE=app_pro.py"
set "VENV_DIR=.venv"
set "USE_VENV=1"
set "PORT=5017"
set "PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"

set "PY_CMD="
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 --version >nul 2>&1
  if %errorlevel%==0 set "PY_CMD=py -3"
)

if not defined PY_CMD (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.8+ first.
    pause
    exit /b 1
  )
  set "PY_CMD=python"
)

echo [INFO] Python command: %PY_CMD%
%PY_CMD% --version
if errorlevel 1 (
  echo [ERROR] Python launcher found but not runnable.
  pause
  exit /b 1
)

if "%USE_VENV%"=="1" (
  if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Creating venv...
    %PY_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
      echo [ERROR] Failed to create venv.
      pause
      exit /b 1
    )
  )
  call "%VENV_DIR%\Scripts\activate.bat"
  if errorlevel 1 (
    echo [ERROR] Failed to activate venv.
    pause
    exit /b 1
  )
  set "PY_CMD=python"
)

%PY_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] pip not available.
  pause
  exit /b 1
)

echo [INFO] Upgrading pip...
%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 (
  echo [WARN] Retry pip upgrade with mirror...
  %PY_CMD% -m pip install --upgrade pip -i %PIP_MIRROR%
  if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
  )
)

if exist requirements.txt (
  echo [INFO] Installing requirements...
  %PY_CMD% -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [WARN] Retry requirements with mirror...
    %PY_CMD% -m pip install -r requirements.txt -i %PIP_MIRROR%
    if errorlevel 1 (
      echo [ERROR] Failed to install requirements.
      pause
      exit /b 1
    )
  )
) else (
  echo [INFO] requirements.txt not found, install fallback packages...
  %PY_CMD% -m pip install flask flask-cors pandas numpy openpyxl xlrd plotly matplotlib requests openai waitress
  if errorlevel 1 (
    echo [WARN] Retry fallback with mirror...
    %PY_CMD% -m pip install flask flask-cors pandas numpy openpyxl xlrd plotly matplotlib requests openai waitress -i %PIP_MIRROR%
    if errorlevel 1 (
      echo [ERROR] Failed to install fallback packages.
      pause
      exit /b 1
    )
  )
)

if not exist "%APP_FILE%" (
  echo [ERROR] Entry file not found: %APP_FILE%
  pause
  exit /b 1
)

set "PORT_IN_USE="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do (
  set "PORT_IN_USE=1"
  set "PORT_PID=%%a"
)

if defined PORT_IN_USE (
  echo [ERROR] Port %PORT% is in use. PID=!PORT_PID!
  echo [TIP] tasklist /fi "PID eq !PORT_PID!"
  pause
  exit /b 1
)

echo [INFO] Starting app at http://localhost:%PORT%
%PY_CMD% "%APP_FILE%"
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" echo [ERROR] App exited with code %ERR%
pause
exit /b %ERR%
