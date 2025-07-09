import curses
import os
import re
import importlib.util
import glob

class Renderer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.theme = "dark"
        self.wrap = False
        self.setup_colors()
        self.sidebar = False
        self.files = []
        self.selected_file = 0
        self.sidebar_scroll = 0
        self.cwd = os.getcwd()
        self.refresh_files()
        self.show_line_numbers = True
        self.external_highlighters = {}
        config_dir = os.path.expanduser("~/.config/tedit")
        if os.path.isdir(config_dir):
            for path in glob.glob(os.path.join(config_dir, "*.py")):
                ext = os.path.splitext(os.path.basename(path))[0]
                spec = importlib.util.spec_from_file_location(f"tedit_{ext}", path)
                if spec is not None and spec.loader is not None:
                    mod = importlib.util.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(mod)
                        if hasattr(mod, "highlight_line"):
                            self.external_highlighters[ext] = mod.highlight_line
                    except Exception:
                        pass

    def set_theme(self, theme):
        self.theme = theme
        self.setup_colors()

    def setup_colors(self):
        curses.start_color()
        curses.use_default_colors()
        if self.theme == "light":
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_WHITE)
            curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_CYAN)
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
        else:
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_YELLOW)

    def toggle_wrap(self):
        self.wrap = not self.wrap

    def refresh_files(self):
        entries = os.listdir(self.cwd)
        folders = [f for f in entries if os.path.isdir(os.path.join(self.cwd, f))]
        files = [f for f in entries if os.path.isfile(os.path.join(self.cwd, f))]
        folders.sort()
        files.sort()
        folders = [f + '/' for f in folders]
        self.files = folders + files
        if os.path.abspath(self.cwd) != os.path.abspath(os.sep):
            self.files = ['..'] + self.files

    def change_directory(self, new_dir):
        if new_dir == '..':
            parent = os.path.dirname(self.cwd)
            self.cwd = parent
        else:
            self.cwd = os.path.join(self.cwd, new_dir)
        self.selected_file = 0
        self.refresh_files()

    def toggle_sidebar(self):
        self.sidebar = not self.sidebar
        if self.sidebar:
            self.refresh_files()

    def toggle_line_numbers(self):
        self.show_line_numbers = not self.show_line_numbers

    def highlight_line(self, line, filetype):
        ext = None
        if filetype:
            ext = os.path.splitext(filetype)[-1].lstrip('.')
        if ext and ext in self.external_highlighters:
            try:
                return self.external_highlighters[ext](line, filetype)
            except Exception:
                pass
        if filetype and filetype.endswith('.py'):
            keywords = r'\b(def|class|import|from|as|if|elif|else|for|while|try|except|with|return|yield|in|is|not|and|or|pass|break|continue|lambda|True|False|None)\b'
            line = re.sub(keywords, lambda m: f'\x01{m.group(0)}\x02', line)
            line = re.sub(r'#[^\n]*', lambda m: f'\x03{m.group(0)}\x02', line)
            line = re.sub(r'("[^"]*"|\'[^\"]*\')', lambda m: f'\x04{m.group(0)}\x02', line)
        elif filetype and (filetype.endswith('.md') or filetype.endswith('.markdown')):
            line = re.sub(r'^(#+)(.*)', lambda m: f'\x01{m.group(1)}{m.group(2)}\x02', line)
            line = re.sub(r'\*\*([^*]+)\*\*', lambda m: f'\x04{m.group(0)}\x02', line)
        return line

    def draw(self, buffer, cursor, mode, msg, buf_idx=0, buf_count=1):
        self.stdscr.clear()
        maxy, maxx = self.stdscr.getmaxyx()
        height, width = maxy - 1, maxx
        sidebar_width = 20 if self.sidebar else 0
        num_width = 5 if self.show_line_numbers else 0
        minimap_width = 8
        text_width = width - sidebar_width - minimap_width - num_width
        visual_range = None
        if mode == "VISUAL" and cursor.visual_start is not None:
            visual_range = cursor.get_visual_range()
        self._draw_buffer(
            buffer, cursor, mode, msg, buf_idx, buf_count,
            sidebar_width, num_width, minimap_width, 0, text_width, height,
            split=False, focused=True,
            draw_sidebar=self.sidebar, draw_minimap=True, draw_status=True, draw_cursor=True,
            visual_range=visual_range
        )
        self.stdscr.refresh()

    def _draw_buffer(self, buffer, cursor, mode, msg, buf_idx, buf_count, sidebar_width, num_width, minimap_width, y_offset, text_width, height, split=False, focused=False, draw_sidebar=False, draw_minimap=False, draw_status=False, draw_cursor=False, visual_range=None):
        maxy, maxx = self.stdscr.getmaxyx()
        width = maxx
        if draw_sidebar:
            total_files = len(self.files)
            max_visible = height
            if self.selected_file < self.sidebar_scroll:
                self.sidebar_scroll = self.selected_file
            elif self.selected_file >= self.sidebar_scroll + max_visible:
                self.sidebar_scroll = self.selected_file - max_visible + 1
            self.sidebar_scroll = max(0, min(self.sidebar_scroll, max(0, total_files - max_visible)))
            visible_files = self.files[self.sidebar_scroll:self.sidebar_scroll+max_visible]
            for i, fname in enumerate(visible_files):
                idx = i + self.sidebar_scroll
                attr = curses.color_pair(2) if idx == self.selected_file else curses.color_pair(1)
                if fname.endswith('/') or fname == '..':
                    attr = curses.color_pair(4) if idx != self.selected_file else curses.color_pair(5)
                self.stdscr.addstr(i + y_offset, 0, fname[:sidebar_width-1].ljust(sidebar_width-1), attr)
            for i in range(height):
                self.stdscr.addstr(i + y_offset, sidebar_width-1, '|', curses.color_pair(3))
        cursor.fix_cursor()
        if cursor.cy < cursor.scroll:
            cursor.scroll = cursor.cy
        if cursor.cy >= cursor.scroll + height:
            cursor.scroll = cursor.cy - height + 1
        for i in range(cursor.scroll, cursor.scroll + height):
            if i >= len(buffer.lines):
                break
            line = buffer.lines[i]
            filetype = buffer.filename or ''
            hline = self.highlight_line(line, filetype)
            idx = 0
            col = sidebar_width + (num_width if self.show_line_numbers else 0)
            color = curses.color_pair(1)
            if self.show_line_numbers:
                num = f"{i+1:4} "
                attr = curses.color_pair(2) if i == cursor.cy else curses.color_pair(1)
                self.stdscr.addstr(i - cursor.scroll + y_offset, sidebar_width, num, attr)
            if self.wrap:
                wrap_col = col
                line_buffer = []
                color = curses.color_pair(1)
                curr_col = 0
                idx = 0
                hlen = len(hline)
                while idx < hlen:
                    ch = hline[idx]
                    if ch == '\x01':
                        color = curses.color_pair(2)
                        idx += 1
                        continue
                    elif ch == '\x03':
                        color = curses.color_pair(4)
                        idx += 1
                        continue
                    elif ch == '\x04':
                        color = curses.color_pair(3)
                        idx += 1
                        continue
                    elif ch == '\x02':
                        color = curses.color_pair(1)
                        idx += 1
                        continue
                    else:
                        line_buffer.append((ch, color))
                        idx += 1
                max_text_width = text_width - num_width
                row = i - cursor.scroll + y_offset
                col_offset = wrap_col
                curr = 0
                while curr < len(line_buffer):
                    chunk = line_buffer[curr:curr+max_text_width]
                    for j, (wch, wcolor) in enumerate(chunk):
                        try:
                            self.stdscr.addstr(row, col_offset + j, wch, wcolor)
                        except curses.error:
                            pass
                    curr += max_text_width
                    row += 1
                    if row - (i - cursor.scroll + y_offset) >= height:
                        break
            else:
                vis_y1 = vis_x1 = vis_y2 = vis_x2 = None
                if visual_range is not None:
                    vis_y1, vis_x1, vis_y2, vis_x2 = visual_range
                line_start = cursor.scroll_x
                line_end = cursor.scroll_x + text_width - 1
                idx = line_start
                col_offset = col
                while idx < len(hline) and idx <= line_end:
                    ch = hline[idx]
                    highlight = False
                    if (vis_y1 is not None and vis_x1 is not None and vis_y2 is not None and vis_x2 is not None):
                        if vis_y1 == vis_y2:
                            if i == vis_y1 and vis_x1 <= idx <= vis_x2:
                                highlight = True
                        else:
                            if (i == vis_y1 and idx >= vis_x1) or (i == vis_y2 and idx <= vis_x2) or (vis_y1 < i < vis_y2):
                                highlight = True
                    if ch == '\x01':
                        color = curses.color_pair(2)
                    elif ch == '\x03':
                        color = curses.color_pair(4)
                    elif ch == '\x04':
                        color = curses.color_pair(3)
                    elif ch == '\x02':
                        color = curses.color_pair(1)
                    else:
                        draw_color = curses.color_pair(5) if highlight else color
                        self.stdscr.addstr(i - cursor.scroll + y_offset, col_offset, ch, draw_color)
                        col_offset += 1
                    idx += 1
            if i == cursor.cy:
                if cursor.cx < cursor.scroll_x:
                    cursor.scroll_x = cursor.cx
                elif cursor.cx >= cursor.scroll_x + text_width:
                    cursor.scroll_x = cursor.cx - text_width + 1
        if draw_minimap:
            minmap_x = width - minimap_width
            total_lines = len(buffer.lines)
            for y in range(height):
                line_idx = int(y * total_lines / height) if total_lines > 0 else 0
                if 0 <= line_idx < total_lines:
                    ch = '|' if cursor.scroll <= line_idx < cursor.scroll + height else '.'
                    self.stdscr.addstr(y + y_offset, minmap_x, ch, curses.color_pair(2 if ch == '|' else 1))
        modified = "*" if buffer.undo_stack else " "
        if draw_status:
            status = f" {mode} | {modified}{buffer.filename or '[No Name]'} | Ln {cursor.cy + 1}, Col {cursor.cx + 1} | Buf {buf_idx+1}/{buf_count} {msg}"
            self.stdscr.addstr(maxy - 1, 0, status[:maxx - 1], curses.color_pair(3))
        if draw_cursor and focused:
            self.stdscr.move(cursor.cy - cursor.scroll + y_offset, sidebar_width + (num_width if self.show_line_numbers else 0) + (cursor.cx - cursor.scroll_x))

    def draw_split(self, buffers, cursors, modes, msgs, split_mode, split_focus, split_buffers, buf_count):
        self.stdscr.clear()
        maxy, maxx = self.stdscr.getmaxyx()
        sidebar_width = 20 if self.sidebar else 0
        num_width = 5 if self.show_line_numbers else 0
        minimap_width = 8
        if split_mode == 'vsplit':
            width1 = (maxx - sidebar_width - minimap_width - num_width) // 2
            width2 = (maxx - sidebar_width - minimap_width - num_width) - width1
            text_width1 = width1
            text_width2 = width2
            height = maxy - 1
            self._draw_buffer(
                buffers[0], cursors[0], modes[0], msgs[0], split_buffers[0], buf_count,
                sidebar_width, num_width, minimap_width, 0, text_width1, height,
                split=True, focused=(split_focus==0),
                draw_sidebar=self.sidebar, draw_minimap=True, draw_status=False, draw_cursor=(split_focus==0)
            )
            self._draw_buffer(
                buffers[1], cursors[1], modes[1], msgs[1], split_buffers[1], buf_count,
                sidebar_width + text_width1, num_width, minimap_width, 0, text_width2, height,
                split=True, focused=(split_focus==1),
                draw_sidebar=False, draw_minimap=True, draw_status=True, draw_cursor=(split_focus==1)
            )
            for y in range(height):
                self.stdscr.addch(y, sidebar_width + text_width1, curses.ACS_VLINE, curses.color_pair(3))
        self.stdscr.refresh()

    def draw_command(self, cmd_str):
        maxy, maxx = self.stdscr.getmaxyx()
        if maxy > 0:
            pad_len = max(0, maxx - len(cmd_str) - 1)
            try:
                self.stdscr.addstr(maxy - 1, 0, ":" + cmd_str + " " * pad_len, curses.color_pair(3))
            except curses.error:
                pass
        self.stdscr.move(maxy - 1, len(cmd_str) + 1)
        self.stdscr.refresh()

    def confirm_exit(self):
        maxy, maxx = self.stdscr.getmaxyx()
        height, width = 3, 30
        starty = (maxy - height) // 2
        startx = (maxx - width) // 2
        win = curses.newwin(height, width, starty, startx)
        win.bkgd(' ', curses.color_pair(3))
        win.box()
        win.addstr(1, 2, "Exit without saving? (y/n)")
        win.refresh()
        while True:
            c = win.getch()
            if c in (ord('y'), ord('Y')):
                return True
            elif c in (ord('n'), ord('N')):
                return False

    def get_input(self, prompt):
        maxy, maxx = self.stdscr.getmaxyx()
        curses.echo()
        self.stdscr.addstr(maxy - 1, 0, prompt)
        s = self.stdscr.getstr(maxy - 1, len(prompt), 100).decode("utf-8")
        curses.noecho()
        return s