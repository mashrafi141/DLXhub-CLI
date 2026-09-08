#!/usr/bin/env python3
"""
RGS Video Downloader - Termux / Android
Single-file XXXFollow downloader.

Features:
    1. Single Video mode
    2. Multiple Video mode
    3. Best video + best available audio
    4. FFmpeg merge to MP4 when separate streams exist
    5. Retry / Skip / Quit on errors
    6. .download folder beside this script

Run:
    python downloader.py

Dependencies:
    pkg install ffmpeg
    python -m pip install -U yt-dlp requests beautifulsoup4
"""

import os
import re
import sys
import time
import shutil
import json
import urllib3
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
    os.system("clear")


def term_width():
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


def line(char="─"):
    print(DIM + char * min(max(term_width() - 2, 20), 78) + RESET)


def banner():
    clear()
    w = min(max(term_width() - 2, 30), 78)
    print()
    print(ORANGE + BOLD + "╔" + "═" * (w - 2) + "╗" + RESET)
    title = " RGS VIDEO DOWNLOADER "
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
    print(DIM + "  XXXFollow → local MP4 downloader" + RESET)
    print()


def pause(message="Press ENTER to continue..."):
    try:
        input(DIM + "  " + message + RESET)
    except (KeyboardInterrupt, EOFError):
        pass


# ---------- Paths ----------

# The output directory is relative to the directory containing this script.
# This remains predictable even when the command is launched from elsewhere.
SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = SCRIPT_DIR / ".download"


def ensure_download_dir():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------- URL / metadata ----------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Mobile Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
    "Referer": "https://www.xxxfollow.com/",
}

VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v")

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def normalize_url(url):
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def is_xxxfollow_url(url):
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return host == "xxxfollow.com" or host.endswith(".xxxfollow.com")
    except Exception:
        return False


def extract_id_from_url(url):
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    parts = [p for p in path.split("/") if p]
    candidate = unquote(parts[-1]) if parts else ""
    m = re.search(r"(?:^|[-_])(\d{3,})(?:[-_]|$)", candidate)
    return m.group(1) if m else candidate

def safe_filename(name):
    name = unquote(name or "").strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        name = "xxxfollow_video"
    return name[:150]


def unique_path(path):
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    n = 2

    while True:
        candidate = path.with_name(f"{stem}_{n}{suffix}")
        if not candidate.exists():
            return candidate
        n += 1


# ---------- XXXFollow resolver ----------

MEDIA_RE = re.compile(r'''(?:https?:)?(?:\/\/)?[^\"'<>\s]+?(?:\.mp4|\.webm|\.m4v|\.mov)(?:\?[^\"'<>\s]*)?''', re.I)
HLS_RE = re.compile(r'''(?:https?:)?(?:\/\/)?[^\"'<>\s]+?\.m3u8(?:\?[^\"'<>\s]*)?''', re.I)


def _clean_media_url(value):
    if not value:
        return None
    value = str(value).replace('\\/', '/').replace('\\u0026', '&').replace('&amp;', '&')
    value = value.strip('\\\"\' )]};,')
    if value.startswith('//'):
        value = 'https:' + value
    return value if value.startswith(('http://', 'https://')) else None


def collect_video_urls(html):
    urls, seen = [], set()

    def add(value):
        value = _clean_media_url(value)
        if not value or value in seen:
            return
        low = value.lower()
        if any(ext in low for ext in ('.mp4', '.webm', '.m4v', '.mov', '.m3u8')):
            seen.add(value)
            urls.append(value)

    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all('meta'):
        key = (tag.get('property') or tag.get('name') or '').lower()
        if key in {'og:video', 'og:video:url', 'og:video:secure_url', 'twitter:player:stream'}:
            add(tag.get('content'))

    for tag in soup.find_all(['video', 'source']):
        for attr in ('src', 'data-src', 'data-video', 'data-file', 'data-url', 'data-src-url'):
            add(tag.get(attr))

    for script in soup.find_all('script'):
        text = script.string or script.get_text() or ''
        for match in MEDIA_RE.findall(text):
            add(match)
        for match in HLS_RE.findall(text):
            add(match)

    for pattern in (MEDIA_RE, HLS_RE):
        for match in pattern.findall(html):
            add(match)

    return urls


def _is_ssl_verification_error(exc):
    text = str(exc).lower()
    return (
        "certificate verify failed" in text
        or "hostname mismatch" in text
        or "sslcertverificationerror" in text
        or "ssl error" in text
    )


def fetch_page(session, url):
    try:
        response = session.get(url, headers=HEADERS, timeout=(15,45), allow_redirects=True, verify=True)
    except requests.exceptions.SSLError as exc:
        if not is_xxxfollow_url(url) or not _is_ssl_verification_error(exc):
            raise
        print(YELLOW + "  ! XXXFollow TLS verification failed; using site-only fallback..." + RESET)
        response = session.get(url, headers=HEADERS, timeout=(15,45), allow_redirects=True, verify=False)
    response.raise_for_status()
    return response.text, response.url


def _walk_json(value, add):
    if isinstance(value, dict):
        for v in value.values():
            if isinstance(v, str) and any(x in v.lower() for x in ('.mp4','.webm','.m4v','.mov','.m3u8')):
                add(v, 'JSON/application state')
            _walk_json(v, add)
    elif isinstance(value, list):
        for v in value:
            _walk_json(v, add)


def _script_urls(html, base):
    from urllib.parse import urljoin
    out=[]; seen=set(); soup=BeautifulSoup(html,'html.parser')
    for tag in soup.find_all('script'):
        src=tag.get('src')
        if src:
            u=urljoin(base,src)
            if u not in seen: seen.add(u); out.append(u)
    return out


def _iframe_urls(html, base):
    from urllib.parse import urljoin
    out=[]; seen=set(); soup=BeautifulSoup(html,'html.parser')
    for tag in soup.find_all('iframe'):
        src=tag.get('src') or tag.get('data-src')
        if src:
            u=urljoin(base,src)
            if u.startswith(('http://','https://')) and u not in seen: seen.add(u); out.append(u)
    return out


def resolve_video_urls(session, page_url):
    html, final_url = fetch_page(session, page_url)
    urls=[]; seen=set()
    def add(value, source):
        value=_clean_media_url(value)
        if not value or value in seen: return
        if any(x in value.lower() for x in ('.mp4','.webm','.m4v','.mov','.m3u8')):
            seen.add(value); urls.append((value,source))
    for u in collect_video_urls(html): add(u,'page HTML / embedded data')
    soup=BeautifulSoup(html,'html.parser')
    for script in soup.find_all('script'):
        text=script.string or script.get_text() or ''
        if script.get('type')=='application/ld+json':
            try: _walk_json(json.loads(text),add)
            except Exception: pass
        for m in MEDIA_RE.findall(text): add(m,'page JavaScript')
        for m in HLS_RE.findall(text): add(m,'page JavaScript')
    for iframe in _iframe_urls(html,final_url)[:8]:
        try: ih,ifinal=fetch_page(session,iframe)
        except Exception: continue
        for u in collect_video_urls(ih): add(u,'embedded player')
        for m in MEDIA_RE.findall(ih): add(m,'embedded player')
        for m in HLS_RE.findall(ih): add(m,'embedded player')
    for script_url in _script_urls(html,final_url)[:12]:
        try:
            r=session.get(script_url,headers=HEADERS,timeout=(10,25),verify=True)
        except requests.exceptions.SSLError as exc:
            if is_xxxfollow_url(script_url) and _is_ssl_verification_error(exc):
                try: r=session.get(script_url,headers=HEADERS,timeout=(10,25),verify=False)
                except Exception: continue
            else: continue
        except Exception: continue
        if r.ok:
            for m in MEDIA_RE.findall(r.text): add(m,'first-party JavaScript')
            for m in HLS_RE.findall(r.text): add(m,'first-party JavaScript')
    return urls, final_url


def resolve_video_url(session, page_url):
    urls, final_url=resolve_video_urls(session,page_url)
    if urls: return urls[0][0],final_url
    raise RuntimeError('Could not find a direct video/stream URL on the supplied XXXFollow page.')

# ---------- FFmpeg / yt-dlp ----------

def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def check_dependencies():
    """
    FFmpeg is required when XXXFollow provides separate video/audio streams.
    yt-dlp is the primary extractor.
    """
    if not ffmpeg_available():
        print(RED + BOLD + "  ✗ FFmpeg was not found." + RESET)
        print()
        print(YELLOW + "  Install it in Termux with:" + RESET)
        print("    pkg install ffmpeg")
        return False

    return True


def format_bytes(num):
    units = ["B", "KB", "MB", "GB"]
    value = float(num)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{num} B"


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


def ytdlp_opts(format_selector=None, output_dir=None, mode="video"):
    opts={
        "format": format_selector or ("bestvideo*+bestaudio/best" if mode=="video" else "bestaudio/best"),
        "outtmpl": str(Path(output_dir or DOWNLOAD_DIR) / "%(title).150B [%(id)s].%(ext)s"),
        "noplaylist": True, "quiet": True, "no_warnings": True, "noprogress": True,
        "progress_hooks": [ytdlp_progress], "retries": 5, "fragment_retries": 5,
        "file_access_retries": 5, "extractor_retries": 3, "continuedl": True,
        "overwrites": False, "socket_timeout": 30, "http_headers": HEADERS,
        "referer": "https://www.xxxfollow.com/", "ffmpeg_location": shutil.which("ffmpeg"),
        "postprocessors": ([{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"192"}] if mode=="audio" else []),
    }
    if mode=="video": opts["merge_output_format"]="mp4"
    return opts


def find_downloaded_output(before_files, info):
    """
    Find the actual output file created by yt-dlp.

    We compare the directory before/after the download because yt-dlp may
    first create a .webm/.mp4 temporary file and then merge it into MP4.
    """
    after_files = {
        p for p in DOWNLOAD_DIR.iterdir()
        if p.is_file()
    }

    candidates = list(after_files - before_files)

    # Ignore partial/temp files.
    candidates = [
        p for p in candidates
        if not p.name.endswith((".part", ".ytdl", ".temp"))
    ]

    if candidates:
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    requested = info.get("requested_downloads") or []
    for item in requested:
        filepath = item.get("filepath")
        if filepath:
            p = Path(filepath)
            if p.exists():
                return p

    filepath = info.get("_filename")
    if filepath and Path(filepath).exists():
        return Path(filepath)

    return None


def download_with_ytdlp(page_url, number, session=None, format_selector=None, output_dir=None, mode='video'):
    out=Path(output_dir or DOWNLOAD_DIR); out.mkdir(parents=True,exist_ok=True)
    before_files={p for p in out.iterdir() if p.is_file()}
    options=ytdlp_opts(format_selector,out,mode)
    print(DIM+'  Trying yt-dlp extractor...'+RESET)
    with yt_dlp.YoutubeDL(options) as ydl:
        info=ydl.extract_info(page_url,download=False)
        if not info: raise RuntimeError('No stream metadata found.')
        title=info.get('title') or info.get('id') or 'xxxfollow_video'
        print(WHITE+f'  Title: {title}'+RESET)
        print(ORANGE+f'  Downloading {"audio (MP3)" if mode=="audio" else "video (MP4)"}...'+RESET)
        ydl.process_info(info)
        after={p for p in out.iterdir() if p.is_file()}; candidates=[p for p in after-before_files if not p.name.endswith(('.part','.ytdl','.temp'))]
        if candidates:
            candidates.sort(key=lambda p:p.stat().st_mtime,reverse=True); return candidates[0],info
        fp=info.get('_filename')
        if fp and Path(fp).exists(): return Path(fp),info
    raise RuntimeError('Download completed but output file could not be resolved.')


# ---------- Legacy direct downloader / fallback ----------

def choose_extension(video_url, response):
    content_type = (response.headers.get("Content-Type") or "").lower()

    if "webm" in content_type:
        return ".webm"
    if "quicktime" in content_type or "mov" in content_type:
        return ".mov"
    if "mp4" in content_type:
        return ".mp4"

    path = urlparse(video_url).path.lower()
    for ext in VIDEO_EXTENSIONS:
        if ext in path:
            return ext

    return ".mp4"


def progress_bar(done, total, started, width=34):
    if total and total > 0:
        ratio = min(1.0, done / total)
        filled = int(width * ratio)
        bar = "█" * filled + "░" * (width - filled)
        percent = ratio * 100
        elapsed = max(time.time() - started, 0.001)
        speed = done / elapsed
        speed_text = format_bytes(speed) + "/s"
        return f"{bar} {percent:6.2f}%  {speed_text}"

    elapsed = max(time.time() - started, 0.001)
    speed = done / elapsed
    return f"{format_bytes(done):>10}  {format_bytes(speed)}/s"


def download_video(session, video_url, output_path):
    """
    Kept as a fallback utility for a direct progressive URL.

    NOTE:
    This method cannot manufacture audio if the direct URL itself contains
    only video. The primary yt-dlp method above is what fixes that issue.
    """
    temp_path = output_path.with_suffix(output_path.suffix + ".part")

    if temp_path.exists():
        try:
            temp_path.unlink()
        except OSError:
            pass

    request_headers={**HEADERS,"Accept":"video/av01,video/webm,video/mp4,video/*;q=0.9,*/*;q=0.5","Referer":"https://www.xxxfollow.com/"}
    try:
        response_ctx=session.get(video_url,headers=request_headers,stream=True,timeout=(20,60),allow_redirects=True,verify=True)
    except requests.exceptions.SSLError as exc:
        if not is_xxxfollow_url(video_url) or not _is_ssl_verification_error(exc): raise
        response_ctx=session.get(video_url,headers=request_headers,stream=True,timeout=(20,60),allow_redirects=True,verify=False)
    with response_ctx as response:
        response.raise_for_status()

        total = int(response.headers.get("Content-Length") or 0)
        started = time.time()
        done = 0

        with open(temp_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue

                file.write(chunk)
                done += len(chunk)

                text = progress_bar(done, total, started)
                print(
                    "\r  " + CYAN + text + RESET + " " * 8,
                    end="",
                    flush=True,
                )

        print()

    if not temp_path.exists() or temp_path.stat().st_size == 0:
        raise RuntimeError("Downloaded file is empty.")

    temp_path.replace(output_path)


# ---------- Single video workflow ----------

def download_one(session, page_url, number, format_selector=None, output_dir=None, mode='video'):
    print(); line('─'); print(BLUE+BOLD+f'  {mode.upper()} #{number} [XXXFollow]'+RESET)
    if not check_dependencies(): raise RuntimeError('FFmpeg is required.')
    target=page_url
    try:
        output,info=download_with_ytdlp(target,number,session,format_selector,output_dir,mode)
        if output and output.exists():
            print(GREEN+BOLD+f'  ✓ Complete — {output.name} ({format_bytes(output.stat().st_size)})'+RESET); return output,info
    except Exception as exc:
        if mode=='audio': raise RuntimeError(f'Audio extraction failed: {exc}')
        print(DIM+f'  yt-dlp fallback: {exc}'+RESET)
    if mode=='audio': raise RuntimeError('No audio stream available.')
    # Original direct-stream discovery fallback.
    out=Path(output_dir or DOWNLOAD_DIR); out.mkdir(parents=True,exist_ok=True); before={p for p in out.iterdir() if p.is_file()}
    candidates,final_url=resolve_video_urls(session,page_url)
    if not candidates: raise RuntimeError('No media URL was discovered from page/player data.')
    for index,(stream_url,source) in enumerate(candidates[:12],1):
        print(CYAN+f'  Checking stream #{index} ({source})...'+RESET)
        try:
            h={**HEADERS,'Referer':final_url}; r=session.get(stream_url,headers=h,stream=True,timeout=(20,60),allow_redirects=True,verify=True); r.raise_for_status()
            ctype=(r.headers.get('Content-Type') or '').lower()
            if 'video/' not in ctype and not stream_url.lower().split('?')[0].endswith(('.mp4','.webm','.m4v','.mov')): r.close(); continue
            name=safe_filename('xxxfollow_'+str(extract_id_from_url(page_url))); ext='.webm' if 'webm' in ctype else '.mp4'; output=unique_path(out/(name+ext)); temp=output.with_suffix(output.suffix+'.part'); total=int(r.headers.get('Content-Length') or 0); done=0; started=time.time()
            with open(temp,'wb') as f:
                for chunk in r.iter_content(1024*256):
                    if chunk:
                        from core import ui as _ui; _ui.progress(done, total, sp, ((total-done)/sp if total and sp else None))
            print(); temp.replace(output); print(GREEN+BOLD+f'  ✓ Complete — {output.name} ({format_bytes(output.stat().st_size)})'+RESET); return output,{'title':name}
        except Exception: continue
    raise RuntimeError('Discovered candidates were not valid downloadable video streams.')

def get_url(prompt="URL › "):
    try:
        value = input(VIOLET + "  " + prompt + RESET).strip()
    except (KeyboardInterrupt, EOFError):
        return None

    return value


def retry_skip_quit():
    print()
    print(YELLOW + "  [R] Retry   [S] Skip   [Q] Quit" + RESET)

    try:
        choice = input(VIOLET + "  › " + RESET).strip().lower()
    except (KeyboardInterrupt, EOFError):
        return "q"

    if choice == "r":
        return "r"
    if choice == "q":
        return "q"
    return "s"


# ---------- Single mode ----------

def single_mode(session):
    while True:
        banner()

        print(CYAN + BOLD + "  SINGLE VIDEO" + RESET)
        print(DIM + "  Download one XXXFollow video at a time." + RESET)
        print(DIM + "  Type 'b' to return to the main menu." + RESET)
        print()
        line()

        url = get_url()

        if url is None:
            return

        if url.lower() in {"b", "back"}:
            return

        if url.lower() in {"q", "quit", "exit"}:
            return

        url = normalize_url(url)

        if not url:
            print(RED + "\n  ✗ URL cannot be empty." + RESET)
            time.sleep(1.2)
            continue

        if not is_xxxfollow_url(url):
            print(RED + "\n  ✗ Please enter a XXXFollow URL." + RESET)
            time.sleep(1.4)
            continue

        while True:
            try:
                download_one(session, url, 1)
                pause()
                break

            except requests.RequestException as exc:
                print()
                print(RED + BOLD + "  ✗ Network/download error" + RESET)
                print(DIM + f"  {exc}" + RESET)

            except Exception as exc:
                print()
                print(RED + BOLD + "  ✗ Could not download this video" + RESET)
                print(DIM + f"  {exc}" + RESET)

            action = retry_skip_quit()

            if action == "r":
                continue

            if action == "q":
                return

            break


# ---------- Multiple mode ----------

def collect_multiple_urls():
    """
    Multiple mode accepts:
      - one URL per line
      - multiple URLs separated by spaces on one line
      - empty ENTER to finish input
    """
    urls = []

    print(CYAN + BOLD + "  MULTIPLE VIDEO" + RESET)
    print(DIM + "  Paste URLs one by one." + RESET)
    print(DIM + "  You can also paste several URLs separated by spaces." + RESET)
    print(DIM + "  Press ENTER on an empty line to start downloading." + RESET)
    print(DIM + "  Type 'b' before the queue starts to go back." + RESET)
    print()
    line()

    while True:
        try:
            value = input(VIOLET + "  URL › " + RESET).strip()
        except (KeyboardInterrupt, EOFError):
            return None

        if not value:
            break

        if not urls and value.lower() in {"b", "back"}:
            return None

        # Accept whitespace-separated pasted URLs.
        parts = value.split()

        for part in parts:
            part = normalize_url(part)

            if not is_xxxfollow_url(part):
                print(
                    RED
                    + f"  ✗ Ignored (not a XXXFollow URL): {part}"
                    + RESET
                )
                continue

            urls.append(part)
            print(
                GREEN
                + f"  ✓ Added #{len(urls)}"
                + RESET
            )

    return urls


def multiple_mode(session):
    while True:
        banner()

        urls = collect_multiple_urls()

        if urls is None:
            return

        if not urls:
            print(YELLOW + "\n  No URLs added." + RESET)
            pause()
            continue

        print()
        print(GREEN + BOLD + f"  {len(urls)} video(s) queued." + RESET)
        print()

        success = 0
        skipped = 0

        for index, url in enumerate(urls, start=1):
            while True:
                try:
                    download_one(session, url, index)
                    success += 1
                    break

                except requests.RequestException as exc:
                    print()
                    print(
                        RED
                        + BOLD
                        + f"  ✗ VIDEO #{index} FAILED"
                        + RESET
                    )
                    print(DIM + f"  {exc}" + RESET)

                except Exception as exc:
                    print()
                    print(
                        RED
                        + BOLD
                        + f"  ✗ VIDEO #{index} FAILED"
                        + RESET
                    )
                    print(DIM + f"  {exc}" + RESET)

                action = retry_skip_quit()

                if action == "r":
                    continue

                if action == "q":
                    print()
                    print(YELLOW + "  Batch stopped by user." + RESET)
                    print(
                        f"  Completed: {success}"
                        f"  | Skipped: {skipped}"
                        f"  | Remaining: {len(urls) - index}"
                    )
                    pause()
                    return

                skipped += 1
                break

            print()

        line()
        print(GREEN + BOLD + f"  ✓ Completed: {success}" + RESET)
        print(YELLOW + f"  • Skipped:   {skipped}" + RESET)
        print(DIM + f"  • Total:     {len(urls)}" + RESET)
        print()
        pause("Press ENTER to return to the menu...")
        return


# ---------- Main menu ----------

def main_menu():
    ensure_download_dir()

    session = requests.Session()
    session.headers.update(HEADERS)

    while True:
        banner()

        print(WHITE + "  Output folder:" + RESET)
        print("  " + ORANGE + str(DOWNLOAD_DIR) + RESET)
        print()
        line()

        print()
        print(ORANGE + BOLD + "  [1]" + RESET + "  Single Video")
        print(CYAN + BOLD + "  [2]" + RESET + "  Multiple Videos")
        print(RED + BOLD + "  [Q]" + RESET + "  Quit")
        print()

        try:
            choice = input(VIOLET + BOLD + "  Select › " + RESET).strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "1":
            single_mode(session)

        elif choice == "2":
            multiple_mode(session)

        elif choice in {"q", "quit", "exit"}:
            break

        else:
            print(RED + "  ✗ Invalid option." + RESET)
            time.sleep(1)


def main():
    try:
        main_menu()
    except KeyboardInterrupt:
        print()
    finally:
        clear()
        print()
        print(GREEN + BOLD + "  XXXFollow Downloader closed." + RESET)
        print(DIM + f"  Files are in: {DOWNLOAD_DIR}" + RESET)
        print()


if __name__ == "__main__":
    main()
