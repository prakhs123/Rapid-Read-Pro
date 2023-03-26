import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import azure.cognitiveservices.speech as speechsdk
import ColorOptions


class ReadingConfigurationApp(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master

    def create_widgets(self):
        self.speed = tk.StringVar(value=self.master.SPEED)
        self.speed_label = ttk.Label(self, text="Speed in range (0.5 to 2)")
        self.speed_entry = ttk.Spinbox(self, format="%.2f", increment=0.10, from_=0.5, to=2, textvariable=self.speed)
        self.voices_with_styles = self.get_list_of_available_voices_with_styles()
        self.voice = tk.StringVar(value=self.master.VOICE)
        self.voice_label = ttk.Label(self, text="Voice")
        voices_choices = (v for v, _ in self.voices_with_styles)
        self.voice_entry = ttk.OptionMenu(self, self.voice, self.master.VOICE, *voices_choices)
        self.style = tk.StringVar(value=self.master.STYLE)
        self.style_label = ttk.Label(self, text="Style")
        self.style_entry = ttk.OptionMenu(self, self.style, self.master.STYLE, *tuple(self.get_styles_of_voice()))
        self.voice.trace("w", self.update_style_based_on_voices)
        self.color_option = tk.StringVar(value=self.master.COLOR_OPTION)
        self.color_options_label = ttk.Label(self, text="Color Options")
        self.color_options_entry = ttk.OptionMenu(self, self.color_option, self.master.COLOR_OPTION._name_, *(c._name_ for c in ColorOptions.COLOR_OPTIONS))
        self.font_option = tk.StringVar(value=self.master.FONT_OPTION)
        self.font_name_label = ttk.Label(self, text="Font Name")
        self.font_name_entry = ttk.OptionMenu(self, self.font_option, self.master.FONT_OPTION, *(f for f in tkFont.families() if f in self.SUPPORTED_FONTS))
        self.top_font_size = tk.StringVar(value=self.master.TOP_FONT_SIZE)
        self.top_font_size_label = ttk.Label(self, text="Top Text Font Size")
        self.top_font_size_entry = ttk.Entry(self, textvariable=self.top_font_size)
        self.bottom_font_size = tk.StringVar(value=self.master.BOTTOM_FONT_SIZE)
        self.bottom_font_size_label = ttk.Label(self, text="Bottom Text Font Size")
        self.bottom_font_size_entry = ttk.Entry(self, textvariable=self.bottom_font_size)
        self.center_font_size = tk.StringVar(value=self.master.CENTER_FONT_SIZE)
        self.center_font_size_label = ttk.Label(self, text="Center Text Font Size")
        self.center_font_size_entry = ttk.Entry(self, textvariable=self.center_font_size)
        self.word_font_size = tk.StringVar(value=self.master.WORD_FONT_SIZE)
        self.word_font_size_label = ttk.Label(self, text="Center Word Font Size")
        self.word_font_size_entry = ttk.Entry(self, textvariable=self.word_font_size)
        self.seperator_line_height = tk.StringVar(value=self.master.SEPERATOR_LINE_HEIGHT)
        self.seperator_line_height_label = ttk.Label(self, text="Focus Line Height")
        self.seperator_line_height_entry = ttk.Entry(self, textvariable=self.seperator_line_height)
        self.seperator_line_width = tk.StringVar(value=self.master.SEPERATOR_LINE_WIDTH)
        self.seperator_line_width_label = ttk.Label(self, text="Focus Line Width")
        self.seperator_line_width_entry = ttk.Entry(self, textvariable=self.seperator_line_width)
        self.num_words_in_center_text = tk.StringVar(value=self.master.NUM_WORDS_IN_CENTER_TEXT)
        self.num_words_in_center_text_label = ttk.Label(self, text="Num words in center text")
        self.num_words_in_center_text_entry = ttk.Entry(self, textvariable=self.num_words_in_center_text)
        self.next_button = ttk.Button(self, command=self.next_window, text='Next')
        self.back_button = ttk.Button(self, text="Back", command=self.back_window)

        self.speed_label.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.speed_entry.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.voice_label.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.voice_entry.grid(row=1, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.style_label.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.style_entry.grid(row=2, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.color_options_label.grid(row=3, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.color_options_entry.grid(row=3, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.font_name_label.grid(row=4, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.font_name_entry.grid(row=4, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.top_font_size_label.grid(row=5, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.top_font_size_entry.grid(row=5, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.bottom_font_size_label.grid(row=6, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.bottom_font_size_entry.grid(row=6, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.center_font_size_label.grid(row=7, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.center_font_size_entry.grid(row=7, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.word_font_size_label.grid(row=8, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.word_font_size_entry.grid(row=8, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.seperator_line_height_label.grid(row=9, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.seperator_line_height_entry.grid(row=9, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.seperator_line_width_label.grid(row=10, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.seperator_line_width_entry.grid(row=10, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.num_words_in_center_text_label.grid(row=11, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.num_words_in_center_text_entry.grid(row=11, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.back_button.grid(row=12, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.next_button.grid(row=12, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.master.eval('tk::PlaceWindow . center')

    def next_window(self):
        self.master.SPEED = self.speed.get()
        self.master.VOICE = self.voice.get()
        self.master.STYLE = self.style.get()
        SELECTED_COLOR_OPTION = ColorOptions.COLOR_OPTIONS.personal_favourite
        for c in ColorOptions.COLOR_OPTIONS:
            if c._name_ == self.color_option.get():
                SELECTED_COLOR_OPTION = c
        self.master.COLOR_OPTION = SELECTED_COLOR_OPTION
        self.master.FONT_OPTION = self.font_option.get()
        self.master.TOP_FONT_SIZE = int(self.top_font_size.get())
        self.master.BOTTOM_FONT_SIZE = int(self.bottom_font_size.get())
        self.master.CENTER_FONT_SIZE = int(self.center_font_size.get())
        self.master.WORD_FONT_SIZE = int(self.word_font_size.get())
        self.master.SEPERATOR_LINE_HEIGHT = int(self.seperator_line_height.get())
        self.master.SEPERATOR_LINE_WIDTH = int(self.seperator_line_width.get())
        self.master.NUM_WORDS_IN_CENTER_TEXT = int(self.num_words_in_center_text.get())
        self.master.show_next_window()

    def back_window(self):
        self.master.show_back_window()

    def get_list_of_available_voices_with_styles(self):
        speech_config = speechsdk.SpeechConfig(subscription=self.master.SPEECH_KEY, region=self.master.SPEECH_REGION)
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        r = speech_synthesizer.get_voices_async().get()
        en_voices = [v for v in r.voices if v._locale.startswith("en")]
        voices_with_styles = [(v._short_name, v._style_list if v._style_list[0] != '' else ['default']) for v in
                              en_voices]
        return voices_with_styles

    def get_styles_of_voice(self):
        for v, s in self.voices_with_styles:
            if v == self.voice.get():
                return s

    def update_style_based_on_voices(self, *args):
        styles = self.get_styles_of_voice()
        self.style.set(styles[0])
        self.style_entry['menu'].delete(0, 'end')
        for style in styles:
            self.style_entry['menu'].add_command(label=style, command=tk._setit(self.style, style))

    SUPPORTED_FONTS = ['Verdana',
                       'Arial',
                       'Times New Roman',
                       'Comic Sans MS',
                       'Courier New',
                       'Georgia',
                       'Helvetica',
                       'Merriweather',
                       'Source Code Pro',
                       'Tahoma',
                       'Calibri',
                       'Lato']