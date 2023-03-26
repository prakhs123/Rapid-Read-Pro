import shutil
import tempfile
import tkinter as tk
import os
import logging

import ColorOptions
from EpubConfigurationApp import EpubConfigurationApp
from IndexConfigurationApp import IndexConfigurationApp
from InputsApp import InputsApp
from RapidReadProApp import RapidReadProApp
from ReadingConfigurationApp import ReadingConfigurationApp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Rapid Read Pro")
        self.columnconfigure(0, weight=1)
        self.SPEECH_KEY = os.environ.get('SPEECH_KEY', "")
        self.SPEECH_REGION = os.environ.get('SPEECH_REGION', "")
        self.FILE = ""
        self.NUM_TOKENS = "50"
        self.START_INDEX = 0
        self.SPEED = "1.20"
        self.VOICE = "en-US-AriaNeural"
        self.STYLE = "narration-professional"
        self.COLOR_OPTION = ColorOptions.COLOR_OPTIONS.personal_favourite
        self.FONT_OPTION = "Times New Roman"
        self.TOP_FONT_SIZE = 24
        self.BOTTOM_FONT_SIZE = 24
        self.CENTER_FONT_SIZE = 36
        self.WORD_FONT_SIZE = 60
        self.SEPERATOR_LINE_HEIGHT = 15
        self.SEPERATOR_LINE_WIDTH = 3
        self.NUM_WORDS_IN_CENTER_TEXT = 5
        self.tmp = tempfile.mkdtemp()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window_classes = [InputsApp, EpubConfigurationApp, IndexConfigurationApp, ReadingConfigurationApp,
                               RapidReadProApp]
        self.current_window = 0
        self.create_window()

    def on_closing(self):
        if os.path.exists(self.tmp):
            logging.info("Deleting tmp directory")
            shutil.rmtree(self.tmp)
        self.quit()
        self.destroy()

    def create_window(self):
        self.window = self.window_classes[self.current_window](self)
        self.window.create_widgets()
        if isinstance(self.window, RapidReadProApp):
            self.window.pack(fill=tk.BOTH, expand=1)
        else:
            self.window.pack()
            self.geometry('{}x{}'.format(self.window.winfo_reqwidth(), self.window.winfo_reqheight()))

    def destroy_window(self):
        self.window.pack_forget()
        self.window.destroy()

    def show_next_window(self):
        self.destroy_window()
        self.current_window += 1
        self.create_window()

    def show_back_window(self):
        self.destroy_window()
        self.current_window -= 1
        self.create_window()


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
