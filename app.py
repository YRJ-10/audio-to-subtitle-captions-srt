import customtkinter as ctk
from tkinter import filedialog, messagebox
import whisper
import threading
import os
import shutil
import subprocess

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
        self.geometry("860x560")
        self.minsize(780, 520)
        self.configure(fg_color=("#F5F7FA", "#101318"))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.model_var = ctk.StringVar(value="base")
        self.language_var = ctk.StringVar(value="Indonesia")
        self.format_var = ctk.StringVar(value="srt")
        self.words_var = ctk.StringVar(value="6")
        self.output_dir_var = ctk.StringVar(value="")
        self.file_path_var = ctk.StringVar(value="")

        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.eyebrow = ctk.CTkLabel(
            self.header_frame,
            text="AUDIO TO SUBTITLE",
            text_color=("#5D6B82", "#9AA4B2"),
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.eyebrow.grid(row=0, column=0, sticky="w")

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="Buat Subtitle dari Media",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.format_badge = ctk.CTkLabel(
            self.header_frame,
            text="MP3  WAV  MP4  MKV  MOV",
            height=30,
            corner_radius=8,
            fg_color=("#E8EEF6", "#1B2430"),
            text_color=("#526070", "#B8C2D1"),
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.format_badge.grid(row=1, column=1, sticky="e")

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 16))
        self.content_frame.grid_columnconfigure(0, weight=3)
        self.content_frame.grid_columnconfigure(1, weight=2)
        self.content_frame.grid_rowconfigure(0, weight=1)

        self.media_panel = ctk.CTkFrame(
            self.content_frame,
            corner_radius=8,
            border_width=1,
            border_color=("#D7DEE8", "#253041")
        )
        self.media_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.media_panel.grid_columnconfigure(0, weight=1)
        self.media_panel.grid_rowconfigure(6, weight=1)

        self.media_title = ctk.CTkLabel(
            self.media_panel,
            text="Media",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.media_title.grid(row=0, column=0, sticky="w", padx=22, pady=(22, 12))

        self.file_label = ctk.CTkLabel(self.media_panel, text="File audio/video")
        self.file_label.grid(row=1, column=0, sticky="w", padx=22, pady=(0, 6))

        self.file_frame = ctk.CTkFrame(self.media_panel, fg_color="transparent")
        self.file_frame.grid(row=2, column=0, sticky="ew", padx=22)
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.file_entry = ctk.CTkEntry(
            self.file_frame,
            textvariable=self.file_path_var,
            placeholder_text="Belum ada file dipilih",
            height=42,
            corner_radius=8
        )
        self.file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.file_entry.configure(state="disabled")
        self.file_button = ctk.CTkButton(
            self.file_frame,
            text="Pilih File",
            command=self.select_media_file,
            width=124,
            height=42,
            corner_radius=8
        )
        self.file_button.grid(row=0, column=1)

        self.output_label = ctk.CTkLabel(self.media_panel, text="Folder hasil")
        self.output_label.grid(row=3, column=0, sticky="w", padx=22, pady=(18, 6))

        self.output_frame = ctk.CTkFrame(self.media_panel, fg_color="transparent")
        self.output_frame.grid(row=4, column=0, sticky="ew", padx=22)
        self.output_frame.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(
            self.output_frame,
            textvariable=self.output_dir_var,
            placeholder_text="Kosongkan untuk menyimpan di folder media",
            height=42,
            corner_radius=8
        )
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.output_button = ctk.CTkButton(
            self.output_frame,
            text="Pilih Folder",
            command=self.select_output_dir,
            width=124,
            height=42,
            corner_radius=8
        )
        self.output_button.grid(row=0, column=1)

        self.action_frame = ctk.CTkFrame(self.media_panel, fg_color="transparent")
        self.action_frame.grid(row=5, column=0, sticky="ew", padx=22, pady=(28, 0))
        self.action_frame.grid_columnconfigure(0, weight=1)

        self.btn_select = ctk.CTkButton(
            self.action_frame,
            text="Mulai Proses",
            command=self.process_file,
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=8
        )
        self.btn_select.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.btn_open_output = ctk.CTkButton(
            self.action_frame,
            text="Buka Folder Hasil",
            command=self.open_output_folder,
            height=48,
            width=160,
            corner_radius=8,
            fg_color=("#DDE5EF", "#263241"),
            hover_color=("#CED8E5", "#303E50"),
            text_color=("#253041", "#E7EDF5"),
            state="disabled"
        )
        self.btn_open_output.grid(row=0, column=1)

        self.settings_panel = ctk.CTkFrame(
            self.content_frame,
            corner_radius=8,
            border_width=1,
            border_color=("#D7DEE8", "#253041")
        )
        self.settings_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.settings_panel.grid_columnconfigure(0, weight=1)
        self.settings_panel.grid_rowconfigure(9, weight=1)

        self.settings_title = ctk.CTkLabel(
            self.settings_panel,
            text="Pengaturan",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.settings_title.grid(row=0, column=0, sticky="w", padx=22, pady=(22, 14))

        self.model_label = ctk.CTkLabel(self.settings_panel, text="Model")
        self.model_label.grid(row=1, column=0, sticky="w", padx=22, pady=(0, 6))
        self.model_menu = ctk.CTkOptionMenu(
            self.settings_panel,
            values=MODEL_OPTIONS,
            variable=self.model_var,
            height=40,
            corner_radius=8
        )
        self.model_menu.grid(row=2, column=0, sticky="ew", padx=22)

        self.language_label = ctk.CTkLabel(self.settings_panel, text="Bahasa")
        self.language_label.grid(row=3, column=0, sticky="w", padx=22, pady=(16, 6))
        self.language_menu = ctk.CTkOptionMenu(
            self.settings_panel,
            values=list(LANGUAGE_OPTIONS.keys()),
            variable=self.language_var,
            height=40,
            corner_radius=8
        )
        self.language_menu.grid(row=4, column=0, sticky="ew", padx=22)

        self.format_label = ctk.CTkLabel(self.settings_panel, text="Format subtitle")
        self.format_label.grid(row=5, column=0, sticky="w", padx=22, pady=(16, 6))
        self.format_menu = ctk.CTkOptionMenu(
            self.settings_panel,
            values=FORMAT_OPTIONS,
            variable=self.format_var,
            height=40,
            corner_radius=8
        )
        self.format_menu.grid(row=6, column=0, sticky="ew", padx=22)

        self.words_label = ctk.CTkLabel(self.settings_panel, text="Kata per subtitle")
        self.words_label.grid(row=7, column=0, sticky="w", padx=22, pady=(16, 6))
        self.words_entry = ctk.CTkEntry(
            self.settings_panel,
            textvariable=self.words_var,
            height=40,
            corner_radius=8
        )
        self.words_entry.grid(row=8, column=0, sticky="ew", padx=22)

        self.footer_frame = ctk.CTkFrame(
            self,
            corner_radius=8,
            border_width=1,
            border_color=("#D7DEE8", "#253041")
        )
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 24))
        self.footer_frame.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(self.footer_frame, mode="indeterminate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 6))
        self.progress.set(0)

        self.status = ctk.CTkLabel(
            self.footer_frame,
            text="Status: Menunggu file...",
            anchor="w",
            font=ctk.CTkFont(size=12)
        )
        self.status.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))
        
        self.model = None
        self.model_name = None
        self.is_processing = False
        self.last_output_path = None
        self.controls = [
            self.model_menu,
            self.language_menu,
            self.format_menu,
            self.words_entry,
            self.output_entry,
            self.output_button,
            self.file_button,
        ]
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def select_output_dir(self):
        output_dir = filedialog.askdirectory(title="Pilih Folder Output")
        if output_dir:
            self.output_dir_var.set(output_dir)

    def select_media_file(self):
        filepath = filedialog.askopenfilename(
            title="Pilih File",
            filetypes=(
                ("Media Files", "*.mp3 *.wav *.m4a *.mp4 *.mkv *.mov *.aac *.flac"),
                ("All Files", "*.*")
            )
        )
        if filepath:
            self.last_output_path = None
            self.file_path_var.set(filepath)
            self.update_output_button_state()
            self.status.configure(text=f"Status: File siap diproses - {os.path.basename(filepath)}", text_color="gray")

    def process_file(self):
        if self.is_processing:
            messagebox.showinfo("Sedang Diproses", "Tunggu proses saat ini selesai dulu.")
            return

        filepath = self.file_path_var.get().strip()
        if not filepath:
            self.select_media_file()
            filepath = self.file_path_var.get().strip()

        if not filepath:
            return

        if not os.path.isfile(filepath):
            messagebox.showerror("File Tidak Ditemukan", "File media yang dipilih tidak ditemukan.")
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
        self.btn_open_output.configure(state="disabled")
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
        self.update_output_button_state()

    def update_output_button_state(self):
        if self.last_output_path and os.path.exists(self.last_output_path):
            self.btn_open_output.configure(state="normal")
        else:
            self.btn_open_output.configure(state="disabled")

    def finish_success(self, output_path):
        def update_ui():
            self.last_output_path = output_path
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

    def open_output_folder(self):
        if not self.last_output_path or not os.path.exists(self.last_output_path):
            messagebox.showinfo("Belum Ada Hasil", "Belum ada file hasil yang bisa dibuka.")
            return

        if os.name == "nt":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(self.last_output_path)])
        else:
            subprocess.Popen(["open", os.path.dirname(self.last_output_path)])

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
