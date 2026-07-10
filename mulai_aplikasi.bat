@echo off
echo Menginstal library Python yang dibutuhkan (Whisper AI & CustomTkinter)...
py -m pip install openai-whisper customtkinter

echo.
echo Memastikan FFmpeg terinstall di Windows (Dibutuhkan untuk memproses Audio)...
winget install gyan.ffmpeg -e --accept-package-agreements --accept-source-agreements

echo.
echo Membuka Aplikasi (Layar terminal ini akan tertutup dan UI modern akan muncul)...
start pyw app.py
exit
