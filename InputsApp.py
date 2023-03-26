import os.path
import tkinter as tk
from tkinter import ttk, filedialog
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import ResultReason


class InputsApp(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master

    def create_widgets(self):
        self.speech_key = tk.StringVar(value=self.master.SPEECH_KEY)
        self.speech_region = tk.StringVar(value=self.master.SPEECH_REGION)
        self.filepath = tk.StringVar(value=self.master.FILE)

        self.speech_key_label = ttk.Label(self, text="SPEECH_KEY")
        self.speech_key_entry = ttk.Entry(self, textvariable=self.speech_key, width=30)
        self.speech_region_label = ttk.Label(self, text="SPEECH_REGION")
        self.speech_region_entry = ttk.Entry(self, textvariable=self.speech_region)
        self.add_file_button = ttk.Button(self, text="Open EPUB/PDF", command=self.open_file)
        self.next_button = ttk.Button(self, command=self.next_window, text='Next')

        self.speech_key_label.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.speech_key_entry.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.speech_region_label.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.speech_region_entry.grid(row=1, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.add_file_button.grid(row=2, columnspan=2, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.next_button.grid(row=3, columnspan=2, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.master.eval('tk::PlaceWindow . center')

    def next_window(self):
        self.master.SPEECH_KEY = self.speech_key.get()
        self.master.SPEECH_REGION = self.speech_region.get()
        working = self.check_speech_key()
        if not working:
            self.next_button.config(text="Invalid Speech Key, Correct the key and press here again")
            return
        self.master.FILE = self.filepath.get()
        self.master.show_next_window()

    def check_speech_key(self):
        speech_config = speechsdk.SpeechConfig(subscription=self.master.SPEECH_KEY, region=self.master.SPEECH_REGION)
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        r = speech_synthesizer.get_voices_async().get()
        if r.reason != ResultReason.VoicesListRetrieved:
            return False
        else:
            return True

    def open_file(self):
        file_path = filedialog.askopenfilename(title="Add Epub/PDF File",
                                               filetypes=(("pdf file", "*.pdf"), ("epub file", "*.epub")))
        self.filepath.set(file_path)
        filename = os.path.basename(file_path)
        self.add_file_button.config(text=filename)
