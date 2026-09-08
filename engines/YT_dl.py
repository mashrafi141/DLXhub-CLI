#!/usr/bin/env python3
"""
YT VIDEO DOWNLOADER - Termux / Android

Features
--------
1. Single Video mode
2. Multiple Videos mode
3. Playlist URL mode - downloads every video automatically
4. Video download as MP4 (best available video + audio)
5. Audio download as MP3
6. Live one-line progress bar similar to the original RGS downloader
7. Automatic playlist-name folders
8. Creates ./ytdownloads beside this script (normal folder, no leading dot)
9. Retry / Skip / Quit for failed items
10. Uses yt-dlp

Install on Termux:
    pkg update
    pkg install python ffmpeg
    python -m pip install -U yt-dlp

Run:
    python YT_downloader.py
"""

import os
import re
import sys
import time
import shutil
from pathlib import Path
from urllib.parse import urlparse

try:
    import yt_dlp
except ImportError:
    print("\033[91mMissing dependency: yt-dlp\033[0m")
    print("Run: python -m pip install -U yt-dlp")
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
DOWNLOAD_DIR = SCRIPT_DIR / "ytdownloads"
VIDEO_DIR = DOWNLOAD_DIR / "video"
AUDIO_DIR = DOWNLOAD_DIR / "audio"


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
    title = " YOUTUBE DOWNLOADER "
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
    print(DIM + "  YouTube → local video / audio downloader" + RESET)
    print()


def pause(message="Press ENTER to continue..."):
    try:
        input(DIM + "  " + message + RESET)
    except (KeyboardInterrupt, EOFError):
        pass


def ensure_download_dirs():
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)


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


def is_youtube_url(url):
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
        return (
            host == "youtube.com"
            or host.endswith(".youtube.com")
            or host == "youtu.be"
            or host.endswith(".youtu.be")
        )
    except Exception:
        return False


def safe_filename(name):
    name = str(name or "").strip()
    # Remove characters invalid on Windows/Linux/Android file systems.
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    # Avoid reserved/special path names.
    if name in {".", "..", ""}:
        name = "youtube_download"
    return name[:180]


def format_bytes(value):
    value = float(value or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return "0 B"


def format_time(seconds):
    if seconds is None:
        return "--"
    try:
        seconds = int(float(seconds))
    except (TypeError, ValueError):
        return "--"
    if seconds < 0:
        return "--"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def progress_line(data):
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

def progress_hook(data):
    try:
        progress_line(data)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# yt-dlp configuration
# -----------------------------------------------------------------------------
def base_ydl_options():
    return {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ignoreerrors": False,
        "retries": 3,
        "fragment_retries": 3,
        "file_access_retries": 3,
        "concurrent_fragment_downloads": 1,
        "progress_hooks": [progress_hook],
        "windowsfilenames": True,
        "restrictfilenames": False,
        "continuedl": True,
        "overwrites": False,
        "noplaylist": True,
    }


def check_ffmpeg():
    return shutil.which("ffmpeg") is not None


def extract_info(url, flat=False):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": False,
        "extract_flat": flat,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def looks_like_playlist(url):
    """Use URL parameters first, then yt-dlp metadata when needed."""
    try:
        parsed = urlparse(url)
        query = parsed.query.lower()
        if "list=" in query:
            return True
        if "playlist" in parsed.path.lower():
            return True
    except Exception:
        pass
    return False


# -----------------------------------------------------------------------------
# Download functions
# -----------------------------------------------------------------------------
def make_output_template(root, playlist_name=None):
    root = Path(root)

    if playlist_name:
        playlist_dir = root / safe_filename(playlist_name)
        playlist_dir.mkdir(parents=True, exist_ok=True)
        return str(playlist_dir / "%(playlist_index&{} - |)s%(title)s.%(ext)s")

    return str(root / "%(title)s.%(ext)s")


def make_simple_template(root, playlist_name=None):
    root = Path(root)
    if playlist_name:
        playlist_dir = root / safe_filename(playlist_name)
        playlist_dir.mkdir(parents=True, exist_ok=True)
        return str(playlist_dir / "%(playlist_index)03d - %(title)s.%(ext)s")
    return str(root / "%(title)s.%(ext)s")


def video_options(output_root, playlist_name=None, format_selector=None):
    opts = base_ydl_options()
    opts.update({
        # Best video + best audio, merged to MP4 when possible.
        "format": format_selector or (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo+bestaudio/best"
        ),
        "merge_output_format": "mp4",
        "outtmpl": make_simple_template(output_root, playlist_name),
    })
    return opts


def audio_options(output_root, playlist_name=None, format_selector=None):
    opts = base_ydl_options()
    opts.update({
        "format": format_selector or "bestaudio/best",
        "outtmpl": make_simple_template(output_root, playlist_name),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    })
    return opts


def show_info(info, number=None):
    title = info.get("title") or "Unknown title"
    duration = info.get("duration")
    channel = info.get("channel") or info.get("uploader") or ""
    width = info.get("width")
    height = info.get("height")

    prefix = f"VIDEO #{number}" if number else "VIDEO"
    print(BLUE + BOLD + f"  {prefix}" + RESET)
    print(WHITE + f"  Title: {title}" + RESET)
    if channel:
        print(DIM + f"  Channel: {channel}" + RESET)
    details = []
    if width and height:
        details.append(f"{width}x{height}")
    if duration:
        details.append(format_time(duration))
    if details:
        print(DIM + "  " + "  |  ".join(details) + RESET)


def download_one(url, mode, number=None, playlist_name=None, format_selector=None, output_root=None, info=None):
    url=normalize_url(url)
    if not is_youtube_url(url): raise RuntimeError("Please enter a valid YouTube URL.")
    if info is None: info=extract_info(url,flat=False)
    if not info: raise RuntimeError("YouTube did not return video information.")
    if info.get("_type")=="playlist": raise RuntimeError("This is a playlist URL. Use Playlist mode.")
    show_info(info,number)
    root=Path(output_root) if output_root else (AUDIO_DIR if mode=='audio' else VIDEO_DIR)
    root.mkdir(parents=True,exist_ok=True)
    if mode=='audio':
        if not check_ffmpeg(): raise RuntimeError("ffmpeg is required for MP3 extraction. Install: pkg install ffmpeg")
        opts=audio_options(root, None, format_selector); print(ORANGE+"  Downloading audio (MP3)..."+RESET)
    else:
        opts=video_options(root, None, format_selector); print(ORANGE+"  Downloading video (MP4)..."+RESET)
    started=time.time()
    with yt_dlp.YoutubeDL(opts) as ydl: ydl.download([url])
    elapsed=time.time()-started
    print(); print(GREEN+BOLD+f"  ✓ Complete — {format_time(elapsed)}"+RESET)
    return True

def get_playlist_metadata(url):
    print(DIM + "  Reading playlist information..." + RESET)
    info = extract_info(url, flat=True)

    if not info or info.get("_type") != "playlist":
        raise RuntimeError("This URL does not appear to be a YouTube playlist.")

    title = info.get("title") or "YouTube Playlist"
    entries = [
        entry for entry in (info.get("entries") or [])
        if entry and entry.get("url")
    ]

    if not entries:
        raise RuntimeError("No downloadable videos were found in this playlist.")

    return safe_filename(title), entries


def download_playlist(url, mode, format_selector=None, playlist_name=None):
    if not is_youtube_url(url): raise RuntimeError("Please enter a valid YouTube playlist URL.")
    if mode=='audio' and not check_ffmpeg(): raise RuntimeError("ffmpeg is required for MP3 extraction. Install: pkg install ffmpeg")
    playlist_name, entries=get_playlist_metadata(url) if playlist_name is None else (playlist_name, get_playlist_metadata(url)[1])
    root=DOWNLOAD_DIR/playlist_name
    out_root=root/'audio' if mode=='audio' else root/'video'
    out_root.mkdir(parents=True,exist_ok=True)
    print(); line(); print(CYAN+BOLD+f"  PLAYLIST  ·  {playlist_name}"+RESET); print(GREEN+f"  {len(entries)} item(s) queued"+RESET); print()
    success=failed=skipped=0
    for index,entry in enumerate(entries,1):
        entry_url=entry.get('webpage_url') or entry.get('url')
        if not entry_url: failed+=1; continue
        print(VIOLET+BOLD+f"  [{index:02d}/{len(entries):02d}] "+RESET+(entry.get('title') or 'Unknown title'))
        try:
            info=extract_info(entry_url,flat=False)
            download_one(entry_url,mode,index,format_selector=format_selector,output_root=out_root,info=info)
            success+=1
        except Exception as exc:
            print(RED+BOLD+f"\n  ✗ [{index}/{len(entries)}] FAILED"+RESET); print(DIM+f"  {exc}"+RESET)
            action=retry_skip_quit()
            if action=='r':
                try:
                    download_one(entry_url,mode,index,format_selector=format_selector,output_root=out_root)
                    success+=1; continue
                except Exception as exc2: print(RED+f"  ✗ Retry failed: {exc2}"+RESET)
            if action=='q':
                print(YELLOW+f"  Stopped · completed {success} · remaining {len(entries)-index}"+RESET); pause(); return
            skipped+=1
    print(); line(); print(GREEN+BOLD+f"  ✓ Completed {success}/{len(entries)}"+RESET); print(YELLOW+f"  • Skipped {skipped}"+RESET); print(RED+f"  • Failed {failed}"+RESET); pause()


# -----------------------------------------------------------------------------
# Retry menu
# -----------------------------------------------------------------------------
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
# Single video mode
# -----------------------------------------------------------------------------
def single_mode():
    while True:
        banner()
        print(CYAN + BOLD + "  SINGLE VIDEO" + RESET)
        print(DIM + "  Download one YouTube video." + RESET)
        print(DIM + "  Type 'b' to return to the main menu." + RESET)
        print()
        line()

        value = get_url()
        if value is None or value.lower() in {"b", "back"}:
            return

        url = normalize_url(value)
        if not url:
            print(RED + "\n  ✗ URL cannot be empty." + RESET)
            time.sleep(0.8)
            continue

        print()
        print(WHITE + "  Select download type:" + RESET)
        print(ORANGE + "  [1]" + RESET + " Video (MP4)")
        print(CYAN + "  [2]" + RESET + " Audio (MP3)")
        print()

        try:
            kind = input(VIOLET + "  Select › " + RESET).strip()
        except (KeyboardInterrupt, EOFError):
            return

        mode = "video" if kind == "1" else "audio" if kind == "2" else None
        if not mode:
            print(RED + "  ✗ Invalid option." + RESET)
            time.sleep(0.8)
            continue

        while True:
            try:
                download_one(url, mode, 1)
                pause()
                break
            except KeyboardInterrupt:
                raise
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
# Multiple video mode
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
            if not is_youtube_url(part):
                print(RED + f"  ✗ Ignored: {part}" + RESET)
                continue
            urls.append(part)
            print(GREEN + f"  ✓ Added #{len(urls)}" + RESET)

    return urls


def multiple_mode():
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
        print(WHITE + "  Select download type:" + RESET)
        print(ORANGE + "  [1]" + RESET + " Video (MP4)")
        print(CYAN + "  [2]" + RESET + " Audio (MP3)")
        print()

        try:
            kind = input(VIOLET + "  Select › " + RESET).strip()
        except (KeyboardInterrupt, EOFError):
            return

        mode = "video" if kind == "1" else "audio" if kind == "2" else None
        if not mode:
            print(RED + "  ✗ Invalid option." + RESET)
            time.sleep(0.8)
            continue

        print()
        print(GREEN + BOLD + f"  {len(urls)} video(s) queued." + RESET)

        success = 0
        skipped = 0
        failed = 0

        for index, url in enumerate(urls, start=1):
            while True:
                try:
                    download_one(url, mode, index)
                    success += 1
                    break
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    failed += 1
                    print(
                        RED + BOLD
                        + f"\n  ✗ VIDEO #{index} FAILED"
                        + RESET
                    )
                    print(DIM + f"  {exc}" + RESET)

                    action = retry_skip_quit()
                    if action == "r":
                        failed -= 1
                        continue
                    if action == "q":
                        print(YELLOW + "\n  Batch stopped by user." + RESET)
                        print(
                            f"  Completed: {success} | "
                            f"Skipped: {skipped} | "
                            f"Failed: {failed} | "
                            f"Remaining: {len(urls) - index}"
                        )
                        pause()
                        return
                    skipped += 1
                    break

        line()
        print(GREEN + BOLD + f"  ✓ Completed: {success}" + RESET)
        print(YELLOW + f"  • Skipped:   {skipped}" + RESET)
        print(RED + f"  • Failed:    {failed}" + RESET)
        print(DIM + f"  • Total:     {len(urls)}" + RESET)
        print()
        pause("Press ENTER to return to the menu...")
        return


# -----------------------------------------------------------------------------
# Playlist mode
# -----------------------------------------------------------------------------
def playlist_mode():
    while True:
        banner()
        print(CYAN + BOLD + "  PLAYLIST DOWNLOAD" + RESET)
        print(DIM + "  Paste a YouTube playlist link to download every video." + RESET)
        print(DIM + "  A folder with the playlist name will be created automatically." + RESET)
        print(DIM + "  Type 'b' to return to the main menu." + RESET)
        print()
        line()

        value = get_url()
        if value is None or value.lower() in {"b", "back"}:
            return

        url = normalize_url(value)
        if not url:
            print(RED + "\n  ✗ URL cannot be empty." + RESET)
            time.sleep(0.8)
            continue

        print()
        print(WHITE + "  Select download type:" + RESET)
        print(ORANGE + "  [1]" + RESET + " Video (MP4)")
        print(CYAN + "  [2]" + RESET + " Audio (MP3)")
        print()

        try:
            kind = input(VIOLET + "  Select › " + RESET).strip()
        except (KeyboardInterrupt, EOFError):
            return

        mode = "video" if kind == "1" else "audio" if kind == "2" else None
        if not mode:
            print(RED + "  ✗ Invalid option." + RESET)
            time.sleep(0.8)
            continue

        try:
            download_playlist(url, mode)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(RED + BOLD + "\n  ✗ Playlist error" + RESET)
            print(DIM + f"  {exc}" + RESET)
            pause()
        return


# -----------------------------------------------------------------------------
# Main menu
# -----------------------------------------------------------------------------
def main_menu():
    ensure_download_dirs()

    while True:
        banner()
        print(WHITE + "  Output folder:" + RESET)
        print("  " + ORANGE + str(DOWNLOAD_DIR) + RESET)
        print()
        print(DIM + "  Video files → ytdownloads/video/" + RESET)
        print(DIM + "  Audio files → ytdownloads/audio/" + RESET)
        print()
        line()
        print()
        print(ORANGE + BOLD + "  [1]" + RESET + "  Single Video")
        print(CYAN + BOLD + "  [2]" + RESET + "  Multiple Videos")
        print(VIOLET + BOLD + "  [3]" + RESET + "  Playlist")
        print(RED + BOLD + "  [Q]" + RESET + "  Quit")
        print()

        try:
            choice = input(VIOLET + BOLD + "  Select › " + RESET).strip().lower()
        except (KeyboardInterrupt, EOFError):
            break

        if choice == "1":
            single_mode()
        elif choice == "2":
            multiple_mode()
        elif choice == "3":
            playlist_mode()
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
        print(GREEN + BOLD + "  YouTube Downloader closed." + RESET)
        print(DIM + f"  Files are in: {DOWNLOAD_DIR}" + RESET)
        print()


if __name__ == "__main__":
    main()
