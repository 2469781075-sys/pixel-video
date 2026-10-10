# 像素视频项目

这是以中文文章为脚本、曼波朗读为音轨的像素动画仓库。读取用户本轮要求，延续已确认的画风和结构修正；保留既有检查图、小样和成片。

## 项目技能

技能安装在本仓库 `.agents/skills/`，不依赖全局目录是否可写。处理对应任务时先读取所列入口，再按需读取参考文件：

- 视频规划、分镜、动画、配音字幕、教室布局和画面修复：`.agents/skills/pixel-video-production/SKILL.md`。
- 生成或编辑角色、背景、透明部件等位图素材：`.agents/skills/imagegen/SKILL.md`；使用当前可用的内置图片工具及其实际参数。
- 已有或明确选择 React/Remotion 视频流程：`.agents/skills/remotion-best-practices/SKILL.md`。
- 像素调色板、人体比例、步行关键帧与脚底锚点：`.agents/skills/pixel-art-studio/SKILL.md`。
- 本地音视频处理、原文字幕、响度和实际成片代表帧：`.agents/skills/ffmpeg-skill/SKILL.md`。

现有正式视频使用 Python/Pillow/FFmpeg。不要因下载了 Remotion 参考技能就迁移整个项目；按用户目标和实际依赖选择流程。曼波继续复用现有模型及音轨。

Remotion 4.0.534 已配置在 `/workspace/video-tools/remotion`，使用系统 Chromium 和 CPU；安装与启动助手在 `/workspace/video-tools/setup`。已验证带曼波音轨和原文字幕的 1080p 测试导出；可按新作品需要选用。复用说明及可恢复工具包见 `docs/remotion-runtime.md`。

用户只要求图片检查时交付图片；要求完整视频时完成声画、逐句原文字幕、导出和验证。新文章的句数和时长从原文及实际音轨计算，当前作品的 21 句与 141 秒不适用于所有作品。

使用现有云任务的独立检出；仅在用户明确要求时创建额外 worktree。环境快照可能保存工具和模型，但后台语音进程需要重新检查并按需启动。技能不会自动安装依赖或激活其中的示例脚本。

技能来源、固定版本和本地适配记录在 `.agents/skills/sources.lock.json`；用途及使用示例见 `docs/video-skills.md`。
