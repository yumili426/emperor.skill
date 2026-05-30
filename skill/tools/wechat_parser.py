#!/usr/bin/env python3
"""
微信聊天记录解析器
"""

import csv
import json
import logging
import os
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class WeChatParser:
    """微信聊天记录解析器"""

    def __init__(self, skill_dir: str):
        """
        初始化解析器

        Args:
            skill_dir: skill 目录路径
        """
        self.skill_dir = Path(skill_dir)
        self.court_dir = self.skill_dir / "court"

    def detect_format(self, file_path: str) -> str:
        """
        检测文件格式

        Args:
            file_path: 文件路径

        Returns:
            文件格式（txt/html/csv/json）
        """
        ext = Path(file_path).suffix.lower()
        format_map = {
            ".txt": "txt",
            ".html": "html",
            ".htm": "html",
            ".csv": "csv",
            ".json": "json",
        }
        return format_map.get(ext, "txt")

    def parse(self, file_path: str, slug: str) -> Dict:
        """
        解析微信聊天记录

        Args:
            file_path: 文件路径
            slug: 角色标识

        Returns:
            解析结果 {"messages": [...], "full_text": "..."}
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return {"messages": [], "full_text": ""}

        # 归档原始文件
        archive_dir = self.court_dir / slug / "memories" / "chats"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / file_path.name
        if not archive_path.exists():
            shutil.copy2(file_path, archive_path)

        # 检测格式并解析
        fmt = self.detect_format(str(file_path))
        if fmt == "html":
            messages = self._parse_html(file_path)
        elif fmt == "csv":
            messages = self._parse_csv(file_path)
        elif fmt == "json":
            messages = self._parse_json(file_path)
        else:
            messages = self._parse_txt(file_path)

        return {
            "messages": messages,
            "full_text": self.to_full_text(messages),
        }

    def _parse_txt(self, file_path: Path) -> List[Dict]:
        """
        解析 txt 格式聊天记录

        Args:
            file_path: 文件路径

        Returns:
            消息列表
        """
        messages = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
            except Exception as e:
                logger.error("Failed to read txt file %s: %s", file_path, e)
                return messages
        except Exception as e:
            logger.error("Failed to open file %s: %s", file_path, e)
            return messages

        # 模式1: 2024-01-15 14:30:22 张三\n消息内容
        pattern1 = re.compile(
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)\n(.+?)(?=\n\d{4}[-/]|$)",
            re.DOTALL,
        )

        # 模式2: 张三 2024/1/15 14:30\n消息内容
        pattern2 = re.compile(
            r"(.+?)\s+(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\n(.+?)(?=\n.+?\s+\d{4}[-/]|$)",
            re.DOTALL,
        )

        matches = list(pattern1.finditer(content))
        if matches:
            for m in matches:
                messages.append(
                    {
                        "timestamp": m.group(1).strip(),
                        "sender": m.group(2).strip(),
                        "message": m.group(3).strip(),
                    }
                )
        else:
            matches = list(pattern2.finditer(content))
            for m in matches:
                messages.append(
                    {
                        "sender": m.group(1).strip(),
                        "timestamp": m.group(2).strip(),
                        "message": m.group(3).strip(),
                    }
                )

        if not messages:
            logger.warning("TXT parsing produced no messages for %s", file_path)

        return messages

    def _parse_html(self, file_path: Path) -> List[Dict]:
        """
        解析 html 格式聊天记录

        Args:
            file_path: 文件路径

        Returns:
            消息列表
        """
        messages = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="gbk") as f:
                    content = f.read()
            except Exception as e:
                logger.error("Failed to read html file %s: %s", file_path, e)
                return messages
        except Exception as e:
            logger.error("Failed to open file %s: %s", file_path, e)
            return messages

        # 尝试提取常见 HTML 结构
        pattern = re.compile(
            r'<[^>]*class=["\'](?:time|timestamp)["\'][^>]*>([^<]+)<.*?'
            r'<[^>]*class=["\'](?:sender|name|nickname)["\'][^>]*>([^<]+)<.*?'
            r'<[^>]*class=["\'](?:content|message|text)["\'][^>]*>([^<]+)<',
            re.DOTALL | re.IGNORECASE,
        )

        for m in pattern.finditer(content):
            messages.append(
                {
                    "timestamp": m.group(1).strip(),
                    "sender": m.group(2).strip(),
                    "message": m.group(3).strip(),
                }
            )

        # 如果没有匹配到结构化内容，尝试简单的文本提取
        if not messages:
            logger.warning("Structured HTML parsing found no messages, falling back to text extraction for %s", file_path)
            text = re.sub(r"<[^>]+>", "\n", content)
            text = re.sub(r"&nbsp;", " ", text)
            text = re.sub(r"&lt;", "<", text)
            text = re.sub(r"&gt;", ">", text)
            text = re.sub(r"&amp;", "&", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            for line in lines:
                messages.append(
                    {"timestamp": "", "sender": "", "message": line}
                )

        return messages

    def _parse_csv(self, file_path: Path) -> List[Dict]:
        messages = []
        encodings = ["utf-8", "gbk", "utf-8-sig"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        msg = {
                            "timestamp": row.get("time", row.get("timestamp", row.get("时间", row.get("日期", "")))),
                            "sender": row.get("sender", row.get("name", row.get("发送者", row.get("昵称", "")))),
                            "message": row.get("message", row.get("content", row.get("内容", row.get("消息", "")))),
                        }
                        if msg["message"]:
                            messages.append(msg)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.error("Failed to parse csv file %s: %s", file_path, e)
                break

        if not messages:
            logger.warning("CSV parsing produced no messages for %s", file_path)

        return messages

    def _parse_json(self, file_path: Path) -> List[Dict]:
        """
        解析 json 格式聊天记录

        Args:
            file_path: 文件路径

        Returns:
            消息列表
        """
        messages = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in file %s: %s", file_path, e)
            return messages
        except Exception as e:
            logger.error("Failed to read JSON file %s: %s", file_path, e)
            return messages

        # 支持数组格式
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    msg = {
                        "timestamp": str(
                            item.get(
                                "time",
                                item.get(
                                    "timestamp",
                                    item.get("时间", item.get("date", "")),
                                ),
                            )
                        ),
                        "sender": str(
                            item.get(
                                "sender",
                                item.get(
                                    "name",
                                    item.get("发送者", item.get("nickname", "")),
                                ),
                            )
                        ),
                        "message": str(
                            item.get(
                                "message",
                                item.get(
                                    "content",
                                    item.get("内容", item.get("text", "")),
                                ),
                            )
                        ),
                    }
                    if msg["message"]:
                        messages.append(msg)

        # 支持嵌套格式 {"messages": [...]} 或 {"data": [...]}
        elif isinstance(data, dict):
            inner = data.get("messages", data.get("data", data.get("list", [])))
            if isinstance(inner, list):
                for item in inner:
                    if isinstance(item, dict):
                        msg = {
                            "timestamp": str(
                                item.get("time", item.get("timestamp", ""))
                            ),
                            "sender": str(
                                item.get("sender", item.get("name", ""))
                            ),
                            "message": str(
                                item.get("message", item.get("content", ""))
                            ),
                        }
                        if msg["message"]:
                            messages.append(msg)

        return messages

    def to_full_text(self, messages: List[Dict]) -> str:
        """
        将消息列表转换为可读文本

        Args:
            messages: 消息列表

        Returns:
            格式化后的文本
        """
        lines = []
        for msg in messages:
            ts = msg.get("timestamp", "")
            sender = msg.get("sender", "")
            content = msg.get("message", "")
            if ts:
                lines.append(f"[{ts}] {sender}: {content}")
            else:
                lines.append(f"{sender}: {content}")
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = WeChatParser(skill_dir)

    print("微信聊天记录解析器")
    print(f"Court 目录: {parser.court_dir}")
    print("支持格式: txt, html, csv, json")
