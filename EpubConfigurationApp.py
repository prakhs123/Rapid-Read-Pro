import tkinter as tk
from tkinter import ttk

import pdfplumber
from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup
import xml.sax.saxutils


class EpubConfigurationApp(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master

    def create_widgets(self):
        self.num_tokens = tk.StringVar(value=self.master.NUM_TOKENS)
        self.tokens_label = ttk.Label(self, text="Number of tokens/Number of pages for pdf")
        self.tokens_entry = ttk.Entry(self, textvariable=self.num_tokens)
        self.listbox = tk.Listbox(self, width=50)
        lines = self.get_contents()
        if lines:
            self.listbox.config(height=min(len(lines), 50))
            for line in lines:
                self.listbox.insert(tk.END, line)
            self.listbox.bind("<<ListboxSelect>>", self.next_window)
        self.back_button = ttk.Button(self, text="Back", command=self.back_window)
        self.tokens_label.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.tokens_entry.grid(row=0, column=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.listbox.grid(row=1, columnspan=2, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.back_button.grid(row=2, columnspan=2, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.master.eval('tk::PlaceWindow . center')

    def get_contents(self):
        try:
            if self.master.FILE.endswith(".epub"):
                book = epub.read_epub(self.master.FILE)
                self.items = [item for item in book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]
            elif self.master.FILE.endswith(".pdf"):
                pdf = pdfplumber.open(self.master.FILE)
                self.items = range(len(pdf.pages))
                pdf.close()
            else:
                raise FileNotFoundError("non supported file")
        except FileNotFoundError as e:
            self.listbox.insert(tk.END, "Enter EPub/Pdf to continue")
            self.listbox.config(height=1)
            return []
        lines = []
        for pg_no, item in enumerate(self.items):
            if self.master.FILE.endswith(".epub"):
                lines.append(f"ITEM PAGE: {pg_no}, ITEM CONTENTS: {item.file_name}\n")
            else:
                lines.append(f"ITEM PAGE: {pg_no},")
        return lines

    def back_window(self):
        self.master.show_back_window()

    def next_window(self, event):
        selected_item = self.listbox.get(self.listbox.curselection())
        item_page = int(selected_item[len("ITEM PAGE: ") - 1: selected_item.index(',')])
        if self.master.FILE.endswith(".epub"):
            item = self.items[item_page]
            html = item.get_content()
            soup = BeautifulSoup(html, 'html.parser')
            for s in soup.find_all(['tr', 'th', 'td']):
                s.extract()
            cc = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'dt', 'dd', 'li'])
            contents = []
            for content in cc:
                if content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'dt', 'dd', 'li']):
                    continue
                contents.append(content)
            self.master.ssml_strings = self.create_ssml_strings(contents, int(self.num_tokens.get()))
        else:
            self.create_ssml_strings_for_pdf(item_page)
        self.master.show_next_window()

    def create_ssml_strings_for_pdf(self, item_page):
        num_tokens = int(self.num_tokens.get())
        pdf = pdfplumber.open(self.master.FILE)
        self.master.ssml_strings = []
        for page in pdf.pages[item_page:item_page+num_tokens]:
            lines = page.extract_text_simple(x_tolerance=1, y_tolerance=3).replace('ﬁ', 'fi').split('\n')
            start_token = 0
            token_number = 0
            paragraphs = []
            current_paragraph = ""
            for line in lines:
                current_paragraph += xml.sax.saxutils.escape(line)
                if len(line) < 48:
                    # new paragraph
                    paragraphs.append((current_paragraph, "p", "none"))
                    current_paragraph = ""
                    token_number += 1
            if current_paragraph:
                paragraphs.append((current_paragraph, "p", "none"))
            self.master.ssml_strings.append((paragraphs, token_number, start_token, token_number))
        pdf.close()

    def create_ssml_strings(self, contents, num_tokens):
        def reset_ssml_string():
            nonlocal curr_ssml_string, current_token_number_inside_index, token_number
            if current_token_number_inside_index < 1:
                return
            if curr_ssml_string is None:
                return
            ssml_strings.append((curr_ssml_string, current_token_number_inside_index, token_number,
                                 token_number + current_token_number_inside_index))
            curr_ssml_string = []
            token_number += current_token_number_inside_index
            current_token_number_inside_index = 0

        token_number = 0
        ssml_strings = []
        current_token_number_inside_index = 0
        curr_ssml_string = []

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
            token_string = (text, doc_tag, emphasis_level)
            curr_ssml_string.append(token_string)
            current_token_number_inside_index += 1

        if curr_ssml_string:
            ssml_strings.append((curr_ssml_string, current_token_number_inside_index, token_number,
                                 token_number + current_token_number_inside_index))
            current_token_number_inside_index += 1

        return ssml_strings