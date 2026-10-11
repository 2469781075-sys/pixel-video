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

最新完整视频在 `rpg-film/film-light-rain/`：141 秒、1080p、24 fps，以用户确认的 16 张独立分镜制作掌机 RPG A 轻颗粒动画。雨天教室使用阴天漫射光，暮色与夜色教室不加阳光；河流和骑士等幻想画面按原设定保留。相机固定，局部动作使用生成的姿态与透明部件；包括同桌离席、触窗扣、第一人称水平推拉窗、放下双手、开窗后室内变化及合书。全文曼波朗读保持 1.0 倍速，21 句大字幕独立烧录，最长三行。制作前读取该目录的 README、shots.json、asset-plan.json、render.py 和实际成片代表帧。

原第二版 `rpg-film/full-film-v2/`、原版 `rpg-film/full-film/`、完整静态分镜和各颗粒检查图继续保留。新版本验证全文字幕、实际配音覆盖、全部声明动作区域之外的固定像素，以及部分实际编码帧的相机位移；技术通过不等于用户已验收美术。生成过场和动作时只改需要变化的部分，不用整体缩放代替人物动作，不把随机颗粒覆盖脸部。

使用现有云任务的独立检出；仅在用户明确要求时创建额外 worktree。环境快照可能保存工具和模型，但后台语音进程需要重新检查并按需启动。技能不会自动安装依赖或激活其中的示例脚本。

技能来源、固定版本和本地适配记录在 `.agents/skills/sources.lock.json`；用途及使用示例见 `docs/video-skills.md`。

用户已指出第二版存在旧图裁切充当新分镜、主角夹在桌间及椅子在桌前等缺陷。其技术验证不代表美术验收通过；不要用有缺陷的座位图作结构模板。制作前读取 `.agents/skills/pixel-video-production/references/shot-review.md`；新坐姿结构检查图在 `rpg-film/rebuild-review/`，不等于已完成重制视频。

本次重制的四张核心静态镜头与原文对应记录在 `rpg-film/reboot-shots/`，用户已明确认可这四张核心构图，并要求补齐其他画面。图 1、2 朝后墙，图 4 朝前墙，窗墙在画面左右的变化来自相机方向。第 4 张采用已经修正额外鞋子的版本，后续有更强像素版。

已确认的完整静态分镜在 `rpg-film/complete-storyboard/`：16 张对应全文 21 句，12 个新增画面、3 个核心图画风统一版、1 个已有强像素核心图。此目录保留原静态预览，正式动画另存在 `rpg-film/film-light-rain/`。第 2 张已修成一层高台，第 3 张重新绘制后排俯视空间。图 13 的原句全文触发图片工具拦截，图上只示意前半句；全文仍保存在 original.txt、shots.json、原曼波旁白及最新正式视频中，不以图片预览字幕代替或删改原文。后续仍须全文逐句曼波朗读、大字幕和固定机位；先查 README、assets.json 及 shots.json，再做动作与背景连续性核对。
