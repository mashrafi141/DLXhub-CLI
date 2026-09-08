#!/usr/bin/env python3
"""
RGS VIDEO DOWNLOADER - Termux / Android

Features
--------
1. Single Video mode
2. Multiple Video mode
3. Uses RedGIFs' current v2 API instead of scraping the HTML page
4. Automatically requests a temporary API token
5. Selects HD -> SD -> GIF progressive MP4/WebM stream
6. Progressive RedGIFs media is saved directly, so embedded audio is preserved
7. Retry / Skip / Quit on every failed item
8. Output folder is .download beside this script
9. No extra project files are required

Install:
    pkg install python
    python -m pip install -U requests

Run:
    python downloader.py
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
except ImportError:
    print("\033[91mMissing dependency: requests\033[0m")
    print("Run: python -m pip install -U requests")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Terminal UI
# -----------------------------------------------------------------------------
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

SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = SCRIPT_DIR / ".download"

BASE_URL = "https://www.redgifs.com"
API_URL = "https://api.redgifs.com/v2"

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; Mobile) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Mobile Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.8",
    "Referer": BASE_URL + "/",
    "Origin": BASE_URL,
}

API_HEADERS = {
    "referer": BASE_URL + "/",
    "origin": BASE_URL,
    "content-type": "application/json",
}


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
    print(DIM + "  RedGIFs → local video downloader" + RESET)
    print()


def pause(message="Press ENTER to continue..."):
    try:
        input(DIM + "  " + message + RESET)
    except (KeyboardInterrupt, EOFError):
        pass


def ensure_download_dir():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def normalize_url(value):
    value = (value or "").strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value
    return value


def is_redgifs_url(url):
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return host == "redgifs.com" or host.endswith(".redgifs.com")
    except Exception:
        return False


def extract_video_id(url):
    """Extract a RedGIFs id from /watch/<id>, /ifr/<id>, or a direct thumbs URL."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = unquote(parsed.path).strip("/")
    parts = [p for p in path.split("/") if p]

    if host.endswith("redgifs.com") and len(parts) >= 2:
        if parts[0].lower() in {"watch", "ifr", "gif", "gifs", "video", "videos"}:
            return parts[1]

    if host.startswith("thumbs") and parts:
        name = parts[-1].split(".")[0]
        name = re.sub(r"-(?:mobile|desktop|hd|sd)$", "", name, flags=re.I)
        if name:
            return name

    if parts:
        candidate = parts[-1]
        candidate = candidate.split(".")[0]
        if re.fullmatch(r"[A-Za-z0-9_-]{5,100}", candidate):
            return candidate

    return None


def safe_filename(name):
    name = unquote(str(name or "")).strip()
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return (name or "redgifs_video")[:150]


def unique_path(path):
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    n = 2
    while True:
        candidate = path.with_name(f"{stem}_{n}{suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def format_bytes(value):
    value = float(value or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return "0 B"


def format_time(seconds):
    if seconds is None or seconds < 0:
        return "--"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def progress(downloaded,total,started,speed=None):
    if speed is None:
        speed = downloaded / max(time.time() - started, .001)
    try:
        from core import ui as _ui
        eta = ((total - downloaded) / speed) if speed and total else None
        _ui.progress(downloaded, total, speed, eta)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# RedGIFs API client
# -----------------------------------------------------------------------------
class RedGifsClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(BASE_HEADERS)
        self.token = None

    def get_token(self):
        """Get a fresh temporary token from the official RedGIFs API."""
        response = self.session.get(
            f"{API_URL}/auth/temporary",
            headers={
                **BASE_HEADERS,
                "Accept": "application/json, text/plain, */*",
            },
            timeout=(15, 30),
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("token")
        if not token:
            raise RuntimeError("RedGIFs did not return a temporary API token.")
        self.token = token
        return token

    def api_get(self, endpoint, video_id):
        """Call the RedGIFs v2 API and refresh the token once on 401."""
        for attempt in range(2):
            if not self.token:
                self.get_token()

            headers = {
                **API_HEADERS,
                "Authorization": f"Bearer {self.token}",
                "X-CustomHeader": f"{BASE_URL}/watch/{video_id}",
                "Accept": "application/json, text/plain, */*",
            }

            response = self.session.get(
                f"{API_URL}/{endpoint.lstrip('/')}",
                headers=headers,
                timeout=(15, 30),
            )

            if response.status_code == 401 and attempt == 0:
                self.token = None
                continue

            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and data.get("error"):
                raise RuntimeError(f"RedGIFs API: {data['error']}")
            return data

        raise RuntimeError("RedGIFs API authorization failed.")

    def resolve_candidates(self,page_url):
        video_id=extract_video_id(page_url)
        if not video_id: raise RuntimeError('Could not extract the RedGIFs video ID from this URL.')
        data=self.api_get(f'gifs/{video_id}?views=yes',video_id); gif=data.get('gif') or data; urls=gif.get('urls') or {}
        title=gif.get('title') or ' '.join(gif.get('tags') or []) or video_id; duration=gif.get('duration'); width=gif.get('width'); height=gif.get('height')
        candidates=[]
        for q,u in [('HD',urls.get('hd')),('SD',urls.get('sd')),('GIF',urls.get('gif'))]:
            if u: candidates.append({'quality':q,'url':u,'title':title,'duration':duration,'width':width,'height':height,'id':video_id})
        if not candidates: raise RuntimeError('RedGIFs API returned no downloadable media URL.')
        return candidates

    def resolve(self,page_url,preferred='best'):
        candidates=self.resolve_candidates(page_url)
        if preferred and preferred!='best':
            for c in candidates:
                if c['quality'].lower()==str(preferred).lower(): return c
        media=candidates[0]
        print(WHITE+f"  Title: {media['title']}"+RESET)
        print(DIM+f"  Available: {', '.join(c['quality'] for c in candidates)}"+RESET)
        return media

    def download(self, media, number, output_dir=None):
        title = safe_filename(media["title"])
        video_id = safe_filename(media["id"])
        target_dir=Path(output_dir or DOWNLOAD_DIR); target_dir.mkdir(parents=True,exist_ok=True)
        output = unique_path(target_dir / f"{title} [{video_id}].mp4")
        temp = output.with_suffix(output.suffix + ".part")

        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass

        print(ORANGE + "  Downloading..." + RESET)
        started = time.time()
        downloaded = 0

        headers = {
            **BASE_HEADERS,
            "Accept": "video/mp4,video/webm,video/*;q=0.9,*/*;q=0.5",
            "Referer": f"{BASE_URL}/watch/{media['id']}",
        }

        with self.session.get(
            media["url"],
            headers=headers,
            stream=True,
            timeout=(20, 120),
            allow_redirects=True,
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length") or 0)
            content_type = (response.headers.get("Content-Type") or "").lower()

            # RedGIFs can occasionally return WebM. Keep the real extension.
            if "webm" in content_type and output.suffix.lower() == ".mp4":
                output = output.with_suffix(".webm")
                temp = output.with_suffix(output.suffix + ".part")
                output = unique_path(output)
                temp = output.with_suffix(output.suffix + ".part")

            with open(temp, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 512):
                    if not chunk:
                        continue
                    file.write(chunk)
                    downloaded += len(chunk)
                    progress(downloaded, total, started)

        print()

        if not temp.exists() or temp.stat().st_size == 0:
            raise RuntimeError("The downloaded media file is empty.")

        temp.replace(output)
        return output


# -----------------------------------------------------------------------------
# Download workflow
# -----------------------------------------------------------------------------
def download_one(client, page_url, number):
    print()
    line()
    print(BLUE + BOLD + f"  VIDEO #{number}" + RESET)
    print(DIM + "  Resolving RedGIFs video stream..." + RESET)

    media = client.resolve(page_url)
    output = client.download(media, number)

    size = format_bytes(output.stat().st_size)
    print(GREEN + BOLD + f"  ✓ Complete — {output.name} ({size})" + RESET)
    return output


def retry_skip_quit():
    print()
    print(YELLOW + "  [R] Retry   [S] Skip   [Q] Quit" + RESET)
    try:
        choice = input(VIOLET + "  › " + RESET).strip().lower()
    except (KeyboardInterrupt, EOFError):
        return "q"
    return choice if choice in {"r", "s", "q"} else "s"


def get_url(prompt="URL › "):
    try:
        return input(VIOLET + "  " + prompt + RESET).strip()
    except (KeyboardInterrupt, EOFError):
        return None


# -----------------------------------------------------------------------------
# Single mode
# -----------------------------------------------------------------------------
def single_mode(client):
    while True:
        banner()
        print(CYAN + BOLD + "  SINGLE VIDEO" + RESET)
        print(DIM + "  Download one RedGIFs video at a time." + RESET)
        print(DIM + "  Type 'b' to return to the main menu." + RESET)
        print()
        line()

        value = get_url()
        if value is None:
            return

        if value.lower() in {"b", "back"}:
            return
        if value.lower() in {"q", "quit", "exit"}:
            return

        url = normalize_url(value)
        if not url:
            print(RED + "\n  ✗ URL cannot be empty." + RESET)
            time.sleep(1)
            continue
        if not is_redgifs_url(url):
            print(RED + "\n  ✗ Please enter a RedGIFs URL." + RESET)
            time.sleep(1.2)
            continue

        while True:
            try:
                download_one(client, url, 1)
                pause()
                break
            except requests.RequestException as exc:
                print(RED + BOLD + "\n  ✗ Network error" + RESET)
                print(DIM + f"  {exc}" + RESET)
            except Exception as exc:
                print(RED + BOLD + "\n  ✗ Could not download this video" + RESET)
                print(DIM + f"  {exc}" + RESET)

            action = retry_skip_quit()
            if action == "r":
                continue
            if action == "q":
                return
            break


# -----------------------------------------------------------------------------
# Multiple mode
# -----------------------------------------------------------------------------
def collect_multiple_urls():
    urls = []
    print(CYAN + BOLD + "  MULTIPLE VIDEOS" + RESET)
    print(DIM + "  Paste one URL per line, or several URLs separated by spaces." + RESET)
    print(DIM + "  Press ENTER on an empty line when finished." + RESET)
    print(DIM + "  Type 'b' before the queue starts to return." + RESET)
    print()
    line()

    while True:
        value = get_url()
        if value is None:
            return None
        if not value:
            break
        if not urls and value.lower() in {"b", "back"}:
            return None

        for part in value.split():
            part = normalize_url(part)
            if not is_redgifs_url(part):
                print(RED + f"  ✗ Ignored: {part}" + RESET)
                continue
            urls.append(part)
            print(GREEN + f"  ✓ Added #{len(urls)}" + RESET)

    return urls


def multiple_mode(client):
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
                    download_one(client, url, index)
                    success += 1
                    break
                except requests.RequestException as exc:
                    print(RED + BOLD + f"\n  ✗ VIDEO #{index} FAILED" + RESET)
                    print(DIM + f"  {exc}" + RESET)
                except Exception as exc:
                    print(RED + BOLD + f"\n  ✗ VIDEO #{index} FAILED" + RESET)
                    print(DIM + f"  {exc}" + RESET)

                action = retry_skip_quit()
                if action == "r":
                    continue
                if action == "q":
                    print(YELLOW + "\n  Batch stopped by user." + RESET)
                    print(f"  Completed: {success} | Skipped: {skipped} | Remaining: {len(urls) - index}")
                    pause()
                    return
                skipped += 1
                break

        line()
        print(GREEN + BOLD + f"  ✓ Completed: {success}" + RESET)
        print(YELLOW + f"  • Skipped:   {skipped}" + RESET)
        print(DIM + f"  • Total:     {len(urls)}" + RESET)
        print()
        pause("Press ENTER to return to the menu...")
        return


# -----------------------------------------------------------------------------
# Main menu
# -----------------------------------------------------------------------------
def main_menu():
    ensure_download_dir()
    client = RedGifsClient()

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
            single_mode(client)
        elif choice == "2":
            multiple_mode(client)
        elif choice in {"q", "quit", "exit"}:
            break
        else:
            print(RED + "  ✗ Invalid option." + RESET)
            time.sleep(0.8)


def main():
    try:
        main_menu()
    except KeyboardInterrupt:
        pass
    finally:
        clear()
        print()
        print(GREEN + BOLD + "  RGS Downloader closed." + RESET)
        print(DIM + f"  Files are in: {DOWNLOAD_DIR}" + RESET)
        print()


if __name__ == "__main__":
    main()
