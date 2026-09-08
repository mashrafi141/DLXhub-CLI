from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engines'))
import XF_dl as E
from core.paths import ensure
from core import ui
from modules.common import media_choice

def _one(url,number=1):
    base=ensure('xf'); session=E.requests.Session(); session.headers.update(E.HEADERS)
    ui.header('XXXFollow','DLXhub  •  XXXFollow module','XF')
    # Probe via yt-dlp first for real quality choices; fall back to page resolver.
    try: mode,fmt,label,info=media_choice(url,'xf')
    except Exception:
        candidates,_=E.resolve_video_urls(session,url)
        if not candidates: raise
        ui.section('DOWNLOAD TYPE',ui.YELLOW); ui.menu_item('1','Video',ui.CYAN); ui.menu_item('2','Audio',ui.YELLOW)
        c=ui.prompt('Type'); mode='video' if c=='1' else 'audio' if c=='2' else None
        if not mode: raise RuntimeError('Invalid media type.')
        fmt='bestvideo+bestaudio/best' if mode=='video' else 'bestaudio/best'; label='Best available'
    out,info=E.download_one(session,url,number,fmt,base/'audio' if mode=='audio' else base/'video',mode)
    ui.status(f'Saved {out.name}','ok'); return out

def menu():
    while True:
        ui.header('XXXFollow','DLXhub  •  XXXFollow module','XF')
        ui.section('DOWNLOAD')
        ui.menu_item('1','Download media',ui.ORANGE,'single')
        ui.menu_item('2','Batch download',ui.CYAN,'multiple URLs')
        ui.menu_item('B','Back',ui.RED)
        c=ui.prompt()
        if c is None or c.lower()=='b': return
        try:
            if c=='1':
                u=ui.prompt_url();
                if not u: continue
                _one(u,1); ui.pause()
            elif c=='2':
                from modules.common import batch_mode
                ui.header('XXXFollow','Batch queue · one media type · best quality','XF')
                urls=[]
                while True:
                    u=ui.prompt_url()
                    if not u: break
                    urls += u.split()
                if not urls:
                    ui.status('No URLs added.','warn'); ui.pause(); continue
                mode,fmt=batch_mode(ui)
                base=ensure('xf'); success=failed=0
                for i,u in enumerate(urls,1):
                    try:
                        if 'xf'=='xf':
                            session=E.requests.Session(); session.headers.update(E.HEADERS)
                            out,_=E.download_one(session,u,i,fmt,base/('audio' if mode=='audio' else 'video'),mode)
                        else:
                            out,_=E.download_one(u,i,fmt,base/('audio' if mode=='audio' else 'video'),mode)
                        success+=1; ui.status(f'[{i}/{len(urls)}] Saved {out.name}','ok')
                    except Exception as e:
                        failed+=1; ui.status(f'[{i}/{len(urls)}] {e}','err')
                ui.status(f'Batch complete · {success}/{len(urls)} successful','ok' if failed==0 else 'warn')
                if failed: ui.status(f'Failed: {failed}','err')
                ui.pause()
            else: ui.status('Invalid option','err'); ui.pause()
        except Exception as e: ui.status(str(e),'err'); ui.pause()
