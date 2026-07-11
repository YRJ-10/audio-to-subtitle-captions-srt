@echo off
setlocal
cd /d "%~dp0"

echo Audio to Subtitle - Launcher
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
        set "PYTHON_CMD=%LocalAppData%\Programs\Python\Python313\python.exe"
    )
)

if not defined PYTHON_CMD (
    echo Python tidak ditemukan.
    echo Install Python 3.10 atau lebih baru, lalu jalankan file ini lagi.
    echo.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo File requirements.txt tidak ditemukan.
    echo Pastikan launcher dijalankan dari folder aplikasi.
    echo.
    pause
    exit /b 1
)

echo Memastikan library Python sudah tersedia...
"%PYTHON_CMD%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Gagal menginstal library Python.
    echo Periksa koneksi internet dan instalasi Python, lalu coba lagi.
    echo.
    pause
    exit /b 1
)

echo.
echo Mengecek FFmpeg...
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo FFmpeg belum ditemukan di PATH.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo Winget juga tidak ditemukan. Install FFmpeg manual, lalu buka aplikasi lagi.
        echo.
        pause
        exit /b 1
    )

    choice /M "Install FFmpeg dengan winget sekarang"
    if errorlevel 2 (
        echo Instalasi FFmpeg dibatalkan.
        echo.
        pause
        exit /b 1
    )

    winget install gyan.ffmpeg -e --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo.
        echo Gagal menginstal FFmpeg.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Membuka aplikasi...
start "" "%PYTHON_CMD%" "%~dp0app.py"
endlocal
