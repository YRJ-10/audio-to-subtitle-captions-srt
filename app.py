import customtkinter as ctk
from tkinter import filedialog, messagebox
import whisper
import threading
import os
import shutil

# Konfigurasi Tampilan Modern
ctk.set_appearance_mode("System")  # Mengikuti tema Windows (Gelap/Terang)
ctk.set_default_color_theme("blue")

MODEL_OPTIONS = ("tiny", "base", "small", "medium")
LANGUAGE_OPTIONS = {
    "Indonesia": "id",
    "English": "en",
    "Auto detect": None,
}
FORMAT_OPTIONS = ("srt", "vtt", "txt")


def format_timestamp(seconds: float):
    milliseconds = round(seconds * 1000.0)
    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000
    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000
    secs = milliseconds // 1_000
    milliseconds -= secs * 1_000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def format_vtt_timestamp(seconds: float):
    return format_timestamp(seconds).replace(",", ".")


def get_unique_output_path(output_dir, filename, extension):
    output_path = os.path.join(output_dir, f"{filename}.{extension}")
    if not os.path.exists(output_path):
        return output_path

    counter = 2
    while True:
        output_path = os.path.join(output_dir, f"{filename}_{counter}.{extension}")
        if not os.path.exists(output_path):
            return output_path
        counter += 1


class SubtitleApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Audio to Subtitle (Indonesian)")
        self.geometry("620x520")
        self.resizable(False, False)
        
        # Frame Kontainer Utama
        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        # Judul Aplikasi
        self.label = ctk.CTkLabel(self.frame, text="Konversi Audio/Video ke Subtitle", font=ctk.CTkFont(size=18, weight="bold"))
        self.label.pack(pady=(20, 10))

        self.model_var = ctk.StringVar(value="base")
        self.language_var = ctk.StringVar(value="Indonesia")
        self.format_var = ctk.StringVar(value="srt")
        self.words_var = ctk.StringVar(value="6")
        self.output_dir_var = ctk.StringVar(value="")

        self.options_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.options_frame.pack(padx=24, pady=(8, 6), fill="x")
        self.options_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.model_label = ctk.CTkLabel(self.options_frame, text="Model")
        self.model_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.model_menu = ctk.CTkOptionMenu(self.options_frame, values=MODEL_OPTIONS, variable=self.model_var)
        self.model_menu.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        self.language_label = ctk.CTkLabel(self.options_frame, text="Bahasa")
        self.language_label.grid(row=0, column=1, sticky="w", padx=8)
        self.language_menu = ctk.CTkOptionMenu(self.options_frame, values=list(LANGUAGE_OPTIONS.keys()), variable=self.language_var)
        self.language_menu.grid(row=1, column=1, sticky="ew", padx=8)

        self.format_label = ctk.CTkLabel(self.options_frame, text="Format")
        self.format_label.grid(row=0, column=2, sticky="w", padx=(8, 0))
        self.format_menu = ctk.CTkOptionMenu(self.options_frame, values=FORMAT_OPTIONS, variable=self.format_var)
        self.format_menu.grid(row=1, column=2, sticky="ew", padx=(8, 0))

        self.words_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.words_frame.pack(padx=24, pady=(6, 6), fill="x")
        self.words_frame.grid_columnconfigure(1, weight=1)

        self.words_label = ctk.CTkLabel(self.words_frame, text="Kata per subtitle")
        self.words_label.grid(row=0, column=0, sticky="w", padx=(0, 12))
        self.words_entry = ctk.CTkEntry(self.words_frame, textvariable=self.words_var, width=80)
        self.words_entry.grid(row=0, column=1, sticky="w")

        self.output_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.output_frame.pack(padx=24, pady=(6, 10), fill="x")
        self.output_frame.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(
            self.output_frame,
            textvariable=self.output_dir_var,
            placeholder_text="Folder output: sama dengan file media"
        )
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.output_button = ctk.CTkButton(self.output_frame, text="Pilih Folder", command=self.select_output_dir, width=120)
        self.output_button.grid(row=0, column=1)

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
        self.model_name = None
        self.is_processing = False
        self.controls = [
            self.model_menu,
            self.language_menu,
            self.format_menu,
            self.words_entry,
            self.output_entry,
            self.output_button,
        ]
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def select_output_dir(self):
        output_dir = filedialog.askdirectory(title="Pilih Folder Output")
        if output_dir:
            self.output_dir_var.set(output_dir)

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

        settings = self.get_transcription_settings(filepath)
        if settings is None:
            return

        # Mengubah UI saat sedang proses
        self.is_processing = True
        self.set_controls_state("disabled")
        self.status.configure(text=f"Status: Memuat model {settings['model']}... proses pertama bisa agak lama.", text_color="orange")
        self.progress.start() # Jalankan animasi progress bar
        
        # Jalankan di background agar UI tidak macet
        threading.Thread(target=self.transcribe_worker, args=(filepath, settings), daemon=True).start()

    def get_transcription_settings(self, filepath):
        try:
            words_per_caption = int(self.words_var.get().strip())
        except ValueError:
            messagebox.showerror("Input Tidak Valid", "Jumlah kata per subtitle harus berupa angka.")
            return None

        if words_per_caption < 1 or words_per_caption > 20:
            messagebox.showerror("Input Tidak Valid", "Jumlah kata per subtitle harus antara 1 sampai 20.")
            return None

        output_dir = self.output_dir_var.get().strip() or os.path.dirname(filepath)
        if not os.path.isdir(output_dir):
            messagebox.showerror("Folder Tidak Ditemukan", "Folder output tidak ditemukan.")
            return None

        return {
            "model": self.model_var.get(),
            "language": LANGUAGE_OPTIONS[self.language_var.get()],
            "format": self.format_var.get(),
            "words_per_caption": words_per_caption,
            "output_dir": output_dir,
        }
        
    def transcribe_worker(self, filepath, settings):
        try:
            if self.model is None or self.model_name != settings["model"]:
                self.model = whisper.load_model(settings["model"])
                self.model_name = settings["model"]

            self.set_status("Status: Sedang memproses suara... jangan tutup aplikasi dulu.", "#1E90FF")

            result = self.model.transcribe(filepath, language=settings["language"], word_timestamps=True)

            filename = os.path.splitext(os.path.basename(filepath))[0]
            output_path = get_unique_output_path(settings["output_dir"], filename, settings["format"])

            captions = self.build_captions(result, settings["words_per_caption"])
            self.write_output(output_path, settings["format"], captions)
            
            self.finish_success(output_path)
            
        except Exception as e:
            self.finish_error(e)

    def build_captions(self, result, words_per_caption):
        captions = []

        for seg in result["segments"]:
            words = seg.get("words", [])
            if not words:
                captions.append((seg["start"], seg["end"], seg["text"].strip()))
                continue

            chunk_words = []
            chunk_start = words[0]["start"]

            for i, word in enumerate(words):
                chunk_words.append(word["word"].strip())

                if len(chunk_words) >= words_per_caption or i == len(words) - 1:
                    captions.append((chunk_start, word["end"], " ".join(chunk_words)))
                    chunk_words = []
                    if i < len(words) - 1:
                        chunk_start = words[i + 1]["start"]

        return captions

    def write_output(self, output_path, output_format, captions):
        with open(output_path, "w", encoding="utf-8") as f:
            if output_format == "srt":
                self.write_srt(f, captions)
            elif output_format == "vtt":
                self.write_vtt(f, captions)
            else:
                self.write_txt(f, captions)

    def write_srt(self, file, captions):
        for index, (start, end, text) in enumerate(captions, start=1):
            file.write(f"{index}\n{format_timestamp(start)} --> {format_timestamp(end)}\n{text}\n\n")

    def write_vtt(self, file, captions):
        file.write("WEBVTT\n\n")
        for start, end, text in captions:
            file.write(f"{format_vtt_timestamp(start)} --> {format_vtt_timestamp(end)}\n{text}\n\n")

    def write_txt(self, file, captions):
        for start, end, text in captions:
            file.write(f"[{format_timestamp(start)} - {format_timestamp(end)}] {text}\n")

    def set_status(self, text, color):
        self.after(0, lambda: self.status.configure(text=text, text_color=color))

    def set_controls_state(self, state):
        self.btn_select.configure(state=state)
        for control in self.controls:
            control.configure(state=state)

    def reset_processing_ui(self):
        self.is_processing = False
        self.set_controls_state("normal")
        self.progress.stop()
        self.progress.set(0)

    def finish_success(self, output_path):
        def update_ui():
            self.status.configure(text=f"Selesai! Disimpan sebagai: {os.path.basename(output_path)}", text_color="green")
            self.reset_processing_ui()
            messagebox.showinfo("Sukses", f"Subtitle berhasil dibuat dan disimpan di:\n\n{output_path}")

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
