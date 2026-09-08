from pathlib import Path
import sys, shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engines'))
import RG_dl as E
from core.paths import ensure
from core import ui
from core.audio import extract

def _one(url,number=1):
    base=ensure('rg'); client=E.RedGifsClient()
    ui.header('RedGIFs','DLXhub  •  RedGIFs media hub','RG')
    ui.status('Resolving RedGIFs media...','info')
    candidates=client.resolve_candidates(url)
    ui.section('MEDIA',ui.CYAN)
    ui.status(candidates[0]['title'],'ok')
    ui.section('DOWNLOAD TYPE',ui.YELLOW); ui.menu_item('1','Video',ui.CYAN,'MP4 / source'); ui.menu_item('2','Audio',ui.YELLOW,'MP3')
    c=ui.prompt('Type')
    if c not in ('1','2'): raise RuntimeError('Invalid media type.')
    mode='video' if c=='1' else 'audio'
    ui.section('AVAILABLE QUALITY',ui.CYAN)
    for i,m in enumerate(candidates,1): ui.menu_item(str(i),m['quality'],ui.CYAN,f'{m.get("width") or "?"}x{m.get("height") or "?"}')
    q=ui.prompt('Quality')
    if not q or not q.isdigit() or not 1<=int(q)<=len(candidates): raise RuntimeError('Invalid quality.')
    media=candidates[int(q)-1]
    if mode=='video':
        out=client.download(media,number,base/'video'); ui.status(f'Saved {out.name}','ok'); return out
    tmp=base/'.tmp'; tmp.mkdir(exist_ok=True); src=client.download(media,number,tmp/'video'); out=extract(src,base/'audio',ui.safe_filename(media['title']));
    try: src.unlink()
    except OSError: pass
    ui.status(f'Saved {out.name}','ok'); return out

def menu():
    while True:
        ui.header('RedGIFs','DLXhub  •  RedGIFs module','RG')
        ui.section('DOWNLOAD')
        ui.menu_item('1','Download media',ui.ORANGE,'single')
        ui.menu_item('2','Batch download',ui.CYAN,'multiple URLs')
        ui.menu_item('B','Back',ui.RED)
        c=ui.prompt()
        if c is None or c.lower()=='b': return
        try:
            if c=='1':
                url=ui.prompt_url();
                if not url: continue
                _one(url,1); ui.pause()
            elif c=='2':
                from modules.common import batch_mode
                ui.header('RedGIFs','Batch queue · one media type · best quality','RG')
                urls=[]
                while True:
                    u=ui.prompt_url()
                    if not u: break
                    urls += u.split()
                if not urls:
                    ui.status('No URLs added.','warn'); ui.pause(); continue
                mode,_fmt=batch_mode(ui)
                base=ensure('rg'); client=E.RedGifsClient(); success=failed=0
                for i,u in enumerate(urls,1):
                    try:
                        candidates=client.resolve_candidates(u)
                        if not candidates: raise RuntimeError('No downloadable media found.')
                        media=candidates[0]
                        if mode=='video':
                            client.download(media,i,base/'video')
                        else:
                            tmp=base/'.tmp'; tmp.mkdir(exist_ok=True)
                            src=client.download(media,i,tmp/'video')
                            extract(src,base/'audio',ui.safe_filename(media['title']))
                            try: src.unlink()
                            except OSError: pass
                        success+=1
                        ui.status(f'[{i}/{len(urls)}] {media.get("title","Media")}','ok')
                    except Exception as e:
                        failed+=1; ui.status(f'[{i}/{len(urls)}] {e}','err')
                ui.status(f'Batch complete · {success}/{len(urls)} successful','ok' if failed==0 else 'warn')
                if failed: ui.status(f'Failed: {failed}','err')
                ui.pause()
            else: ui.status('Invalid option','err'); ui.pause()
        except Exception as e: ui.status(str(e),'err'); ui.pause()
