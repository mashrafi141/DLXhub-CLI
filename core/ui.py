import os, re, shutil, sys, time

RESET='\033[0m'; BOLD='\033[1m'; DIM='\033[2m'; UNDER='\033[4m'
BLACK='\033[30m'; WHITE='\033[97m'; GRAY='\033[90m'
RED='\033[38;5;196m'; ORANGE='\033[38;5;208m'; YELLOW='\033[38;5;226m'
GREEN='\033[38;5;82m'; CYAN='\033[38;5;51m'; BLUE='\033[38;5;39m'
VIOLET='\033[38;5;141m'; MAGENTA='\033[38;5;213m'
BG_DARK='\033[48;5;235m'

def width():
    try: return max(40, shutil.get_terminal_size((80,24)).columns)
    except Exception: return 80

def clear():
    # ANSI clear is more reliable than spawning `clear` on Termux.
    sys.stdout.write('\033[2J\033[H\033[3J')
    sys.stdout.flush()

def cursor_hide(): sys.stdout.write('\033[?25l'); sys.stdout.flush()
def cursor_show(): sys.stdout.write('\033[?25h'); sys.stdout.flush()

def line(char='─'):
    print(GRAY + char * min(width()-2, 78) + RESET)

def safe_filename(s, fallback='download'):
    s=re.sub(r'[\\/:*?"<>|]+','_',str(s or '').strip())
    s=re.sub(r'\s+',' ',s).strip(' .')
    return (s or fallback)[:180]

def _center(text, n):
    text=str(text); return text.center(n)

def header(title, subtitle='', icon='◆'):
    clear(); w=min(width()-2,78)
    print()
    print(ORANGE+BOLD+'╔'+'═'*(w-2)+'╗'+RESET)
    label=f' {icon}  {title} '
    label=label[:w-2]
    print(ORANGE+BOLD+'║'+RESET + VIOLET+BOLD+label.center(w-2)+RESET + ORANGE+BOLD+'║'+RESET)
    print(ORANGE+BOLD+'╚'+'═'*(w-2)+'╝'+RESET)
    if subtitle: print(DIM+'  '+subtitle+RESET)
    print()

def section(title, accent=CYAN):
    print(accent+BOLD+'  ┌─ '+title+' '+('─'*max(0,min(42,width()-12-len(title))))+'┐'+RESET)

def menu_item(key, text, accent=WHITE, hint=''):
    tail=('  '+DIM+hint+RESET) if hint else ''
    print(f'  {accent}{BOLD}[{key}]{RESET} {WHITE}{text}{RESET}{tail}')

def status(text, kind='info'):
    colors={'ok':GREEN,'info':CYAN,'warn':YELLOW,'err':RED}
    symbols={'ok':'✓','info':'•','warn':'!','err':'✗'}
    c=colors.get(kind,CYAN); s=symbols.get(kind,'•')
    print(f'  {c}{BOLD}{s}{RESET} {text}')

def pause(msg='Press ENTER to continue...'):
    try: input(DIM+'  '+msg+RESET)
    except (KeyboardInterrupt,EOFError): pass

def prompt(label='Select', accent=VIOLET):
    try: return input(f'\n  {accent}{BOLD}{label} ›{RESET} ').strip()
    except (KeyboardInterrupt,EOFError): return None

def prompt_url():
    try: return input(f'\n  {VIOLET}{BOLD}URL ›{RESET} ').strip()
    except (KeyboardInterrupt,EOFError): return None

def _visible_len(text):
    return len(re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(text)))

def _format_eta(seconds):
    if seconds is None:
        return "--:--"
    try:
        seconds = max(0, int(float(seconds)))
    except (TypeError, ValueError):
        return "--:--"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def progress(done,total,speed=0,eta=None,prefix=''):
    """Render exactly one terminal row using CR + ANSI erase."""
    cols = max(40, shutil.get_terminal_size((80, 24)).columns)
    done = max(0.0, float(done or 0))
    total = max(0.0, float(total or 0))
    ratio = min(1.0, done / total) if total else 0.0
    speed = max(0.0, float(speed or 0))

    if speed < 1024 * 1024:
        speed_text = f"{speed/1024:.1f} KB/s"
    else:
        speed_text = f"{speed/1024/1024:.1f} MB/s"
    eta_text = _format_eta(eta)
    prefix_text = (str(prefix).strip() + " ") if prefix else ""

    fixed = 2 + _visible_len(prefix_text) + 7 + 1 + len(speed_text) + 5 + len(eta_text)
    bar_width = max(8, min(28, cols - fixed - 1))

    while True:
        filled = int(bar_width * ratio)
        bar = "█" * filled + "░" * (bar_width - filled)
        text = (
            f"  {prefix_text}{CYAN}{bar}{RESET} "
            f"{ratio*100:5.1f}% {GREEN}{speed_text}{RESET} ETA {eta_text}"
        )
        if _visible_len(text) < cols or bar_width <= 8:
            break
        bar_width -= 1

    sys.stdout.write("\r\033[2K" + text)
    sys.stdout.flush()

def progress_done(prefix='Complete'):
    sys.stdout.write('\033[1G\033[2K'+f'  {GREEN}{BOLD}✓ {prefix}{RESET}\n'); sys.stdout.flush()

def spinner(label, seconds=.35):
    chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    for c in chars[:4]:
        sys.stdout.write(f'\r\033[2K  {CYAN}{c}{RESET} {label}'); sys.stdout.flush(); time.sleep(seconds/4)
    sys.stdout.write('\r\033[2K'); sys.stdout.flush()

class CursorGuard:
    def __enter__(self): cursor_hide(); return self
    def __exit__(self,*args): cursor_show()
