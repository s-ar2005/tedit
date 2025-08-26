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
        self.external_linters = {}
        self.diagnostic_symbols = {
            'error': 'E',
            'warning': 'W',
            'info': 'I',
            'todo': 'T',
        }
        self.diagnostic_colors = {
            'error': 6,
            'warning': 7,
            'info': 8,
            'todo': 9,
        }
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
                        if hasattr(mod, "lint_buffer"):
                            self.external_linters[ext] = mod.lint_buffer
                    except Exception:
                        pass
        config_path = os.path.expanduser("~/.config/tedit.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path) as f:
                    cfg = json.load(f)
                self.diagnostic_symbols.update(cfg.get("diagnostic_symbols", {}))
                self.diagnostic_colors.update(cfg.get("diagnostic_colors", {}))
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
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_WHITE)
            curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_WHITE)
            curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
            curses.init_pair(6, curses.COLOR_CYAN, curses.COLOR_WHITE)
            curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_WHITE)
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_RED)
            curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(13, curses.COLOR_BLUE, curses.COLOR_WHITE)
            curses.init_pair(14, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
            curses.init_pair(15, curses.COLOR_BLUE, curses.COLOR_WHITE)
            curses.init_pair(16, curses.COLOR_BLACK, curses.COLOR_CYAN)
        else:
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
            curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)
            curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLACK)
            curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_RED)
            curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_YELLOW)
            curses.init_pair(11, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(13, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(14, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
            curses.init_pair(15, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(16, curses.COLOR_BLACK, curses.COLOR_CYAN)

        self.diagnostic_colors = {
            'error': 9,
            'warning': 10,
            'info': 11,
            'todo': 10,
        }

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

    def _draw_buffer_tabs(self, current_buffer_idx, all_buffers_filenames, max_width):
        if not all_buffers_filenames:
            return
        
        tab_y = 0
        x_offset = 0
        for i, filename in enumerate(all_buffers_filenames):
            display_name = os.path.basename(filename) if filename else "[No Name]"
            tab_text = f" {display_name} "
            attr = curses.color_pair(1)
            if i == current_buffer_idx:
                attr = curses.color_pair(12) | curses.A_BOLD
           
            if x_offset + len(tab_text) > max_width:
                break
            
            try:
                self.stdscr.addstr(tab_y, x_offset, tab_text, attr)
            except curses.error:
                pass
            
            x_offset += len(tab_text)
            if i < len(all_buffers_filenames) - 1 and x_offset < max_width:
                try:
                    self.stdscr.addstr(tab_y, x_offset, "|", curses.color_pair(12))
                except curses.error:
                    pass
                x_offset += 1

    def highlight_line(self, line, filetype, diagnostics=None):
        ext = None
        if filetype:
            ext = os.path.splitext(filetype)[-1].lstrip('.')
        if diagnostics:
            priority = {'error': 0, 'warning': 1, 'todo': 2, 'info': 3}
            diagnostics.sort(key=lambda d: priority.get(d[0], 99))
            dtype, _ = diagnostics[0]
            color_code = self.diagnostic_colors.get(dtype, 1)
            return f'\\x01D{color_code}{line}\\x02' # Diagnostic highlight
        if ext and ext in self.external_highlighters:
            try:
                return self.external_highlighters[ext](line, filetype)
            except Exception:
                pass
        if filetype and filetype.endswith('.py'):
            keywords = r'\b(def|class|import|from|as|if|elif|else|for|while|try|except|with|return|yield|in|is|not|and|or|pass|break|continue|lambda|True|False|None)\b'
            line = re.sub(keywords, lambda m: f'\\x01K{m.group(0)}\\x02', line)
            line = re.sub(r'#[^\n]*', lambda m: f'\\x01C{m.group(0)}\\x02', line)
            line = re.sub(r'("[^"]*"|\'[^\']*\')', lambda m: f'\\x01S{m.group(0)}\\x02', line)
            line = re.sub(r'\b\d+(\.\d*)?\b', lambda m: f'\\x01N{m.group(0)}\\x02', line)
            line = re.sub(r'\b(def|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', lambda m: f'{m.group(1)}\\x01F{m.group(2)}\\x02', line)
        elif filetype and (filetype.endswith('.md') or filetype.endswith('.markdown')):
            line = re.sub(r'^(#+)(.*)', lambda m: f'\\x01H{m.group(1)}{m.group(2)}\\x02', line) # Headers
            line = re.sub(r'\*\*([^*]+)\*\*', lambda m: f'\\x01B{m.group(0)}\\x02', line) # Bold
            line = re.sub(r'\*([^*]+)\*', lambda m: f'\\x01I{m.group(0)}\\x02', line) # Italic
        return line

    def draw(self, buffer, cursor, mode, msg, buf_idx=0, all_buffers_filenames=None):
        if self.theme == "light":
            self.stdscr.bkgd(' ', curses.color_pair(1))
        else:
            self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.clear()
        maxy, maxx = self.stdscr.getmaxyx()
        tab_height = 1 if all_buffers_filenames else 0
        height, width = maxy - 1 - tab_height, maxx
        sidebar_width = 20 if self.sidebar else 0
        num_width = 5 if self.show_line_numbers else 0
        minimap_width = 8
        text_width = width - sidebar_width - minimap_width - num_width
        visual_range = None
        if mode == "VISUAL" and cursor.visual_start is not None:
            visual_range = cursor.get_visual_range()
        self._draw_buffer_tabs(buf_idx, all_buffers_filenames, maxx)
        self._draw_buffer(
            buffer, cursor, mode, msg, buf_idx, len(all_buffers_filenames) if all_buffers_filenames else 1,
            sidebar_width, num_width, minimap_width, tab_height, text_width, height,
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
                attr = curses.color_pair(1)
                if idx == self.selected_file:
                    attr = curses.color_pair(14)
                elif fname.endswith('/') or fname == '..':
                    attr = curses.color_pair(15)
                self.stdscr.addstr(i + y_offset, 0, fname[:sidebar_width-1].ljust(sidebar_width-1), attr)
            for i in range(height):
                self.stdscr.addstr(i + y_offset, sidebar_width-1, '|', curses.color_pair(12))
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
            diag = buffer.diagnostics.get(i, [])
            hline = self.highlight_line(line, filetype, diag)
            idx = 0
            col = sidebar_width + (num_width if self.show_line_numbers else 0)
            color = curses.color_pair(1)
            diagnostic_bg = None
            diag_symbol = ''
            diag_color = curses.color_pair(1)
            if diag:
                priority = {'error': 0, 'warning': 1, 'todo': 2, 'info': 3}
                diag.sort(key=lambda d: priority.get(d[0], 99))
                dtype, dmsg = diag[0]
                diag_symbol = self.diagnostic_symbols.get(dtype, '?')
                diag_color = curses.color_pair(self.diagnostic_colors.get(dtype, 1))

            if self.show_line_numbers:
                num = f"{i+1:4} "
                attr = curses.color_pair(13)
                if i == cursor.cy:
                    attr |= curses.A_REVERSE
                self.stdscr.addstr(i - cursor.scroll + y_offset, sidebar_width, num, attr)
                if diag_symbol:
                    self.stdscr.addstr(i - cursor.scroll + y_offset, sidebar_width + len(num), diag_symbol, diag_color)
            
            line_start = cursor.scroll_x
            line_end = cursor.scroll_x + text_width - 1
            idx = line_start
            col_offset = col
            current_color_pair = 1
            temp_line_buffer = []
            j = 0
            while j < len(hline):
                ch = hline[j]
                if ch == '\\' and j + 1 < len(hline) and hline[j+1] == 'x':
                    if j + 3 < len(hline) and hline[j+2] == '0' and hline[j+3] == '1':
                        j += 4
                        code = hline[j]
                        j += 1
                        if code == 'K': current_color_pair = 2
                        elif code == 'S': current_color_pair = 3
                        elif code == 'C': current_color_pair = 4
                        elif code == 'N': current_color_pair = 5
                        elif code == 'F': current_color_pair = 6
                        elif code == 'H': current_color_pair = 2
                        elif code == 'B': current_color_pair = 5
                        elif code == 'I': current_color_pair = 6
                        elif code == 'D':
                            color_code_str = hline[j]
                            j += 1
                            try:
                                color_code = int(color_code_str)
                                current_color_pair = color_code
                            except ValueError:
                                current_color_pair = 1
                        continue
                    elif j + 3 < len(hline) and hline[j+2] == '0' and hline[j+3] == '2':
                        current_color_pair = 1
                        j += 4
                        continue
                
                if idx >= line_start and idx <= line_end:
                    temp_line_buffer.append((ch, curses.color_pair(current_color_pair)))
                idx += 1
                j += 1

            for char_data in temp_line_buffer:
                ch, color_pair = char_data
                highlight = False
                if (visual_range is not None and
                    ((i == visual_range[0] and i == visual_range[2] and visual_range[1] <= col_offset - col + cursor.scroll_x < visual_range[3]) or
                     (i == visual_range[0] and i < visual_range[2] and visual_range[1] <= col_offset - col + cursor.scroll_x) or
                     (i > visual_range[0] and i < visual_range[2]) or
                     (i == visual_range[2] and i > visual_range[0] and col_offset - col + cursor.scroll_x <= visual_range[3]))):
                    highlight = True

                draw_color = curses.color_pair(16) if highlight else color_pair
                try:
                    self.stdscr.addstr(i - cursor.scroll + y_offset, col_offset, ch, draw_color)
                except curses.error:
                    pass
                col_offset += 1

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
                    self.stdscr.addstr(y + y_offset, minmap_x, ch, curses.color_pair(13 if ch == '|' else 1)) # Line number color for minimap
        modified = "*" if buffer.undo_stack else " "
        if draw_status:
            diag_msgs = buffer.diagnostics.get(cursor.cy, [])
            diag_text = ''
            if diag_msgs:
                diag_text = '; '.join(m for _, m in diag_msgs)
            
            # Enhanced status bar
            status_mode_color = curses.color_pair(12)
            if mode == "INSERT":
                status_mode_color = curses.color_pair(10) # Warning color for insert mode
            elif mode == "VISUAL":
                status_mode_color = curses.color_pair(9) # Error color for visual mode

            status_left = f" {mode} "
            status_right = f" {modified}{os.path.basename(buffer.filename or '[No Name]')} | Ln {cursor.cy + 1}, Col {cursor.cx + 1} | Buf {buf_idx+1}/{buf_count} "
            if diag_text:
                status_right += f" | {diag_text} "
            
            # Calculate status_left and status_right
            status_left = f" {mode} "
            status_right = f" {modified}{os.path.basename(buffer.filename or '[No Name]')} | Ln {cursor.cy + 1}, Col {cursor.cx + 1} | Buf {buf_idx+1}/{buf_count} "
            if diag_text:
                status_right += f" | {diag_text} "

            # Ensure status_left fits within maxx
            if len(status_left) > maxx:
                status_left = status_left[:max(0, maxx - 3)] + "..." if maxx > 3 else status_left[:maxx]

            # Calculate available width for status_right after status_left
            available_width_for_right_section = maxx - len(status_left)

            # If there's no space for status_right, make it empty
            if available_width_for_right_section <= 0:
                status_right = ""
                remaining_width = 0
                start_col_right = len(status_left) # This will be maxx or more, but status_right is empty
            else:
                # Calculate ideal start column for right-aligned status_right
                ideal_start_col_right = maxx - len(status_right)

                # Ensure status_right doesn't overlap status_left
                start_col_right = max(len(status_left), ideal_start_col_right)

                # Truncate status_right if it extends beyond maxx from its start_col_right
                # Ensure that start_col_right + len(status_right) is always < maxx
                max_printable_chars = maxx - start_col_right - 1

                if max_printable_chars < 0: # No space to print anything
                    status_right = ""
                elif len(status_right) > max_printable_chars:
                    # If there's space for ellipsis
                    if max_printable_chars >= 3:
                        status_right = status_right[:max_printable_chars - 3] + "..."
                    else: # No space for ellipsis, just truncate
                        status_right = status_right[:max_printable_chars]

                # Calculate remaining width for padding
                remaining_width = start_col_right - len(status_left)

                # Ensure remaining_width is not negative
                if remaining_width < 0:
                    remaining_width = 0

            # Draw status_left
            self.stdscr.addstr(maxy - 1, 0, status_left, status_mode_color)

            # Calculate start_col_right based on compact size
            fixed_padding = 2 # Or some other small number for compactness
            start_col_right_compact = len(status_left) + fixed_padding

            # Truncate status_right if it goes beyond maxx from its compact start position
            available_space_for_right_string_compact = maxx - start_col_right_compact
            if len(status_right) > available_space_for_right_string_compact:
                if available_space_for_right_string_compact >= 3:
                    status_right = status_right[:available_space_for_right_string_compact - 3] + "..."
                else:
                    status_right = status_right[:available_space_for_right_string_compact]

            # Draw status_right
            if status_right and (start_col_right_compact < maxx):
                self.stdscr.addstr(maxy - 1, start_col_right_compact, status_right, curses.color_pair(12))

            # Calculate end_of_status_bar after drawing status_right
            end_of_status_bar = start_col_right_compact + len(status_right)

            # Clear the rest of the line to make it "compact"
            # This is important because previous draws might have left characters
            # from a full-width status bar.
            clear_start_col = end_of_status_bar
            
            # Ensure clear_start_col is within valid range [0, maxx-1]
            if clear_start_col < 0:
                clear_start_col = 0
            
            # Iterate from clear_start_col to maxx-1, adding a space character
            for x in range(clear_start_col, maxx):
                try:
                    self.stdscr.addch(maxy - 1, x, ' ', curses.color_pair(1))
                except curses.error:
                    # If addch fails, it means we've gone out of bounds, stop clearing
                    break
            
            # Display message over status bar if present
            if msg:
                msg_display = f" {msg} "
                # Ensure msg_display fits within the screen width
                self.stdscr.addstr(maxy - 1, 0, msg_display[:maxx], curses.color_pair(12) | curses.A_BOLD)

        if draw_cursor and focused:
            self.stdscr.move(cursor.cy - cursor.scroll + y_offset, sidebar_width + (num_width if self.show_line_numbers else 0) + (cursor.cx - cursor.scroll_x))

    def draw_split(self, buffers, cursors, modes, msgs, split_mode, split_focus, split_buffers, all_buffers_filenames=None):
        if self.theme == "light":
            self.stdscr.bkgd(' ', curses.color_pair(1))
        else:
            self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.clear()
        maxy, maxx = self.stdscr.getmaxyx()
        tab_height = 1 if all_buffers_filenames else 0
        sidebar_width = 20 if self.sidebar else 0
        num_width = 5 if self.show_line_numbers else 0
        minimap_width = 8
        if split_mode == 'vsplit':
            width1 = (maxx - sidebar_width - minimap_width - num_width) // 2
            width2 = (maxx - sidebar_width - minimap_width - num_width) - width1
            text_width1 = width1
            text_width2 = width2
            height = maxy - 1 - tab_height
            self._draw_buffer_tabs(split_buffers[split_focus], all_buffers_filenames, maxx) # Pass current focused buffer for highlighting
            self._draw_buffer(
                buffers[0], cursors[0], modes[0], msgs[0], split_buffers[0], len(all_buffers_filenames) if all_buffers_filenames else 1,
                sidebar_width, num_width, minimap_width, tab_height, text_width1, height,
                split=True, focused=(split_focus==0),
                draw_sidebar=self.sidebar, draw_minimap=True, draw_status=False, draw_cursor=(split_focus==0)
            )
            self._draw_buffer(
                buffers[1], cursors[1], modes[1], msgs[1], split_buffers[1], len(all_buffers_filenames) if all_buffers_filenames else 1,
                sidebar_width + text_width1, num_width, minimap_width, tab_height, text_width2, height,
                split=True, focused=(split_focus==1),
                draw_sidebar=False, draw_minimap=True, draw_status=True, draw_cursor=(split_focus==1)
            )
            for y in range(height):
                self.stdscr.addch(y + tab_height, sidebar_width + text_width1, curses.ACS_VLINE, curses.color_pair(12)) # Status bar color for separator
        self.stdscr.refresh()

    def draw_command(self, cmd_str):
        maxy, maxx = self.stdscr.getmaxyx()
        if maxy > 0:
            pad_len = max(0, maxx - len(cmd_str) - 1)
            try:
                self.stdscr.addstr(maxy - 1, 0, ":" + cmd_str + " " * pad_len, curses.color_pair(12)) # Status bar color
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
        win.bkgd(' ', curses.color_pair(12)) # Status bar color for dialog
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

    def get_external_linter(self, ext):
        return self.external_linters.get(ext)