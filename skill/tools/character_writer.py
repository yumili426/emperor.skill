#!/usr/bin/env python3
"""
角色文件管理器 - 管理蒸馏角色的文件结构
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class CharacterWriter:
    """角色文件管理器"""

    # 成长等级定义
    GROWTH_LEVELS = {
        1: {"name": "新秀", "exp_required": 0},
        2: {"name": "熟练", "exp_required": 20},
        3: {"name": "精通", "exp_required": 50},
        4: {"name": "大师", "exp_required": 100},
        5: {"name": "传奇", "exp_required": 200},
    }

    # 宫廷角色到成长方向的映射
    GROWTH_PATH_MAP = {
        "首辅": "politics",
        "次辅": "politics",
        "尚书": "politics",
        "将军": "military",
        "翰林": "culture",
        "太监": "intrigue",
        "御史": "politics",
        "皇后": "politics",
        "嫔妃": "culture",
        "贵妃": "culture",
        "妃": "culture",
        "嫔": "culture",
        "贵人": "culture",
        "太子": "politics",
        "太后": "politics",
    }

    def __init__(self, skill_dir: str):
        """
        初始化角色文件管理器

        Args:
            skill_dir: skill 目录路径
        """
        self.skill_dir = Path(skill_dir)
        self.court_dir = self.skill_dir / "court"
        self.court_dir.mkdir(exist_ok=True)

    def create_character(
        self,
        slug: str,
        name: str,
        real_name: str,
        title: str,
        rank: str,
        distillation_level: str,
        court_role: str,
        **kwargs,
    ) -> dict:
        """
        创建新角色

        Args:
            slug: 角色标识
            name: 角色昵称
            real_name: 真实姓名
            title: 宫廷职位
            rank: 官阶
            distillation_level: 蒸馏等级
            court_role: 宫廷角色分类
            **kwargs: 可选字段

        Returns:
            角色元数据字典
        """
        char_dir = self.court_dir / slug
        char_dir.mkdir(parents=True, exist_ok=True)

        # 创建 memories 子目录
        memories_dir = char_dir / "memories"
        memories_dir.mkdir(parents=True, exist_ok=True)
        (memories_dir / "chats").mkdir(parents=True, exist_ok=True)
        (memories_dir / "photos").mkdir(parents=True, exist_ok=True)
        (memories_dir / "social").mkdir(parents=True, exist_ok=True)

        # 构建默认元数据
        now = datetime.now().isoformat()
        growth_path = self.GROWTH_PATH_MAP.get(court_role, "politics")

        meta = {
            "slug": slug,
            "name": name,
            "real_name": real_name,
            "title": title,
            "rank": rank,
            "distillation_level": distillation_level,
            "join_date": datetime.now().strftime("%Y-%m-%d"),
            "loyalty": kwargs.get("loyalty", 50),
            "affection": kwargs.get("affection", 50),
            "power": kwargs.get("power", 50),
            "ability": {
                "politics": kwargs.get("ability_politics", 50),
                "military": kwargs.get("ability_military", 50),
                "culture": kwargs.get("ability_culture", 50),
                "intrigue": kwargs.get("ability_intrigue", 50),
            },
            "personality": {
                "mbti": kwargs.get("mbti", ""),
                "traits": kwargs.get("traits", []),
                "likes": kwargs.get("likes", []),
                "dislikes": kwargs.get("dislikes", []),
            },
            "speech_patterns": {
                "fillers": kwargs.get("fillers", []),
                "endings": kwargs.get("endings", []),
                "emoji": kwargs.get("emoji", []),
            },
            "court_role": court_role,
            "harem_level": kwargs.get("harem_level", None),
            "relationship_to_emperor": kwargs.get("relationship_to_emperor", "neutral"),
            "relationship_to_others": kwargs.get("relationship_to_others", {}),
            "context_level": kwargs.get("context_level", "support"),
            "tags": kwargs.get("tags", []),
            "special_events": kwargs.get("special_events", []),
            "favor_events": kwargs.get("favor_events", {}),
            "level": 1,
            "experience": 0,
            "growth_path": growth_path,
            "created_at": now,
            "last_interaction": now,
        }

        # 写入 meta.json
        with open(char_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 写入 portrait.md 骨架
        portrait_content = f"""# {name} — {title}

## 基本信息
- 宫廷身份：{title}
- 官阶：{rank}
- 蒸馏等级：{distillation_level}

## 灵魂原声

（待填充）

## 句式习惯

（待填充）

## 反应模式

（待填充）

## 灵魂碎片

（待填充）
"""
        with open(char_dir / "portrait.md", "w", encoding="utf-8") as f:
            f.write(portrait_content)

        # 写入 record.md 骨架
        record_content = f"""# {name} — 朝堂档案

## 入朝记录
- 入朝时间：{meta['join_date']}
- 宫廷职位：{title}
- 官阶：{rank}

## 重要事件

（暂无）

## 决策记录

（暂无）
"""
        with open(char_dir / "record.md", "w", encoding="utf-8") as f:
            f.write(record_content)

        # 更新索引
        self._update_index(slug, name, title, rank, distillation_level)

        return meta

    def update_meta(self, slug: str, updates: dict) -> dict:
        """
        更新角色元数据

        Args:
            slug: 角色标识
            updates: 要更新的字段

        Returns:
            更新后的元数据字典
        """
        char_dir = self.court_dir / slug
        meta_file = char_dir / "meta.json"

        if not meta_file.exists():
            return {}

        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # 递归合并更新
        self._deep_merge(meta, updates)

        # 更新 last_interaction
        meta["last_interaction"] = datetime.now().isoformat()

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    def get_character(self, slug: str) -> Optional[dict]:
        """
        获取角色元数据

        Args:
            slug: 角色标识

        Returns:
            角色元数据字典，不存在则返回 None
        """
        meta_file = self.court_dir / slug / "meta.json"
        if not meta_file.exists():
            return None

        with open(meta_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_characters(self) -> list:
        """
        列出所有角色

        Returns:
            角色元数据字典列表
        """
        characters = []
        if not self.court_dir.exists():
            return characters

        for item in self.court_dir.iterdir():
            if item.is_dir() and item.name != "__pycache__":
                meta_file = item / "meta.json"
                if meta_file.exists():
                    with open(meta_file, "r", encoding="utf-8") as f:
                        characters.append(json.load(f))

        return sorted(characters, key=lambda x: x.get("name", ""))

    def add_experience(self, slug: str, amount: int) -> dict:
        """
        为角色增加经验值

        Args:
            slug: 角色标识
            amount: 经验值

        Returns:
            更新后的元数据字典
        """
        meta = self.get_character(slug)
        if not meta:
            return {}

        # 增加经验
        meta["experience"] = meta.get("experience", 0) + amount

        # 检查升级
        current_level = meta.get("level", 1)
        while current_level < 5 and meta["experience"] >= self.GROWTH_LEVELS.get(current_level + 1, {}).get("exp_required", float("inf")):
            current_level += 1
            growth_path = meta.get("growth_path", "politics")
            if "ability" in meta and growth_path in meta["ability"]:
                meta["ability"][growth_path] = min(
                    100, meta["ability"][growth_path] + 2
                )

        meta["level"] = current_level

        # 写回
        meta_file = self.court_dir / slug / "meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta

    def _update_index(
        self, slug: str, name: str, title: str, rank: str, distillation_level: str
    ) -> None:
        """
        更新角色索引文件

        Args:
            slug: 角色标识
            name: 角色昵称
            title: 宫廷职位
            rank: 官阶
            distillation_level: 蒸馏等级
        """
        index_file = self.court_dir / "index.md"

        if not index_file.exists():
            return

        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()

        new_row = f"| {name} | {title} | {rank} | {distillation_level} | 在朝 |"

        lines = content.split("\n")
        # Find the table section: header row with | 序号 | 姓名 | ... followed by |------|... separator
        insert_index = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("|") and "序号" in stripped and "姓名" in stripped:
                # This is the header row; the separator is next, character rows go after separator
                if i + 2 < len(lines) and "---" in lines[i + 1]:
                    # Find where character rows end (next section starts)
                    for j in range(i + 2, len(lines)):
                        if lines[j].strip() and not lines[j].strip().startswith("|"):
                            insert_index = j
                            break
                    else:
                        insert_index = len(lines)
                break

        if insert_index is not None:
            lines.insert(insert_index, new_row)
            with open(index_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        else:
            # Append after the separator line as fallback
            for i, line in enumerate(lines):
                if "---" in line and i > 0 and lines[i - 1].strip().startswith("|"):
                    lines.insert(i, new_row)
                    with open(index_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))
                    break

    def _deep_merge(self, base: dict, updates: dict) -> None:
        """
        递归合并字典

        Args:
            base: 基础字典
            updates: 更新字典
        """
        for key, value in updates.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(base[key], value)
            else:
                base[key] = value


if __name__ == "__main__":
    # 测试
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    writer = CharacterWriter(skill_dir)

    # 列出角色
    characters = writer.list_characters()
    print(f"当前角色数: {len(characters)}")

    # 创建测试角色
    meta = writer.create_character(
        slug="test-character",
        name="测试角色",
        real_name="测试",
        title="翰林",
        rank="从五品",
        distillation_level="L1",
        court_role="翰林",
        traits=["聪明"],
    )
    print(f"创建角色: {meta['name']}")

    # 测试经验增长
    meta = writer.add_experience("test-character", 25)
    print(f"经验: {meta['experience']}, 等级: {meta['level']}")

    # 清理测试数据
    import shutil

    test_dir = writer.court_dir / "test-character"
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("已清理测试数据")
