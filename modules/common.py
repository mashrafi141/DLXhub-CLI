from pathlib import Path
from core import ui
from core.quality import probe, choose_quality, selector, is_x_post, normalize_x_url

def media_choice(url, platform, cookie=None, custom=None):
    if platform=='x' and not is_x_post(url):
        raise RuntimeError('This is an X profile/link, not a video post. Use an X status URL like x.com/user/status/123...')
    info=None
    if custom is not None:
        title=custom.get('title') or 'Media'; ui.status(title,'ok')
        return 'video','best','Best available',info
    target=normalize_x_url(url) if platform=='x' else url
    ui.section('MEDIA',ui.CYAN)
    ui.status('Reading available media formats...','info')
    info=probe(target,cookie,platform)
    title=info.get('title') or info.get('id') or 'Media'
    ui.status(title,'ok')
    ui.section('DOWNLOAD TYPE',ui.YELLOW)
    ui.menu_item('1','Video',ui.CYAN,'MP4')
    ui.menu_item('2','Audio',ui.YELLOW,'MP3')
    c=ui.prompt('Type')
    if c not in ('1','2'): raise RuntimeError('Invalid media type.')
    mode='video' if c=='1' else 'audio'
    choice,label=choose_quality(ui,info,mode)
    return mode,selector(mode,choice),label,info


def batch_mode(ui):
    """Choose type once for a batch; quality is always best available."""
    ui.section('BATCH DOWNLOAD TYPE', ui.YELLOW)
    ui.menu_item('1','Video',ui.CYAN,'MP4 · Best available')
    ui.menu_item('2','Audio',ui.YELLOW,'MP3 · Best available')
    c=ui.prompt('Type')
    if c not in ('1','2'):
        raise RuntimeError('Invalid media type.')
    mode='video' if c=='1' else 'audio'
    return mode,selector(mode,'best')
