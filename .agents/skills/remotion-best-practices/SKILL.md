---
name: remotion-best-practices
description: 官方 Remotion 视频技能参考包，指导 React 视频的逐帧动画、分场景时间轴、音轨、字幕、静帧检查和 MP4 导出。用于已经采用或明确选择 Remotion 的视频项目；本仓库现有 Python/FFmpeg 流程继续由 pixel-video-production 指导。
---

# Remotion 视频参考

本目录保留 `remotion-dev/skills` 的完整参考文件，固定来源版本记录在 `../sources.lock.json`。原始入口保存在 [UPSTREAM-SKILL.md](UPSTREAM-SKILL.md)，此入口只调整技能发现范围与本项目默认选择。

先确认任务需要 Remotion，再按需要读取对应文件：

- [逐帧动画、图层、音频与场景](remotion-markup/REFERENCE.md)
- [分场景视频](remotion-markup/multi-scene-video.md)
- [时间轴与插值](remotion-markup/timing.md)
- [已有音轨的嵌入与混音](remotion-markup/audio.md)
- [字幕](remotion-captions/REFERENCE.md) 与 [导入 SRT](remotion-captions/import-srt-captions.md)
- [视频与静帧导出](remotion-render/REFERENCE.md)
- [音视频时长与尺寸](remotion-multimedia/REFERENCE.md)
- [Studio 预览](remotion-studio/REFERENCE.md)
- [当前 API 文档](remotion-docs/REFERENCE.md)

以实际安装的 Remotion 版本为准，使用项目锁文件与相应版本文档；本参考包包含较新的 API，不假定其他项目已安装这些功能。下载技能参考文件不等于安装 Remotion、React 或浏览器渲染环境。

制作本仓库像素短片时，先遵循 [项目制作规范](../pixel-video-production/SKILL.md)。复用用户指定的曼波音轨；配音示例中的 ElevenLabs 服务只是上游示例。用户明确要求成片时，完成实际导出；仅要图片检查时交付静帧。在没有可访问浏览器的云环境，用实际导出的静帧检查画面。
