#!/usr/bin/env python3
"""
QQ 聊天记录解析器
"""

import email
import logging
import os
import re
import shutil
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class QQParser:
    """QQ 聊天记录解析器"""

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
            文件格式（txt/mht）
        """
        ext = Path(file_path).suffix.lower()
        if ext == ".mht":
            return "mht"
        return "txt"

    def parse(self, file_path: str, slug: str) -> Dict:
        """
        解析 QQ 聊天记录

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
        if fmt == "mht":
            messages = self._parse_mht(file_path)
        else:
            messages = self._parse_txt(file_path)

        return {
            "messages": messages,
            "full_text": self.to_full_text(messages),
        }

    def _parse_txt(self, file_path: Path) -> List[Dict]:
        """
        解析 txt 格式 QQ 聊天记录

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

        # 模式1: 2024-01-15 14:30:22 张三(12345678)\n消息内容
        pattern1 = re.compile(
            r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)\s*\(\d+\)\n(.+?)(?=\n\d{4}[-/]|$)",
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

    def _parse_mht(self, file_path: Path) -> List[Dict]:
        """
        解析 mht 格式 QQ 聊天记录

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
                logger.error("Failed to read mht file %s: %s", file_path, e)
                return messages
        except Exception as e:
            logger.error("Failed to open file %s: %s", file_path, e)
            return messages

        # 尝试用 email 模块解析 MIME
        try:
            msg = email.message_from_string(content)
            html_content = ""
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_content += payload.decode(charset, errors="ignore")
        except Exception:
            html_content = content

        # 从 HTML 中提取聊天内容
        if html_content:
            messages = self._extract_from_html(html_content)

        return messages

    def _extract_from_html(self, html_content: str) -> List[Dict]:
        """
        从 HTML 内容中提取聊天记录

        Args:
            html_content: HTML 内容

        Returns:
            消息列表
        """
        messages = []

        # 尝试常见 QQ 导出 HTML 结构
        # 模式: <div class="msg"><div class="time">时间</div><div class="sender">发送者</div><div class="content">内容</div></div>
        pattern = re.compile(
            r'<[^>]*class=["\'](?:time|timestamp)["\'][^>]*>([^<]+)<.*?'
            r'<[^>]*class=["\'](?:sender|name|nickname)["\'][^>]*>([^<]+)<.*?'
            r'<[^>]*class=["\'](?:content|message|text)["\'][^>]*>([^<]+)<',
            re.DOTALL | re.IGNORECASE,
        )

        for m in pattern.finditer(html_content):
            messages.append(
                {
                    "timestamp": m.group(1).strip(),
                    "sender": m.group(2).strip(),
                    "message": m.group(3).strip(),
                }
            )

        # 如果没有匹配到结构化内容，尝试简单的文本提取
        if not messages:
            logger.warning("Structured HTML parsing found no messages, falling back to text extraction")
            text = re.sub(r"<[^>]+>", "\n", html_content)
            text = re.sub(r"&nbsp;", " ", text)
            text = re.sub(r"&lt;", "<", text)
            text = re.sub(r"&gt;", ">", text)
            text = re.sub(r"&amp;", "&", text)
            text = re.sub(r"\n{3,}", "\n\n", text)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            for line in lines:
                messages.append({"timestamp": "", "sender": "", "message": line})

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
    parser = QQParser(skill_dir)

    print("QQ 聊天记录解析器")
    print(f"Court 目录: {parser.court_dir}")
    print("支持格式: txt, mht")
