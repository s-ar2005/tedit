import curses
import json
import os

class InputHandler:
    def __init__(self, stdscr, buffer, cursor, renderer):
        self.stdscr = stdscr
        self.buffer = buffer
        self.cursor = cursor
        self.renderer = renderer
        self.mode = "NORMAL"
        self.msg = ""
        self.keymap = self.load_keybindings()
        self.last_search = None
        self.last_search_idx = None
        
    def load_keybindings(self):
        default = {
            "insert": "i",
            "left": "h",
            "right": "l",
            "up": "k",
            "down": "j",
            "word_forward": "w",
            "word_backward": "b",
            "yank": "y",
            "delete": "d",
            "paste": "p",
            "undo": "u",
            "redo": "r",
            "search": "/",
            "visual": "v",
            "escape": 27,
            "toggle_sidebar": 266,
            "toggle_line_numbers": 267,
            "page_up": 339,
            "page_down": 338,
            "tab": 9,
            "f1": 265,
            "f2": 266,
            "f3": 267,
            "delete_key": 330
        }
        config_path = os.path.expanduser("~/.config/tedit.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                usermap = json.load(f)
                default.update(usermap)
        elif os.path.exists("keybindings.json"):
            with open("keybindings.json") as f:
                usermap = json.load(f)
                default.update(usermap)
        return default
            
    def handle_insert_mode(self, k):
        km = self.keymap
        if getattr(self.buffer, 'read_only', False):
            self.msg = "Read-only buffer!"
            return
        if k == km.get("escape", 27):
            self.mode = "NORMAL"
        elif k in (curses.KEY_BACKSPACE, 127):
            self.cursor.cy, self.cursor.cx = self.buffer.backspace(self.cursor.cy, self.cursor.cx)
        elif k == 10:
            prev_line = self.buffer.lines[self.cursor.cy]
            indent = len(prev_line) - len(prev_line.lstrip(' '))
            self.buffer.newline(self.cursor.cy, self.cursor.cx)
            self.cursor.cy += 1
            self.cursor.cx = indent
            self.buffer.lines[self.cursor.cy] = ' ' * indent + self.buffer.lines[self.cursor.cy]
        elif k == km.get("delete_key", curses.KEY_DC):
            self.buffer.delete_char(self.cursor.cy, self.cursor.cx)
        elif k == km.get("left", ord("h")) or k == curses.KEY_LEFT:
            self.cursor.move_cursor(0, -1)
        elif k == km.get("right", ord("l")) or k == curses.KEY_RIGHT:
            self.cursor.move_cursor(0, 1)
        elif k == km.get("up", ord("k")) or k == curses.KEY_UP:
            self.cursor.move_cursor(-1, 0)
        elif k == km.get("down", ord("j")) or k == curses.KEY_DOWN:
            self.cursor.move_cursor(1, 0)
        elif k == km.get("page_up", curses.KEY_PPAGE):
            maxy, _ = self.renderer.stdscr.getmaxyx()
            self.cursor.move_cursor(-(maxy-1), 0)
        elif k == km.get("page_down", curses.KEY_NPAGE):
            maxy, _ = self.renderer.stdscr.getmaxyx()
            self.cursor.move_cursor((maxy-1), 0)
        elif 32 <= k <= 126:
            self.buffer.insert_char(k, self.cursor.cy, self.cursor.cx)
            self.cursor.cx += 1
        else:
            self.msg = f"Unhandled {k}"
            
    def handle_normal_mode(self, k):
        km = self.keymap
        if k == ord("m"):
            k2 = self.stdscr.getch()
            if 97 <= k2 <= 122:
                self.cursor.marks = getattr(self.cursor, 'marks', {})
                self.cursor.marks[chr(k2)] = (self.cursor.cy, self.cursor.cx)
                self.msg = f"Mark {chr(k2)} set"
                return
        if k == ord("'"):
            k2 = self.stdscr.getch()
            if 97 <= k2 <= 122:
                self.cursor.marks = getattr(self.cursor, 'marks', {})
                pos = self.cursor.marks.get(chr(k2))
                if pos:
                    self.cursor.cy, self.cursor.cx = pos
                    self.cursor.fix_cursor()
                    self.msg = f"Jumped to mark {chr(k2)}"
                else:
                    self.msg = f"No mark {chr(k2)}"
                return
        if k == curses.KEY_F1:
            self.buffer.lines = self.help_text().splitlines()
            self.buffer.filename = "[HELP]"
            self.cursor.cy = 0
            self.cursor.cx = 0
            self.msg = "Help opened"
            return
        if k == km.get("toggle_sidebar", 266):
            self.renderer.toggle_sidebar()
            return
        if k == km.get("toggle_line_numbers", 267):
            self.renderer.toggle_line_numbers()
            return
        if self.renderer.sidebar:
            if k == curses.KEY_UP:
                self.renderer.selected_file = max(0, self.renderer.selected_file - 1)
                return
            elif k == curses.KEY_DOWN:
                self.renderer.selected_file = min(len(self.renderer.files) - 1, self.renderer.selected_file + 1)
                return
            elif k in (10, 13):
                fname = self.renderer.files[self.renderer.selected_file]
                self.renderer.toggle_sidebar()
                return f":e {fname}"
        if k == ord(km["insert"]):
            self.mode = "INSERT"
        elif k == ord(km["left"]) or k == curses.KEY_LEFT:
            self.cursor.move_cursor(0, -1)
        elif k == ord(km["right"]) or k == curses.KEY_RIGHT:
            self.cursor.move_cursor(0, 1)
        elif k == ord(km["down"]) or k == curses.KEY_DOWN:
            self.cursor.move_cursor(1, 0)
        elif k == ord(km["up"]) or k == curses.KEY_UP:
            self.cursor.move_cursor(-1, 0)
        elif k == ord(km["word_forward"]):
            self.cursor.move_word_forward()
        elif k == ord(km["word_backward"]):
            self.cursor.move_word_backward()
        elif k == ord(km["yank"]):
            self.buffer.yank_line(self.cursor.cy)
        elif k == ord(km["delete"]):
            k2 = self.stdscr.getch()
            if k2 == ord(km["delete"]):
                self.buffer.delete_line(self.cursor.cy)
                if self.cursor.cy >= len(self.buffer.lines):
                    self.cursor.cy = len(self.buffer.lines) - 1
                self.cursor.cx = 0
        elif k == ord(km["paste"]):
            self.buffer.paste(self.cursor.cy, self.cursor.cx)
            self.cursor.cx += len(self.buffer.clipboard)
        elif k == ord(km["undo"]):
            if self.buffer.undo():
                self.msg = "Undo"
                self.cursor.fix_cursor()
            else:
                self.msg = "Nothing to undo"
        elif k == ord(km["redo"]):
            if self.buffer.redo():
                self.msg = "Redo"
                self.cursor.fix_cursor()
            else:
                self.msg = "Nothing to redo"
        elif k == ord(km["search"]):
            self.search()
        elif k == ord("n"):
            if self.last_search:
                y, x = self.buffer.search_next(self.last_search, self.cursor.cy, self.cursor.cx)
                if y is not None:
                    self.cursor.cy = y
                    self.cursor.cx = x
                    self.cursor.scroll = self.cursor.cy
                    self.msg = f"Next: '{self.last_search}' at {y+1},{x+1}"
                else:
                    self.msg = f"No further match for '{self.last_search}'"
            return
        elif k == ord("N"):
            if self.last_search:
                y, x = self.buffer.search_prev(self.last_search, self.cursor.cy, self.cursor.cx)
                if y is not None:
                    self.cursor.cy = y
                    self.cursor.cx = x
                    self.cursor.scroll = self.cursor.cy
                    self.msg = f"Prev: '{self.last_search}' at {y+1},{x+1}"
                else:
                    self.msg = f"No previous match for '{self.last_search}'"
            return
        elif k == ord(km["visual"]):
            self.mode = "VISUAL"
            self.cursor.visual_select()
        elif k == km["escape"]:
            return "exit_confirm"
        elif k == km.get("page_up", curses.KEY_PPAGE):
            maxy, _ = self.renderer.stdscr.getmaxyx()
            self.cursor.move_cursor(-(maxy-1), 0)
        elif k == km.get("page_down", curses.KEY_NPAGE):
            maxy, _ = self.renderer.stdscr.getmaxyx()
            self.cursor.move_cursor((maxy-1), 0)
        elif k == km.get("tab", 9):
            pass
        else:
            try:
                self.msg = f"Unhandled {chr(k)}"
            except:
                self.msg = f"Unhandled {k}"
            
    def handle_visual_mode(self, k):
        km = self.keymap
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
                self.mode = "NORMAL"
                if y1 == y2:
                    self.msg = f"Cut {abs(x2-x1)+1} chars"
                else:
                    self.msg = f"Cut {abs(y2-y1)+1} lines"
        elif k == ord("y"):
            vr = self.cursor.get_visual_range()
            if vr:
                y1, x1, y2, x2 = vr
                self.buffer.clipboard = self.buffer.get_visual_clipboard(y1, x1, y2, x2)
                self.cursor.visual_start = None
                self.mode = "NORMAL"
                if y1 == y2:
                    self.msg = f"Yanked {abs(x2-x1)+1} chars"
                else:
                    self.msg = f"Yanked {abs(y2-y1)+1} lines"
        elif k == ord("p"):
            vr = self.cursor.get_visual_range()
            if vr:
                y1, x1, y2, x2 = vr
                self.buffer.delete_visual(y1, x1, y2, x2)
                self.cursor.cy = y1
                self.cursor.cx = x1
                clip = self.buffer.clipboard
                if clip:
                    lines = clip.split('\n')
                    for idx, line in enumerate(lines):
                        self.buffer.lines.insert(self.cursor.cy + idx, line)
                    self.msg = "Pasted clipboard"
                self.cursor.visual_start = None
                self.mode = "NORMAL"
        elif k == ord("h") or k == curses.KEY_LEFT:
            self.cursor.move_cursor(0, -1)
        elif k == ord("l") or k == curses.KEY_RIGHT:
            self.cursor.move_cursor(0, 1)
        elif k == ord("j") or k == curses.KEY_DOWN:
            self.cursor.move_cursor(1, 0)
        elif k == km.get("page_up", curses.KEY_PPAGE):
            maxy, _ = self.renderer.stdscr.getmaxyx()
            self.cursor.move_cursor(-(maxy-1), 0)
        elif k == km.get("page_down", curses.KEY_NPAGE):
            maxy, _ = self.renderer.stdscr.getmaxyx()
            self.cursor.move_cursor((maxy-1), 0)
        elif k == ord("k") or k == curses.KEY_UP:
            self.cursor.move_cursor(-1, 0)
        elif k == km.get("delete_key", curses.KEY_DC):
            self.buffer.delete_char(self.cursor.cy, self.cursor.cx)
        elif k == 27:
            self.mode = "NORMAL"
            self.cursor.visual_start = None
        else:
            self.msg = f"Unhandled VISUAL {chr(k)}"
            
    def handle_command_mode(self, cmd_str):
        if cmd_str == "split":
            if hasattr(self.renderer, 'buffers') and len(self.renderer.buffers) < 2:
                self.msg = "Need at least 2 buffers to split!"
                return
            return ":split"
        if cmd_str == "vsplit":
            if hasattr(self.renderer, 'buffers') and len(self.renderer.buffers) < 2:
                self.msg = "Need at least 2 buffers to split!"
                return
            return ":vsplit"
        if cmd_str == "unsplit":
            return ":unsplit"
        if cmd_str == "history":
            self.buffer.show_history = True
            self.msg = "Undo/redo history shown"
            return
        if cmd_str.startswith("replace "):
            try:
                _, search, replace = cmd_str.split(" ", 2)
            except ValueError:
                self.msg = "Usage: :replace <search> <replace>"
                return
            count = self.buffer.replace_all(search, replace)
            self.msg = f"Replaced {count} occurrence(s)"
            return
        if cmd_str.startswith("goto "):
            try:
                _, line = cmd_str.split(" ", 1)
                line = int(line) - 1
                self.cursor.cy = max(0, min(line, len(self.buffer.lines)-1))
                self.cursor.fix_cursor()
                self.msg = f"Jumped to line {line+1}"
            except Exception:
                self.msg = "Usage: :goto <line>"
            return
        if cmd_str.startswith("theme "):
            _, theme = cmd_str.split(" ", 1)
            self.renderer.set_theme(theme.strip())
            self.msg = f"Theme set to {theme.strip()}"
            return
        if cmd_str == "wrap":
            self.renderer.toggle_wrap()
            self.msg = f"Word wrap {'on' if self.renderer.wrap else 'off'}"
            return
        if cmd_str == "help":
            self.buffer.lines = self.help_text().splitlines()
            self.buffer.filename = "[HELP]"
            self.cursor.cy = 0
            self.cursor.cx = 0
            self.msg = "Help opened"
            return
        if cmd_str.startswith("!"):
            import subprocess
            cmd = cmd_str[1:]
            try:
                output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
            except Exception as e:
                output = str(e)
            self.buffer.lines = output.splitlines() or [""]
            self.buffer.filename = f"[!{cmd}]"
            self.cursor.cy = 0
            self.cursor.cx = 0
            self.msg = f"Output of !{cmd}"
            return
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
            self.last_search = s
            self.last_search_idx = (y, x)
            self.msg = f"Found '{s}' at {y+1},{x+1}"
        else:
            self.msg = f"'{s}' not found"

    def help_text(self):
        return """
Tedit Help
----------

Normal mode keys:
  i         - insert mode
  dd        - delete line
  yy        - yank line
  p         - paste
  u/r       - undo/redo
  /         - search
  :         - command mode
  v         - visual mode
  PgUp/PgDn - page up/down
  :e <file> - open file
  :view <file> - open read-only
  :bn/:bp   - next/prev buffer
  :bx/:bc   - close/create buffer
  F2        - toggle sidebar
  F3        - toggle line numbers
  F1/:help  - help
  :goto <n> - jump to line
  :theme <t> - set theme
  :wrap     - toggle word wrap
  :!cmd     - run shell command
  ma/'a     - set/jump mark a
  Tab       - switch split focus

Visual mode: d/y/p/h/j/k/l, PgUp/PgDn
Insert mode: Esc to normal, arrows, PgUp/PgDn
"""