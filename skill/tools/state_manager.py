#!/usr/bin/env python3
"""
状态管理器 - 管理游戏状态
"""

import json
import os
from datetime import datetime
from pathlib import Path


class StateManager:
    """游戏状态管理器"""

    def __init__(self, skill_dir: str):
        """
        初始化状态管理器

        Args:
            skill_dir: skill 目录路径
        """
        self.skill_dir = Path(skill_dir)
        self.state_dir = self.skill_dir / "state"
        self.save_dir = self.state_dir / "save_slots"

        # 确保目录存在
        self.state_dir.mkdir(exist_ok=True)
        self.save_dir.mkdir(exist_ok=True)

    def load_kingdom(self) -> dict:
        """
        加载王国状态

        Returns:
            王国状态字典
        """
        kingdom_file = self.state_dir / "kingdom.json"
        if kingdom_file.exists():
            with open(kingdom_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_kingdom()

    def save_kingdom(self, kingdom: dict) -> None:
        """
        保存王国状态

        Args:
            kingdom: 王国状态字典
        """
        kingdom_file = self.state_dir / "kingdom.json"
        with open(kingdom_file, "w", encoding="utf-8") as f:
            json.dump(kingdom, f, ensure_ascii=False, indent=2)

    def load_relations(self) -> dict:
        """
        加载关系状态

        Returns:
            关系状态字典
        """
        relations_file = self.state_dir / "relations.json"
        if relations_file.exists():
            with open(relations_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"characters": [], "relations": {}, "last_updated": None}

    def save_relations(self, relations: dict) -> None:
        """
        保存关系状态

        Args:
            relations: 关系状态字典
        """
        relations_file = self.state_dir / "relations.json"
        with open(relations_file, "w", encoding="utf-8") as f:
            json.dump(relations, f, ensure_ascii=False, indent=2)

    def advance_day(self) -> dict:
        """
        推进一天

        Returns:
            更新后的王国状态
        """
        kingdom = self.load_kingdom()

        # 推进日期（农历月默认按30天计，节日有特殊日期偏移容差）
        kingdom["current_day"] += 1
        if kingdom["current_day"] > 30:
            kingdom["current_day"] = 1
            kingdom["current_month"] += 1
            if kingdom["current_month"] > 12:
                kingdom["current_month"] = 1
                kingdom["current_year"] += 1

        # 每日结算
        kingdom = self._daily_settlement(kingdom)

        self.save_kingdom(kingdom)
        return kingdom

    def _daily_settlement(self, kingdom: dict) -> dict:
        """
        每日结算

        Args:
            kingdom: 王国状态

        Returns:
            更新后的王国状态
        """
        # 国库收入
        income = int(kingdom["stats"]["economy"] * 10)
        kingdom["treasury"] += income

        # 军队消耗
        upkeep = int(kingdom["army"] * 0.1)
        kingdom["treasury"] -= upkeep

        # 国库不能为负
        if kingdom["treasury"] < 0:
            kingdom["treasury"] = 0
            kingdom["stats"]["stability"] -= 5

        return kingdom

    def _default_kingdom(self) -> dict:
        """
        默认王国状态

        Returns:
            默认王国状态字典
        """
        return {
            "dynasty_name": "大明",
            "era_name": "",
            "current_year": 1,
            "current_month": 1,
            "current_day": 1,
            "stats": {
                "economy": 70,
                "military": 60,
                "culture": 75,
                "stability": 65,
                "popularity": 80
            },
            "treasury": 10000,
            "army": 50000,
            "territory": {
                "core": ["京师", "江南", "蜀中"],
                "border": ["北境", "西疆"],
                "contested": ["南疆"]
            },
            "neighbors": [
                {
                    "name": "北元",
                    "relation": "hostile",
                    "power": 75,
                    "army": 40000
                },
                {
                    "name": "朝鲜",
                    "relation": "tributary",
                    "power": 40,
                    "army": 15000
                }
            ],
            "court_positions": {
                "shoufu": None,
                "cifu": None,
                "personnel_shangshu": None,
                "revenue_shangshu": None,
                "rites_shangshu": None,
                "war_shangshu": None,
                "justice_shangshu": None,
                "works_shangshu": None,
                "jinwei_commander": None,
                "dongchang_commander": None,
                "empress": None,
                "crown_prince": None
            },
            "crown_prince": {
                "has_heir": False,
                "current_heir": None,
                "princes": []
            },
            "harem": {
                "empress": None,
                "guifei": None,
                "fei": [],
                "pin": [],
                "guiren": []
            },
            "spy_system": {
                "unlocked": False,
                "jinyiwei": False,
                "dongchang": False,
                "xichang": False,
                "unlock_events_triggered": []
            },
            "examination_cycle": {
                "last_xiangshi": 0,
                "next_xiangshi": 3,
                "last_huishi": 0,
                "last_dianshi": 0
            }
        }

    def save_game(self, slot: int, name: str = None) -> str:
        """
        保存游戏

        Args:
            slot: 存档槽位
            name: 存档名

        Returns:
            存档路径
        """
        slot_dir = self.save_dir / f"slot{slot}"
        slot_dir.mkdir(exist_ok=True)

        # 保存王国状态
        kingdom = self.load_kingdom()
        with open(slot_dir / "kingdom.json", "w", encoding="utf-8") as f:
            json.dump(kingdom, f, ensure_ascii=False, indent=2)

        # 保存关系状态
        relations = self.load_relations()
        with open(slot_dir / "relations.json", "w", encoding="utf-8") as f:
            json.dump(relations, f, ensure_ascii=False, indent=2)

        # 保存存档信息
        save_info = {
            "slot": slot,
            "name": name or f"存档{slot}",
            "saved_at": datetime.now().isoformat(),
            "game_time": f"{kingdom['era_name']}{kingdom['current_year']}年{kingdom['current_month']}月{kingdom['current_day']}日"
        }
        with open(slot_dir / "info.json", "w", encoding="utf-8") as f:
            json.dump(save_info, f, ensure_ascii=False, indent=2)

        return str(slot_dir)

    def load_game(self, slot: int) -> bool:
        """
        加载游戏

        Args:
            slot: 存档槽位

        Returns:
            是否成功加载
        """
        slot_dir = self.save_dir / f"slot{slot}"
        if not slot_dir.exists():
            return False

        # 加载王国状态
        kingdom_file = slot_dir / "kingdom.json"
        if kingdom_file.exists():
            with open(kingdom_file, "r", encoding="utf-8") as f:
                kingdom = json.load(f)
            self.save_kingdom(kingdom)

        # 加载关系状态
        relations_file = slot_dir / "relations.json"
        if relations_file.exists():
            with open(relations_file, "r", encoding="utf-8") as f:
                relations = json.load(f)
            self.save_relations(relations)

        return True

    def list_saves(self) -> list:
        """
        列出所有存档

        Returns:
            存档列表
        """
        saves = []
        for slot_dir in self.save_dir.iterdir():
            if slot_dir.is_dir() and slot_dir.name.startswith("slot"):
                info_file = slot_dir / "info.json"
                if info_file.exists():
                    with open(info_file, "r", encoding="utf-8") as f:
                        info = json.load(f)
                    saves.append(info)
        return sorted(saves, key=lambda x: x["slot"])


if __name__ == "__main__":
    # 测试
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manager = StateManager(skill_dir)

    # 加载默认状态
    kingdom = manager.load_kingdom()
    print("初始状态:")
    print(f"  朝代: {kingdom['dynasty_name']}")
    print(f"  经济: {kingdom['stats']['economy']}")
    print(f"  军事: {kingdom['stats']['military']}")
    print(f"  国库: {kingdom['treasury']}")

    # 推进一天
    kingdom = manager.advance_day()
    print("\n推进一天后:")
    print(f"  日期: {kingdom['current_year']}年{kingdom['current_month']}月{kingdom['current_day']}日")
    print(f"  国库: {kingdom['treasury']}")
