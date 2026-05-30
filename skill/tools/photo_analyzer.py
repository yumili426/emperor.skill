#!/usr/bin/env python3
"""
照片 EXIF 分析器
"""

import os
import shutil
import struct
from pathlib import Path
from typing import Dict, Optional, Tuple


class PhotoAnalyzer:
    """照片 EXIF 分析器"""

    def __init__(self, skill_dir: str):
        """
        初始化分析器

        Args:
            skill_dir: skill 目录路径
        """
        self.skill_dir = Path(skill_dir)
        self.court_dir = self.skill_dir / "court"

    def analyze(self, file_path: str, slug: str) -> Dict:
        """
        分析照片 EXIF 信息

        Args:
            file_path: 文件路径
            slug: 角色标识

        Returns:
            EXIF 元数据字典
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return {}

        # 验证文件格式
        ext = file_path.suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            return {}

        # 归档文件
        archive_dir = self.court_dir / slug / "memories" / "photos"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / file_path.name
        if not archive_path.exists():
            shutil.copy2(file_path, archive_path)

        # 分析 EXIF
        if ext in (".jpg", ".jpeg"):
            metadata = self._analyze_jpeg(file_path)
        else:
            metadata = self._analyze_png(file_path)

        metadata["file_path"] = str(archive_path)
        metadata["file_name"] = file_path.name
        metadata["file_size"] = os.path.getsize(file_path)

        return metadata

    def _analyze_jpeg(self, file_path: Path) -> Dict:
        """
        分析 JPEG 照片 EXIF

        Args:
            file_path: 文件路径

        Returns:
            EXIF 数据字典
        """
        metadata = {}

        try:
            with open(file_path, "rb") as f:
                data = f.read()

            # 查找 EXIF APP1 标记
            i = 0
            while i < len(data) - 4:
                if data[i] == 0xFF and data[i + 1] == 0xE1:
                    # EXIF APP1 标记
                    segment_length = struct.unpack(">H", data[i + 2 : i + 4])[0]
                    exif_data = data[i + 4 : i + 2 + segment_length]

                    # 检查 EXIF 标识
                    if exif_data[:6] == b"Exif\x00\x00":
                        tiff_data = exif_data[6:]
                        metadata.update(self._parse_exif_tiff(tiff_data))
                    break
                elif data[i] == 0xFF and data[i + 1] in (0xD8, 0xD9):
                    i += 2
                elif data[i] == 0xFF and data[i + 1] != 0x00:
                    segment_length = struct.unpack(">H", data[i + 2 : i + 4])[0]
                    i += 2 + segment_length
                else:
                    i += 1
        except Exception:
            pass

        return metadata

    def _parse_exif_tiff(self, data: bytes) -> Dict:
        """
        解析 EXIF TIFF 数据

        Args:
            data: TIFF 数据

        Returns:
            EXIF 字段字典
        """
        metadata = {}

        if len(data) < 8:
            return metadata

        # 字节序
        if data[:2] == b"II":
            endian = "<"
        elif data[:2] == b"MM":
            endian = ">"
        else:
            return metadata

        # IFD0 偏移
        ifd0_offset = struct.unpack(f"{endian}I", data[4:8])[0]

        # 解析 IFD0
        ifd0 = self._parse_ifd(data, ifd0_offset, endian)
        metadata.update(ifd0)

        # 查找 GPS IFD
        for tag_id, value in ifd0.items():
            if tag_id == 0x8825:  # GPSInfo
                gps_offset = value
                gps_data = self._parse_gps_ifd(data, gps_offset, endian)
                if gps_data:
                    metadata["gps"] = gps_data

        return metadata

    def _parse_ifd(self, data: bytes, offset: int, endian: str) -> Dict:
        """
        解析 IFD（图像文件目录）

        Args:
            data: 数据
            offset: IFD 偏移
            endian: 字节序

        Returns:
            IFD 字段字典
        """
        result = {}

        try:
            if offset + 2 > len(data):
                return result

            tag_count = struct.unpack(f"{endian}H", data[offset : offset + 2])[0]

            for i in range(tag_count):
                tag_offset = offset + 2 + i * 12
                if tag_offset + 12 > len(data):
                    break

                tag_id = struct.unpack(f"{endian}H", data[tag_offset : tag_offset + 2])[0]
                tag_type = struct.unpack(f"{endian}H", data[tag_offset + 2 : tag_offset + 4])[0]
                value_count = struct.unpack(
                    f"{endian}I", data[tag_offset + 4 : tag_offset + 8]
                )[0]
                value_offset = struct.unpack(
                    f"{endian}I", data[tag_offset + 8 : tag_offset + 12]
                )[0]

                value = self._read_tag_value(data, tag_type, value_count, value_offset, endian)
                if value is not None:
                    result[tag_id] = value
        except Exception:
            pass

        return result

    def _read_tag_value(
        self, data: bytes, tag_type: int, value_count: int, value_offset: int, endian: str
    ) -> Optional[object]:
        """
        读取标签值

        Args:
            data: 数据
            tag_type: 标签类型
            value_count: 值数量
            value_offset: 值偏移
            endian: 字节序

        Returns:
            标签值
        """
        try:
            # 类型 2: ASCII
            if tag_type == 2:
                if value_count <= 4:
                    value = data[value_offset : value_offset + value_count]
                else:
                    value = data[value_offset : value_offset + value_count]
                return value.rstrip(b"\x00").decode("ascii", errors="ignore")

            # 类型 3: SHORT
            elif tag_type == 3:
                if value_count == 1:
                    return struct.unpack(f"{endian}H", data[value_offset : value_offset + 2])[0]
                else:
                    return [
                        struct.unpack(f"{endian}H", data[value_offset + i * 2 : value_offset + i * 2 + 2])[0]
                        for i in range(value_count)
                    ]

            # 类型 4: LONG
            elif tag_type == 4:
                if value_count == 1:
                    return struct.unpack(f"{endian}I", data[value_offset : value_offset + 4])[0]
                else:
                    return [
                        struct.unpack(f"{endian}I", data[value_offset + i * 4 : value_offset + i * 4 + 4])[0]
                        for i in range(value_count)
                    ]

            # 类型 5: RATIONAL
            elif tag_type == 5:
                if value_count == 1:
                    num = struct.unpack(f"{endian}I", data[value_offset : value_offset + 4])[0]
                    den = struct.unpack(f"{endian}I", data[value_offset + 4 : value_offset + 8])[0]
                    return num / den if den != 0 else 0
                else:
                    return [
                        struct.unpack(f"{endian}I", data[value_offset + i * 8 : value_offset + i * 8 + 4])[0]
                        / struct.unpack(f"{endian}I", data[value_offset + i * 8 + 4 : value_offset + i * 8 + 8])[0]
                        for i in range(value_count)
                    ]
        except Exception:
            pass

        return None

    def _parse_gps_ifd(self, data: bytes, offset: int, endian: str) -> Dict:
        """
        解析 GPS IFD

        Args:
            data: 数据
            offset: GPS IFD 偏移
            endian: 字节序

        Returns:
            GPS 数据字典
        """
        gps = {}
        try:
            ifd = self._parse_ifd(data, offset, endian)

            # GPS 纬度 (0x0002) 和纬度参考 (0x0001)
            if 0x0001 in ifd and 0x0002 in ifd:
                ref = ifd[0x0001]
                coords = ifd[0x0002]
                if isinstance(coords, list) and len(coords) == 3:
                    lat = coords[0] + coords[1] / 60 + coords[2] / 3600
                    if ref == "S":
                        lat = -lat
                    gps["latitude"] = lat

            # GPS 经度 (0x0004) 和经度参考 (0x0003)
            if 0x0003 in ifd and 0x0004 in ifd:
                ref = ifd[0x0003]
                coords = ifd[0x0004]
                if isinstance(coords, list) and len(coords) == 3:
                    lon = coords[0] + coords[1] / 60 + coords[2] / 3600
                    if ref == "W":
                        lon = -lon
                    gps["longitude"] = lon
        except Exception:
            pass

        return gps

    def _analyze_png(self, file_path: Path) -> Dict:
        """
        分析 PNG 照片元数据

        Args:
            file_path: 文件路径

        Returns:
            元数据字典
        """
        metadata = {}

        try:
            with open(file_path, "rb") as f:
                # PNG 签名
                signature = f.read(8)
                if signature != b"\x89PNG\r\n\x1a\n":
                    return metadata

                # 读取 chunks
                while True:
                    length_bytes = f.read(4)
                    if len(length_bytes) < 4:
                        break

                    chunk_length = struct.unpack(">I", length_bytes)[0]
                    chunk_type = f.read(4)

                    if chunk_type == b"IHDR":
                        width = struct.unpack(">I", f.read(4))[0]
                        height = struct.unpack(">I", f.read(4))[0]
                        metadata["width"] = width
                        metadata["height"] = height
                        f.read(chunk_length - 8)
                    elif chunk_type in (b"tEXt", b"iTXt"):
                        chunk_data = f.read(chunk_length)
                        # 解析文本块
                        null_pos = chunk_data.find(b"\x00")
                        if null_pos != -1:
                            key = chunk_data[:null_pos].decode("ascii", errors="ignore")
                            value = chunk_data[null_pos + 1 :].decode("utf-8", errors="ignore")
                            metadata[key] = value
                    else:
                        f.read(chunk_length)

                    # CRC
                    f.read(4)
        except Exception:
            pass

        return metadata

    def extract_readable_metadata(self, metadata: Dict) -> str:
        """
        提取可读的元数据文本

        Args:
            metadata: 原始元数据

        Returns:
            格式化的元数据文本
        """
        lines = []

        # 常见 EXIF 标签映射
        tag_names = {
            0x010F: "相机制造商",
            0x0110: "相机型号",
            0x9003: "拍摄时间",
            0x9004: "数字化时间",
            0x829A: "曝光时间",
            0x829D: "光圈值",
            0xA002: "像素宽度",
            0xA003: "像素高度",
        }

        for tag_id, name in tag_names.items():
            if tag_id in metadata:
                lines.append(f"{name}: {metadata[tag_id]}")

        if "gps" in metadata:
            gps = metadata["gps"]
            if "latitude" in gps:
                lines.append(f"纬度: {gps['latitude']:.6f}")
            if "longitude" in gps:
                lines.append(f"经度: {gps['longitude']:.6f}")

        # PNG 文本元数据
        for key in ("Description", "Author", "Copyright", "Comment"):
            if key in metadata:
                lines.append(f"{key}: {metadata[key]}")

        return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    analyzer = PhotoAnalyzer(skill_dir)

    print("照片 EXIF 分析器")
    print(f"Court 目录: {analyzer.court_dir}")
    print("支持格式: JPEG (EXIF), PNG (tEXt/iTXt)")
