"""Package the finished film and an offline player without changing its media."""
import hashlib
from html import escape
import json
from pathlib import Path
import zipfile

P = Path(__file__).resolve().parent


def clock(seconds):
    return f'{int(seconds) // 60}:{int(seconds) % 60:02d}'


def main():
    shots = json.loads((P / 'shots.json').read_text())['shots']
    buttons = '\n'.join(
        f'<button type="button" data-time="{s["start"]}">{clock(s["start"])} · {escape(s["title"])}</button>'
        for s in shots)
    page = '''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>窗 · 轻颗粒雨天版 · 曼波朗读</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#091729;color:#e8eef7;font-family:system-ui,sans-serif;line-height:1.65}
main{max-width:1120px;margin:auto;padding:24px 18px}h1{margin:0;font-size:32px}p{margin:12px 0;color:#bccce0}
video{display:block;width:100%;height:auto;background:#071327;border:1px solid #41658a;margin:22px 0}
a{color:#a8d9ff}nav{display:flex;flex-wrap:wrap;gap:18px;margin-bottom:24px}.chapters{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:8px}
button{color:#d9e9f8;text-align:left;background:#153048;border:1px solid #426886;padding:10px 12px;border-radius:4px;cursor:pointer;font:inherit}
button:hover,button:focus-visible{background:#21435e;outline:2px solid #9bd4ee}figure{margin:24px 0}img{display:block;width:100%;height:auto}figcaption{margin-top:8px;color:#b8cbe0}
</style><main>
<h1>窗</h1><p>轻颗粒雨天版 · 掌机 RPG 像素动画 · 全文曼波朗读 · 2 分 21 秒</p>
<video id="film" controls playsinline preload="metadata" poster="poster.png" aria-label="窗完整动画">
<source src="window-light-rain-mambo.mp4" type="video/mp4">请使用下方链接下载视频观看。</video>
<nav aria-label="下载"><a href="window-light-rain-mambo.mp4" download>下载完整视频</a><a href="subtitles.srt" download>原文字幕</a><a href="mambo-narration.mp3" download>曼波音轨</a></nav>
<div class="chapters" aria-label="镜头跳转">CHAPTER_BUTTONS</div>
<figure><img src="encoded-contact-sheet.png" alt="实际成片的十六个镜头"><figcaption>教室、开窗、河流、骑士与夜色。</figcaption></figure>
</main><script>
const movie=document.getElementById('film');
document.querySelectorAll('[data-time]').forEach(button=>button.addEventListener('click',()=>{
const seek=()=>{movie.currentTime=Number(button.dataset.time);movie.play().catch(()=>{});};
if(movie.readyState>=1)seek();else{movie.addEventListener('loadedmetadata',seek,{once:true});movie.load();}
}));
</script></html>
'''
    (P / 'index.html').write_text(page.replace('CHAPTER_BUTTONS', buttons))
    plan = json.loads((P / 'asset-plan.json').read_text())
    plan['current_status'] = 'Full film exported and technically verified; delivered for user viewing'
    (P / 'asset-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    files = ['index.html', 'README.md', 'window-light-rain-mambo.mp4', 'mambo-narration.mp3',
             'subtitles.srt', 'subtitles.ass', 'original.txt', 'narration-timings.json',
             'shots.json', 'verification.json', 'render-plan.json', 'subtitle-layout.json',
             'asset-plan.json', 'lighting-edits.json', 'animation-assets.json', 'chapters.ffmeta',
             'preview-times.json', 'poster.png', 'encoded-contact-sheet.png', 'encoded-action-sheet.png']
    files += [p.relative_to(P).as_posix() for p in sorted((P / 'previews').glob('*.png'))]
    target = P / 'window-light-rain-delivery.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in files:
            archive.write(P / file, file)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(files)
        assert archive.read('window-light-rain-mambo.mp4') == (P / 'window-light-rain-mambo.mp4').read_bytes()
    manifest = {'main_video': 'window-light-rain-mambo.mp4', 'package': target.name,
                'package_files': len(files), 'offline_player': 'index.html', 'files': []}
    for file in [P / 'window-light-rain-mambo.mp4', target, P / 'subtitles.srt', P / 'mambo-narration.mp3']:
        manifest['files'].append({'file': file.name, 'bytes': file.stat().st_size,
                                  'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
    (P / 'deliverables.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'package': str(target), 'files': len(files), 'bytes': target.stat().st_size}))


if __name__ == '__main__':
    main()
