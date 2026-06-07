# About Lessons In Love

本目录用于存放LiL相关工具。

目前包含：
- [更好的双语显示](./zz_better_bilingual_toggle.rpy)：一个面向LiL两种不同汉化版的语言插件，提供快速切换和双语展示功能。将插件放在LiL的`game`目录下即可使用。
- [双语渲染探针](./tools/bilingual_render_probe.py)：用于无头加载目标Ren'Py游戏，临时安装当前双语插件，并扫描对白、菜单和翻译字符串的显示路径。

## 双语渲染探针

常用命令：

```powershell
python tools\bilingual_render_probe.py "D:\LessonsInLove0.39.0-0.39.0-pc-subscribestar" -o reports\probe_039_current.jsonl
```

说明：
- 默认会测试`translated`、`original`、`translated_first`和`original_first`四种显示模式。
- 默认模拟游戏启动后的插件路径；可用`--path load`测试读档后的路径。
- 默认只做文本对象构造检查；可加`--render`进一步调用Ren'Py文本渲染。
- 探针会临时复制插件和探针脚本到目标游戏的`game`目录，结束后自动恢复原文件。
- 报告写入`reports/`，该目录不会提交到仓库。
