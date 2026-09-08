#!/usr/bin/env python3
from core import ui
from core.paths import PLATFORM, ensure
import atexit
atexit.register(ui.cursor_show)

def main():
    for key in PLATFORM: ensure(key)
    with ui.CursorGuard():
        while True:
            ui.header('DLXhub','Premium multi-platform terminal media hub','◆')
            ui.section('PLATFORM HUB',ui.ORANGE)
            ui.menu_item('1','RedGIFs',ui.ORANGE,'video · audio')
            ui.menu_item('2','XXXFollow',ui.MAGENTA,'video · audio')
            ui.menu_item('3','Facebook',ui.BLUE,'video · audio')
            ui.menu_item('4','Twitter / X',ui.CYAN,'video · audio')
            ui.menu_item('5','YouTube',ui.GREEN,'video · audio · playlist')
            print(); ui.line(); print()
            ui.menu_item('Q','Quit',ui.RED)
            c=ui.prompt()
            if c is None or c.lower()=='q': break
            try:
                if c=='1': from modules.rg import menu; menu()
                elif c=='2': from modules.xf import menu; menu()
                elif c=='3': from modules.fb import menu; menu()
                elif c=='4': from modules.x import menu; menu()
                elif c=='5': from modules.yt import menu; menu()
                else: ui.status('Invalid option','err'); ui.pause()
            except KeyboardInterrupt:
                continue
            except Exception as e:
                ui.status(f'Module error: {e}','err'); ui.pause()
    ui.clear(); ui.cursor_show(); print(ui.GREEN+ui.BOLD+'  DLXhub closed.'+ui.RESET)

if __name__=='__main__': main()
