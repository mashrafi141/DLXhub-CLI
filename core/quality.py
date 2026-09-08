from pathlib import Path
from urllib.parse import urlparse
import re
try:
    import yt_dlp
except ImportError:
    yt_dlp=None

def normalize_x_url(url):
    p=urlparse(url)
    host=p.netloc.lower().split(':')[0]
    if host=='x.com' or host.endswith('.x.com'):
        return 'https://twitter.com'+p.path+(('?'+p.query) if p.query else '')
    return url

def is_x_post(url):
    p=urlparse(url); host=p.netloc.lower().split(':')[0]
    if 'twitter.com' not in host and 'x.com' not in host: return True
    return bool(re.search(r'/(?:i/)?status/\d+',p.path))

def probe(url,cookiefile=None,platform=None):
    if yt_dlp is None: raise RuntimeError('yt-dlp is required for media metadata.')
    target=normalize_x_url(url) if platform=='x' else url
    opts={'quiet':True,'no_warnings':True,'skip_download':True,'noplaylist':True,'extract_flat':False}
    if cookiefile and Path(cookiefile).exists(): opts['cookiefile']=str(cookiefile)
    with yt_dlp.YoutubeDL(opts) as ydl: return ydl.extract_info(target,download=False)

def quality_options(info):
    fmts=info.get('formats') or []
    heights=sorted({int(f.get('height')) for f in fmts if f.get('vcodec') not in (None,'none') and f.get('height')},reverse=True)
    video=[('best','Best available')] + [(str(h),f'{h}p') for h in heights if h not in (0,)]
    abrs=sorted({int(round(float(f.get('abr')))) for f in fmts if f.get('acodec') not in (None,'none') and f.get('abr')},reverse=True)
    audio=[('best','Best available')] + [(str(a),f'{a} kbps') for a in abrs]
    return video,audio

def selector(mode, choice):
    if mode=='audio':
        return 'bestaudio/best' if choice=='best' else f'bestaudio[abr<={choice}]/bestaudio/best'
    return 'bestvideo+bestaudio/best' if choice=='best' else f'bestvideo[height<={choice}]+bestaudio/best[height<={choice}]'

def choose_quality(ui,info,mode):
    video,audio=quality_options(info); items=video if mode=='video' else audio
    ui.section('AVAILABLE QUALITY',ui.CYAN if mode=='video' else ui.YELLOW)
    for i,(_,label) in enumerate(items,1): ui.menu_item(str(i),label,ui.CYAN if mode=='video' else ui.YELLOW)
    c=ui.prompt('Quality')
    if not c or not c.isdigit() or not (1<=int(c)<=len(items)): raise RuntimeError('Invalid quality selection.')
    return items[int(c)-1][0],items[int(c)-1][1]
