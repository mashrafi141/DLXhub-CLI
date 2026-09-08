from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engines'))
import fbX_dl as E
from core.paths import ensure, cookie_file
from core import ui
from modules.common import media_choice

COOKIE=cookie_file('X_cookies.txt')

def _one(url,number=1):
    base=ensure('x'); mode,fmt,label,info=media_choice(url,'x',COOKIE)
    # fbX engine normalizes x.com -> twitter.com internally, improving compatibility with older yt-dlp.
    out,info=E.download_one(url,number,fmt,base/'audio' if mode=='audio' else base/'video',mode)
    ui.status(f'Saved {out.name}','ok'); return out

def menu():
    while True:
        ui.header('Twitter / X','DLXhub  •  Twitter / X module','X')
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
                ui.header('Twitter / X','Batch queue · one media type · best quality','X')
                urls=[]
                while True:
                    u=ui.prompt_url()
                    if not u: break
                    urls += u.split()
                if not urls:
                    ui.status('No URLs added.','warn'); ui.pause(); continue
                mode,fmt=batch_mode(ui)
                base=ensure('x'); success=failed=0
                for i,u in enumerate(urls,1):
                    try:
                        if 'x'=='xf':
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
