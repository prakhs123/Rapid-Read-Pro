import argparse
import logging
import os
import random
import string
import sys
import tempfile
import time
import tkinter as tk
import wave
import xml.etree.ElementTree as ET
import xml.sax.saxutils
from datetime import timedelta
from queue import Queue, LifoQueue

import azure.cognitiveservices.speech as speechsdk
import pyaudio
from bs4 import BeautifulSoup
from ebooklib import epub
from just_playback import Playback
from requests_html import HTMLSession

# configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SPEECH_KEY = os.environ.get('SPEECH_KEY')
SPEECH_REGION = os.environ.get('SPEECH_REGION')

if not SPEECH_KEY:
    raise ValueError("SPEECH_KEY is not set.")

if not SPEECH_REGION:
    raise ValueError("SPEECH_REGION is not set.")


def speech_synthesis_get_available_voices(text):
    """gets the available voices list."""
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'),
                                           region=os.environ.get('SPEECH_REGION'))
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    result = speech_synthesizer.get_voices_async(text).get()
    # Check result
    if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
        logging.info('Voices successfully retrieved, they are:')
        for voice in result.voices:
            logging.info(voice.name)
    elif result.reason == speechsdk.ResultReason.Canceled:
        logging.error("Speech synthesis canceled; error details: {}".format(result.error_details))


def display_text_that_will_be_converted_to_speech(text):
    logging.debug("converting following text to speech")
    logging.debug(text)


def extract_first_emphasis_text(xml_string):
    # Parse the XML string into an ElementTree object
    xml_root = ET.fromstring(xml_string)

    # Find the first emphasis tag and extract its text
    emphasis = xml_root.find('.//{*}emphasis')
    emphasis_text = emphasis.text.strip() if emphasis is not None else ""

    # Return the emphasis text
    return emphasis_text


def extract_emphasis_text(xml_string):
    # Parse the XML string into an ElementTree object
    xml_root = ET.fromstring(xml_string)

    # Find all the emphasis tags and extract their text
    emphasis_texts = [emphasis.text.strip() for emphasis in xml_root.findall('.//{*}emphasis')]

    # Join the texts together with newlines
    return '\n'.join(emphasis_texts)


def get_speech_synthesizer(file_path):
    # This example requires environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'),
                                           region=os.environ.get('SPEECH_REGION'))
    speech_config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm)
    audio_config = speechsdk.audio.AudioOutputConfig(filename=file_path)
    return speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)


def create_ssml_string(text, doc_tag, emphasis_level):
    text = text.replace('\n', ' ')
    return f"""
        <{doc_tag}>
            <mstts:express-as style="{STYLE}">
                <prosody rate="{SPEED}">
                    <emphasis level="{emphasis_level}">
                        {text}
                    </emphasis>
                </prosody>
            </mstts:express-as>
        </{doc_tag}>"""


def create_ssml_strings(contents, token_number, num_tokens):
    def reset_ssml_string():
        nonlocal curr_ssml_string, current_token_number_inside_index, token_number
        if current_token_number_inside_index < 1:
            return
        if curr_ssml_string == header:
            return
        curr_ssml_string += footer
        ssml_strings.append((curr_ssml_string, current_token_number_inside_index, token_number,
                             token_number + current_token_number_inside_index))
        curr_ssml_string = header
        token_number += current_token_number_inside_index
        current_token_number_inside_index = 0

    ssml_strings = []
    header = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
        <voice name="{VOICE}">"""
    footer = """
        </voice>
    </speak>"""
    curr_ssml_string = header
    current_token_number_inside_index = 0

    for content in contents:
        text = xml.sax.saxutils.escape(content.get_text())

        if content.name.startswith('h1'):
            doc_tag = "s"
            emphasis_level = "strong"
            reset_ssml_string()
        elif content.name.startswith('h2') or content.name.startswith('h3'):
            doc_tag = "s"
            emphasis_level = "moderate"
            reset_ssml_string()
        else:
            doc_tag = "p"
            emphasis_level = "none"

        if current_token_number_inside_index >= num_tokens:
            reset_ssml_string()
        if text == '':
            reset_ssml_string()
            continue
        if len(text.split()) < 1:
            continue
        token_string = create_ssml_string(text, doc_tag, emphasis_level)
        curr_ssml_string += token_string
        current_token_number_inside_index += 1
        logging.debug(
            f"token_string:\n {token_string}\ntoken_index: {token_number + current_token_number_inside_index}")

    if curr_ssml_string:
        curr_ssml_string += footer
        ssml_strings.append((curr_ssml_string, current_token_number_inside_index, token_number,
                             token_number + current_token_number_inside_index))
        current_token_number_inside_index += 1

    return ssml_strings


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


def parse_args():
    parser = argparse.ArgumentParser(description='Text to speech converter')
    parser.add_argument('epub_or_html_file', type=str, metavar='EPUB_OR_HTML_FILE',
                        help='path to the EPUB/HTML file to convert to speech')
    parser.add_argument('--get-available-voices', type=str, default=None,
                        help="Enter a locale in BCP-47 format (e.g. en-US) that you want to get the voices of")
    parser.add_argument('--num-tokens', type=int, default=50,
                        help='number of tokens in one ssml string, default 1')
    parser.add_argument('--item-page', type=int, default=None,
                        help='index of the page in the EPUB file to convert to speech')
    parser.add_argument('--start-index', type=int, default=None,
                        help='index of ssml string to start speech')
    return parser.parse_args()


def initial_setup():
    args = parse_args()
    locale = args.get_available_voices
    if locale:
        speech_synthesis_get_available_voices(locale)
        sys.exit(0)
    item_page = args.item_page
    num_tokens = args.num_tokens
    try:
        if args.epub_or_html_file.endswith('.epub'):
            book = epub.read_epub(args.epub_or_html_file)
            items = [item for item in book.get_items() if item.get_type() == 9]
            for pg_no, item in enumerate(items):
                logging.info(f"ITEM PAGE: {pg_no}, ITEM CONTENTS: {item.file_name}")
            if item_page is None:
                item_page = int(input("Enter Item Page to read"))
            item = items[item_page]
            html = item.get_content()
        elif args.epub_or_html_file.startswith('http'):
            session = HTMLSession()
            r = session.get(args.epub_or_html_file)
            html = r.text
            session.close()
        elif args.epub_or_html_file.endswith('.html'):
            with open(args.epub_or_html_file, 'r') as file:
                html = file.read()
        else:
            raise Exception('File Not Supported')
    except FileNotFoundError:
        logging.error("The file is not found.")
        return
    soup = BeautifulSoup(html, 'html.parser')
    contents = []
    if args.epub_or_html_file.startswith('http'):
        if soup.article:
            contents = soup.article.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
        elif soup.section:
            contents = soup.section.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'])
    else:
        contents = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'dt', 'dd'])
    ssml_strings = create_ssml_strings(contents, 0, num_tokens)
    for i, (ssml_string, total_tokens, start_token, end_token) in enumerate(ssml_strings):
        logging.info(f"Index: {i}, Text Heading: {extract_first_emphasis_text(ssml_string)}")
    if args.start_index is None:
        si = int(input("Enter start index to read"))
    else:
        si = args.start_index
    return ssml_strings, si


def switch(word_length):
    return {
        1: 0,  # First letter
        2: 1,  # Second letter
        3: 1,  # Second letter
        4: 1,  # Second letter
        5: 1,  # Second letter
        6: 2,  # Third letter
        7: 2,  # Third letter
        8: 2,  # Third letter
        9: 2,  # Third letter
        10: 3,  # Fourth letter
        11: 3,  # Fourth letter
        12: 3,  # Fourth letter
        13: 3,  # Fourth letter
        0: -1,
    }.get(word_length, 4)  # Fifth letter


def display_word(playback):
    if displaying.get() is True:
        word_index, num_words, word, word_time, left_words, right_words, previous_words, forward_words, word_offset = curr_display_queue.get()
        if word_index < num_words:
            if not line_queue1.empty():
                id1, id2 = line_queue1.get()
                top_line.delete(id1)
                top_line.delete(id2)
            if not line_queue2.empty():
                id1, id2 = line_queue2.get()
                bottom_line.delete(id1)
                bottom_line.delete(id2)
            center_text.config(state=tk.NORMAL)
            center_text.delete("1.0", tk.END)
            highlight_index_word = switch(len(word))
            diff = (CENTER_TEXT_WIDTH * CENTER_TEXT_HEIGHT) // 2 - highlight_index_word - 1 - len(left_words) - 1
            left_words_m = ' ' * diff + left_words + ' '
            diff2 = (CENTER_TEXT_WIDTH * CENTER_TEXT_HEIGHT) // 2 - (
                        len(word) - highlight_index_word - 1 + len(right_words) + 1)
            right_words_m = ' ' + right_words + (' ' * diff2)
            full_text = left_words_m + word + right_words_m
            center_text.tag_add("left_words", "1.0", f"1.{len(left_words_m) - 1}")
            center_text.tag_config("left_words")
            center_text.insert(tk.END, left_words_m, "left_words")
            center_text.tag_add("center_word", f"1.{len(left_words_m)}", f"1.{len(left_words_m) + len(word) - 1}")
            center_text.tag_config("center_word", font=(FONT_NAME, WORD_FONT_SIZE))
            center_text.insert(tk.END, word, "center_word")
            center_text.tag_add("right_words", f"1.{len(left_words_m) + len(word)}",
                                f"1.{len(left_words_m + word + right_words_m)}")
            center_text.tag_config("right_words")
            center_text.insert(tk.END, right_words_m, "right_words")
            center_width = center_text.winfo_width() // 2
            x_pos = center_text.bbox(f'1.{CENTER_TEXT_WIDTH // 2 - 1}')[0]
            center_text.tag_add('lmargin1', "1.0", "1.end")
            center_text.tag_config('lmargin1', lmargin1=center_width - x_pos)
            center_text.tag_add("highlight", f"1.{CENTER_TEXT_WIDTH // 2 - 1}")
            center_text.tag_config("highlight", foreground=HIGHLIGHT_COLOR)
            center_text.config(state=tk.DISABLED)
            if previous_words:
                previous_words = '\n' * (TOP_TEXT_ROWS - 2 - (
                            len(previous_words) // (TOP_TEXT_HEIGHT * TOP_TEXT_WIDTH))) + previous_words
                top_text.delete("1.0", tk.END)
                top_text.insert(f"end", previous_words)
                top_text.tag_add("center", "1.0", "end")
            if forward_words:
                forward_words = '\n' + forward_words
                bottom_text.delete("1.0", tk.END)
                bottom_text.insert("end", forward_words)
                bottom_text.tag_add("center", "1.0", "end")
            _, _ = display_queue.get()
            id1 = top_line.create_line(0, top_line.winfo_height() // 2, center_text.winfo_width(),
                                       top_line.winfo_height() // 2, width=top_line_width, fill=top_line_color)
            x_pos = center_text.winfo_width() // 2
            id2 = top_line.create_line(x_pos, top_line.winfo_height() // 2, x_pos, top_line.winfo_height(),
                                       width=top_line_width, fill=top_line_color)
            line_queue1.put((id1, id2))
            id3 = bottom_line.create_line(0, bottom_line.winfo_height() // 2, center_text.winfo_width(),
                                          bottom_line.winfo_height() // 2, width=bottom_line_width,
                                          fill=bottom_line_color)
            x_pos = center_text.winfo_width() // 2
            id4 = bottom_line.create_line(x_pos, bottom_line.winfo_height() // 2, x_pos, 0, width=bottom_line_width,
                                          fill=bottom_line_color)
            line_queue2.put((id3, id4))
            # SYNC
            if word_index == num_words - 1:
                while playback.playing:
                    time.sleep(0.1)
                playback.stop()
                audio_queue.get()
                displaying.set(False)
                playing.set(False)
                return
            next_display_id = root.after(word_time, display_word, playback)
            display_queue.put((word_index + 1, next_display_id,))
            if playback and round(playback.curr_pos * 1000) - (word_offset + word_time) > 625:
                logging.debug(f"SYNCING {((round(playback.curr_pos * 1000) - (word_offset + word_time)) // 1000)}")
                playback.pause()
                time.sleep(((round(playback.curr_pos * 1000) - (word_offset + word_time)) // 1000))
                playback.resume()


def play_with_pyaudio(file_path):
    wf = wave.open(file_path, 'rb')

    # Define callback for playback (1)
    def callback(in_data, frame_count, time_info, status):
        data = wf.readframes(frame_count)
        # If len(data) is less than requested frame_count, PyAudio automatically
        # assumes the stream is finished, and the stream stops.
        if status in [pyaudio.paComplete, pyaudio.paAbort] or len(data) < frame_count:
            playing.set(False)
            audio_queue.get()

        return data, pyaudio.paContinue

    # Instantiate PyAudio and initialize PortAudio system resources (2)
    p = pyaudio.PyAudio()
    # Open stream using callback (3)
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True,
                    stream_callback=callback)
    return stream, p, wf


def play_with_playback(file_path):
    playback = Playback()  # creates an object for managing playback of a single audio file
    playback.load_file(file_path)
    return playback


def generate_filename():
    letters = string.ascii_lowercase
    filename = ''.join(random.choice(letters) for _ in range(10))
    return filename


def generate_words(word_duration_tuple_list):
    left_words_list = []
    right_words_list = []
    previous_words_list = []
    forward_words_list = []
    words_list = []
    words_time_list = []
    for word_index in range(len(word_duration_tuple_list)):
        if word_index - 5 >= 0:
            left_words = [wd[0] for wd in word_duration_tuple_list[word_index - 5:word_index]]
            left_words = ' '.join(left_words)
            previous_words = [wd[0] for wd in word_duration_tuple_list[:word_index - 5]]
            previous_words = ' '.join(previous_words)
        else:
            left_words = [wd[0] for wd in word_duration_tuple_list[0:word_index]]
            left_words = ' '.join(left_words)
            previous_words = None
        if word_index + 5 < len(word_duration_tuple_list):
            right_words = [wd[0] for wd in word_duration_tuple_list[word_index + 1:word_index + 5]]
            right_words = ' '.join(right_words)
            forward_words = [wd[0] for wd in word_duration_tuple_list[word_index + 5:]]
            forward_words = ' '.join(forward_words)
        else:
            right_words = [wd[0] for wd in word_duration_tuple_list[word_index + 1:len(word_duration_tuple_list)]]
            right_words = ' '.join(right_words)
            forward_words = None
        word = word_duration_tuple_list[word_index][0]
        word_time = word_duration_tuple_list[word_index][2]
        left_words_list.append(left_words)
        right_words_list.append(right_words)
        previous_words_list.append(previous_words)
        forward_words_list.append(forward_words)
        words_list.append(word)
        words_time_list.append(word_time)
    return words_list, words_time_list, left_words_list, right_words_list, previous_words_list, forward_words_list


def start_audio_and_display(index):
    if playing.get() is True:
        root.wait_variable(playing)
    if displaying.get() is True:
        root.wait_variable(displaying)
    ssml_string, total_tokens, start_token, end_token = ssml_strings[index]
    logging.info(f"Current Index: {index}")
    logging.info(f"Reading from start_token: {start_token}, end_token {end_token}")

    file_path = os.path.join(temp_dir, f'{generate_filename()}.wav')
    logging.info(file_path)
    synthesizer = get_speech_synthesizer(file_path)
    milliseconds_audio_duration, words_offset_duration = speak(synthesizer, ssml_string)
    global words_offset_duration_main
    words_offset_duration_main = words_offset_duration.copy()
    logging.info(
        f"Audio Duration {timedelta(microseconds=milliseconds_audio_duration * 1000)}, words {len(words_offset_duration)}")
    logging.info(
        f"WPM: {len(words_offset_duration) / (timedelta(microseconds=milliseconds_audio_duration * 1000).seconds / 60)}")
    logging.info(f"Scheduling next index after {timedelta(microseconds=milliseconds_audio_duration * 1000)}")

    words_list, words_time_list, left_words_list, right_words_list, previous_words_list, forward_words_list = generate_words(
        words_offset_duration)

    for word_index in range(len(words_list)):
        word, word_time, left_words, right_words, previous_words, forward_words = \
            words_list[word_index], words_time_list[word_index], left_words_list[word_index], right_words_list[
                word_index], \
            previous_words_list[word_index], forward_words_list[word_index]
        curr_display_queue.put(
            (word_index, len(words_list), word, word_time, left_words, right_words, previous_words, forward_words,
             words_offset_duration[word_index][1]))

    next_id = root.after(milliseconds_audio_duration, start_audio_and_display, index + 1)
    execution_stack.put(next_id)

    playing.set(True)
    displaying.set(True)
    # stream, p, wf = play_with_pyaudio(file_path)
    playback = play_with_playback(file_path)
    playback.play()
    # playback = None
    next_display_id = root.after(0, display_word, playback)
    audio_queue.put((playback, index,))
    display_queue.put((0, next_display_id,))

    logging.info(f'Index {index} completed')


# create button functions
def play_pause(evt):
    playback, index = audio_queue.get()
    word_index, display_id_under_queue = display_queue.get()
    if playing.get() and displaying.get():
        logging.info("Pause Button Pressed")
        # Pause audio
        playback.pause()
        playing.set(False)
        # Cancel next display
        if display_id_under_queue:
            root.after_cancel(display_id_under_queue)
        displaying.set(False)
        # stop next execution
        if execution_stack.empty() is False:
            root.after_cancel(execution_stack.get())
        audio_queue.put((playback, index,))
        display_queue.put((word_index, None,))
    elif not playing.get() and not displaying.get():
        logging.info("Play Button Pressed")
        global words_offset_duration_main
        time_left = [d for _, _, d in words_offset_duration_main[word_index:]]
        time_left = sum(time_left)
        # schedule next execution
        next_id = root.after(time_left, start_audio_and_display, index + 1)
        execution_stack.put(next_id)
        # Start audio
        audio_queue.put((playback, index,))
        playing.set(True)
        playback.resume()

        # Start display
        displaying.set(True)
        next_display_id = root.after(0, display_word, playback)
        display_queue.put((word_index, next_display_id,))


def back(evt):
    logging.info("Back Button Pressed")
    playback, index = audio_queue.get()
    _, display_id_under_queue = display_queue.get()
    # stop playing
    playback.stop()
    playing.set(False)
    # Cancel next display
    if display_id_under_queue:
        root.after_cancel(display_id_under_queue)
    while not curr_display_queue.empty():
        curr_display_queue.get()
    displaying.set(False)
    # Cancel next execution
    if execution_stack.empty() is False:
        root.after_cancel(execution_stack.get())
    # start new execution
    next_id = root.after(0, start_audio_and_display, index - 1)
    execution_stack.put(next_id)


def restart(evt):
    logging.info("Restart Button Pressed")
    playback, index = audio_queue.get()
    _, display_id_under_queue = display_queue.get()
    # stop playing
    playback.stop()
    playing.set(False)
    # Cancel next display
    if display_id_under_queue:
        root.after_cancel(display_id_under_queue)
    while not curr_display_queue.empty():
        curr_display_queue.get()
    displaying.set(False)
    # Cancel next execution
    if execution_stack.empty() is False:
        root.after_cancel(execution_stack.get())
    # Start new execution
    next_id = root.after(0, start_audio_and_display, index)
    execution_stack.put(next_id)


def skip(evt):
    logging.info("Skip Button Pressed")
    playback, index = audio_queue.get()
    _, display_id_under_queue = display_queue.get()
    # stop playing
    playback.stop()
    playing.set(False)
    # Cancel next display
    if display_id_under_queue:
        root.after_cancel(display_id_under_queue)
    while not curr_display_queue.empty():
        curr_display_queue.get()
    displaying.set(False)
    # cancel next execution
    if execution_stack.empty() is False:
        root.after_cancel(execution_stack.get())
    # start new execution
    next_id = root.after(0, start_audio_and_display, index + 1)
    execution_stack.put(next_id)


if __name__ == '__main__':

    SPEED = "+0.00%"
    VOICE = "en-US-AriaNeural"
    STYLE = "narration-professional"
    BACKGROUND_COLOR = '#F7ECCF'
    TEXT_COLOR = "#77614F"
    HIGHLIGHT_COLOR = "#F57A10"
    FONT_NAME = 'Merriweather'
    TOP_FONT_SIZE = 24
    BOTTOM_FONT_SIZE = 24
    CENTER_FONT_SIZE = 48
    WORD_FONT_SIZE = 72
    SEPERATOR_LINE_WIDTH = 3
    TOP_TEXT_HEIGHT = 15
    TOP_TEXT_WIDTH = 100
    TOP_TEXT_ROWS = 4
    CENTER_TEXT_HEIGHT = 1
    CENTER_TEXT_WIDTH = 100
    CENTER_TEXT_ROWS = 1
    BOTTOM_TEXT_HEIGHT = 15
    BOTTOM_TEXT_WIDTH = 100
    BOTTOM_TEXT_ROWS = 4
    ssml_strings, start_index = initial_setup()
    root = tk.Tk()
    root.config(bg=BACKGROUND_COLOR)
    audio_queue = Queue()
    display_queue = Queue()
    curr_display_queue = Queue()
    execution_stack = LifoQueue()
    line_queue1 = LifoQueue()
    line_queue2 = LifoQueue()
    playing = tk.BooleanVar()
    displaying = tk.BooleanVar()
    words_offset_duration_main = []
    with tempfile.TemporaryDirectory() as temp_dir:
        # create buttons with hotkeys
        play_button = tk.Button(root, text="Play", command=lambda: play_pause(None))
        pause_button = tk.Button(root, text="Pause", command=lambda: play_pause(None))

        root.bind("<space>", lambda event: play_pause(event))
        back_button = tk.Button(root, text="Back", command=lambda: back(None))
        root.bind("b", lambda event: back(back))

        restart_button = tk.Button(root, text="Restart", command=lambda: restart(None))
        root.bind("r", lambda event: restart(event))

        skip_button = tk.Button(root, text="Skip", command=lambda: skip(None))
        root.bind("s", lambda event: skip(event))

        play_button.grid(row=11, column=0, sticky="sew")
        pause_button.grid(row=11, column=1, sticky="sew")
        back_button.grid(row=11, column=2, sticky="sew")
        restart_button.grid(row=11, column=3, sticky="sew")
        skip_button.grid(row=11, column=4, sticky="sew")

        top_text = tk.Text(root, font=(FONT_NAME, TOP_FONT_SIZE), bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
                           height=TOP_TEXT_HEIGHT, width=TOP_TEXT_WIDTH, wrap="word")
        top_text.tag_configure("center", justify='center')
        top_text.grid(row=0, column=0, rowspan=TOP_TEXT_ROWS, columnspan=5, sticky="sew")

        center_text = tk.Text(root, font=(FONT_NAME, CENTER_FONT_SIZE), bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
                              height=CENTER_TEXT_HEIGHT, width=CENTER_TEXT_WIDTH, wrap="none", spacing1=24, spacing2=24)
        center_text.grid(row=5, rowspan=CENTER_TEXT_ROWS, column=0, columnspan=5, sticky="nsew")

        bottom_text = tk.Text(root, font=(FONT_NAME, BOTTOM_FONT_SIZE), bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
                              height=BOTTOM_TEXT_HEIGHT, width=BOTTOM_TEXT_WIDTH, wrap="word")
        bottom_text.tag_configure("center", justify="center")
        bottom_text.grid(row=7, column=0, rowspan=BOTTOM_TEXT_ROWS, columnspan=5, sticky="new")

        top_line = tk.Canvas(root, height=1, bg=BACKGROUND_COLOR)
        top_line.grid(row=4, column=0, columnspan=5, sticky="nsew")
        top_line_color = TEXT_COLOR
        top_line_width = SEPERATOR_LINE_WIDTH
        bottom_line = tk.Canvas(root, height=1, bg=BACKGROUND_COLOR)
        bottom_line.grid(row=6, column=0, columnspan=5, sticky="nsew")
        bottom_line_color = TEXT_COLOR
        bottom_line_width = SEPERATOR_LINE_WIDTH

        for i in range(12):
            root.rowconfigure(i, weight=1)
        root.rowconfigure(5, weight=2)
        for i in range(5):
            root.columnconfigure(i, weight=1)
        if start_index >= len(ssml_strings):
            sys.exit(0)

        PLAY_BUTTON = tk.Button(root, command=lambda: start_audio_and_display(start_index))
        root.bind('<Return>', lambda event: start_audio_and_display(start_index))
        root.mainloop()
