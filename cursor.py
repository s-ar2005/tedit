class Cursor:
    def __init__(self, lines):
        self.lines = lines
        self.cx = 0
        self.cy = 0
        self.scroll = 0
        self.visual_start = None
        self.marks = {}
        
    def fix_cursor(self):
        if self.cy < 0:
            self.cy = 0
        if self.cy >= len(self.lines):
            self.cy = len(self.lines) - 1
        if self.cx < 0:
            self.cx = 0
        if self.cx > len(self.lines[self.cy]):
            self.cx = len(self.lines[self.cy])
            
    def move_cursor(self, dy, dx):
        self.cy += dy
        self.fix_cursor()
        self.cx += dx
        if self.cx > len(self.lines[self.cy]):
            self.cx = len(self.lines[self.cy])
        if self.cx < 0:
            self.cx = 0
            
    def move_word_forward(self):
        line = self.lines[self.cy]
        i = self.cx + 1
        while i < len(line) and line[i].isalnum():
            i += 1
        while i < len(line) and not line[i].isalnum():
            i += 1
        self.cx = i if i <= len(line) else len(line)
        
    def move_word_backward(self):
        line = self.lines[self.cy]
        i = self.cx - 1
        while i > 0 and line[i].isalnum():
            i -= 1
        while i > 0 and not line[i].isalnum():
            i -= 1
        self.cx = i if i >= 0 else 0
        
    def get_visual_range(self):
        if self.visual_start is None:
            return None
        (y1, x1), (y2, x2) = self.visual_start, (self.cy, self.cx)
        if (y1, x1) > (y2, x2):
            (y1, x1), (y2, x2) = (y2, x2), (y1, x1)
        return (y1, x1, y2, x2)
        
    def visual_select(self):
        if self.visual_start is None:
            self.visual_start = (self.cy, self.cx)
        else:
            self.visual_start = None