#!/usr/bin/env python3
"""
RGS Video Downloader - Termux / Android / PC
Single-file Twitter (X) & Facebook Video Downloader.

Features:
    1. Single Video mode
    2. Multiple Video mode (Batch)
    3. Twitter (X) and Facebook Official API/Extractor Stream Support
    4. Private Video support via 'Fb_cookies.txt' and 'X_cookies.txt'
    5. Direct Fallback Engine for Parsing Errors
    6. Best video + best audio merge via FFmpeg
    7. Clean UI with Single-line Progress Bar
    8. Retry / Skip / Quit options
    9. Files saved inside .download folder beside this script
"""

import os
import re
import sys
import time
import shutil
from pathlib import Path
from urllib.parse import urlparse, unquote

try:
    import requests
    from bs4 import BeautifulSoup
    import yt_dlp
except ImportError as exc:
    print("\033[91mMissing dependency:\033[0m", exc)
    print()
    print("Install with:")
    print("  pkg install ffmpeg")
    print("  python -m pip install -U yt-dlp requests beautifulsoup4")
    sys.exit(1)


# ---------- Terminal / UI ----------

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ORANGE = "\033[38;5;208m"
BLUE = "\033[38;5;39m"
VIOLET = "\033[38;5;141m"
GREEN = "\033[38;5;82m"
RED = "\033[38;5;196m"
CYAN = "\033[38;5;51m"
WHITE = "\033[97m"
YELLOW = "\033[38;5;226m"


def clear():
    os.system("clear" if os.name != "nt" else "cls")


def term_width():
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def line(char="─"):
    print(DIM + char * min(max(term_width() - 2, 20), 78) + RESET)


def check_cookies_status():
    fb_exists = FB_COOKIES.exists()
    x_exists = X_COOKIES.exists()
    
    if fb_exists or x_exists:
        fb_status = f"{GREEN}Fb Cookies: ✓{RESET}" if fb_exists else f"{DIM}Fb Cookies: ✗{RESET}"
        x_status = f"{GREEN}X Cookies: ✓{RESET}" if x_exists else f"{DIM}X Cookies: ✗{RESET}"
        print(f"  [{fb_status} | {x_status}] - Private Stream Ready")
    else:
        print(DIM + "  [!] No 'Fb_cookies.txt' or 'X_cookies.txt' found. Public Media Only." + RESET)


def banner():
    clear()
    w = min(max(term_width() - 2, 30), 78)
    print()
    print(ORANGE + BOLD + "╔" + "═" * (w - 2) + "╗" + RESET)
    title = " RGS SOCIAL VIDEO DOWNLOADER "
    left = max(0, (w - 2 - len(title)) // 2)
    right = max(0, w - 2 - len(title) - left)
    print(
        ORANGE + BOLD + "║" + RESET
        + " " * left
        + VIOLET + BOLD + title + RESET
        + " " * right
        + ORANGE + BOLD + "║" + RESET
    )
    print(ORANGE + BOLD + "╚" + "═" * (w - 2) + "╝" + RESET)
    print()
    print(DIM + "  Twitter (X) & Facebook → Local MP4 Downloader" + RESET)
    check_cookies_status()
    print()


def pause(message="Press ENTER to continue..."):
    try:
        input(DIM + "  " + message + RESET)
    except (KeyboardInterrupt, EOFError):
        pass


# ---------- Paths & Cookies ----------

SCRIPT_DIR = Path(__file__).resolve().parent
COOKIES_DIR = SCRIPT_DIR / 'cookies'
COOKIES_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR = SCRIPT_DIR / ".download"
FB_COOKIES = COOKIES_DIR / "Fb_cookies.txt"
X_COOKIES = COOKIES_DIR / "X_cookies.txt"


def ensure_download_dir():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------- URL & Helpers ----------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def normalize_url(url):
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def normalize_x_url(url):
    p=urlparse(url); host=p.netloc.lower().split(':')[0]
    if host=='x.com' or host.endswith('.x.com'):
        return 'https://twitter.com'+p.path+(('?'+p.query) if p.query else '')
    return url

def is_x_post_url(url):
    p=urlparse(url); host=p.netloc.lower().split(':')[0]
    if 'twitter.com' not in host and 'x.com' not in host: return True
    return bool(re.search(r'/(?:i/)?status/\d+',p.path))

def is_supported_url(url):
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        supported = [
            "twitter.com", "x.com", 
            "facebook.com", "fb.watch", "m.facebook.com", "web.facebook.com"
        ]
        return any(domain in host for domain in supported)
    except Exception:
        return False


def get_platform_name(url):
    host = urlparse(url).netloc.lower()
    if "twitter" in host or "x.com" in host:
        return "Twitter (X)"
    if "facebook" in host or "fb.watch" in host:
        return "Facebook"
    return "Social Platform"


def safe_filename(name):
    name = unquote(name or "").strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        name = "social_video"
    return name[:150]


def unique_path(path):
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def format_bytes(num):
    units = ["B", "KB", "MB", "GB"]
    value = float(num or 0)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{num} B"


# ---------- Direct FB Fallback Resolver ----------

def extract_facebook_direct(page_url, session):
    resp = session.get(page_url, headers=HEADERS, timeout=(15, 30), allow_redirects=True)
    html = resp.text

    hd_match = (
        re.search(r'browser_native_hd_url["\']\s*:\s*["\']([^"\\\']+)', html)
        or re.search(r'hd_src["\']\s*:\s*["\']([^"\\\']+)', html)
        or re.search(r'playable_url_quality_hd["\']\s*:\s*["\']([^"\\\']+)', html)
    )

    sd_match = (
        re.search(r'browser_native_sd_url["\']\s*:\s*["\']([^"\\\']+)', html)
        or re.search(r'sd_src["\']\s*:\s*["\']([^"\\\']+)', html)
        or re.search(r'playable_url["\']\s*:\s*["\']([^"\\\']+)', html)
    )

    media_url = None
    if hd_match:
        media_url = hd_match.group(1).replace("\\/", "/")
    elif sd_match:
        media_url = sd_match.group(1).replace("\\/", "/")

    if not media_url:
        soup = BeautifulSoup(html, "html.parser")
        for meta in soup.find_all("meta"):
            prop = meta.get("property") or meta.get("name") or ""
            if prop in ("og:video", "og:video:url", "og:video:secure_url"):
                content = meta.get("content")
                if content and "fbcdn" in content:
                    media_url = content
                    break

    if media_url:
        title_match = re.search(r"<title>(.*?)</title>", html, re.I)
        title = title_match.group(1) if title_match else "facebook_video"
        title = re.sub(r"\| Facebook$", "", title, flags=re.I).strip()
        return media_url, safe_filename(title)

    return None, None


# ---------- Downloader Engine ----------

def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def check_dependencies():
    if not ffmpeg_available():
        print(RED + BOLD + "  ✗ FFmpeg was not found." + RESET)
        print(YELLOW + "  Please install FFmpeg to merge video & audio properly." + RESET)
        return False
    return True


def ytdlp_progress(data):
    try:
        from core import ui as _ui
        if data.get("status") == "downloading":
            _ui.progress(
                data.get("downloaded_bytes") or 0,
                data.get("total_bytes") or data.get("total_bytes_estimate") or 0,
                data.get("speed") or 0,
                data.get("eta"),
            )
        elif data.get("status") == "finished":
            _ui.progress_done("Processing...")
    except Exception:
        pass


def get_ytdlp_options(url, format_selector=None, output_dir=None, mode='video'):
    platform=get_platform_name(url)
    out=Path(output_dir or DOWNLOAD_DIR); out.mkdir(parents=True,exist_ok=True)
    opts={
      'format': format_selector or ('bestvideo+bestaudio/best' if mode=='video' else 'bestaudio/best'),
      'merge_output_format':'mp4' if mode=='video' else None,
      'outtmpl':str(out/'%(extractor)s_%(title).100B [%(id)s].%(ext)s'),
      'noplaylist':True,'quiet':True,'no_warnings':True,'noprogress':True,
      'progress_hooks':[ytdlp_progress],'retries':5,'fragment_retries':5,'socket_timeout':30,
      'http_headers':HEADERS,'ffmpeg_location':shutil.which('ffmpeg')
    }
    if opts.get('merge_output_format') is None: opts.pop('merge_output_format',None)
    if mode=='audio':
        opts['postprocessors']=[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'192'}]
    if platform=='Facebook' and FB_COOKIES.exists(): opts['cookiefile']=str(FB_COOKIES)
    elif platform=='Twitter (X)' and X_COOKIES.exists(): opts['cookiefile']=str(X_COOKIES)
    return opts

def load_cookies_to_session(session, cookie_file):
    if cookie_file.exists():
        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("#") and line.strip():
                        parts = line.strip().split("\t")
                        if len(parts) >= 7:
                            domain, _, path, secure, _, name, value = parts[:7]
                            session.cookies.set(name, value, domain=domain, path=path)
        except Exception:
            pass


def find_downloaded_output(before_files, info):
    after_files = {p for p in DOWNLOAD_DIR.iterdir() if p.is_file()}
    candidates = list(after_files - before_files)
    candidates = [p for p in candidates if not p.name.endswith((".part", ".ytdl", ".temp"))]

    if candidates:
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    filepath = info.get("_filename")
    if filepath and Path(filepath).exists():
        return Path(filepath)

    return None


def download_video_stream(page_url, number, format_selector=None, output_dir=None, mode='video'):
    target=normalize_x_url(page_url) if get_platform_name(page_url)=='Twitter (X)' else page_url
    out=Path(output_dir or DOWNLOAD_DIR); out.mkdir(parents=True,exist_ok=True)
    before_files={p for p in out.iterdir() if p.is_file()}
    platform=get_platform_name(page_url)
    print(DIM+f'  Extracting {platform} stream meta-data...'+RESET)
    # Preserve the original Facebook direct-stream fallback for the default/best
    # video path. Explicit quality selections stay on yt-dlp so the user's
    # chosen resolution is respected.
    if platform == 'Facebook' and mode == 'video' and (not format_selector or format_selector.startswith('bestvideo')):
        try:
            session=requests.Session(); load_cookies_to_session(session,FB_COOKIES)
            media_url,title=extract_facebook_direct(target,session)
            if media_url:
                output_file=unique_path(out/f'{safe_filename(title)}.mp4'); temp=output_file.with_suffix('.mp4.part')
                print(WHITE+f'  Title: {safe_filename(title)}'+RESET); print(ORANGE+'  Downloading via Facebook Direct Stream Engine...'+RESET)
                with session.get(media_url,stream=True,timeout=(20,60)) as r:
                    r.raise_for_status(); total=int(r.headers.get('Content-Length') or 0); started=time.time(); done=0
                    with open(temp,'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*256):
                            if chunk:
                                f.write(chunk); done+=len(chunk); elapsed=max(time.time()-started,.001); sp=done/elapsed; pct=(done/total*100 if total else 0); cols=max(42,shutil.get_terminal_size((80,24)).columns-2); bw=max(8,min(24,cols-36)); fill=int(bw*pct/100) if total else 0; bar='█'*fill+'░'*(bw-fill); sys.stdout.write('\033[1G\033[2K'+f'  {CYAN}{bar}{RESET} {pct:5.1f}% {GREEN}{format_bytes(sp)}/s{RESET}'); sys.stdout.flush()
                print(); temp.replace(output_file); return output_file,{'title':title}
        except Exception as exc:
            print(DIM+f'  Direct stream bypass skipped: {exc}'+RESET)
    options=get_ytdlp_options(target,format_selector,out,mode)
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info=ydl.extract_info(target,download=False)
            if not info: raise RuntimeError('Failed to fetch stream details.')
            title=info.get('title') or info.get('id') or 'media'
            print(WHITE+f'  Title: {safe_filename(title)}'+RESET)
            print(ORANGE+f'  Downloading {"audio (MP3)" if mode=="audio" else "video (MP4)"}...'+RESET)
            ydl.process_info(info)
            after={p for p in out.iterdir() if p.is_file()}; cand=[p for p in after-before_files if not p.name.endswith(('.part','.ytdl','.temp'))]
            if cand:
                cand.sort(key=lambda p:p.stat().st_mtime,reverse=True); return cand[0],info
            requested=info.get('requested_downloads') or []
            for item in requested:
                fp=item.get('filepath');
                if fp and Path(fp).exists(): return Path(fp),info
    except Exception as exc:
        raise RuntimeError(f'Stream Download Error: {exc}')
    raise RuntimeError('Download completed but output file could not be resolved.')


# ---------- Download Workflows ----------

def download_one(page_url, number, format_selector=None, output_dir=None, mode='video'):
    print(); line('─'); print(BLUE+BOLD+f'  {mode.upper()} #{number} [{get_platform_name(page_url)}]'+RESET)
    if not check_dependencies(): raise RuntimeError('FFmpeg dependency check failed.')
    output,info=download_video_stream(page_url,number,format_selector,output_dir,mode)
    if output and output.exists():
        print(GREEN+BOLD+f'  ✓ Complete — {output.name} ({format_bytes(output.stat().st_size)})'+RESET); return output,info
    raise RuntimeError('File creation failed.')

def retry_skip_quit():
    print()
    print(YELLOW + "  [R] Retry   [S] Skip   [Q] Quit" + RESET)
    try:
        choice = input(VIOLET + "  › " + RESET).strip().lower()
    except (KeyboardInterrupt, EOFError):
        return "q"

    if choice in {"r", "s", "q"}:
        return choice
    return "s"


# ---------- Modes ----------

def single_mode():
    while True:
        banner()
        print(CYAN + BOLD + "  SINGLE VIDEO MODE" + RESET)
        print(DIM + "  Supported: Twitter / X, Facebook (Public & Private Videos)" + RESET)
        print(DIM + "  Type 'b' to return to the main menu." + RESET)
        print()
        line()

        try:
            url = input(VIOLET + "  URL › " + RESET).strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not url or url.lower() in {"b", "back", "q", "quit"}:
            return

        url = normalize_url(url)

        if not is_supported_url(url):
            print(RED + "\n  ✗ Please enter a valid Twitter (X) or Facebook URL." + RESET)
            time.sleep(1.5)
            continue

        while True:
            try:
                download_one(url, 1)
                pause()
                break
            except Exception as exc:
                print()
                print(RED + BOLD + "  ✗ Download Failed" + RESET)
                print(DIM + f"  {exc}" + RESET)

            action = retry_skip_quit()
            if action == "r":
                continue
            if action == "q":
                return
            break


def multiple_mode():
    while True:
        banner()
        urls = []
        print(CYAN + BOLD + "  MULTIPLE VIDEO MODE (BATCH)" + RESET)
        print(DIM + "  Paste URLs separated by space or line-by-line." + RESET)
        print(DIM + "  Press ENTER on an empty line to start downloading." + RESET)
        print(DIM + "  Type 'b' to go back." + RESET)
        print()
        line()

        while True:
            try:
                value = input(VIOLET + "  URL › " + RESET).strip()
            except (KeyboardInterrupt, EOFError):
                return

            if not value:
                break

            if not urls and value.lower() in {"b", "back"}:
                return

            parts = value.split()
            for part in parts:
                part = normalize_url(part)
                if not is_supported_url(part):
                    print(RED + f"  ✗ Skipped invalid URL: {part}" + RESET)
                    continue
                urls.append(part)
                print(GREEN + f"  ✓ Added #{len(urls)} [{get_platform_name(part)}]" + RESET)

        if not urls:
            print(YELLOW + "\n  No valid URLs added." + RESET)
            pause()
            continue

        print()
        print(GREEN + BOLD + f"  {len(urls)} video(s) queued for processing." + RESET)
        print()

        success = 0
        skipped = 0

        for index, url in enumerate(urls, start=1):
            while True:
                try:
                    download_one(url, index)
                    success += 1
                    break
                except Exception as exc:
                    print()
                    print(RED + BOLD + f"  ✗ VIDEO #{index} FAILED" + RESET)
                    print(DIM + f"  {exc}" + RESET)

                action = retry_skip_quit()
                if action == "r":
                    continue
                if action == "q":
                    print()
                    print(YELLOW + "  Batch download process terminated by user." + RESET)
                    pause()
                    return
                skipped += 1
                break

        line()
        print(GREEN + BOLD + f"  ✓ Completed: {success}" + RESET)
        print(YELLOW + f"  • Skipped:   {skipped}" + RESET)
        print(DIM + f"  • Total:     {len(urls)}" + RESET)
        print()
        pause()
        return


# ---------- Main Menu ----------

def main_menu():
    ensure_download_dir()

    while True:
        banner()
        print(WHITE + "  Download Destination:" + RESET)
        print("  " + ORANGE + str(DOWNLOAD_DIR) + RESET)
        print()
        line()
        print()
        print(ORANGE + BOLD + "  [1]" + RESET + "  Single Video (Twitter / Facebook)")
        print(CYAN + BOLD + "  [2]" + RESET + "  Multiple Videos (Batch Mode)")
        print(RED + BOLD + "  [Q]" + RESET + "  Quit")
        print()

        try:
            choice = input(VIOLET + BOLD + "  Select Option › " + RESET).strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "1":
            single_mode()
        elif choice == "2":
            multiple_mode()
        elif choice in {"q", "quit", "exit"}:
            break
        else:
            print(RED + "  ✗ Invalid choice." + RESET)
            time.sleep(1)


def main():
    try:
        main_menu()
    except KeyboardInterrupt:
        pass
    finally:
        clear()
        print()
        print(GREEN + BOLD + "  Downloader Session Closed." + RESET)
        print(DIM + f"  Files are safely saved in: {DOWNLOAD_DIR}" + RESET)
        print()


if __name__ == "__main__":
    main()