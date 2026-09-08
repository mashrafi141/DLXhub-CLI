from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOWNLOADS=ROOT/'downloads'
COOKIES=ROOT/'cookies'
PLATFORM={
 'rg':DOWNLOADS/'.RG_downloads',
 'xf':DOWNLOADS/'.XF_downloads',
 'fb':DOWNLOADS/'FB_downloads',
 'x':DOWNLOADS/'X_downloads',
 'yt':DOWNLOADS/'YT_downloads',
}

def cookie_file(name):
    COOKIES.mkdir(parents=True, exist_ok=True)
    return COOKIES/name

def ensure(key):
    base=PLATFORM[key]
    for sub in ('video','audio'):
        (base/sub).mkdir(parents=True,exist_ok=True)
    return base

def playlist_root(key,name):
    base=ensure(key)/str(name)
    for sub in ('video','audio'): (base/sub).mkdir(parents=True,exist_ok=True)
    return base
