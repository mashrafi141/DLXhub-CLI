# DLXhub

Premium Termux multi-platform media downloader.

## Platforms
- RedGIFs
- XXXFollow
- Facebook
- Twitter / X
- YouTube

## Output
```
downloads/
├── .RG_downloads/{video,audio}/
├── .XF_downloads/{video,audio}/
├── FB_downloads/{video,audio}/
├── X_downloads/{video,audio}/
└── YT_downloads/{video,audio}/
```
YouTube playlists use:
`downloads/YT_downloads/<Playlist Name>/{video,audio}/`

## Install
```bash
pkg update
pkg install python ffmpeg
python -m pip install -U -r requirements.txt
python DLXhub.py
```

For Facebook/X content requiring authentication, copy your own cookie exports as `Fb_cookies.txt` and `X_cookies.txt` into the project root. Do not share these files.

## X links
Use a post URL such as `https://x.com/user/status/123...`. A profile URL such as `https://x.com/user` is not a specific video post and is rejected intentionally.
