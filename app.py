import customtkinter as ctk
from tkinter import filedialog, messagebox
import whisper
import threading
import os
import shutil

# Konfigurasi Tampilan Modern
ctk.set_appearance_mode("System")  # Mengikuti tema Windows (Gelap/Terang)
ctk.set_default_color_theme("blue")

def format_timestamp(seconds: float):
    milliseconds = round(seconds * 1000.0)
    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000
    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000
    secs = milliseconds // 1_000
    milliseconds -= secs * 1_000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

class SubtitleApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Audio to Subtitle (Indonesian)")
        self.geometry("500x320")
        self.resizable(False, False)
        
        # Frame Kontainer Utama
        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        # Judul Aplikasi
        self.label = ctk.CTkLabel(self.frame, text="Konversi Audio/Video ke Subtitle", font=ctk.CTkFont(size=18, weight="bold"))
        self.label.pack(pady=(20, 10))
        
        # Tombol Pilih File (Desain Modern)
        self.btn_select = ctk.CTkButton(self.frame, text="Pilih File & Proses", command=self.process_file, height=45, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=10)
        self.btn_select.pack(pady=15)
        
        # Progress Bar Animasi
        self.progress = ctk.CTkProgressBar(self.frame, mode="indeterminate", width=350)
        self.progress.pack(pady=10)
        self.progress.set(0) # Sembunyikan pergerakan di awal
        
        # Status Label
        self.status = ctk.CTkLabel(self.frame, text="Status: Menunggu file...", font=ctk.CTkFont(size=12))
        self.status.pack(pady=(5, 20))
        
        self.model = None
        self.is_processing = False
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def process_file(self):
        if self.is_processing:
            messagebox.showinfo("Sedang Diproses", "Tunggu proses saat ini selesai dulu.")
            return

        filepath = filedialog.askopenfilename(
            title="Pilih File",
            filetypes=(("Media Files", "*.mp3 *.wav *.m4a *.mp4 *.mkv"), ("All Files", "*.*"))
        )
        if not filepath:
            return

        if shutil.which("ffmpeg") is None:
            messagebox.showerror(
                "FFmpeg Tidak Ditemukan",
                "FFmpeg belum tersedia di Windows PATH.\n\n"
                "Jalankan mulai_aplikasi.bat atau install FFmpeg dulu, lalu buka aplikasi lagi."
            )
            return

        # Mengubah UI saat sedang proses
        self.is_processing = True
        self.btn_select.configure(state="disabled")
        self.status.configure(text="Status: Memuat AI model... proses pertama bisa agak lama.", text_color="orange")
        self.progress.start() # Jalankan animasi progress bar
        
        # Jalankan di background agar UI tidak macet
        threading.Thread(target=self.transcribe_worker, args=(filepath,), daemon=True).start()
        
    def transcribe_worker(self, filepath):
        try:
            if self.model is None:
                self.model = whisper.load_model("base")

            self.set_status("Status: Sedang memproses suara... jangan tutup aplikasi dulu.", "#1E90FF")
            
            result = self.model.transcribe(filepath, language="id", word_timestamps=True)
            
            output_dir = os.path.dirname(filepath)
            filename = os.path.splitext(os.path.basename(filepath))[0]
            srt_path = os.path.join(output_dir, f"{filename}.srt")
            
            with open(srt_path, "w", encoding="utf-8") as f:
                segment_id = 1
                for seg in result["segments"]:
                    words = seg.get("words", [])
                    if not words:
                        start = format_timestamp(seg['start'])
                        end = format_timestamp(seg['end'])
                        text = seg['text'].strip()
                        f.write(f"{segment_id}\n{start} --> {end}\n{text}\n\n")
                        segment_id += 1
                        continue
                        
                    chunk_words = []
                    chunk_start = words[0]['start']
                    
                    for i, w in enumerate(words):
                        chunk_words.append(w['word'].strip())
                        
                        if len(chunk_words) >= 6 or i == len(words) - 1:
                            start = format_timestamp(chunk_start)
                            end = format_timestamp(w['end'])
                            text = " ".join(chunk_words)
                            f.write(f"{segment_id}\n{start} --> {end}\n{text}\n\n")
                            segment_id += 1
                            chunk_words = []
                            if i < len(words) - 1:
                                chunk_start = words[i+1]['start']
            
            self.finish_success(filename, srt_path)
            
        except Exception as e:
            self.finish_error(e)

    def set_status(self, text, color):
        self.after(0, lambda: self.status.configure(text=text, text_color=color))

    def reset_processing_ui(self):
        self.is_processing = False
        self.btn_select.configure(state="normal")
        self.progress.stop()
        self.progress.set(0)

    def finish_success(self, filename, srt_path):
        def update_ui():
            self.status.configure(text=f"Selesai! Disimpan sebagai: {filename}.srt", text_color="green")
            self.reset_processing_ui()
            messagebox.showinfo("Sukses", f"Subtitle berhasil dibuat dan disimpan di:\n\n{srt_path}")

        self.after(0, update_ui)

    def finish_error(self, error):
        error_text = str(error).strip() or error.__class__.__name__

        def update_ui():
            self.status.configure(text="Status: Gagal memproses file.", text_color="red")
            self.reset_processing_ui()
            messagebox.showerror(
                "Error",
                "Gagal memproses file.\n\n"
                "Coba pastikan file media bisa dibuka, FFmpeg sudah terpasang, "
                "dan ruang penyimpanan masih cukup.\n\n"
                f"Detail:\n{error_text}"
            )

        self.after(0, update_ui)

    def on_close(self):
        if self.is_processing:
            should_close = messagebox.askyesno(
                "Proses Masih Berjalan",
                "Transkripsi masih berjalan. Kalau aplikasi ditutup sekarang, proses akan dibatalkan.\n\n"
                "Tetap tutup aplikasi?"
            )
            if not should_close:
                return

        self.destroy()

if __name__ == "__main__":
    app = SubtitleApp()
    app.mainloop()
