# Tedit

> A fast, minimal, keyboard-driven terminal text editor. Inspired by Vim, built with pure Python.  

![screenshot](screenshot.jpg)

---

## 🚀 Features

- Modal editing (Normal, Insert, Visual)
- Vim-style keybindings (`i`, `dd`, `yy`, `p`, `u`, `v`, etc.)
- Word navigation (`w`, `b`)
- Search with `/`
- Clipboard-style yank and paste
- Undo / Redo
- Visual selection + deletion
- Line numbers + simple status bar
- Command mode (`:`) with:
  - `:w` to save
  - `:q` to quit
  - `:wq` to save & quit
  - `:q!` to quit without saving
- Exit confirmation if changes aren’t saved
- Runs in any real terminal (curses-based)
- Fully keyboard controlled
- No external dependencies

---

## Using it through the repository

```bash
git clone https://github.com/s-ar2005/tedit
cd tedit
python3 main.py <filename>
```

---

## Keybindings

| Mode   | Key          | Action                        |
| ------ | ------------ | ----------------------------- |
| Normal | `i`          | Enter insert mode             |
| Normal | `dd`         | Delete current line           |
| Normal | `yy`         | Yank (copy) line              |
| Normal | `p`          | Paste                         |
| Normal | `u` / `r`    | Undo / Redo                   |
| Normal | `/`          | Search                        |
| Normal | `:`          | Enter command mode            |
| Normal | `v`          | Visual mode (select text)     |
| Insert | `Esc`        | Return to normal mode         |
| Visual | `d` / `y`    | Delete / Yank selected        |
| Any    | `Arrow Keys` | Move cursor                   |
| Normal | `Esc`        | Exit with confirmation dialog |

---

## Roadmap

* Configurable keybindings
* Syntax highlighting
* Plugin system
* Tabs/splits?
* Written in C version someday?

---

## License

MIT — do whatever you want with it.

---

## Made by Sarah <3
