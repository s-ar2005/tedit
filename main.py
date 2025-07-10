#!/usr/bin/env python3
import curses
import sys
import os
import json
import time
from buffer import Buffer
from cursor import Cursor
from renderer import Renderer
from inputhandler import InputHandler

class Tedit:
    def __init__(self, stdscr, *args):
        self.stdscr = stdscr
        curses.curs_set(1)
        curses.mousemask(1)
        self.buffers = []
        self.cursors = []
        self.input_handlers = []
        self.current = 0
        self.renderer = Renderer(stdscr)
        self.split_mode = None
        self.split_buffers = None
        self.split_focus = 0
        self.no_session = '--no-session' in args
        filenames = [a for a in args if not a.startswith('--')]
        self.session_path = os.path.expanduser("~/.config/tedit.session")
        self.last_autosave = time.time()
        self.config = {}
        config_path = os.path.expanduser("~/.config/tedit.json")
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    self.config = json.load(f)
            except Exception:
                self.config = {}
        self.autosave_enabled = self.config.get("autosave", False)
        if not os.path.exists(os.path.dirname(self.session_path)):
            os.makedirs(os.path.dirname(self.session_path), exist_ok=True)
        if not self.no_session and os.path.exists(self.session_path):
            self.load_session()
        elif filenames:
            for fname in filenames:
                self.open_buffer(fname)
        else:
            self.open_buffer(None)
        self.run()

    def open_buffer(self, filename, cy=0, cx=0, read_only=False):
        buf = Buffer(filename)
        buf.read_only = read_only
        cur = Cursor(buf.lines)
        cur.cy = cy
        cur.cx = cx
        handler = InputHandler(self.stdscr, buf, cur, self.renderer)
        self.buffers.append(buf)
        self.cursors.append(cur)
        self.input_handlers.append(handler)
        self.current = len(self.buffers) - 1
        try:
            handler.run_linter()
        except Exception:
            pass

    def save_session(self, name=None):
        if self.no_session:
            return
        path = self.session_path if not name else os.path.expanduser(f"~/.config/tedit_{name}.session")
        data = {
            "buffers": [
                {
                    "filename": b.filename,
                    "cy": c.cy,
                    "cx": c.cx,
                    "read_only": getattr(b, "read_only", False)
                }
                for b, c in zip(self.buffers, self.cursors)
            ],
            "current": self.current
        }
        with open(path, "w") as f:
            json.dump(data, f)

    def load_session(self, name=None):
        path = self.session_path if not name else os.path.expanduser(f"~/.config/tedit_{name}.session")
        with open(path) as f:
            data = json.load(f)
        for bufinfo in data["buffers"]:
            self.open_buffer(bufinfo["filename"], bufinfo["cy"], bufinfo["cx"], bufinfo.get("read_only", False))
        self.current = data.get("current", 0)

    def autosave(self):
        now = time.time()
        if now - self.last_autosave > 10:
            for b in self.buffers:
                if b.filename and not getattr(b, 'read_only', False):
                    b.save_file()
            self.last_autosave = now

    def run(self):
        cmd_mode = False
        cmd_str = ""
        while True:
            if self.split_mode == 'vsplit' and self.split_buffers is not None:
                try:
                    bufidx0, bufidx1 = self.split_buffers
                    if (0 <= bufidx0 < len(self.buffers)) and (0 <= bufidx1 < len(self.buffers)):
                        bufs = [self.buffers[bufidx0], self.buffers[bufidx1]]
                        curs = [self.cursors[bufidx0], self.cursors[bufidx1]]
                        handlers = [self.input_handlers[bufidx0], self.input_handlers[bufidx1]]
                        focus = self.split_focus
                        buf = bufs[focus]
                        cur = curs[focus]
                        handler = handlers[focus]
                    else:
                        self.split_mode = None
                        self.split_buffers = None
                        self.split_focus = 0
                        buf = self.buffers[self.current]
                        cur = self.cursors[self.current]
                        handler = self.input_handlers[self.current]
                except Exception:
                    self.split_mode = None
                    self.split_buffers = None
                    self.split_focus = 0
                    buf = self.buffers[self.current]
                    cur = self.cursors[self.current]
                    handler = self.input_handlers[self.current]
            else:
                buf = self.buffers[self.current]
                cur = self.cursors[self.current]
                handler = self.input_handlers[self.current]
            if cmd_mode:
                self.renderer.draw_command(cmd_str)
                k = self.stdscr.getch()
                if k in (10, 13):
                    result = self.handle_command_mode(cmd_str, handler)
                    if result == "quit":
                        self.save_session()
                        break
                    if result == ":vsplit":
                        if len(self.buffers) == 1:
                            self.open_buffer(None)
                        self.split_mode = "vsplit"
                        self.split_buffers = (self.current, (self.current+1)%len(self.buffers))
                        self.split_focus = 0
                    elif result == ":unsplit":
                        self.split_mode = None
                        self.split_buffers = None
                        self.split_focus = 0
                    cmd_mode = False
                    cmd_str = ""
                elif k in (27,):
                    cmd_mode = False
                    cmd_str = ""
                    handler.msg = "Command cancelled"
                elif k in (8, 127, curses.KEY_BACKSPACE):
                    cmd_str = cmd_str[:-1]
                elif 32 <= k <= 126:
                    cmd_str += chr(k)
                continue
            if self.split_mode == 'vsplit' and self.split_buffers is not None:
                try:
                    bufidx0, bufidx1 = self.split_buffers
                    if (0 <= bufidx0 < len(self.buffers)) and (0 <= bufidx1 < len(self.buffers)):
                        bufs = [self.buffers[bufidx0], self.buffers[bufidx1]]
                        curs = [self.cursors[bufidx0], self.cursors[bufidx1]]
                        handlers = [self.input_handlers[bufidx0], self.input_handlers[bufidx1]]
                        if hasattr(self.renderer, 'draw_split'):
                            self.renderer.draw_split(bufs, curs, [h.mode for h in handlers], [h.msg for h in handlers], 'vsplit', self.split_focus, self.split_buffers, len(self.buffers))
                        for h in handlers:
                            h.msg = ""
                    else:
                        self.split_mode = None
                        self.split_buffers = None
                        self.split_focus = 0
                        self.renderer.draw(buf, cur, handler.mode, handler.msg, self.current, len(self.buffers))
                        handler.msg = ""
                except Exception:
                    self.split_mode = None
                    self.split_buffers = None
                    self.split_focus = 0
                    self.renderer.draw(buf, cur, handler.mode, handler.msg, self.current, len(self.buffers))
                    handler.msg = ""
            else:
                self.renderer.draw(buf, cur, handler.mode, handler.msg, self.current, len(self.buffers))
                handler.msg = ""
            k = self.stdscr.getch()
            if self.autosave_enabled:
                self.autosave()
            if self.split_mode and k == 9:
                self.split_focus = 1 - self.split_focus
                continue
            if handler.mode == "INSERT":
                handler.handle_insert_mode(k)
            elif handler.mode == "NORMAL":
                if k == ord(":"):
                    cmd_mode = True
                    cmd_str = ""
                else:
                    result = handler.handle_normal_mode(k)
                    if isinstance(result, str) and result.startswith(":e "):
                        filename = result[3:].strip()
                        self.open_buffer(filename)
                        handler.msg = f"Opened {filename}"
                    elif isinstance(result, str) and result.startswith(":view "):
                        filename = result[6:].strip()
                        self.open_buffer(filename, read_only=True)
                        handler.msg = f"Viewing {filename} (read-only)"
                    elif result and result.startswith(":b") and result[2:].isdigit():
                        idx = int(result[2:]) - 1
                        if 0 <= idx < len(self.buffers):
                            self.current = idx
                            handler.msg = f"Switched to buffer {idx+1}/{len(self.buffers)}"
                        else:
                            handler.msg = f"No buffer {idx+1}"
                    elif result and result.startswith(":session save "):
                        name = result.split(" ", 2)[2]
                        self.save_session(name)
                        handler.msg = f"Session saved as {name}"
                    elif result and result.startswith(":session load "):
                        name = result.split(" ", 2)[2]
                        self.buffers.clear(); self.cursors.clear(); self.input_handlers.clear()
                        self.load_session(name)
                        handler.msg = f"Session {name} loaded"
                    elif result == "exit_confirm":
                        if self.renderer.confirm_exit():
                            self.save_session()
                            break
                    elif result == ":switch_split":
                        if self.split_mode:
                            self.split_focus = 1 - self.split_focus
                        continue
            elif handler.mode == "VISUAL":
                handler.handle_visual_mode(k)

    def handle_command_mode(self, cmd_str, handler):
        if cmd_str.startswith("e "):
            filename = cmd_str[2:].strip()
            self.open_buffer(filename)
            handler.msg = f"Opened {filename}"
        elif cmd_str.startswith("view "):
            filename = cmd_str[5:].strip()
            self.open_buffer(filename, read_only=True)
            handler.msg = f"Viewing {filename} (read-only)"
        elif cmd_str == "bn":
            self.current = (self.current + 1) % len(self.buffers)
            handler.msg = f"Buffer {self.current + 1}/{len(self.buffers)}"
        elif cmd_str == "bp":
            self.current = (self.current - 1) % len(self.buffers)
            handler.msg = f"Buffer {self.current + 1}/{len(self.buffers)}"
        elif cmd_str == "bx":
            if len(self.buffers) > 1:
                self.close_buffer(self.current)
                handler.msg = f"Closed buffer. Now at {self.current + 1}/{len(self.buffers)}"
            else:
                handler.msg = "Can't close last buffer!"
        elif cmd_str == "bc":
            self.open_buffer(None)
            handler.msg = f"Created new buffer {len(self.buffers)}"
        elif cmd_str.startswith("b") and cmd_str[1:].isdigit():
            idx = int(cmd_str[1:]) - 1
            if 0 <= idx < len(self.buffers):
                self.current = idx
                handler.msg = f"Switched to buffer {idx+1}/{len(self.buffers)}"
            else:
                handler.msg = f"No buffer {idx+1}"
        elif cmd_str == "vsplit":
            if len(self.buffers) == 1:
                self.open_buffer(None)
            self.split_mode = "vsplit"
            self.split_buffers = (self.current, (self.current+1)%len(self.buffers))
            self.split_focus = 0
        elif cmd_str == "unsplit":
            return ":unsplit"
        elif cmd_str.startswith("session save "):
            return f":session save {cmd_str.split(' ',2)[2]}"
        elif cmd_str.startswith("session load "):
            return f":session load {cmd_str.split(' ',2)[2]}"
        else:
            return handler.handle_command_mode(cmd_str)

    def close_buffer(self, idx):
        if len(self.buffers) > 1:
            del self.buffers[idx]
            del self.cursors[idx]
            del self.input_handlers[idx]
            if self.split_mode and self.split_buffers is not None:
                if idx in self.split_buffers:
                    self.split_mode = None
                    self.split_buffers = None
                    self.split_focus = 0
            self.current = max(0, self.current - 1)

def main():
    import signal
    def ignore_sigint(signum, frame):
        pass
    signal.signal(signal.SIGINT, ignore_sigint)
    curses.wrapper(Tedit, *sys.argv[1:])

if __name__ == "__main__":
    main()