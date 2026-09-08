import shutil, subprocess
from pathlib import Path

def extract(src,out_dir,title):
    if not shutil.which('ffmpeg'): raise RuntimeError('ffmpeg is required for MP3 audio. Install: pkg install ffmpeg')
    out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    out=out_dir/f'{title}.mp3'; n=1
    while out.exists(): out=out_dir/f'{title}_{n}.mp3'; n+=1
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(src),'-vn','-codec:a','libmp3lame','-q:a','2',str(out)],check=True)
    return out
