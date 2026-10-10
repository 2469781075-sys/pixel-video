# 曼波朗读云端配置

目标：在 Linux 云环境用 CPU 运行 GPT-SoVITS，复用曼波音色和基础模型，不占用用户电脑显卡。CPU 实际速度需要在首次真实朗读后测量。

已获取 MamboTTS v1.2.1 发布包中的 `manbo-e10.ckpt`、`manbo_e8_s168.pth` 和 `refer.wav`。采用官方 GPT-SoVITS `20250606v2pro` 版本，提交 `d7c2210da8c013e81a94bfc7b811a477c99fd506`。源码和原有动画文件保持原样。

工具目录 `/workspace/tts-tools/setup`，独立语音环境 `/workspace/tts-tools/mambo-venv`，曼波声线目录 `/workspace/tts-tools/mambo-models`，基础模型目录 `/workspace/tts-tools/base-models`。

## 当前进度

- 已安装 CPU PyTorch、上游引擎依赖和动画依赖；已检查依赖兼容性及引擎入口导入。
- 逐句客户端用合成测试音频验证了 21 句原文传递、WAV 长度计算、全文拼接和字幕时间轴。这不代表已经生成真实曼波朗读。
- 基础模型下载受到云环境网络策略限制，返回代理 `403 Forbidden`。真实语音合成尚未完成。
- 已保存所需下载域名的环境配置草稿。保存草稿不等于网络设置已应用，也不等于环境已发布。

## 后续启动

1. 在环境设置保存网络配置并发布环境，使模型下载域名生效。
2. `bash /workspace/tts-tools/setup/install.sh --download-models` 下载中文 RoBERTa、HuBERT 和 G2PW；资源保留在 `/workspace/tts-tools` 下。
3. `bash /workspace/tts-tools/setup/start_mambo.sh` 启动仅绑定云机器回环地址的 CPU 引擎。这是内部接口，不是用户预览网址。
4. 引擎启动后先执行 `/workspace/tts-tools/mambo-venv/bin/python /workspace/tts-tools/setup/narrate.py --limit 1 --output /workspace/tts-tools/narration-preview`。必须检查实际声音、发音、音色和运行耗时；成功后再去掉 `--limit 1` 生成全文。
5. `narration.wav` 是整段音轨，`001.wav` 等是逐句音频，`timings.json` 和 `subtitles.srt` 采用实际音频长度。默认句间停顿 0.25 秒，语速 1.0。

后续文章只需提供原文，再由助手整理新的逐句脚本。`narrate.py` 可通过 `--script`、`--original` 和 `--output` 指定对应文件。每次生成前核对逐句拼接与原文完全一致。

## 手动提供基础模型

如果网络配置无法修改，可以从已安装的 MamboTTS 的 `GPT-SoVITS/GPT_SoVITS/` 中提供这三个目录：

- `pretrained_models/chinese-roberta-wwm-ext-large`（含权重、配置、词表和 tokenizer 文件）
- `pretrained_models/chinese-hubert-base`（含权重和配置）
- `text/G2PWModel`（含 `g2pW.onnx`、配置及配套字典文件）

保留各目录的全部内容，压缩后通过聊天附件或可下载链接提供。无需上传 Windows runtime、整个 8 GB 引擎整合包或已经获取的曼波声线文件。如果附件过大，可以使用可供当前环境读取的下载链接；受网络策略限制的域名仍需加入环境设置。

动画仍沿用掌机 RPG A 风格；后续重做窗户和人物落地/遮挡，镜头保持稳定，字幕逐字采用原文。已有 30 秒版本保留作对照，不能视为这些修正已经完成。
