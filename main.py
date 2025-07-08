#!/usr/bin/env python3
import curses
import sys
from buffer import Buffer
from cursor import Cursor
from renderer import Renderer
from inputhandler import InputHandler

class Tedit:
    def __init__(self, stdscr, filename=None):
        self.stdscr = stdscr
        curses.curs_set(1)
        
        self.buffer = Buffer(filename)
        self.cursor = Cursor(self.buffer.lines)
        self.renderer = Renderer(stdscr)
        self.input_handler = InputHandler(stdscr, self.buffer, self.cursor, self.renderer)
        
        self.run()
        
    def run(self):
        cmd_mode = False
        cmd_str = ""
        
        while True:
            if cmd_mode:
                self.renderer.draw_command(cmd_str)
                k = self.stdscr.getch()
                
                if k in (10, 13):
                    result = self.input_handler.handle_command_mode(cmd_str)
                    if result == "quit":
                        break
                    cmd_mode = False
                    cmd_str = ""
                elif k in (27,):
                    cmd_mode = False
                    cmd_str = ""
                    self.input_handler.msg = "Command cancelled"
                elif k in (8, 127, curses.KEY_BACKSPACE):
                    cmd_str = cmd_str[:-1]
                elif 32 <= k <= 126:
                    cmd_str += chr(k)
                continue
                
            self.renderer.draw(self.buffer, self.cursor, self.input_handler.mode, self.input_handler.msg)
            self.input_handler.msg = ""
            
            k = self.stdscr.getch()
            
            if self.input_handler.mode == "INSERT":
                self.input_handler.handle_insert_mode(k)
            elif self.input_handler.mode == "NORMAL":
                if k == ord(":"):
                    cmd_mode = True
                    cmd_str = ""
                else:
                    result = self.input_handler.handle_normal_mode(k)
                    if result == "exit_confirm":
                        if self.renderer.confirm_exit():
                            break
            elif self.input_handler.mode == "VISUAL":
                self.input_handler.handle_visual_mode(k)

def main():
    curses.wrapper(Tedit, *(sys.argv[1:] if len(sys.argv) > 1 else []))

if __name__ == "__main__":
    main()