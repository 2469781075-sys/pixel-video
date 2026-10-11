# 今后视频制作使用的 skills

本仓库保存两套官方技能、两套社区技能和一套项目专用技能，由 [AGENTS.md](../AGENTS.md) 指定入口。技能提供制作方法和辅助工具；实际图片、配音和视频仍由相应运行环境完成。

| 技能 | 本项目用途 | 来源与已验证范围 |
| --- | --- | --- |
| [imagegen](../.agents/skills/imagegen/SKILL.md) | 场景、角色、参考图一致性和图片修改 | [OpenAI](https://github.com/openai/skills/tree/49f948faa9258a0c61caceaf225e179651397431/skills/.system/imagegen)，优先使用内置图片工具 |
| [remotion-best-practices](../.agents/skills/remotion-best-practices/SKILL.md) | 图层、逐帧动画、分镜时间轴、音轨与字幕 | [Remotion](https://github.com/remotion-dev/skills/tree/32b241b97f4e0e4ab61fe9a41b05e6e64503f8c5/skills/remotion-best-practices)，引擎 4.0.534 已安装并完成实际 MP4 导出 |
| [pixel-art-studio](../.agents/skills/pixel-art-studio/SKILL.md) | 像素调色板、人物比例、脚底锚点、动作关键帧和图集 | 社区 [Gamezxz/pixel-art-studio](https://github.com/Gamezxz/pixel-art-studio/tree/f8c246635c4621a6c2b427833149afdc3dc3c719)，四帧示例、PNG、GIF、图集与编辑数据导出通过 |
| [ffmpeg-skill](../.agents/skills/ffmpeg-skill/SKILL.md) | 音视频探测、字幕、拼接、响度与成片代表帧 | 社区 [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill/tree/1f7e7e3ad1c30cb39fe9032abb5b39cca8e63376)，安装后的 probe.py、look.py 已检查实际 MP4 |
| [pixel-video-production](../.agents/skills/pixel-video-production/SKILL.md) | 掌机 RPG 短片、曼波朗读、逐句原文字幕与画面检查 | 本项目专用，记录已确认的画面与制作要求 |

项目技能保留横向推拉窗、双人并桌、有同桌的靠窗座位、升高一层的讲台、自然坐姿和落地、第一人称开窗及开窗后的场景变化。保留已有画风、检查图和成片，原文逐句用于字幕和配音。

## 工具选择

现有正式片用 Python/Pillow/FFmpeg 完成，已有可工作的渲染流程。Remotion 适合今后的 React 图层、分镜时间轴与逐帧预览，按作品需要选用。安装与复用见 [Remotion 运行环境说明](remotion-runtime.md)，本次没有迁移已交付的正式片。

社区技能按当前问题筛选。Pixel Art Studio 提供具体像素动作、锚点与导出方法；FFmpeg 提供可检查实际输出的本地工具。小说改编分镜技能、需要桌面 Aseprite 服务的工具和大型技能合集也经过检索，当前不引入这些额外流程。

参考方法仍需通过实际看图确认人体、遮挡和动作。用户的位图生成与修改继续使用当前内置 image_gen；Python 绘图和图片清理为可选工具，不自动改变图片编辑方式。FFmpeg 其他可选脚本未全部测试，不自动改写文案、删除停顿或改变画面比例。两套社区工具不需要新增 API 密钥、Aseprite 或 GPU。

## 使用与保存

可以直接要求：“使用 $pixel-video-production，把这篇文章制作成掌机 RPG 像素视频，配曼波朗读和逐句原文字幕。”也可以只要求图片检查。助手按 AGENTS.md 读取相应技能；菜单是否显示文件取决于客户端发现机制，文件入口始终可读。

具体来源提交、原始文件 SHA-256 和本地适配记录在 [sources.lock.json](../.agents/skills/sources.lock.json)。社区包保留 MIT 许可证和未修改的 UPSTREAM-SKILL.md，本地入口限定项目范围。没有运行远程安装器或自动升级。imagegen 保留 Apache 许可证；Remotion skills 上游没有独立许可证文件，不将该参考包标为 MIT 或 Apache。

用户对第二版提出了旧图裁切过多与坐姿结构错误的反馈。本轮没有再安装第三方包，而是在项目专用技能中加入必读的 [分镜与坐姿复核](../.agents/skills/pixel-video-production/references/shot-review.md)，并使用现有内置图片工具重绘 [全身侧面结构图](../rpg-film/rebuild-review/01-seat-profile.png)。数值检查与引擎安装不能替代分镜创作和桌椅遮挡的实际看图复核；这张结构图不代表完整重制视频已完成。

OpenAI 旧 skills 仓库已迁移至 [plugins](https://github.com/openai/plugins)。检查新仓库后保留兼容当前工具的固定 imagegen 版本。项目专用技能此前按 skill-creator 规范初始化和验证。

技能随 Git 保存，Remotion 依赖和曼波模型保留在云环境。新的安装、启动说明将保存为环境配置草稿；查看、保存并发布后才能形成新的快照。当前实例已实际测试，独立新任务恢复尚未验证。
