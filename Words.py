class Words:
    def __init__(self):
        self.words_list = []
        self.words_offset_list = []
        self.words_time_list = []
        self.left_words_list = []
        self.right_words_list = []
        self.previous_words_list = []
        self.forward_words_list = []

    def append(self, word, offset, time, left_words, right_words, previous_words, forward_words):
        self.words_list.append(word)
        self.words_offset_list.append(offset)
        self.words_time_list.append(time)
        self.left_words_list.append(left_words)
        self.right_words_list.append(right_words)
        self.previous_words_list.append(previous_words)
        self.forward_words_list.append(forward_words)

    def __getitem__(self, index):
        return (self.words_list[index], self.words_offset_list[index], self.words_time_list[index],
                self.left_words_list[index], self.right_words_list[index],
                self.previous_words_list[index], self.forward_words_list[index])

    def __len__(self):
        return len(self.words_list)