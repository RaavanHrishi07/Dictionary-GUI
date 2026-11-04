
import tkinter as tk
from tkinter import ttk, messagebox
from io import BytesIO
import threading
import requests
import pygame
from gtts import gTTS
import json
import os

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
SUGGEST_URL = "https://api.datamuse.com/sug"
FAVOURITES_FILE = "favourites.json"


class DictionaryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("English Dictionary")
        self.root.geometry("850x720")
        self.root.minsize(700, 550)

        self.word = tk.StringVar()
        self.accent = tk.StringVar(value="British English")
        self.status = tk.StringVar(value="Enter a word to get started.")

        self.history = []
        self.favourites = self.load_favourites()
        self.favourites_window = None
        self.favourites_list = None

        self.current_word = ""
        self.audio_data = None
        self.audio_key = None
        self.audio_loading = False
        self.mixer_initialized = False

        self.search_id = 0
        self.suggestion_id = 0
        self.suggestion_timer = None
        self.audio_request_id = 0
        self.closing = False

        self.setup_ui()
        self.word.trace_add("write", self.on_word_changed)
        self.accent.trace_add("write", self.on_accent_changed)

        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

    # -------- FAVOURITES STORAGE --------

    def load_favourites(self):
        if not os.path.exists(FAVOURITES_FILE):
            return []

        try:
            with open(FAVOURITES_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, list):
                return list(dict.fromkeys(
                    word for word in data
                    if isinstance(word, str) and word.strip()
                ))

        except (json.JSONDecodeError, OSError) as error:
            print("Favourite Loading Error:", error)

        return []

    def save_favourites(self):
        try:
            with open(FAVOURITES_FILE, "w", encoding="utf-8") as file:
                json.dump(
                    self.favourites,
                    file,
                    indent=4,
                    ensure_ascii=False
                )
            return True

        except OSError as error:
            print("Favourite Saving Error:", error)
            messagebox.showerror(
                "Storage Error",
                "Could not save favourite words."
            )
            return False

    def add_favourite(self):
        if not self.current_word:
            messagebox.showinfo(
                "No Word Selected",
                "Search for a word before adding it to favourites."
            )
            return

        if self.current_word in self.favourites:
            messagebox.showinfo(
                "Already Added",
                f"'{self.current_word}' is already in your favourites."
            )
            return

        self.favourites.insert(0, self.current_word)

        if self.save_favourites():
            self.update_favourites_button()
            self.refresh_favourites_list()

            self.status.set(
                f"'{self.current_word}' added to favourites."
            )

    def remove_favourite(self):
        if self.favourites_list is None:
            return

        selection = self.favourites_list.curselection()

        if not selection:
            messagebox.showinfo(
                "Select a Word",
                "Please select a favourite word to remove."
            )
            return

        selected_word = self.favourites_list.get(selection[0])

        self.favourites.remove(selected_word)

        if self.save_favourites():
            self.refresh_favourites_list()
            self.update_favourites_button()
            self.status.set(
                f"'{selected_word}' removed from favourites."
            )

    def update_favourites_button(self):
        if not hasattr(self, "favourite_button"):
            return

        if self.current_word in self.favourites:
            self.favourite_button.configure(
                text="★ Remove Favourite",
                command=self.remove_current_favourite
            )
        else:
            self.favourite_button.configure(
                text="☆ Add to Favourites",
                command=self.add_favourite
            )

    def remove_current_favourite(self):
        if self.current_word not in self.favourites:
            return

        if not messagebox.askyesno(
            "Remove Favourite",
            f"Remove '{self.current_word}' from favourites?"
        ):
            return

        self.favourites.remove(self.current_word)

        if self.save_favourites():
            self.update_favourites_button()
            self.refresh_favourites_list()
            self.status.set(
                f"'{self.current_word}' removed from favourites."
            )

    def open_favourites(self):
        if (
            self.favourites_window is not None
            and self.favourites_window.winfo_exists()
        ):
            self.favourites_window.lift()
            self.refresh_favourites_list()
            return

        window = tk.Toplevel(self.root)
        self.favourites_window = window

        window.title("My Favourite Words")
        window.geometry("400x450")
        window.minsize(320, 350)
        window.transient(self.root)

        ttk.Label(
            window,
            text="★ MY FAVOURITE WORDS",
            font=("Segoe UI", 16, "bold"),
            foreground="#2457D6"
        ).pack(pady=(18, 5))

        ttk.Label(
            window,
            text="Double-click a word to search its meaning.",
            font=("Segoe UI", 9)
        ).pack(pady=(0, 12))

        list_frame = ttk.Frame(window, padding=(15, 0, 15, 10))
        list_frame.pack(fill="both", expand=True)

        self.favourites_list = tk.Listbox(
            list_frame,
            font=("Segoe UI", 12),
            selectmode=tk.SINGLE,
            activestyle="dotbox",
            exportselection=False
        )
        self.favourites_list.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.favourites_list.yview
        )
        scrollbar.pack(side="right", fill="y")

        self.favourites_list.configure(
            yscrollcommand=scrollbar.set
        )

        self.favourites_list.bind(
            "<Double-Button-1>",
            self.search_selected_favourite
        )
        self.favourites_list.bind(
            "<Return>",
            self.search_selected_favourite
        )

        button_frame = ttk.Frame(window, padding=10)
        button_frame.pack(fill="x")

        ttk.Button(
            button_frame,
            text="Search Word",
            command=self.search_selected_favourite
        ).pack(side="left", padx=5, expand=True)

        ttk.Button(
            button_frame,
            text="Remove",
            command=self.remove_favourite
        ).pack(side="left", padx=5, expand=True)

        ttk.Button(
            button_frame,
            text="Close",
            command=window.destroy
        ).pack(side="left", padx=5, expand=True)

        window.protocol(
            "WM_DELETE_WINDOW",
            self.close_favourites_window
        )

        self.refresh_favourites_list()

    def close_favourites_window(self):
        if self.favourites_window is not None:
            self.favourites_window.destroy()

        self.favourites_window = None
        self.favourites_list = None

    def refresh_favourites_list(self):
        if (
            self.favourites_window is None
            or not self.favourites_window.winfo_exists()
            or self.favourites_list is None
        ):
            return

        self.favourites_list.delete(0, tk.END)

        if not self.favourites:
            self.favourites_list.insert(
                tk.END,
                "No favourite words yet."
            )
            return

        for word in self.favourites:
            self.favourites_list.insert(tk.END, word)

    def search_selected_favourite(self, event=None):
        if self.favourites_list is None:
            return "break"

        selection = self.favourites_list.curselection()

        if not selection:
            return "break"

        selected_word = self.favourites_list.get(selection[0])

        if selected_word not in self.favourites:
            return "break"

        self.close_favourites_window()
        self.word.set(selected_word)
        self.search_word()

        return "break"

    # -------- USER INTERFACE --------

    def setup_ui(self):
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="ENGLISH DICTIONARY",
            font=("Segoe UI", 24, "bold"),
            foreground="#2457D6"
        ).pack(pady=(0, 5))

        ttk.Label(
            main,
            text="Discover meanings, pronunciation, examples and more.",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 20))

        search_frame = ttk.Frame(main)
        search_frame.pack(fill="x", pady=5)

        self.search_entry = ttk.Entry(
            search_frame,
            textvariable=self.word,
            font=("Segoe UI", 13)
        )
        self.search_entry.pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )

        self.search_entry.bind("<Return>", self.on_search_enter)
        self.search_entry.bind("<Down>", self.focus_suggestions)

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

        # Autocomplete suggestions
        self.suggestion_frame = ttk.Frame(main)

        self.suggestion_list = tk.Listbox(
            self.suggestion_frame,
            height=5,
            font=("Segoe UI", 10),
            activestyle="dotbox",
            exportselection=False
        )
        self.suggestion_list.pack(fill="x")

        self.suggestion_list.bind(
            "<Double-Button-1>", self.select_suggestion
        )
        self.suggestion_list.bind(
            "<Return>", self.select_suggestion
        )
        self.suggestion_list.bind(
            "<Escape>", lambda event: self.hide_suggestions()
        )

        audio_frame = ttk.Frame(main)
        audio_frame.pack(fill="x", pady=(8, 12))

        ttk.Label(
            audio_frame, text="Accent:"
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

        # Favourite controls
        favourite_frame = ttk.Frame(main)
        favourite_frame.pack(fill="x", pady=(0, 12))

        self.favourite_button = ttk.Button(
            favourite_frame,
            text="☆ Add to Favourites",
            command=self.add_favourite,
            state="disabled"
        )
        self.favourite_button.pack(side="left", padx=(0, 8))

        ttk.Button(
            favourite_frame,
            text="★ View Favourites",
            command=self.open_favourites
        ).pack(side="left")

        history_frame = ttk.Frame(main)
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
            main,
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
            side="left", fill="both", expand=True
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

        ttk.Label(
            main,
            textvariable=self.status,
            font=("Segoe UI", 9)
        ).pack(pady=(10, 0))

        self.show_message(
            "Welcome!\n\nEnter an English word above and click Search."
        )
        self.search_entry.focus_set()

    # -------- THREAD HELPER --------

    def post_to_ui(self, callback):
        if self.closing:
            return

        try:
            self.root.after(0, callback)
        except RuntimeError:
            pass

    # -------- AUTOCOMPLETE --------

    def on_word_changed(self, *args):
        self.suggestion_id += 1
        request_id = self.suggestion_id

        if self.suggestion_timer is not None:
            self.root.after_cancel(self.suggestion_timer)
            self.suggestion_timer = None

        self.hide_suggestions()

        query = self.word.get().strip().lower()

        if len(query) < 2 or not query.isalpha():
            return

        self.suggestion_timer = self.root.after(
            350,
            lambda: self.start_suggestion_request(query, request_id)
        )

    def start_suggestion_request(self, query, request_id):
        self.suggestion_timer = None

        threading.Thread(
            target=self.fetch_suggestions,
            args=(query, request_id),
            daemon=True
        ).start()

    def fetch_suggestions(self, query, request_id):
        try:
            response = requests.get(
                SUGGEST_URL,
                params={"s": query, "max": 8},
                timeout=8
            )
            response.raise_for_status()

            words = [
                item["word"]
                for item in response.json()
                if isinstance(item.get("word"), str)
                and item["word"].lower().startswith(query)
            ]

            self.post_to_ui(
                lambda: self.display_suggestions(
                    query, request_id, words
                )
            )

        except (requests.RequestException, ValueError) as error:
            print("Suggestion Error:", error)

    def display_suggestions(self, query, request_id, words):
        if (
            request_id != self.suggestion_id
            or self.word.get().strip().lower() != query
            or not words
        ):
            return

        self.suggestion_list.delete(0, tk.END)

        for item in words:
            self.suggestion_list.insert(tk.END, item)

        self.suggestion_frame.pack(
            fill="x",
            after=self.search_entry.master,
            pady=(0, 8)
        )

    def hide_suggestions(self):
        self.suggestion_frame.pack_forget()

    def focus_suggestions(self, event):
        if self.suggestion_frame.winfo_manager():
            self.suggestion_list.focus_set()
            self.suggestion_list.selection_clear(0, tk.END)
            self.suggestion_list.selection_set(0)
            self.suggestion_list.activate(0)
            return "break"

    def select_suggestion(self, event=None):
        selection = self.suggestion_list.curselection()

        if not selection:
            return "break"

        selected_word = self.suggestion_list.get(selection[0])
        self.word.set(selected_word)
        self.hide_suggestions()
        self.search_word()
        return "break"

    def on_search_enter(self, event=None):
        self.search_word()
        return "break"

    # -------- DICTIONARY SEARCH --------

    def show_message(self, message):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, message)
        self.result_text.configure(state="disabled")

    def reset_audio(self):
        self.audio_request_id += 1

        if self.mixer_initialized:
            pygame.mixer.music.stop()

        self.audio_data = None
        self.audio_key = None
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

        self.suggestion_id += 1

        if self.suggestion_timer is not None:
            self.root.after_cancel(self.suggestion_timer)
            self.suggestion_timer = None

        self.hide_suggestions()
        self.search_id += 1
        request_id = self.search_id

        self.reset_audio()
        self.current_word = search_term

        self.update_favourites_button()
        self.favourite_button.configure(state="disabled")

        self.search_button.configure(state="disabled")
        self.status.set(f"Searching for '{search_term}'...")

        self.show_message(
            f"Fetching dictionary information for '{search_term}'..."
        )

        threading.Thread(
            target=self.fetch_meaning,
            args=(search_term, request_id),
            daemon=True
        ).start()

    def fetch_meaning(self, search_term, request_id):
        try:
            response = requests.get(
                API_URL.format(requests.utils.quote(search_term, safe="")),
                timeout=15
            )

            if response.status_code == 404:
                self.post_to_ui(
                    lambda: self.show_not_found(search_term, request_id)
                )
                return

            response.raise_for_status()
            data = response.json()

            self.post_to_ui(
                lambda: self.display_results(
                    search_term, data, request_id
                )
            )

        except requests.Timeout:
            self.post_to_ui(
                lambda: self.show_error(
                    "The request timed out. Please try again.",
                    request_id
                )
            )

        except requests.ConnectionError:
            self.post_to_ui(
                lambda: self.show_error(
                    "Unable to connect. Check your internet connection.",
                    request_id
                )
            )

        except (requests.RequestException, ValueError) as error:
            print("API Error:", error)

            self.post_to_ui(
                lambda: self.show_error(
                    "Something went wrong while fetching the meaning.",
                    request_id
                )
            )

    def display_results(self, search_term, data, request_id):
        if request_id != self.search_id:
            return

        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)

        self.result_text.insert(
            tk.END,
            search_term.capitalize() + "\n",
            "heading"
        )
        self.result_text.insert(tk.END, "=" * 45 + "\n\n")

        for entry in data:
            for phonetic in entry.get("phonetics", []):
                pronunciation = phonetic.get("text")

                if pronunciation:
                    self.result_text.insert(
                        tk.END,
                        f"Pronunciation: {pronunciation}\n"
                    )

            for meaning in entry.get("meanings", []):
                part_of_speech = meaning.get(
                    "partOfSpeech", "Unknown"
                )

                self.result_text.insert(
                    tk.END,
                    f"\n{part_of_speech.upper()}\n",
                    "section"
                )

                for index, definition in enumerate(
                    meaning.get("definitions", []),
                    start=1
                ):
                    self.result_text.insert(
                        tk.END,
                        f"{index}. {definition.get('definition', 'No definition available.')}\n"
                    )

                    example = definition.get("example")

                    if example:
                        self.result_text.insert(
                            tk.END,
                            f"   Example: {example}\n"
                        )

                    synonyms = definition.get("synonyms", [])

                    if synonyms:
                        self.result_text.insert(
                            tk.END,
                            f"   Synonyms: {', '.join(synonyms)}\n"
                        )

                    antonyms = definition.get("antonyms", [])

                    if antonyms:
                        self.result_text.insert(
                            tk.END,
                            f"   Antonyms: {', '.join(antonyms)}\n"
                        )

                meaning_synonyms = meaning.get("synonyms", [])

                if meaning_synonyms:
                    self.result_text.insert(
                        tk.END,
                        "\nRelated Synonyms: "
                        + ", ".join(meaning_synonyms) + "\n"
                    )

                meaning_antonyms = meaning.get("antonyms", [])

                if meaning_antonyms:
                    self.result_text.insert(
                        tk.END,
                        "Related Antonyms: "
                        + ", ".join(meaning_antonyms) + "\n"
                    )

        self.result_text.configure(state="disabled")

        if search_term in self.history:
            self.history.remove(search_term)

        self.history.insert(0, search_term)
        self.history = self.history[:5]

        self.history_label.configure(
            text=", ".join(self.history)
        )

        self.play_button.configure(state="normal")
        self.search_button.configure(state="normal")
        self.favourite_button.configure(state="normal")
        self.update_favourites_button()

        self.status.set(
            f"Successfully loaded meaning for '{search_term}'."
        )

    # -------- AUDIO PRONUNCIATION --------

    def on_accent_changed(self, *args):
        if self.mixer_initialized:
            pygame.mixer.music.stop()

        self.audio_request_id += 1
        self.audio_data = None
        self.audio_key = None
        self.audio_loading = False

        if hasattr(self, "play_button"):
            self.play_button.configure(
                state="normal" if self.current_word else "disabled",
                text="🔊 Play Pronunciation"
            )
            self.stop_button.configure(state="disabled")

    def play_audio(self):
        if not self.current_word or self.audio_loading:
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

        word = self.current_word
        accent = self.accent.get()
        key = (word, accent)

        if self.audio_data is not None and self.audio_key == key:
            self.start_playback(self.audio_data)
            return

        self.audio_loading = True
        self.audio_request_id += 1
        request_id = self.audio_request_id

        self.play_button.configure(
            state="disabled",
            text="Generating Audio..."
        )
        self.status.set("Generating pronunciation audio...")

        threading.Thread(
            target=self.generate_audio,
            args=(word, accent, request_id),
            daemon=True
        ).start()

    def generate_audio(self, word, accent, request_id):
        try:
            tld = "co.uk" if accent == "British English" else "com"

            buffer = BytesIO()
            gTTS(text=word, lang="en", tld=tld).write_to_fp(buffer)
            audio_data = buffer.getvalue()

            if not audio_data:
                raise ValueError("Generated audio is empty.")

            self.post_to_ui(
                lambda: self.audio_generated(
                    word, accent, request_id, audio_data
                )
            )

        except Exception as error:
            print("Audio Generation Error:", error)

            self.post_to_ui(
                lambda: self.audio_generation_failed(request_id)
            )

    def audio_generated(self, word, accent, request_id, audio_data):
        if request_id != self.audio_request_id:
            return

        self.audio_loading = False
        self.audio_data = audio_data
        self.audio_key = (word, accent)
        self.start_playback(audio_data)

    def audio_generation_failed(self, request_id):
        if request_id != self.audio_request_id:
            return

        self.audio_loading = False

        self.play_button.configure(
            state="normal",
            text="🔊 Play Pronunciation"
        )
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

    # -------- OTHER CONTROLS --------

    def show_not_found(self, search_term, request_id):
        if request_id != self.search_id:
            return

        self.show_message(
            f"No definition found for '{search_term}'.\n\n"
            "Please check the spelling and try another word."
        )

        self.status.set("Word not found.")
        self.search_button.configure(state="normal")
        self.favourite_button.configure(state="disabled")

    def show_error(self, message, request_id):
        if request_id != self.search_id:
            return

        self.show_message(message)
        self.status.set("Search failed.")
        self.search_button.configure(state="normal")
        self.favourite_button.configure(state="disabled")

    def clear_search(self):
        self.search_id += 1
        self.suggestion_id += 1

        if self.suggestion_timer is not None:
            self.root.after_cancel(self.suggestion_timer)
            self.suggestion_timer = None

        self.word.set("")
        self.current_word = ""
        self.hide_suggestions()
        self.reset_audio()

        self.favourite_button.configure(
            state="disabled",
            text="☆ Add to Favourites",
            command=self.add_favourite
        )

        self.show_message(
            "Enter an English word above and click Search."
        )
        self.status.set("Ready for a new search.")
        self.search_button.configure(state="normal")
        self.search_entry.focus_set()

    def close_application(self):
        self.closing = True

        if self.suggestion_timer is not None:
            self.root.after_cancel(self.suggestion_timer)

        if self.mixer_initialized:
            pygame.mixer.music.stop()
            pygame.mixer.quit()

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DictionaryApp(root)
    root.mainloop()
