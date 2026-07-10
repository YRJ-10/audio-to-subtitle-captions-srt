import tkinter as tk
from tkinter import filedialog, messagebox
import whisper
import threading
import os

def format_timestamp(seconds: float):
    milliseconds = round(seconds * 1000.0)
    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000
    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000
    secs = milliseconds // 1_000
    milliseconds -= secs * 1_000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

class SubtitleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio to Subtitle (Indonesian)")
        self.root.geometry("450x250")
        
        self.label = tk.Label(root, text="Pilih file audio/video untuk dikonversi ke .srt", font=("Arial", 12))
        self.label.pack(pady=20)
        
        self.btn_select = tk.Button(root, text="Pilih File & Proses", command=self.process_file, width=20, height=2, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_select.pack(pady=10)
        
        self.status = tk.Label(root, text="Status: Menunggu file...", fg="blue", font=("Arial", 10))
        self.status.pack(pady=20)
        
        self.model = None

    def process_file(self):
        filepath = filedialog.askopenfilename(
            title="Pilih File",
            filetypes=(("Media Files", "*.mp3 *.wav *.m4a *.mp4 *.mkv"), ("All Files", "*.*"))
        )
        if not filepath:
            return
            
        self.btn_select.config(state=tk.DISABLED)
        self.status.config(text="Status: Memuat AI Model... (Hanya butuh waktu agak lama di awal)")
        
        threading.Thread(target=self.transcribe, args=(filepath,), daemon=True).start()
        
    def transcribe(self, filepath):
        try:
            if self.model is None:
                # Menggunakan model 'base' (jauh lebih ringan dan sangat cepat untuk CPU)
                self.model = whisper.load_model("base")
                
            self.status.config(text="Status: Sedang mengenali suara dan membuat subtitle...")
            
            # Transcribe khusus bahasa Indonesia
            result = self.model.transcribe(filepath, language="id")
            
            # Buat file .srt
            output_dir = os.path.dirname(filepath)
            filename = os.path.splitext(os.path.basename(filepath))[0]
            srt_path = os.path.join(output_dir, f"{filename}.srt")
            
            with open(srt_path, "w", encoding="utf-8") as f:
                for i, segment in enumerate(result["segments"], start=1):
                    start = format_timestamp(segment['start'])
                    end = format_timestamp(segment['end'])
                    text = segment['text'].strip()
                    f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
            
            self.status.config(text=f"Selesai! Disimpan sebagai: {filename}.srt")
            messagebox.showinfo("Sukses", f"Subtitle berhasil dibuat dan disimpan di folder yang sama:\n\n{srt_path}")
            
        except Exception as e:
            self.status.config(text="Status: Terjadi kesalahan!")
            messagebox.showerror("Error", f"Gagal memproses. Pastikan FFmpeg terinstall.\nDetail:\n{str(e)}")
        finally:
            self.btn_select.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = SubtitleApp(root)
    root.mainloop()
