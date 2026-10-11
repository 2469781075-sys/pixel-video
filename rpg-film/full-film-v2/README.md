# 窗 · 丰富分镜第二版

继续采用已确认的强化像素掌机 RPG A 画风，原创棕发主角、绿背心/白衬衫/红领带和现有教室。保留第一版全部图片、声音和视频，新作品另存于本目录。

[下载完整新版 MP4](https://github.com/2469781075-sys/pixel-video/raw/refs/heads/main/rpg-film/full-film-v2/window-full-mambo-v2.mp4) · [逐句原文字幕](subtitles.srt) · [35 镜头时间轴](shots.json) · [实际验证结果](verification.json)

![实际成片代表帧](storyboard.png)

## 本版变化

- 字幕字号由 42 调整到 66，增大约 57%，加粗并加强描边。按标点均衡换行，最长句最多三行；原文整句与实测配音时间保持一致。排版记录见 [subtitle-layout.json](subtitle-layout.json)。

- 镜头由第一版的 15 个增加至 35 个。长句内用多个相关构图承接句意，字幕仍整句保留。
- 新增后排留白、完整三排双人桌，以及同桌在场、轻微转头和离席后的空座位。身体、桌椅与脚底位置固定，头部动作使用内置 image_gen 生成的独立关键姿态。
- 第一人称开窗细分为伸手、窗扣、左扇移动、右手接触右扇、两扇沿水平轨道推开、先后放下手。窗框固定，窗扇尺寸恒定，动作前后错开，避免双手挤在合缝处。
- 开窗后加入同一教室的清凉雨光、窗台与院景变化，再接风、河流、社交和骑士的心理联想，最后回到教室夜色。
- 增加局部书页、眨眼、转头、交谈气泡、雨、水光、风和喷泉细节。每个镜头相机固定，以剪辑和局部图层表达变化。
- 曼波继续使用原有全文音轨，原速、原文，21 句字幕采用原来的实测合成时间；背景声与新窗扣/滑轨动作重新同步。

## 交付与来源

成片为 141 秒、1920×1080、24 fps；低分辨率动画画布 480×270，最近邻放大四倍，H.264/BT.709 与 AAC 48 kHz 双声道。139 秒朗读完整播放，结尾保留两秒。

原文和曼波来源继续使用 `../narration/original.txt`、`../narration/mambo/timings.json` 与 `../narration/mambo/mambo-narration.zip`。没有重新识别、改写、缩短或加速配音；文章措辞和标点保留在 SRT 与画面字幕。

四张新的位图素材在 `assets/`；使用内置 image_gen，完整提示及参考来源在 [asset-prompts.json](asset-prompts.json)。其余已确认的原始素材复用 `../full-film/assets/`。保留旧版图像，不以本次生成覆盖旧文件。

原文时间轴、声画完整解码、每句音轨与原曼波声音的对应、窗扇运动和窗框稳定性、实际编码代表帧与预期场景都由 [verify.py](verify.py) 检查。人体、遮挡和美术质量另通过看图检查，数值检查不能证明所有审美判断。实际报告以 verification.json 为准。

本次实际检查通过：所有 21 句编码音频与原曼波音轨的相关系数均高于 0.996，音频对齐延迟 5 毫秒；整体响度 -17.11 LUFS、真峰值 -1.98 dBTP。完整声画解码通过，全部 35 镜头均核对实际编码画面；另逐句检查 21 个实际字幕排版的边界与行数，文本均位于画面安全区域，最长句为三行。社区工具的规格检查只有一个可选字幕轨提示：字幕已经烧入画面并另附 SRT，因此没有增加会重复显示的播放器字幕轨。详细记录见 [media-check.json](media-check.json)。

## 复现

使用已配置的 Pillow/NumPy Python 环境及 FFmpeg、Noto CJK 字体。渲染器复用原版的素材加载与字幕时间轴，在本版本中单独生成大字号排版，输出只写本版本目录：

```bash
cd /workspace/pixel-video
/workspace/tts-tools/pixel-video-venv/bin/python rpg-film/full-film-v2/render.py --preview-only
/workspace/tts-tools/pixel-video-venv/bin/python rpg-film/full-film-v2/render.py
/workspace/tts-tools/pixel-video-venv/bin/python rpg-film/full-film-v2/verify.py
```

`previews/` 中编号镜头在完整渲染后从实际编码 MP4 提取；`window-*` 为渲染器关键帧几何检查图。`storyboard.png` 和 `poster.png` 最终均来自真实成片。背景声、中间 WAV 和日志只作本地渲染产物，不随仓库提交。
