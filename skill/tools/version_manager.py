#!/usr/bin/env python3
"""
版本管理器 - 管理游戏版本和回滚
"""

import json
import shutil
from datetime import datetime
from pathlib import Path


class VersionManager:
    """版本管理器"""

    def __init__(self, skill_dir: str):
        """
        初始化版本管理器

        Args:
            skill_dir: skill 目录路径
        """
        self.skill_dir = Path(skill_dir)
        self.state_dir = self.skill_dir / "state"
        self.versions_dir = self.state_dir / "versions"

        # 确保目录存在
        self.versions_dir.mkdir(exist_ok=True)

    def create_version(self, description: str = None) -> str:
        """
        创建新版本

        Args:
            description: 版本描述

        Returns:
            版本ID
        """
        # 生成版本ID
        version_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建版本目录
        version_dir = self.versions_dir / version_id
        version_dir.mkdir(exist_ok=True)

        # 复制当前状态
        kingdom_file = self.state_dir / "kingdom.json"
        relations_file = self.state_dir / "relations.json"

        if kingdom_file.exists():
            shutil.copy(kingdom_file, version_dir / "kingdom.json")
        if relations_file.exists():
            shutil.copy(relations_file, version_dir / "relations.json")

        # 保存版本信息
        version_info = {
            "version_id": version_id,
            "description": description or f"版本 {version_id}",
            "created_at": datetime.now().isoformat()
        }
        with open(version_dir / "info.json", "w", encoding="utf-8") as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)

        return version_id

    def restore_version(self, version_id: str) -> bool:
        """
        恢复到指定版本

        Args:
            version_id: 版本ID

        Returns:
            是否成功恢复
        """
        version_dir = self.versions_dir / version_id
        if not version_dir.exists():
            return False

        # 恢复前自动创建备份
        self.create_version(f"auto-backup-before-restore-{version_id}")

        # 恢复王国状态
        kingdom_file = version_dir / "kingdom.json"
        if kingdom_file.exists():
            shutil.copy(kingdom_file, self.state_dir / "kingdom.json")

        # 恢复关系状态
        relations_file = version_dir / "relations.json"
        if relations_file.exists():
            shutil.copy(relations_file, self.state_dir / "relations.json")

        return True

    def list_versions(self) -> list:
        """
        列出所有版本

        Returns:
            版本列表
        """
        versions = []
        for version_dir in self.versions_dir.iterdir():
            if version_dir.is_dir():
                info_file = version_dir / "info.json"
                if info_file.exists():
                    with open(info_file, "r", encoding="utf-8") as f:
                        info = json.load(f)
                    versions.append(info)
        return sorted(versions, key=lambda x: x["version_id"], reverse=True)

    def delete_version(self, version_id: str) -> bool:
        """
        删除指定版本

        Args:
            version_id: 版本ID

        Returns:
            是否成功删除
        """
        version_dir = self.versions_dir / version_id
        if not version_dir.exists():
            return False

        shutil.rmtree(version_dir)
        return True


if __name__ == "__main__":
    # 测试
    import os
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manager = VersionManager(skill_dir)

    # 创建版本
    version_id = manager.create_version("测试版本")
    print(f"创建版本: {version_id}")

    # 列出版本
    versions = manager.list_versions()
    print(f"版本数量: {len(versions)}")
    for v in versions:
        print(f"  - {v['version_id']}: {v['description']}")
