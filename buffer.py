import os

class Buffer:
    def __init__(self, filename=None, read_only=False):
        self.filename = filename
        self.lines = [""]
        self.clipboard = ""
        self.undo_stack = []
        self.redo_stack = []
        self.read_only = read_only
        
        if filename and os.path.exists(filename):
            with open(filename, "r") as f:
                self.lines = f.read().splitlines() or [""]
                
    def save_undo(self):
        self.undo_stack.append([line[:] for line in self.lines])
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        
    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.lines)
            self.lines = self.undo_stack.pop()
            return True
        return False
        
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.lines)
            self.lines = self.redo_stack.pop()
            return True
        return False
        
    def insert_char(self, ch, cy, cx):
        self.save_undo()
        line = self.lines[cy]
        self.lines[cy] = line[:cx] + chr(ch) + line[cx:]
        
    def backspace(self, cy, cx):
        if cx == 0:
            if cy == 0:
                return cy, cx
            self.save_undo()
            prev = self.lines[cy - 1]
            self.lines[cy - 1] = prev + self.lines[cy]
            self.lines.pop(cy)
            return cy - 1, len(prev)
        else:
            self.save_undo()
            line = self.lines[cy]
            self.lines[cy] = line[:cx - 1] + line[cx:]
            return cy, cx - 1
            
    def delete_char(self, cy, cx):
        line = self.lines[cy]
        if cx >= len(line):
            if cy == len(self.lines) - 1:
                return
            self.save_undo()
            self.lines[cy] += self.lines[cy + 1]
            self.lines.pop(cy + 1)
        else:
            self.save_undo()
            self.lines[cy] = line[:cx] + line[cx + 1:]
            
    def newline(self, cy, cx):
        self.save_undo()
        line = self.lines[cy]
        self.lines[cy] = line[:cx]
        self.lines.insert(cy + 1, line[cx:])
        
    def yank_line(self, cy):
        self.clipboard = self.lines[cy]
        
    def delete_line(self, cy):
        if len(self.lines) == 1:
            self.lines[0] = ""
        else:
            self.save_undo()
            self.clipboard = self.lines.pop(cy)
            
    def paste(self, cy, cx):
        self.save_undo()
        line = self.lines[cy]
        self.lines[cy] = line[:cx] + self.clipboard + line[cx:]
        
    def delete_visual(self, y1, x1, y2, x2):
        self.save_undo()
        if (y1, x1) > (y2, x2):
            y1, x1, y2, x2 = y2, x2, y1, x1
        if y1 == y2:
            line = self.lines[y1]
            self.clipboard = line[x1:x2 + 1]
            self.lines[y1] = line[:x1] + line[x2 + 1:]
        else:
            self.clipboard = ""
            self.clipboard += self.lines[y1][x1:] + "\n"
            for y in range(y1 + 1, y2):
                self.clipboard += self.lines[y] + "\n"
            self.clipboard += self.lines[y2][:x2 + 1]
            self.lines[y1] = self.lines[y1][:x1] + self.lines[y2][x2 + 1:]
            for _ in range(y2, y1, -1):
                self.lines.pop(_)
                
    def get_visual_clipboard(self, y1, x1, y2, x2):
        if (y1, x1) > (y2, x2):
            y1, x1, y2, x2 = y2, x2, y1, x1
        if y1 == y2:
            return self.lines[y1][x1:x2 + 1]
        else:
            ret = self.lines[y1][x1:] + "\n"
            for y in range(y1 + 1, y2):
                ret += self.lines[y] + "\n"
            ret += self.lines[y2][:x2 + 1]
            return ret
            
    def search(self, query):
        for y, line in enumerate(self.lines):
            x = line.find(query)
            if x >= 0:
                return y, x
        return None, None
        
    def search_next(self, query, cy, cx):
        for y in range(cy, len(self.lines)):
            start = cx+1 if y == cy else 0
            x = self.lines[y].find(query, start)
            if x >= 0:
                return y, x
        for y in range(0, cy):
            x = self.lines[y].find(query)
            if x >= 0:
                return y, x
        return None, None

    def search_prev(self, query, cy, cx):
        for y in range(cy, -1, -1):
            end = cx-1 if y == cy else len(self.lines)
            x = self.lines[y].rfind(query, 0, end)
            if x >= 0:
                return y, x
        for y in range(len(self.lines)-1, cy, -1):
            x = self.lines[y].rfind(query)
            if x >= 0:
                return y, x
        return None, None

    def get_history(self):
        return self.undo_stack, self.redo_stack
        
    def save_file(self):
        if self.filename:
            with open(self.filename, "w") as f:
                f.write("\n".join(self.lines))
            return True
        return False

    def replace_all(self, search, replace):
        self.save_undo()
        count = 0
        for i, line in enumerate(self.lines):
            new_line, n = line.replace(search, replace), line.count(search)
            if n > 0:
                self.lines[i] = new_line
                count += n
        return count