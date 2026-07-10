@echo off
echo Menginstal library Python yang dibutuhkan (Whisper AI)...
pip install openai-whisper

echo.
echo Memastikan FFmpeg terinstall di Windows (Dibutuhkan untuk memproses Audio)...
winget install gyan.ffmpeg -e --accept-package-agreements --accept-source-agreements

echo.
echo Membuka Aplikasi...
python app.py
pause
