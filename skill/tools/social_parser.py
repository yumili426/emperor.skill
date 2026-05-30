#!/usr/bin/env python3
"""
社交媒体截图解析器
"""

import os
import shutil
import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SocialParser:
    """社交媒体截图解析器"""

    def __init__(self, skill_dir: str):
        """
        初始化解析器

        Args:
            skill_dir: skill 目录路径
        """
        self.skill_dir = Path(skill_dir)
        self.court_dir = self.skill_dir / "court"

    def parse(self, file_path: str, slug: str) -> Dict:
        """
        解析社交媒体截图

        Args:
            file_path: 文件路径
            slug: 角色标识

        Returns:
            解析结果 {"file_path", "file_size", "width", "height", "format"}
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return {}

        # 验证文件格式
        ext = file_path.suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg"):
            return {}

        # 归档文件
        archive_dir = self.court_dir / slug / "memories" / "social"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / file_path.name
        if not archive_path.exists():
            shutil.copy2(file_path, archive_path)

        # 获取文件信息
        file_size = os.path.getsize(file_path)

        # 读取图片尺寸
        if ext == ".png":
            width, height = self._read_png_dimensions(file_path)
        elif ext in (".jpg", ".jpeg"):
            width, height = self._read_jpeg_dimensions(file_path)
        else:
            width, height = None, None

        return {
            "file_path": str(archive_path),
            "file_size": file_size,
            "width": width,
            "height": height,
            "format": ext.lstrip("."),
        }

    def list_screenshots(self, slug: str) -> List[Dict]:
        """
        列出角色的所有社交媒体截图

        Args:
            slug: 角色标识

        Returns:
            截图元数据列表
        """
        social_dir = self.court_dir / slug / "memories" / "social"
        if not social_dir.exists():
            return []

        screenshots = []
        for item in social_dir.iterdir():
            if item.is_file() and item.suffix.lower() in (".png", ".jpg", ".jpeg"):
                file_size = os.path.getsize(item)
                ext = item.suffix.lower()

                if ext == ".png":
                    width, height = self._read_png_dimensions(item)
                else:
                    width, height = self._read_jpeg_dimensions(item)

                screenshots.append(
                    {
                        "file_path": str(item),
                        "file_name": item.name,
                        "file_size": file_size,
                        "width": width,
                        "height": height,
                        "format": ext.lstrip("."),
                    }
                )

        return screenshots

    def _read_png_dimensions(self, file_path: Path) -> Tuple[Optional[int], Optional[int]]:
        """
        读取 PNG 图片尺寸

        Args:
            file_path: 文件路径

        Returns:
            (宽度, 高度) 元组
        """
        try:
            with open(file_path, "rb") as f:
                # PNG 签名
                signature = f.read(8)
                if signature != b"\x89PNG\r\n\x1a\n":
                    return None, None

                # IHDR 块
                chunk_length = struct.unpack(">I", f.read(4))[0]
                chunk_type = f.read(4)
                if chunk_type != b"IHDR":
                    return None, None

                width = struct.unpack(">I", f.read(4))[0]
                height = struct.unpack(">I", f.read(4))[0]
                return width, height
        except Exception:
            return None, None

    def _read_jpeg_dimensions(self, file_path: Path) -> Tuple[Optional[int], Optional[int]]:
        """
        读取 JPEG 图片尺寸

        Args:
            file_path: 文件路径

        Returns:
            (宽度, 高度) 元组
        """
        try:
            with open(file_path, "rb") as f:
                data = f.read()

                # 查找 SOF 标记
                i = 0
                while i < len(data) - 1:
                    if data[i] == 0xFF:
                        marker = data[i + 1]
                        # SOF0 (0xC0) 或 SOF2 (0xC2)
                        if marker in (0xC0, 0xC2):
                            # 跳过标记长度和精度
                            height = struct.unpack(">H", data[i + 5 : i + 7])[0]
                            width = struct.unpack(">H", data[i + 7 : i + 9])[0]
                            return width, height
                        # 跳过其他标记段
                        elif marker not in (0xD8, 0xD9):
                            segment_length = struct.unpack(
                                ">H", data[i + 2 : i + 4]
                            )[0]
                            i += 2 + segment_length
                        else:
                            i += 2
                    else:
                        i += 1
        except Exception:
            pass

        return None, None


if __name__ == "__main__":
    # 测试
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = SocialParser(skill_dir)

    print("社交媒体截图解析器")
    print(f"Court 目录: {parser.court_dir}")
    print("支持格式: PNG, JPEG")
