from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engines'))
import YT_dl as E
from core.paths import ensure
from core import ui
from core.quality import quality_options, selector


def valid(url): return E.is_youtube_url(E.normalize_url(url))

def choose_from_info(info,mode):
    vids,auds=quality_options(info); items=vids if mode=='video' else auds
    ui.section('AVAILABLE QUALITY',ui.CYAN if mode=='video' else ui.YELLOW)
    for i,(_,label) in enumerate(items,1): ui.menu_item(str(i),label,ui.CYAN if mode=='video' else ui.YELLOW)
    c=ui.prompt('Quality')
    if not c or not c.isdigit() or not 1<=int(c)<=len(items): raise RuntimeError('Invalid quality selection.')
    return items[int(c)-1][0],items[int(c)-1][1]

def select_media(url, info=None):
    info=info or E.extract_info(url,flat=False)
    if not info: raise RuntimeError('YouTube returned no metadata.')
    ui.section('MEDIA',ui.CYAN); ui.status(info.get('title') or 'YouTube media','ok')
    ui.section('DOWNLOAD TYPE',ui.YELLOW); ui.menu_item('1','Video',ui.CYAN,'MP4'); ui.menu_item('2','Audio',ui.YELLOW,'MP3')
    c=ui.prompt('Type')
    if c not in ('1','2'): raise RuntimeError('Invalid media type.')
    mode='video' if c=='1' else 'audio'; choice,label=choose_from_info(info,mode)
    return mode,selector(mode,choice),label,info

def _one(url,number=1,info=None,output_root=None):
    base=ensure('yt'); mode,fmt,label,info=select_media(url,info)
    outroot=Path(output_root) if output_root else base/mode
    E.download_one(url,mode,number,format_selector=fmt,output_root=outroot,info=info)
    ui.status(f'Completed · {label}','ok')

def _playlist(url):
    base=ensure('yt'); ui.status('Reading playlist metadata...','info'); name,entries=E.get_playlist_metadata(url)
    if not entries: raise RuntimeError('Playlist contains no downloadable items.')
    # Probe first real item for quality choices.
    first=entries[0].get('webpage_url') or entries[0].get('url')
    info=E.extract_info(first,flat=False)
    ui.header('YouTube Playlist',f'{name}  ·  {len(entries)} item(s)','YT')
    ui.status(f'Playlist: {name}','ok'); ui.status(f'Items: {len(entries)}','info')
    mode,fmt,label,_=select_media(first,info)
    root=base/name/mode; root.mkdir(parents=True,exist_ok=True)
    success=failed=0
    for idx,entry in enumerate(entries,1):
        u=entry.get('webpage_url') or entry.get('url')
        title=entry.get('title') or f'Video {idx}'
        print(); ui.status(f'[{idx}/{len(entries)}] {title}','info')
        try:
            E.download_one(u,mode,idx,format_selector=fmt,output_root=root)
            success+=1
        except Exception as e:
            failed+=1; ui.status(str(e),'err')
            action=ui.prompt('Retry [r], Skip [s], Quit [q]')
            if action=='r':
                try: E.download_one(u,mode,idx,format_selector=fmt,output_root=root); success+=1; failed-=1
                except Exception as e2: ui.status(f'Retry failed: {e2}','err')
            elif action=='q': break
    ui.header('Playlist Summary','DLXhub  •  YouTube','YT'); ui.status(f'Completed: {success}/{len(entries)}','ok'); ui.status(f'Failed: {failed}','err' if failed else 'info'); ui.pause()

def menu():
    while True:
        ui.header('YouTube','DLXhub  •  YouTube module','YT')
        ui.section('DOWNLOAD')
        ui.menu_item('1','Download media',ui.ORANGE,'single URL')
        ui.menu_item('2','Batch download',ui.CYAN,'multiple URLs')
        ui.menu_item('3','Playlist download',ui.VIOLET,'playlist URL')
        ui.menu_item('B','Back',ui.RED)
        c=ui.prompt()
        if c is None or c.lower()=='b': return
        try:
            if c=='1':
                u=ui.prompt_url();
                if not u: continue
                if not valid(u): raise RuntimeError('Invalid YouTube URL.')
                _one(u,1); ui.pause()
            elif c=='2':
                from modules.common import batch_mode
                ui.header('YouTube','Batch queue · one media type · best quality','YT')
                urls=[]
                while True:
                    u=ui.prompt_url()
                    if not u: break
                    urls += [x for x in u.split() if valid(x)]
                if not urls:
                    ui.status('No valid URLs added.','warn'); ui.pause(); continue
                mode,fmt=batch_mode(ui)
                success=failed=0
                base=ensure('yt')
                for i,u in enumerate(urls,1):
                    try:
                        E.download_one(u,mode,i,format_selector=fmt,output_root=base/mode)
                        success+=1
                    except Exception as e:
                        failed+=1; ui.status(f'[{i}/{len(urls)}] {e}','err')
                ui.status(f'Batch complete · {success}/{len(urls)} successful','ok' if failed==0 else 'warn')
                if failed: ui.status(f'Failed: {failed}','err')
                ui.pause()
            elif c=='3':
                u=ui.prompt_url();
                if not u: continue
                if not valid(u): raise RuntimeError('Invalid YouTube URL.')
                _playlist(u)
            else: ui.status('Invalid option','err'); ui.pause()
        except Exception as e: ui.status(str(e),'err'); ui.pause()
