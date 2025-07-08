import curses

class Renderer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.setup_colors()
        
    def setup_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
        
    def draw(self, buffer, cursor, mode, msg):
        self.stdscr.clear()
        maxy, maxx = self.stdscr.getmaxyx()
        height, width = maxy - 1, maxx
        
        cursor.fix_cursor()
        
        if cursor.cy < cursor.scroll:
            cursor.scroll = cursor.cy
        if cursor.cy >= cursor.scroll + height:
            cursor.scroll = cursor.cy - height + 1
            
        for i in range(cursor.scroll, cursor.scroll + height):
            if i >= len(buffer.lines):
                break
            line = buffer.lines[i]
            num = f"{i+1:4} "
            attr = curses.color_pair(2) if i == cursor.cy else curses.color_pair(1)
            self.stdscr.addstr(i - cursor.scroll, 0, num, attr)
            
            if mode == "VISUAL" and cursor.visual_start:
                vr = cursor.get_visual_range()
                if vr:
                    y1, x1, y2, x2 = vr
                    if y1 <= i <= y2:
                        start = x1 if i == y1 else 0
                        end = x2 if i == y2 else len(line) - 1
                        for idx, ch in enumerate(line):
                            if start <= idx <= end:
                                self.stdscr.addstr(i - cursor.scroll, 5 + idx, ch, curses.color_pair(4))
                            else:
                                self.stdscr.addstr(i - cursor.scroll, 5 + idx, ch, curses.color_pair(1))
                        continue
                        
            self.stdscr.addstr(i - cursor.scroll, 5, line[:width - 6], curses.color_pair(1))
            
        status = f" {mode} | {buffer.filename or '[No Name]'} | Ln {cursor.cy + 1}, Col {cursor.cx + 1} {msg}"
        self.stdscr.addstr(maxy - 1, 0, status[:maxx - 1], curses.color_pair(3))
        
        self.stdscr.move(cursor.cy - cursor.scroll, cursor.cx + 5)
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