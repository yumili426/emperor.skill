# 皇帝.skill

> 普天之下，莫非王土；率土之滨，莫非王臣。

一个跨平台互动小说技能。把身边真实的人"蒸馏"成臣子、妃子、将军，在一个架空明代世界中体验成为皇帝的掌控感。

## 项目结构

```
├── skill/          # 技能核心（平台无关）
├── docs/           # 产品文档
└── 参考资料/        # 外部参考材料
```

## 使用方式

### Claude Code

在项目根目录创建目录联接，使 Claude Code 能识别该 skill：

**Windows:**
```cmd
mkdir .claude\skills
mklink /J .claude\skills\emperor skill
```

**macOS / Linux:**
```bash
mkdir -p .claude/skills
ln -s "$(pwd)/skill" .claude/skills/emperor
```

然后输入 `/emperor` 即可启动。

### Kiro

将 `skill/` 目录复制或链接到 `~/.kiro/skills/emperor/`。

### 其他平台

`skill/` 目录下的内容完全平台无关。只需让目标平台加载 `skill/SKILL.md` 作为入口即可。

## 安全说明

- 所有蒸馏数据仅存储在本地
- 不会主动联系任何真人
- 生成的虚拟角色均有明确标识
- 可随时删除任何角色数据
