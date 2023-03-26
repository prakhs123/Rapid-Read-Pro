import tkinter as tk
from tkinter import ttk


class IndexConfigurationApp(ttk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master

    def create_widgets(self):
        toc_lines = []
        for i, (ssml_string, total_tokens, start_token, end_token) in enumerate(self.master.ssml_strings):
            toc_lines.append(f"Index: {i}, Text Heading: {ssml_string[0][0][:40]}")
        self.listbox = tk.Listbox(self, width=50, height=min(len(toc_lines), 50))
        for toc_line in toc_lines:
            self.listbox.insert(tk.END, toc_line)
        self.listbox.bind("<<ListboxSelect>>", self.next_window)
        self.back_button = ttk.Button(self, text="Back", command=self.back_window)
        self.listbox.grid(row=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.back_button.grid(row=1, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.master.eval('tk::PlaceWindow . center')

    def back_window(self):
        self.master.show_back_window()

    def next_window(self, event):
        selected_index = self.listbox.get(self.listbox.curselection())
        start_index = int(selected_index[len("Index: ") - 1: selected_index.index(',')])
        self.master.START_INDEX = start_index
        self.master.show_next_window()