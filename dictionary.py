
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading
import pygame
from gtts import gTTS
from io import BytesIO


API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"


class DictionaryApp:

    def __init__(self, root):
        self.root = root
        self.root.title("English Dictionary")
        self.root.geometry("850x720")
        self.root.minsize(700, 550)

        self.word = tk.StringVar()
        self.status = tk.StringVar(
            value="Enter a word to get started."
        )
        self.accent = tk.StringVar(value="British English")

        self.history = []
        self.audio_data = None
        self.audio_loading = False
        self.mixer_initialized = False
        self.current_word = ""

        self.setup_ui()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close_application
        )

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(
            main_frame,
            text="ENGLISH DICTIONARY",
            font=("Segoe UI", 24, "bold"),
            foreground="#2457D6"
        ).pack(pady=(0, 5))

        ttk.Label(
            main_frame,
            text="Discover meanings, pronunciation, examples and more.",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 20))

        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill="x", pady=5)

        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.word,
            font=("Segoe UI", 13)
        )
        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8)
        )

        self.search_entry.bind(
            "<Return>",
            lambda event: self.search_word()
        )

        self.search_button = ttk.Button(
            search_frame,
            text="Search",
            command=self.search_word
        )
        self.search_button.pack(side="left", padx=4)

        ttk.Button(
            search_frame,
            text="Clear",
            command=self.clear_search
        ).pack(side="left", padx=4)

        audio_frame = ttk.Frame(main_frame)
        audio_frame.pack(fill="x", pady=(8, 12))

        ttk.Label(
            audio_frame,
            text="Accent:"
        ).pack(side="left", padx=(0, 5))

        self.accent_box = ttk.Combobox(
            audio_frame,
            textvariable=self.accent,
            values=["British English", "American English"],
            state="readonly",
            width=18
        )
        self.accent_box.pack(side="left", padx=(0, 15))

        self.play_button = ttk.Button(
            audio_frame,
            text="🔊 Play Pronunciation",
            command=self.play_audio,
            state="disabled"
        )
        self.play_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(
            audio_frame,
            text="Stop Audio",
            command=self.stop_audio,
            state="disabled"
        )
        self.stop_button.pack(side="left")

        history_frame = ttk.Frame(main_frame)
        history_frame.pack(fill="x", pady=(0, 12))

        ttk.Label(
            history_frame,
            text="Recent Searches:",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        self.history_label = ttk.Label(
            history_frame,
            text="None",
            font=("Segoe UI", 9)
        )
        self.history_label.pack(side="left", padx=8)

        result_frame = ttk.LabelFrame(
            main_frame,
            text="Dictionary Results",
            padding=12
        )
        result_frame.pack(fill="both", expand=True)

        self.result_text = tk.Text(
            result_frame,
            wrap="word",
            font=("Segoe UI", 10),
            padx=12,
            pady=12,
            relief="flat",
            background="#FAFAFA",
            state="disabled"
        )

        self.result_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            result_frame,
            orient="vertical",
            command=self.result_text.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.result_text.configure(
            yscrollcommand=scrollbar.set
        )

        self.result_text.tag_configure(
            "heading",
            font=("Segoe UI", 15, "bold"),
            foreground="#2457D6"
        )

        self.result_text.tag_configure(
            "section",
            font=("Segoe UI", 11, "bold"),
            foreground="#16804A"
        )

        self.status_label = ttk.Label(
            main_frame,
            textvariable=self.status,
            font=("Segoe UI", 9)
        )
        self.status_label.pack(pady=(10, 0))

        self.show_message(
            "Welcome!\n\nEnter an English word above and click Search."
        )

    def show_message(self, message):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", message)
        self.result_text.configure(state="disabled")

    def reset_audio(self):
        if self.mixer_initialized:
            pygame.mixer.music.stop()

        self.audio_data = None
        self.audio_loading = False

        self.play_button.configure(
            state="disabled",
            text="🔊 Play Pronunciation"
        )
        self.stop_button.configure(state="disabled")

    def search_word(self):
        search_term = self.word.get().strip().lower()

        if not search_term:
            messagebox.showwarning(
                "Empty Input",
                "Please enter a word to search."
            )
            return

        self.reset_audio()
        self.current_word = search_term

        self.search_button.configure(state="disabled")
        self.status.set(f"Searching for '{search_term}'...")

        self.show_message(
            f"Fetching dictionary information for '{search_term}'..."
        )

        threading.Thread(
            target=self.fetch_meaning,
            args=(search_term,),
            daemon=True
        ).start()

    def fetch_meaning(self, search_term):
        try:
            response = requests.get(
                API_URL.format(search_term),
                timeout=15
            )

            if response.status_code == 404:
                self.root.after(
                    0,
                    lambda: self.show_not_found(search_term)
                )
                return

            response.raise_for_status()
            data = response.json()

            self.root.after(
                0,
                lambda: self.display_results(search_term, data)
            )

        except requests.exceptions.Timeout:
            self.root.after(
                0,
                lambda: self.show_error(
                    "The request timed out. Please try again."
                )
            )

        except requests.exceptions.ConnectionError:
            self.root.after(
                0,
                lambda: self.show_error(
                    "Unable to connect. Check your internet connection."
                )
            )

        except (
            requests.exceptions.RequestException,
            ValueError
        ) as error:
            print("API Error:", error)

            self.root.after(
                0,
                lambda: self.show_error(
                    "Something went wrong while fetching the meaning."
                )
            )

    def display_results(self, search_term, data):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")

        self.result_text.insert(
            "end",
            search_term.capitalize() + "\n",
            "heading"
        )

        self.result_text.insert(
            "end",
            "=" * 45 + "\n\n"
        )

        for entry in data:
            for phonetic in entry.get("phonetics", []):
                pronunciation = phonetic.get("text")

                if pronunciation:
                    self.result_text.insert(
                        "end",
                        f"Pronunciation: {pronunciation}\n"
                    )

            for meaning in entry.get("meanings", []):
                part_of_speech = meaning.get(
                    "partOfSpeech",
                    "Unknown"
                )

                self.result_text.insert(
                    "end",
                    f"\n{part_of_speech.upper()}\n",
                    "section"
                )

                for index, definition in enumerate(
                    meaning.get("definitions", []),
                    start=1
                ):
                    self.result_text.insert(
                        "end",
                        f"{index}. {definition.get('definition', 'No definition available.')}\n"
                    )

                    example = definition.get("example")

                    if example:
                        self.result_text.insert(
                            "end",
                            f"   Example: {example}\n"
                        )

                    synonyms = definition.get("synonyms", [])

                    if synonyms:
                        self.result_text.insert(
                            "end",
                            f"   Synonyms: {', '.join(synonyms)}\n"
                        )

                    antonyms = definition.get("antonyms", [])

                    if antonyms:
                        self.result_text.insert(
                            "end",
                            f"   Antonyms: {', '.join(antonyms)}\n"
                        )

                meaning_synonyms = meaning.get("synonyms", [])

                if meaning_synonyms:
                    self.result_text.insert(
                        "end",
                        "\nRelated Synonyms: "
                        + ", ".join(meaning_synonyms)
                        + "\n"
                    )

                meaning_antonyms = meaning.get("antonyms", [])

                if meaning_antonyms:
                    self.result_text.insert(
                        "end",
                        "Related Antonyms: "
                        + ", ".join(meaning_antonyms)
                        + "\n"
                    )

        self.result_text.configure(state="disabled")

        if search_term not in self.history:
            self.history.insert(0, search_term)
            self.history = self.history[:5]

        self.history_label.configure(
            text=", ".join(self.history)
        )

        self.play_button.configure(state="normal")

        self.status.set(
            f"Successfully loaded meaning for '{search_term}'."
        )

        self.search_button.configure(state="normal")

    def play_audio(self):
        if not self.current_word:
            return

        if self.audio_loading:
            return

        if not self.mixer_initialized:
            try:
                pygame.mixer.init()
                self.mixer_initialized = True

            except pygame.error as error:
                print("Audio Initialization Error:", error)

                messagebox.showerror(
                    "Audio Error",
                    "Unable to initialize the audio player."
                )
                return

        if self.audio_data:
            self.start_playback(self.audio_data)
            return

        self.audio_loading = True

        self.play_button.configure(
            state="disabled",
            text="Generating Audio..."
        )

        self.status.set("Generating pronunciation audio...")

        selected_accent = self.accent.get()

        threading.Thread(
            target=self.generate_audio,
            args=(self.current_word, selected_accent),
            daemon=True
        ).start()

    def generate_audio(self, word, accent):
        try:
            if accent == "British English":
                tld = "co.uk"
            else:
                tld = "com"

            audio_buffer = BytesIO()

            tts = gTTS(
                text=word,
                lang="en",
                tld=tld
            )

            tts.write_to_fp(audio_buffer)
            audio_data = audio_buffer.getvalue()

            if not audio_data:
                raise ValueError("Generated audio is empty.")

            self.root.after(
                0,
                lambda: self.audio_generated(
                    word,
                    accent,
                    audio_data
                )
            )

        except Exception as error:
            print("Audio Generation Error:", error)

            self.root.after(
                0,
                lambda: self.audio_generation_failed(word)
            )

    def audio_generated(self, word, accent, audio_data):
        self.audio_loading = False

        if word != self.current_word:
            return

        self.audio_data = audio_data
        self.start_playback(audio_data)

    def audio_generation_failed(self, word):
        self.audio_loading = False

        self.play_button.configure(
            state="normal",
            text="🔊 Play Pronunciation"
        )

        if word != self.current_word:
            return

        self.status.set("Audio generation failed.")

        messagebox.showerror(
            "Audio Error",
            "Could not generate pronunciation audio. "
            "Please check your internet connection and try again."
        )

    def start_playback(self, audio_data):
        try:
            pygame.mixer.music.load(BytesIO(audio_data))
            pygame.mixer.music.play()

            self.play_button.configure(
                state="normal",
                text="🔊 Play Again"
            )

            self.stop_button.configure(state="normal")

            self.status.set("Playing pronunciation audio...")

        except (pygame.error, ValueError) as error:
            print("Playback Error:", error)

            self.status.set("Unable to play audio.")

            messagebox.showerror(
                "Playback Error",
                "The pronunciation audio could not be played."
            )

    def stop_audio(self):
        if self.mixer_initialized:
            pygame.mixer.music.stop()

        self.stop_button.configure(state="disabled")
        self.status.set("Audio playback stopped.")

    def show_not_found(self, search_term):
        self.show_message(
            f"No definition found for '{search_term}'.\n\n"
            "Please check the spelling and try another word."
        )

        self.status.set("Word not found.")
        self.search_button.configure(state="normal")

    def show_error(self, message):
        self.show_message(message)
        self.status.set("Search failed.")
        self.search_button.configure(state="normal")

    def clear_search(self):
        self.word.set()
        self.current_word = ""
        self.reset_audio()

        self.show_message(
            "Enter an English word above and click Search."
        )

        self.status.set("Ready for a new search.")
        self.search_button.configure(state="normal")
        self.search_entry.focus_set()

    def close_application(self):
        if self.mixer_initialized:
            pygame.mixer.music.stop()
            pygame.mixer.quit()

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DictionaryApp(root)
    root.mainloop()
