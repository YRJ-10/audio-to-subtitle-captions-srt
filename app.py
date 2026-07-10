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
            
            # Transcribe dengan word_timestamps agar bisa dipisah lebih pendek
            result = self.model.transcribe(filepath, language="id", word_timestamps=True)
            
            # Buat file .srt
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
                        
                    # Memecah subtitle maksimal 6 kata agar tidak menumpuk
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
