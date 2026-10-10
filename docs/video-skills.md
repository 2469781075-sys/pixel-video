# 今后视频制作使用的 skills

已将两套 GitHub 官方技能和一套项目专用技能保存到本仓库 `.agents/skills/`，并由根目录 `AGENTS.md` 指定使用入口。它们是供助手读取的制作方法、参考文件和辅助工具；图片生成、曼波配音和渲染仍由实际工具完成。

| 技能 | 用途 | 来源与状态 |
| --- | --- | --- |
| [imagegen](../.agents/skills/imagegen/SKILL.md) | 角色与场景素材、参考图一致性、局部修改、透明部件 | [OpenAI 官方技能](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/imagegen)；优先使用现有内置图片工具 |
| [remotion-best-practices](../.agents/skills/remotion-best-practices/SKILL.md) | 逐帧动画、分场景时间轴、音轨、SRT 字幕、静帧和 MP4 导出 | [Remotion 官方技能](https://github.com/remotion-dev/skills/tree/32b241b97f4e0e4ab61fe9a41b05e6e64503f8c5/skills/remotion-best-practices)；参考包已下载，Remotion 引擎尚未安装 |
| [pixel-video-production](../.agents/skills/pixel-video-production/SKILL.md) | 掌机 RPG 像素短片、曼波朗读、逐句原文字幕、稳定镜头与成片检查 | 本项目专用，依据已确认的画面要求和现有制作工具整理 |

专用技能记录了横向推拉窗、双人并桌、有同桌的靠窗座位、升高一层的讲台、周围同学落地和自然坐姿、第一人称开窗及开窗后的场景变化。画风参考已保留的更强像素版；旧版素材继续保存。

## 使用方法

今后在这个仓库继续制作视频，助手按 `AGENTS.md` 读取对应技能。也可以在请求中明确指定：

```text
使用 $pixel-video-production，把下面的文章制作成掌机 RPG 像素视频，配曼波朗读和逐句原文字幕。
```

```text
使用 $pixel-video-production，先给我检查教室全景和第一人称横向推窗两张图片，暂时不做动画。
```

这些文件现在就能被读取；新的会话是否在技能菜单中显示它们，取决于客户端对仓库技能的发现机制。即使菜单未刷新，仓库的 `AGENTS.md` 也明确提供了文件入口。

## 版本和边界

来源固定在具体 Git 提交，文件校验值和本地适配记录保存在 [sources.lock.json](../.agents/skills/sources.lock.json)。下载后没有运行图片 API CLI、地图示例、远程安装器或自动升级。imagegen 的 Apache 许可证随包保留；Remotion skills 检出中没有单独许可证文件，记录原始来源，不将其标注为 MIT 或 Apache。

OpenAI 的旧 `skills` 仓库已标记迁移到 [plugins](https://github.com/openai/plugins)。本次检查了新仓库；其 Remotion 插件存在，但没有对应的 imagegen 技能入口，因此保留旧官方库中兼容当前内置图片工具的固定版本。

本项目技能按 OpenAI 的 `skill-creator` 规范整理，并使用其已审阅的初始化、元数据生成及验证工具。Remotion 上游入口另存为 `UPSTREAM-SKILL.md`，本地入口限定框架使用范围，避免把已有 Python/FFmpeg 工作流强行变成 React 项目。

现有 Python/FFmpeg 和曼波流程继续使用。技能文件会随仓库保存，不需要因为这次下载重新发布云环境；将来若安装新的渲染引擎，再验证运行依赖并更新环境配置。
