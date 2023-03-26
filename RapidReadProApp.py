import random
import string
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
from datetime import timedelta
import azure.cognitiveservices.speech as speechsdk
import logging
import os

from just_playback import Playback

from Words import Words

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def generate_filename():
    letters = string.ascii_lowercase
    filename = ''.join(random.choice(letters) for _ in range(10))
    return filename


def speak(synthesizer, ssml_string):
    words_with_offset = []

    def word_boundary(event):
        nonlocal words_with_offset
        words_with_offset.append((event.audio_offset, event.text,))

    synthesizer.synthesis_word_boundary.connect(word_boundary)
    result = synthesizer.speak_ssml_async(ssml_string).get()
    audio_duration = result.audio_duration
    synthesizer.synthesis_completed.disconnect_all()
    word_durations = []
    words_with_offset.sort()
    if len(words_with_offset) > 1:
        word_durations.append(timedelta(microseconds=words_with_offset[1][0] / 10))
    i = 1
    while i < len(words_with_offset) - 1:
        duration = timedelta(microseconds=words_with_offset[i + 1][0] / 10) - timedelta(
            microseconds=words_with_offset[i][0] / 10)
        word_durations.append(duration)
        i += 1
    last_duration = audio_duration - timedelta(microseconds=words_with_offset[-1][0] / 10)
    word_durations.append(last_duration)
    word_durations = [round(a.seconds * 1000 + a.microseconds / 1000) for a in word_durations]
    words_offset_duration = [(word, round(offset / 10000), duration) for (offset, word), duration in
                             zip(words_with_offset, word_durations)]
    return sum(word_durations), words_offset_duration


def switch(word_length):
    return {
        1: 0,
        2: 1,
        3: 1,
        4: 1,
        5: 1,
        6: 2,
        7: 2,
        8: 2,
        9: 2,
        10: 3,
        11: 3,
        12: 3,
        13: 3,
        0: -1,
    }.get(word_length, 4)


class RapidReadProApp(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.display_queue = None
        self.curr_index = 0
        self.first_run = True
        self.playback = None

    def create_widgets(self):
        self.ssml_strings = self.create_ssml_strings()
        self.master.attributes('-fullscreen', True)
        self.top_frame = ttk.Frame(self)
        self.top_text = tk.Text(self.top_frame, font=(self.master.FONT_OPTION, self.master.TOP_FONT_SIZE),
                                bg=self.master.COLOR_OPTION.bg, fg=self.master.COLOR_OPTION.text, width=1, height=1,
                                wrap="word")
        self.top_frame.grid(row=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.top_text.pack(fill=tk.BOTH, expand=1)

        self.center_frame = ttk.Frame(self)
        self.center_text = tk.Text(self.center_frame, font=(self.master.FONT_OPTION, self.master.CENTER_FONT_SIZE),
                                   bg=self.master.COLOR_OPTION.bg,
                                   fg=self.master.COLOR_OPTION.text, wrap="none", width=1, height=1)
        self.center_frame.grid(row=2, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.center_text.pack(fill=tk.BOTH, expand=1)

        self.bottom_frame = ttk.Frame(self)
        self.bottom_text = tk.Text(self.bottom_frame, font=(self.master.FONT_OPTION, self.master.BOTTOM_FONT_SIZE),
                                   bg=self.master.COLOR_OPTION.bg, fg=self.master.COLOR_OPTION.text, width=1, height=1,
                                   wrap="word")
        self.bottom_frame.grid(row=4, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.bottom_text.pack(fill=tk.BOTH, expand=1)

        self.top_line = tk.Canvas(self, height=self.master.SEPERATOR_LINE_HEIGHT, bg=self.master.COLOR_OPTION.bg)
        self.top_line.grid(row=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.bottom_line = tk.Canvas(self, height=self.master.SEPERATOR_LINE_HEIGHT, bg=self.master.COLOR_OPTION.bg)
        self.bottom_line.grid(row=3, sticky=(tk.N, tk.S, tk.E, tk.W))

        self.button_frame = ttk.Frame(self)
        self.back_window = ttk.Button(self.button_frame, text="Back Window", command=self.back_window)
        self.play_button = ttk.Button(self.button_frame, text="Play/Pause", command=self.play_pause)
        self.master.bind("<space>", lambda event: self.play_pause())
        self.back_button = ttk.Button(self.button_frame, text="Back Index", command=self.back)
        self.master.bind("b", lambda event: self.back())
        self.restart_button = ttk.Button(self.button_frame, text="Restart Index", command=self.restart)
        self.master.bind("r", lambda event: self.restart())
        self.skip_button = ttk.Button(self.button_frame, text="Skip Index", command=self.skip)
        self.master.bind("s", lambda event: self.skip())

        self.button_frame.grid(row=5, sticky=(tk.N, tk.S, tk.E, tk.W))

        self.back_window.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.play_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.back_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.restart_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.skip_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        self.rowconfigure(0, weight=15)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=2)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=15)
        self.rowconfigure(5, weight=1)
        self.columnconfigure(0, weight=1)

        self.start_button = ttk.Button(self, text="Start Reading",
                                       command=lambda: self.start_audio_and_display(self.master.START_INDEX))
        self.start_button.grid(row=2)

    def back_window(self):
        logging.info("Back Window button pressed")
        if self.display_queue:
            display_id_under_queue, word_index = self.display_queue
            if display_id_under_queue:
                self.master.after_cancel(display_id_under_queue)
        if self.playback:
            self.playback.stop()
        self.master.show_back_window()

    def play_pause(self):
        display_id_under_queue, word_index = self.display_queue
        if self.playback.playing:
            logging.info("Pause Button Pressed")
            # Pause audio
            self.playback.pause()
            # Cancel next display
            if display_id_under_queue:
                self.master.after_cancel(display_id_under_queue)
            self.display_queue = (None, word_index,)
        else:
            logging.info("Play Button Pressed")
            self.playback.resume()
            self.display_word(word_index)
            self.display_queue = (None, word_index,)

    def back(self):
        logging.info("Back Button Pressed")
        display_id_under_queue, word_index = self.display_queue
        # stop playing
        self.playback.stop()
        # Cancel next display
        if display_id_under_queue:
            self.master.after_cancel(display_id_under_queue)
        # start new execution
        self.start_audio_and_display(self.curr_index - 1)

    def restart(self):
        logging.info("Restart Button Pressed")
        display_id_under_queue, word_index = self.display_queue
        # stop playing
        self.playback.stop()
        # Cancel next display
        if display_id_under_queue:
            self.master.after_cancel(display_id_under_queue)
        # start new execution
        self.start_audio_and_display(self.curr_index)

    def skip(self):
        logging.info("Skip Button Pressed")
        display_id_under_queue, word_index = self.display_queue
        # stop playing
        self.playback.stop()
        # Cancel next display
        if display_id_under_queue:
            self.master.after_cancel(display_id_under_queue)
        # start new execution
        self.start_audio_and_display(self.curr_index + 1)

    def create_ssml_strings(self):
        ssml_strings = []
        for ssml_string, total_tokens, start_token, end_token in self.master.ssml_strings:
            header = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name="{self.master.VOICE}">"""
            footer = """</voice></speak>"""
            final_string = header
            for text, doc_tag, emphasis_level in ssml_string:
                text = text.replace('\n', ' ')
                if self.master.STYLE != 'default':
                    final_string += f"""<{doc_tag}><mstts:express-as style="{self.master.STYLE}"><prosody rate="{self.master.SPEED}"><emphasis level="{emphasis_level}">{text}</emphasis></prosody></mstts:express-as></{doc_tag}>"""
                else:
                    final_string += f"""<{doc_tag}><prosody rate="{self.master.SPEED}"><emphasis level="{emphasis_level}">{text}</emphasis></prosody></{doc_tag}>"""
            final_string += footer
            ssml_strings.append((final_string, total_tokens, start_token, end_token,))
        return ssml_strings

    def get_data_from_azure(self, ssml_string):
        self.file_path = os.path.join(self.master.tmp, f'{generate_filename()}.mp3')
        logging.info(self.file_path)
        speech_config = speechsdk.SpeechConfig(subscription=self.master.SPEECH_KEY,
                                               region=self.master.SPEECH_REGION)
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=self.file_path)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
        self.milliseconds_audio_duration, self.words_offset_duration = speak(synthesizer, ssml_string)

    def generate_words(self):
        words = Words()
        for word_index in range(len(self.words_offset_duration)):
            if word_index - self.master.NUM_WORDS_IN_CENTER_TEXT >= 0:
                left_words = [wd[0] for wd in
                              self.words_offset_duration[word_index - self.master.NUM_WORDS_IN_CENTER_TEXT:word_index]]
                left_words = ' '.join(left_words)
                previous_words = [wd[0] for wd in
                                  self.words_offset_duration[:word_index - self.master.NUM_WORDS_IN_CENTER_TEXT]]
                previous_words = ' '.join(previous_words)
            else:
                left_words = [wd[0] for wd in self.words_offset_duration[0:word_index]]
                left_words = ' '.join(left_words)
                previous_words = None
            if word_index + self.master.NUM_WORDS_IN_CENTER_TEXT < len(self.words_offset_duration):
                right_words = [wd[0] for wd in
                               self.words_offset_duration[
                               word_index + 1:word_index + self.master.NUM_WORDS_IN_CENTER_TEXT]]
                right_words = ' '.join(right_words)
                forward_words = [wd[0] for wd in
                                 self.words_offset_duration[word_index + self.master.NUM_WORDS_IN_CENTER_TEXT:]]
                forward_words = ' '.join(forward_words)
            else:
                right_words = [wd[0] for wd in
                               self.words_offset_duration[word_index + 1:len(self.words_offset_duration)]]
                right_words = ' '.join(right_words)
                forward_words = None
            word = self.words_offset_duration[word_index][0]
            word_offset = self.words_offset_duration[word_index][1]
            word_time = self.words_offset_duration[word_index][2]
            words.append(word, word_offset, word_time, left_words, right_words, previous_words, forward_words)
        return words

    def play_with_playback(self):
        playback = Playback()
        playback.load_file(self.file_path)
        return playback

    def display_word(self, word_index):
        if word_index == len(self.words):
            if self.playback.playing:
                self.playback.stop()
            self.start_audio_and_display(self.curr_index + 1)
            return
        word, word_offset, word_time, left_words, right_words, previous_words, forward_words = self.words[
            word_index]
        self.center_text.config(state=tk.NORMAL)
        self.center_text.delete("1.0", tk.END)
        if self.first_run:
            center_font = tkFont.Font(family=self.master.FONT_OPTION, size=self.master.CENTER_FONT_SIZE)
            center_font_height = center_font.metrics('linespace')
            total_height = self.center_frame.winfo_height()
            left_over_space = total_height - center_font_height
            spacing1 = 0
            if left_over_space > 0:
                spacing1 = left_over_space // 2
            self.center_text.config(spacing1=spacing1)
            self.first_run = False
        highlight_index_word = switch(len(word))
        left_words += ' '
        right_words = ' ' + right_words
        self.center_text.tag_add("left_words", "1.0", f"1.{len(left_words) - 1}")
        self.center_text.tag_config("left_words")
        self.center_text.insert(tk.END, left_words, "left_words")
        self.center_text.tag_add("center_word", f"1.{len(left_words)}", f"1.{len(left_words) + len(word) - 1}")
        self.center_text.tag_config("center_word", font=(self.master.FONT_OPTION, self.master.WORD_FONT_SIZE))
        self.center_text.insert(tk.END, word, "center_word")
        self.center_text.tag_add("right_words", f"1.{len(left_words) + len(word)}",
                                 f"1.{len(left_words + word + right_words)}")
        self.center_text.tag_config("right_words")
        self.center_text.insert(tk.END, right_words, "right_words")
        center_width = self.center_frame.winfo_width() // 2
        if self.center_text.bbox(f'1.{len(left_words) + highlight_index_word - 1}'):
            x_pos = self.center_text.bbox(f'1.{len(left_words) + highlight_index_word - 1}')[0]
        else:
            x_pos = 0
        self.center_text.tag_add('lmargin1', "1.0", "1.end")
        self.center_text.tag_config('lmargin1', lmargin1=center_width - x_pos)
        self.center_text.tag_add("highlight", f"1.{len(left_words) + highlight_index_word - 1}")
        self.center_text.tag_config("highlight", foreground=self.master.COLOR_OPTION.highlight)
        self.center_text.config(state=tk.DISABLED)
        self.top_text.delete("1.0", tk.END)
        if previous_words:
            self.top_text.insert(f"end", previous_words)
        self.bottom_text.delete("1.0", tk.END)
        if forward_words:
            self.bottom_text.insert("end", forward_words)
        self.top_line.create_line(0, self.top_line.winfo_height() // 2, self.top_line.winfo_width(),
                                  self.top_line.winfo_height() // 2, width=self.master.SEPERATOR_LINE_WIDTH,
                                  fill=self.master.COLOR_OPTION.text)
        self.top_line.create_line(self.center_frame.winfo_width() // 2, self.top_line.winfo_height() // 2,
                                  self.center_frame.winfo_width() // 2, self.top_line.winfo_height(),
                                  width=self.master.SEPERATOR_LINE_WIDTH, fill=self.master.COLOR_OPTION.text)
        self.bottom_line.create_line(0, self.bottom_line.winfo_height() // 2,
                                     self.bottom_line.winfo_width(), self.bottom_line.winfo_height() // 2,
                                     width=self.master.SEPERATOR_LINE_WIDTH,
                                     fill=self.master.COLOR_OPTION.text)
        self.bottom_line.create_line(self.center_frame.winfo_width() // 2, self.bottom_line.winfo_height() // 2,
                                     self.center_frame.winfo_width() // 2, 0,
                                     width=self.master.SEPERATOR_LINE_WIDTH,
                                     fill=self.master.COLOR_OPTION.text)
        if round(self.playback.curr_pos * 1000) - (word_offset + word_time) > 100 and word_time > 100:
            # reduce word time of next occurrence
            logging.info("Reducing word time of this occurrence")
            next_display_id = self.master.after(word_time - 100, self.display_word, word_index + 1)
            self.display_queue = (next_display_id, word_index + 1,)
        else:
            next_display_id = self.master.after(word_time, self.display_word, word_index + 1)
            self.display_queue = (next_display_id, word_index + 1,)

    def start_audio_and_display(self, index):
        if index >= (len(self.ssml_strings)):
            return
        if index == self.master.START_INDEX:
            self.start_button.destroy()
        ssml_string, total_tokens, start_token, end_token = self.ssml_strings[index]
        logging.info(f"Current Index: {index}")
        logging.info(f"Reading from start_token: {start_token}, end_token {end_token}")
        self.get_data_from_azure(ssml_string)
        self.curr_index = index
        logging.info(
            f"Audio Duration {timedelta(microseconds=self.milliseconds_audio_duration * 1000)}, words {len(self.words_offset_duration)}")
        logging.info(
            f"WPM: {len(self.words_offset_duration) / (timedelta(microseconds=self.milliseconds_audio_duration * 1000).seconds / 60)}")
        self.words = self.generate_words()
        self.playback = self.play_with_playback()
        self.playback.play()
        word_index = 0
        self.display_word(word_index)
        self.display_queue = (None, word_index)
        logging.info(f'Index {index} completed')
