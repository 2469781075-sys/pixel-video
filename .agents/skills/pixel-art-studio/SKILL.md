---
name: pixel-art-studio
description: 社区像素美术与精灵动画参考，指导调色板、像素网格、人体比例、逐帧动作、稳定脚底锚点和精灵图集导出。用于本项目的像素人物动作设计、落地检查、素材一致性和可重复的原生精灵工具；图片生成与图片编辑仍使用当前内置 image_gen。
---

# Pixel Art Studio · 项目适配

来源是 `Gamezxz/pixel-art-studio`，版本记录在 `../sources.lock.json`。原始指南完整保存在 [UPSTREAM-SKILL.md](UPSTREAM-SKILL.md)。本入口按项目工具和用户已确认的风格限定使用方式。

按需要读取：

- [人物比例、轮廓与画布](references/patterns.md)
- [像素调色板](references/palettes.md) 与 [明暗和像素技法](references/techniques.md)
- [动画关键姿态、接触帧和稳定锚点](references/animation.md)
- [人体、阴影、轮廓和动作检查](references/validations.md)
- [常见像素失误](references/sharp_edges.md)
- [PNG、GIF 和图集导出](references/export.md)

先遵循 [项目画面规范](../pixel-video-production/references/art-direction.md)，保持已有掌机 RPG 画风。站立角色的脚底锚点固定，坐姿需要椅子支撑；控制局部次要动作，避免通过整幅背景漂移表现动画。

生成或编辑用户的位图素材时使用内置 `image_gen`，不因为本技能的 Python 示例改换图片编辑工具。需要检查像素或制作明确要求的原生程序精灵时，参考 `scripts/pixelstudio.py` 的网格、图层和导出接口；其代码已经通过四帧示例的实际导出检查。`scripts/study.py` 可作参考图的只读分析，输出到新的分析目录，不覆盖原图；数字指标不能证明人体正确。

原始指南中的 `pixelpipe.py` 清理图片、颜色重映射和 Python 绘图属于可选工具，不能自动用于用户的图片修改。遵循当次工具指令及用户选择。脚本无需 Aseprite、GPU 或额外 API 密钥。

使用已配置的 Pillow Python 环境。上游示例里的 `/Users/game/...` 是作者电脑路径；在本项目中用实际技能目录的 `scripts` 路径导入，测试示例可以通过 `PYTHONPATH` 指定它。对话中返回可访问图片，不依赖 macOS 的 `open` 命令。
