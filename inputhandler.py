import curses

class InputHandler:
    def __init__(self, stdscr, buffer, cursor, renderer):
        self.stdscr = stdscr
        self.buffer = buffer
        self.cursor = cursor
        self.renderer = renderer
        self.mode = "NORMAL"
        self.msg = ""
        
    def handle_insert_mode(self, k):
        if k == 27:
            self.mode = "NORMAL"
        elif k in (curses.KEY_BACKSPACE, 127):
            self.cursor.cy, self.cursor.cx = self.buffer.backspace(self.cursor.cy, self.cursor.cx)
        elif k == 10:
            self.buffer.newline(self.cursor.cy, self.cursor.cx)
            self.cursor.cy += 1
            self.cursor.cx = 0
        elif k == curses.KEY_DC:
            self.buffer.delete_char(self.cursor.cy, self.cursor.cx)
        elif k == curses.KEY_LEFT:
            self.cursor.move_cursor(0, -1)
        elif k == curses.KEY_RIGHT:
            self.cursor.move_cursor(0, 1)
        elif k == curses.KEY_UP:
            self.cursor.move_cursor(-1, 0)
        elif k == curses.KEY_DOWN:
            self.cursor.move_cursor(1, 0)
        elif 32 <= k <= 126:
            self.buffer.insert_char(k, self.cursor.cy, self.cursor.cx)
            self.cursor.cx += 1
        else:
            self.msg = f"Unhandled {k}"
            
    def handle_normal_mode(self, k):
        if k == ord("i"):
            self.mode = "INSERT"
        elif k == ord("h") or k == curses.KEY_LEFT:
            self.cursor.move_cursor(0, -1)
        elif k == ord("l") or k == curses.KEY_RIGHT:
            self.cursor.move_cursor(0, 1)
        elif k == ord("j") or k == curses.KEY_DOWN:
            self.cursor.move_cursor(1, 0)
        elif k == ord("k") or k == curses.KEY_UP:
            self.cursor.move_cursor(-1, 0)
        elif k == ord("w"):
            self.cursor.move_word_forward()
        elif k == ord("b"):
            self.cursor.move_word_backward()
        elif k == ord("y"):
            self.buffer.yank_line(self.cursor.cy)
        elif k == ord("d"):
            k2 = self.stdscr.getch()
            if k2 == ord("d"):
                self.buffer.delete_line(self.cursor.cy)
                if self.cursor.cy >= len(self.buffer.lines):
                    self.cursor.cy = len(self.buffer.lines) - 1
                self.cursor.cx = 0
        elif k == ord("p"):
            self.buffer.paste(self.cursor.cy, self.cursor.cx)
            self.cursor.cx += len(self.buffer.clipboard)
        elif k == ord("u"):
            if self.buffer.undo():
                self.cursor.cx = 0
                self.cursor.cy = 0
                self.cursor.fix_cursor()
        elif k == ord("r"):
            if self.buffer.redo():
                self.cursor.cx = 0
                self.cursor.cy = 0
                self.cursor.fix_cursor()
        elif k == ord("/"):
            self.search()
        elif k == ord("v"):
            self.mode = "VISUAL"
            self.cursor.visual_start = None
        elif k == 27:
            return "exit_confirm"
        else:
            self.msg = f"Unhandled {chr(k)}"
            
    def handle_visual_mode(self, k):
        if k == ord("v"):
            self.mode = "NORMAL"
            self.cursor.visual_start = None
        elif k == ord("d"):
            vr = self.cursor.get_visual_range()
            if vr:
                y1, x1, y2, x2 = vr
                self.buffer.delete_visual(y1, x1, y2, x2)
                self.cursor.cy = y1
                self.cursor.cx = x1
                self.cursor.visual_start = None
        elif k == ord("y"):
            vr = self.cursor.get_visual_range()
            if vr:
                y1, x1, y2, x2 = vr
                self.buffer.clipboard = self.buffer.get_visual_clipboard(y1, x1, y2, x2)
        elif k == ord("h") or k == curses.KEY_LEFT:
            self.cursor.move_cursor(0, -1)
        elif k == ord("l") or k == curses.KEY_RIGHT:
            self.cursor.move_cursor(0, 1)
        elif k == ord("j") or k == curses.KEY_DOWN:
            self.cursor.move_cursor(1, 0)
        elif k == ord("k") or k == curses.KEY_UP:
            self.cursor.move_cursor(-1, 0)
        elif k == 27:
            self.mode = "NORMAL"
            self.cursor.visual_start = None
        else:
            self.msg = f"Unhandled VISUAL {chr(k)}"
            
    def handle_command_mode(self, cmd_str):
        if cmd_str == "w":
            if self.buffer.save_file():
                self.msg = "File saved"
            else:
                filename = self.renderer.get_input("Save as: ")
                if filename:
                    self.buffer.filename = filename
                    if self.buffer.save_file():
                        self.msg = "File saved"
        elif cmd_str == "q":
            if not self.buffer.undo_stack:
                return "quit"
            else:
                self.msg = "Unsaved changes! Use q! to quit without saving."
        elif cmd_str == "wq":
            if self.buffer.save_file():
                return "quit"
            else:
                filename = self.renderer.get_input("Save as: ")
                if filename:
                    self.buffer.filename = filename
                    if self.buffer.save_file():
                        return "quit"
        elif cmd_str == "q!":
            return "quit"
        else:
            self.msg = f"Unknown command: {cmd_str}"
            
    def search(self):
        s = self.renderer.get_input("Search: ")
        if not s:
            return
        y, x = self.buffer.search(s)
        if y is not None:
            self.cursor.cy = y
            self.cursor.cx = x
            self.cursor.scroll = self.cursor.cy
            self.msg = f"Found '{s}' at {y+1},{x+1}"
        else:
            self.msg = f"'{s}' not found"