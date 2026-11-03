
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import threading


API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"


class DictionaryApp:

    def __init__(self, root):
        self.root = root
        self.root.title("English Dictionary")
        self.root.geometry("850x700")
        self.root.minsize(700, 550)

        self.word = tk.StringVar()
        self.status = tk.StringVar(value="Enter a word to get started.")
        self.history = []

        self.setup_ui()

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
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        self.search_entry.bind("<Return>", lambda event: self.search_word())

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

        history_frame = ttk.Frame(main_frame)
        history_frame.pack(fill="x", pady=(8, 12))

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
        self.result_text.tag_configure(
            "subheading",
            font=("Segoe UI", 10, "bold")
        )

        ttk.Label(
            main_frame,
            textvariable=self.status,
            font=("Segoe UI", 9)
        ).pack(pady=(10, 0))

        self.show_message(
            "Welcome!\n\nEnter an English word above and click Search."
        )

    def show_message(self, message):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", message)
        self.result_text.configure(state="disabled")

    def search_word(self, event=None):
        search_term = self.word.get().strip().lower()

        if not search_term:
            messagebox.showwarning(
                "Empty Input",
                "Please enter a word to search."
            )
            return

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

        except (requests.exceptions.RequestException, ValueError) as error:
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

        self.result_text.insert("end", "=" * 45 + "\n\n")

        for entry in data:
            for phonetic in entry.get("phonetics", []):
                pronunciation = phonetic.get("text")
                audio = phonetic.get("audio")

                if pronunciation:
                    self.result_text.insert(
                        "end",
                        f"Pronunciation: {pronunciation}\n"
                    )

                if audio:
                    self.result_text.insert(
                        "end",
                        f"Audio pronunciation available: {audio}\n"
                    )

            for meaning in entry.get("meanings", []):
                part_of_speech = meaning.get(
                    "partOfSpeech", "Unknown"
                )

                self.result_text.insert(
                    "end",
                    f"\n{part_of_speech.upper()}\n",
                    "section"
                )

                for index, definition in enumerate(
                    meaning.get("definitions", []), start=1
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

        self.status.set(
            f"Successfully loaded meaning for '{search_term}'."
        )
        self.search_button.configure(state="normal")

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
        self.word.set("")
        self.show_message(
            "Enter an English word above and click Search."
        )
        self.status.set("Ready for a new search.")
        self.search_entry.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = DictionaryApp(root)
    root.mainloop()
