# Remotion 运行环境

Remotion 4.0.534 已安装在 `/workspace/video-tools/remotion`，用于今后需要 React 图层、时间轴和逐帧预览的作品。现有 Python/Pillow/FFmpeg 正式片继续保留。工具目录位于仓库外，没有改动原动画应用的依赖或锁文件。

## 安装与运行

Remotion、CLI、renderer、bundler、media、captions、transitions 固定为 4.0.534；React/React DOM 为 19.3.0；Zod 为 4.5.4。当前 Node 24.19.0、npm 11.9.0，使用系统 Chromium 154.0.8037.57、FFmpeg 7.1.5 和 Noto CJK 字体。CPU 渲染并发为 2，无需为此安装 CUDA 或第二套浏览器。复杂长片耗时不能由五秒测试推断。

在现有检出与保留的环境资产上运行：

```bash
bash /workspace/video-tools/setup/install_remotion.sh
bash /workspace/video-tools/setup/start_remotion.sh
```

安装助手使用固定锁文件、`npm ci --ignore-scripts` 和 `/workspace/video-tools/npm-cache`。锁文件未变时复用依赖；它从保留的教室和曼波首句准备新的测试素材，不覆盖原文件。此前的曼波/Pillow 环境继续由 `/workspace/tts-tools/setup/install.sh` 维护。

Studio 启动命令需要附属命令会话。助手复用已有 Remotion 服务，端口 3001 被其他服务占用时停止，不终止其他进程。内部 loopback 只用于工具健康检查，不能作为用户可访问的预览链接。后台进程不会随环境快照恢复。

实际渲染与验证命令：

```bash
cd /workspace/video-tools/remotion
npm --cache /workspace/video-tools/npm-cache run compositions
npm --cache /workspace/video-tools/npm-cache run render-check
/workspace/tts-tools/pixel-video-venv/bin/python /workspace/video-tools/setup/verify_runtime.py
```

验证脚本需要 Studio 响应。它检查真实 MP4 的规格、完整解码、曼波音轨、固定背景与局部运动，以及包含测试场景的编译资源。

## 已验证结果

[五秒运行测试 MP4](../tools/remotion/runtime-check.mp4) 为 1920×1080、24 fps、120 帧、H.264/yuv420p/BT.709，AAC 双声道 48 kHz。使用已有曼波首句和教室画面，字幕是原文“不知道大家的中学生活是怎么样的？”。这是安装检查片，不是重新制作的正式动画。

完整解码通过。音轨与曼波原音对齐后的相关系数 0.994279，解码偏移 34.542 毫秒，小于一个视频帧；增益约 0.978，未削波。背景固定，仅有整数像素的小范围测试运动。实际导出 [代表帧](../tools/remotion/runtime-check-sheet.png) 中的中文字幕显示正常。

安装、重复安装、场景识别、实际视频导出、Studio HTTP 与编译资源检查通过。没有执行浏览器内人工交互，也没有独立验证发布后另一个任务的恢复。机器可读结果见 [verification.json](../tools/remotion/verification.json)。

社区技能也经过实际测试：安装后的 Pixel Art Studio 导出 32×32 PNG、四帧 GIF、图集与可编辑项目数据；FFmpeg 的 probe.py 读取视频真实规格，look.py 导出该 MP4 的代表帧。其他可选脚本未逐一验证。

## 保存与工具恢复

[runtime-tools.zip](../tools/remotion/runtime-tools.zip) 保留运行工程源文件、package.json、package-lock.json、TypeScript/Remotion 配置和安装、启动、素材准备、验证助手。它不包含 node_modules、npm 缓存或重复音画素材；SHA-256 见 [runtime-tools-manifest.json](../tools/remotion/runtime-tools-manifest.json)。

如果工具文件丢失，可在已有项目、曼波/Pillow 环境和上述系统工具的云环境恢复。恢复保留已有改动，不覆盖不同内容：

```bash
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
folder = Path('/workspace/pixel-video/tools/remotion')
manifest = json.loads((folder / 'runtime-tools-manifest.json').read_text())
archive = folder / 'runtime-tools.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['archive_sha256']
with ZipFile(archive) as z:
    for entry in manifest['files']:
        path = Path(entry['path'])
        assert not path.is_absolute() and '..' not in path.parts
        data = z.read(entry['path'])
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        dest = Path('/workspace/video-tools') / path
        if dest.exists() and dest.read_bytes() != data:
            raise RuntimeError('保留已有改动，请先比较：' + str(dest))
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_bytes(data)
PY
bash /workspace/video-tools/setup/install_remotion.sh
```

环境配置保留既有曼波安装流程并追加已实测的 Remotion 安装与启动说明。配置草稿保存不会执行脚本、发布环境或保存进程。在环境设置中查看、保存并发布后，新快照才会保留运行依赖和模型。社区技能及恢复工具包同时随 Git 仓库保存。
