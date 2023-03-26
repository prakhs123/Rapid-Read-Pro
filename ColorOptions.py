from enum import Enum


class COLOR_OPTIONS(Enum):
    personal_favourite = ('Personal Favourite', '#F7ECCF', '#77614F', '#F57A10')
    pale_pink = ('Pale pink', '#F3EFEF', '#333333', '#F7B32B')
    light_gray_1 = ('Light gray 1', '#F5F5F5', '#333333', '#4A90E2')
    light_gray_2 = ('Light gray 2', '#E6E6E6', '#3E3E3E', '#FF9900')
    nearly_white_1 = ('Nearly white 1', '#F2F2F2', '#4A4A4A', '#7C8E00')
    pale_gray = ('Pale gray', '#ECECEC', '#424242', '#ED1C24')
    cream = ('Cream', '#FFF5E6', '#333333', '#FFCC33')
    light_gray_3 = ('Light gray 3', '#F0F0F0', '#3B3B3B', '#003366')
    nearly_white_2 = ('Nearly white 2', '#EDEDED', '#333333', '#00BFFF')
    pale_beige = ('Pale beige', '#FAF6F1', '#444444', '#FF6347')

    def __init__(self, name, bg, text, highlight):
        self._name_ = name
        self.bg = bg
        self.text = text
        self.highlight = highlight

    def __repr__(self):
        return self._name_