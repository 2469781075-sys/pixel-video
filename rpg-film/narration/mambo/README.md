# 曼波全文朗读 · 云端 CPU 已验证

已根据用户原文逐句合成 21 段曼波朗读，音轨总长 **139 秒（2 分 19 秒）**。模型已加载时，整篇合成耗时约 **227 秒（3 分 47 秒）**；首次单句请求包含发音模型初始化，耗时约 23 秒。这些是当前四核 CPU 云环境的实测值，其他环境可能不同。

- [试听第一句](first-line.mp3)
- [下载全文 MP3](narration.mp3)
- [下载逐句字幕](subtitles.srt)
- [下载配音素材包](mambo-narration.zip)：全文 WAV/MP3、21 段 WAV、字幕、实际时间轴、原文和基础模型来源。
- [实际时间轴](timings.json)
- [当前可复用工具包](mambo-ready-tools.zip)

下载音频后可直接在播放器试听。字幕逐字采用原文，句间加入 0.25 秒停顿；时间戳根据各段 WAV 的实际采样数计算。所有 21 个 WAV 均通过非空、非静音、时长及原文对应检查。声音的听感和个别字词发音仍以实际试听为准。

运行方式为 Linux CPU / float32 / GPT-SoVITS v2 曼波声线；本轮使用云端四核 CPU。基础模型和声线已保存在 `/workspace/tts-tools`。实际引擎重启后再次生成第一句成功，并已设置 Hugging Face 与 Transformers 离线加载，后续可以复用这些本地模型。

环境设置中的安装脚本、启动说明已更新。模型是在上一次发布后下载完成的，因此还需保存并发布最新环境，把这些模型和当前启动说明纳入后续使用的快照。保存配置草稿不等于发布；已验证当前实例和引擎重启，尚未验证最新模型快照在另一个新任务中的恢复。

后续文章由助手整理新的 `original.txt` 和逐句 `sentences.json`，再通过客户端的 `--original`、`--script`、`--output` 参数选择。引擎启动命令为 `bash /workspace/tts-tools/setup/start_mambo.sh`；逐句合成命令为 `/workspace/tts-tools/mambo-venv/bin/python /workspace/tts-tools/setup/narrate.py`。这些路径位于云环境，不需要用户在自己的电脑执行。

已有动画版本保留。配音会用于重新确定正式片时长和字幕；人物落地/遮挡、自然窗户及稳定镜头的画面修正仍待制作。
