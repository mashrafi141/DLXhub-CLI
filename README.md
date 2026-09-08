# ✦ DLXhub CLI

<div align="center">

**Fast • Private • Reliable**

*A lightweight command-line media downloader built for flexible terminal use.*

<br>

**Windows • Termux • Other Python-Compatible Environments**

</div>

---

## 📌 Overview

**DLXhub CLI** is the command-line edition of the DLXhub project.

It provides a clean terminal workflow for downloading supported online media as **video or audio**, selecting available quality options, processing multiple links, handling authenticated downloads through local cookie files, and keeping downloaded content organized.

The project is designed to work from a terminal without requiring a graphical interface.

```text
Paste Link
    ↓
Resolve Media
    ↓
Choose Download Type
    ↓
Choose Quality
    ↓
Download / Process
    ↓
Save Locally
```

---

## ✨ Features

| Feature | Description |
|:--|:--|
| **🎬 Video Downloads** | Download supported media as video with available quality options. |
| **🎵 Audio Downloads** | Extract supported media as MP3 audio. |
| **📋 Playlist Downloads** | Download complete playlists where playlist metadata is supported. |
| **⚡ Batch Downloads** | Queue multiple links and process them in one session. |
| **🎚️ Quality Selection** | Choose from the quality options returned by the source. |
| **📊 Live Progress** | Terminal progress display with percentage, speed and ETA. |
| **🔁 Retry / Skip / Quit** | Recover from individual download failures without losing the whole queue. |
| **🔐 Cookie Support** | Use local cookie exports for content that requires authentication. |
| **🗂️ Smart File Naming** | Preserve meaningful media titles and avoid unnecessary filename collisions. |
| **📁 Automatic Organization** | Separate video, audio and playlist content into dedicated folders. |
| **⌨️ Terminal UI** | Colored sections, menus, status messages and compact progress indicators. |
| **🖥️ Cross-Environment** | Designed for Windows, Termux and other environments capable of running Python and FFmpeg. |

---

## 🧩 Download Modes

### 1. Single Download

Download one supported media URL at a time.

```text
URL
 ↓
Media Detection
 ↓
Video / Audio
 ↓
Quality Selection
 ↓
Download
```

### 2. Batch Download

Add multiple URLs and process them sequentially.

```text
URL 1 ─┐
URL 2 ─┼──→ Queue ──→ Download ──→ Save
URL 3 ─┤
URL 4 ─┘
```

Batch processing includes per-item error handling with:

```text
[R] Retry
[S] Skip
[Q] Quit
```

### 3. Playlist Download

Where playlist metadata is supported, the CLI can resolve the playlist, show the available item count, ask for the desired media type and quality, and process the items sequentially.

```text
Playlist URL
     ↓
Playlist Metadata
     ↓
Playlist Name + Items
     ↓
Video / Audio
     ↓
Quality Selection
     ↓
Download All Items
```

---

## 📂 Download Structure

Downloads are automatically organized under the project's `downloads/` directory.

```text
downloads/
├── .RG_downloads/
│   ├── video/
│   └── audio/
│
├── .XF_downloads/
│   ├── video/
│   └── audio/
│
├── FB_downloads/
│   ├── video/
│   └── audio/
│
├── X_downloads/
│   ├── video/
│   └── audio/
│
└── YT_downloads/
    ├── video/
    └── audio/
```

For playlist downloads:

```text
downloads/
└── YT_downloads/
    └── Playlist Name/
        ├── video/
        └── audio/
```

> Folder names are part of the current project structure and are created automatically when needed.

---

## 🗂️ File Naming

DLXhub CLI attempts to keep the **actual media title** when saving files.

Instead of relying on generic names, downloaded files are stored using meaningful titles whenever the source provides them.

If a filename already exists, the downloader creates a unique filename rather than unnecessarily overwriting the existing file.

---

## 🔐 Cookie / Authentication Support

Some supported sources may require an authenticated session.

For those cases, the project can use local cookie exports stored inside:

```text
cookies/
```

The expected cookie files are managed by the project itself.

### Important

**Never upload, commit, or share your personal cookie files.**

Cookie files may contain active authentication information and should be treated like sensitive credentials.

A typical local structure can look like:

```text
DLXhub_pro/
├── cookies/
│   ├── Fb_cookies.txt
│   └── X_cookies.txt
│
├── core/
├── engines/
├── modules/
├── downloads/
├── DLXhub.py
└── requirements.txt
```

---

# 🪟 Windows

## Requirements

Make sure the environment has:

- **Python 3**
- **FFmpeg**

> Python installation itself is intentionally not included here.

---

## ⚙️ Setup / Build

Open **Command Prompt** or **PowerShell** inside the project directory and install the project dependencies:

```powershell
py -m pip install -U -r requirements.txt
```

If your environment uses `python` instead of `py`:

```powershell
python -m pip install -U -r requirements.txt
```

---

## ▶️ Run

```powershell
py DLXhub.py
```

Or:

```powershell
python DLXhub.py
```

The main terminal interface will open.

---

## 📱 Termux

DLXhub CLI can also be used directly inside **Termux**.

### 1. Update Packages

```bash
pkg update && pkg upgrade
```

### 2. Install Required System Packages

```bash
pkg install python ffmpeg
```

### 3. Install Python Dependencies

From inside the project directory:

```bash
python -m pip install -U -r requirements.txt
```

### 4. Run

```bash
python DLXhub.py
```

That's it.

```text
Termux
  ↓
Python + FFmpeg
  ↓
DLXhub CLI
  ↓
Download
```

---

## 🛠️ Project Structure

```text
DLXhub_pro/
│
├── DLXhub.py
├── requirements.txt
├── VERSION.txt
│
├── core/
│   ├── __init__.py
│   ├── audio.py
│   ├── paths.py
│   ├── quality.py
│   └── ui.py
│
├── engines/
│   ├── RG_dl.py
│   ├── XF_dl.py
│   ├── YT_dl.py
│   └── fbX_dl.py
│
├── modules/
│   ├── __init__.py
│   ├── common.py
│   ├── fb.py
│   ├── rg.py
│   ├── x.py
│   ├── xf.py
│   └── yt.py
│
├── cookies/
└── downloads/
```

### Main Components

| Directory / File | Purpose |
|:--|:--|
| `DLXhub.py` | Main CLI entry point and menu hub |
| `core/` | Shared UI, path, quality and audio utilities |
| `engines/` | Media extraction and download engines |
| `modules/` | Source-specific command-line workflows |
| `cookies/` | Local authentication cookie files |
| `downloads/` | Automatically generated download storage |
| `requirements.txt` | Python dependency configuration |
| `VERSION.txt` | Project version information |

---

## 📦 Dependencies

The project currently defines these Python dependencies:

```text
yt-dlp>=2026.08.19
requests>=2.31.0
beautifulsoup4>=4.12.0
```

**FFmpeg** is also required for media processing and MP3 extraction.

---

## 🎨 Terminal Interface

The CLI uses a colored terminal interface with:

- Box-style headers
- Section separators
- Color-coded menus
- Status indicators
- Download progress bars
- Download speed
- ETA
- Success / warning / error states
- Retry / skip / quit controls

Example workflow:

```text
╔══════════════════════════════════════════════════════╗
║                     ◆  DLXhub                       ║
╚══════════════════════════════════════════════════════╝

  ┌─ DOWNLOAD ─────────────────────────────────────────┐

  [1] Download media
  [2] Batch download
  [3] Playlist download

  Select ›
```

---

## 🔄 Error Handling

DLXhub CLI does not stop the entire workflow just because one item fails.

For batch and playlist operations, individual failures can be handled using:

```text
[R] Retry
[S] Skip
[Q] Quit
```

This makes long download queues easier to manage.

---

## 🧹 Automatic Storage

The required download directories are created automatically.

You do not need to manually create the complete folder structure before the first download.

The project creates the required:

```text
downloads/
cookies/
```

directories when necessary.

---

## 🔗 Android Edition

Prefer a **graphical Android experience** instead of the terminal?

The Android edition of DLXhub provides the same project ecosystem through a dedicated mobile application with a modern graphical interface.

### 📱 Explore the Android Edition

**[→ DLXhub Android — GitHub](https://github.com/mashrafi141/DLXhub)**

```text
DLXhub
├── 🖥️ CLI Edition
│   └── Terminal-based workflow
│
└── 📱 Android Edition
    └── Mobile graphical workflow
```

> **Same project. Different experience.**

---

## 🚀 Quick Start

### Windows

```powershell
py -m pip install -U -r requirements.txt
py DLXhub.py
```

### Termux

```bash
pkg update && pkg upgrade
pkg install python ffmpeg
python -m pip install -U -r requirements.txt
python DLXhub.py
```

---

## ⚠️ Responsible Use

DLXhub CLI is intended for downloading content that you are **authorized to save or use**.

Users are responsible for complying with:

- **Copyright requirements**
- **Terms of service**
- **Privacy requirements**
- **Applicable laws and regulations**

Do not use the project to access, copy, redistribute, or store content without the necessary rights or permission.

---

## 🔒 Security Note

Keep the following private:

```text
cookies/
```

Especially:

```text
*_cookies.txt
```

Do not commit personal cookies to GitHub or share them with other users.

A safe `.gitignore` should exclude local authentication data and generated downloads.

---

## 📄 License

This project is intended for **personal use**.

Unless otherwise stated in the repository, the source code, assets and associated materials remain subject to their respective licenses and permissions.

---

## 💫 DLXhub Ecosystem

```text
                    ✦ DLXhub
                       │
             ┌─────────┴─────────┐
             │                   │
       🖥️ CLI Edition       📱 Android Edition
             │                   │
       Terminal Workflow     Mobile Workflow
             │                   │
             └─────────┬─────────┘
                       │
                 Same Project
```

### Related Repository

**[DLXhub Android →](https://github.com/mashrafi141/DLXhub)**

---

<div align="center">

### **✦ DLXhub CLI**

*Fast downloads. Clean terminal. Full control.*

<br>

**Developed by MASH!141**

</div>
