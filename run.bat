@echo off
cd "%~dp0"
title Hand Gesture Control

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [HGC] Python not found. Installing...
    powershell -Command "& { $url='https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe'; $out=$env:TEMP+'\python-installer.exe'; Write-Host '  Downloading...'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile($url,$out); Write-Host '  Installing...'; Start-Process -FilePath $out -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_test=0' -Wait }"
    for %%i in (python.exe) do set PYTHONPATH=%%~$PATH:i
    echo [HGC] Python installed.
)

pip install opencv-python pyautogui numpy mediapipe comtypes pycaw --quiet 2>nul

echo [HGC] Dependencies ready.
echo.
python main.py
pause
