# 《窗》固定画面朗读演示

一张手绘教室画面始终固定，原速曼波朗读，原文大字幕逐句切换。此样片只包含文章前四个完整句子，26.50 秒、1920×1080、24 fps，不是全文成片。声音复用现有曼波音轨，不是用户自己的声音克隆。

画面来自 `../handdrawn-style-review/01-rainy-classroom.png`，`cover.png` 是逐字节相同的副本。保留整幅构图，以 Lanczos 适配横屏；字幕区叠加恒定半透明底色，不加缩放、移动、雨动画或随机颗粒。原有像素正式动画和手绘检查图继续保留。

用户参考：https://www.bilibili.com/video/BV13THd6aEH1/ 。当前环境访问返回代理 403，未观看该视频；演示根据用户描述的“一张图不变、配音、显示字幕”制作，不声称复现其具体排版。

从仓库根目录执行：

```bash
python rpg-film/still-reading-demo/render.py --dry-run --json
python rpg-film/still-reading-demo/render.py
```

需要 FFmpeg（libx264、libass）、Noto Sans CJK SC 字体和 Python 标准库。脚本从仓库原曼波 ZIP 精确裁取前 26.50 秒 PCM，保留 1.0 倍语速；输出文件已存在时拒绝覆盖。字幕来自现有原文字幕及实测时间轴，长句仅排版换行，不改文字。

`subtitles.srt` 使用原声实际起止时间；烧录 `subtitles.ass` 稍延长到下一句前的停顿，遵循之前的大字幕版式。`original.txt`、`timings.json`、`sources.json` 记录演示范围及来源，`render-plan.json` 记录实际编码命令。`verification.json` 是编码后检查记录；`review/` 是实际视频导出的代表帧。

若之后改用用户自己的声音，需要干净的本人录音及逐字对应文本，配置通用声音克隆权重后先合成短句试听，再依照新音频重排时间轴。当前仅检查了 GPT-SoVITS CPU 环境；尚未得到用户参考录音或验证其声线。
