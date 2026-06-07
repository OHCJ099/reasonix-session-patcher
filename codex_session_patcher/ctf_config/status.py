# -*- coding: utf-8 -*-
"""
CTF 配置状态检查
"""

import os
import re
import json
from dataclasses import dataclass
from typing import List, Optional

CTF_MARKER = 'managed-by: codex-session-patcher:ctf'


def expand_user_path(path: str) -> str:
    """跨平台展开 ~。

    Windows 的 os.path.expanduser 通常优先 USERPROFILE，忽略测试/脚本临时设置的
    HOME。上游测试和不少跨平台部署脚本会通过 HOME 重定向配置根目录，因此这里
    显式优先 HOME，避免 Codex/Claude/OpenCode 配置误写到真实用户目录。
    """
    if path == "~":
        return os.environ.get("HOME") or os.path.expanduser(path)
    if path.startswith("~/") or path.startswith("~\\"):
        home = os.environ.get("HOME")
        if home:
            return os.path.normpath(os.path.join(home, path[2:]))
    return os.path.normpath(os.path.expanduser(path))


DEFAULT_CLAUDE_CTF_WORKSPACE = expand_user_path("~/.claude-ctf-workspace")
DEFAULT_OPENCODE_CTF_WORKSPACE = expand_user_path("~/.opencode-ctf-workspace")


GLOBAL_MARKER = '# __csp_ctf_global__'
DEFAULT_CODEX_PROMPT_FILE = "ctf_optimized.md"
REASONIX_MARKER = '# __rsp_ctf__'


def default_reasonix_dir() -> str:
    return os.path.join(os.environ.get("APPDATA", expand_user_path("~")), "reasonix")


def default_reasonix_global_config() -> str:
    return os.path.join(default_reasonix_dir(), "config.toml")


def default_reasonix_prompt_path() -> str:
    return os.path.join(default_reasonix_dir(), "prompts", DEFAULT_CODEX_PROMPT_FILE)


def detect_reasonix_profile_workspace() -> Optional[str]:
    """从 Reasonix Desktop 最近会话中识别当前项目工作区。

    Reasonix Desktop 会在 `%APPDATA%/reasonix/sessions/*.jsonl.meta` 里记录
    `workspace_root`。Profile 模式应当写入这个工作区下的 `reasonix.toml`，
    而不是另造一个独立启动目录。
    """
    sessions_dir = os.path.join(default_reasonix_dir(), "sessions")
    if not os.path.isdir(sessions_dir):
        return None

    try:
        meta_files = [
            os.path.join(sessions_dir, name)
            for name in os.listdir(sessions_dir)
            if name.endswith(".jsonl.meta")
        ]
    except OSError:
        return None

    meta_files.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    for meta_path in meta_files:
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            workspace = meta.get("workspace_root") or meta.get("cwd") or meta.get("workspace")
            if workspace:
                workspace = os.path.normpath(workspace)
                if os.path.isdir(workspace):
                    return workspace
        except Exception:
            continue
    return None


def default_reasonix_profile_workspace() -> str:
    return detect_reasonix_profile_workspace() or os.path.join(
        os.environ.get("APPDATA", expand_user_path("~")),
        "reasonix-ctf-workspace",
    )


def reasonix_profile_prompt_path_for_workspace(workspace: str) -> str:
    return os.path.join(workspace, ".reasonix", "prompts", DEFAULT_CODEX_PROMPT_FILE)


@dataclass
class CTFStatus:
    """CTF 配置状态"""
    # Codex
    installed: bool = False
    config_exists: bool = False
    prompt_exists: bool = False
    profile_available: bool = False
    global_installed: bool = False
    injection_mode: str = "none"
    global_injection_mode: str = "none"
    config_path: Optional[str] = None
    prompt_path: Optional[str] = None
    # Claude Code
    claude_installed: bool = False
    claude_workspace_exists: bool = False
    claude_prompt_exists: bool = False
    claude_workspace_path: Optional[str] = None
    claude_prompt_path: Optional[str] = None
    # OpenCode
    opencode_installed: bool = False
    opencode_workspace_exists: bool = False
    opencode_prompt_exists: bool = False
    opencode_workspace_path: Optional[str] = None
    opencode_prompt_path: Optional[str] = None
    # Reasonix Desktop
    reasonix_profile_installed: bool = False
    reasonix_profile_workspace_exists: bool = False
    reasonix_profile_prompt_exists: bool = False
    reasonix_profile_workspace_path: Optional[str] = None
    reasonix_profile_config_path: Optional[str] = None
    reasonix_profile_prompt_path: Optional[str] = None
    reasonix_profile_launcher_path: Optional[str] = None
    reasonix_global_installed: bool = False
    reasonix_global_config_exists: bool = False
    reasonix_global_config_path: Optional[str] = None
    reasonix_global_prompt_path: Optional[str] = None
    reasonix_global_injection_mode: str = "none"


def _top_level_lines(content: str) -> List[str]:
    """返回第一个 TOML section 前的顶层行。"""
    lines = content.splitlines()
    section_start = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('[') and not stripped.startswith('#'):
            section_start = index
            break
    return lines[:section_start]


def _has_top_level_key(content: str, key: str) -> bool:
    """检查未注释的顶层 key。"""
    pattern = re.compile(rf'^\s*{re.escape(key)}\s*=')
    return any(pattern.match(line) for line in _top_level_lines(content))


def _get_top_level_string_value(content: str, key: str) -> Optional[str]:
    """读取未注释的顶层字符串值。"""
    pattern = re.compile(rf'^\s*{re.escape(key)}\s*=\s*"([^"]+)"')
    for line in _top_level_lines(content):
        match = pattern.match(line)
        if match:
            return match.group(1)
    return None


def _default_codex_prompt_path(codex_dir: str) -> str:
    return os.path.join(codex_dir, "prompts", DEFAULT_CODEX_PROMPT_FILE)


def _managed_global_block(content: str) -> str:
    """返回全局模式标记后的受管理顶层配置块。"""
    marker_index = content.find(GLOBAL_MARKER)
    if marker_index < 0:
        return ""

    block_lines = []
    for line in content[marker_index:].splitlines():
        stripped = line.strip()
        if block_lines and stripped.startswith('[') and not stripped.startswith('#'):
            break
        block_lines.append(line)
    return "\n".join(block_lines)


def check_ctf_status() -> CTFStatus:
    """
    检查 CTF 配置的安装状态（Codex + Claude Code）

    Returns:
        CTFStatus: 配置状态信息
    """
    # ── Codex 检查 ──
    codex_dir = expand_user_path("~/.codex")
    base_config_path = os.path.join(codex_dir, "config.toml")
    profile_config_path = os.path.join(codex_dir, "ctf.config.toml")

    status = CTFStatus(
        config_path=profile_config_path,
        prompt_path=None,
    )

    if os.path.exists(profile_config_path):
        try:
            with open(profile_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            status.config_exists = True
            if _has_top_level_key(content, "developer_instructions"):
                status.profile_available = True
                status.prompt_exists = True
                status.injection_mode = "append"
                default_prompt_path = _default_codex_prompt_path(codex_dir)
                if os.path.exists(default_prompt_path):
                    status.prompt_path = default_prompt_path
            else:
                prompt_path = _get_top_level_string_value(content, "model_instructions_file")
                if prompt_path:
                    status.profile_available = True
                    status.injection_mode = "replace"
                    status.prompt_path = expand_user_path(prompt_path)
        except Exception:
            pass

    if os.path.exists(base_config_path):
        try:
            with open(base_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if GLOBAL_MARKER in content:
                    status.global_installed = True
                    managed_content = _managed_global_block(content)
                    if _has_top_level_key(managed_content, "developer_instructions"):
                        status.global_injection_mode = "append"
                    elif _has_top_level_key(managed_content, "model_instructions_file"):
                        status.global_injection_mode = "replace"
        except Exception:
            pass

    if status.prompt_path and os.path.exists(status.prompt_path):
        status.prompt_exists = True

    status.installed = status.config_exists and status.prompt_exists and status.profile_available

    # ── Claude Code 检查 ──
    workspace_path = DEFAULT_CLAUDE_CTF_WORKSPACE
    claude_prompt_path = os.path.join(workspace_path, ".claude", "CLAUDE.md")

    status.claude_workspace_path = workspace_path
    status.claude_prompt_path = claude_prompt_path
    status.claude_workspace_exists = os.path.isdir(workspace_path)

    if os.path.exists(claude_prompt_path):
        try:
            with open(claude_prompt_path, 'r', encoding='utf-8') as f:
                content = f.read(500)  # 只需读开头
                if CTF_MARKER in content:
                    status.claude_prompt_exists = True
        except Exception:
            pass

    status.claude_installed = status.claude_workspace_exists and status.claude_prompt_exists

    # ── OpenCode 检查 ──
    opencode_workspace = DEFAULT_OPENCODE_CTF_WORKSPACE
    opencode_agents_path = os.path.join(opencode_workspace, "AGENTS.md")

    status.opencode_workspace_path = opencode_workspace
    status.opencode_prompt_path = opencode_agents_path
    status.opencode_workspace_exists = os.path.isdir(opencode_workspace)

    if os.path.exists(opencode_agents_path):
        try:
            with open(opencode_agents_path, 'r', encoding='utf-8') as f:
                content = f.read(500)
                if CTF_MARKER in content:
                    status.opencode_prompt_exists = True
        except Exception:
            pass

    status.opencode_installed = status.opencode_workspace_exists and status.opencode_prompt_exists

    # ── Reasonix Desktop 检查 ──
    reasonix_workspace = default_reasonix_profile_workspace()
    reasonix_profile_config = os.path.join(reasonix_workspace, "reasonix.toml")
    reasonix_profile_prompt = reasonix_profile_prompt_path_for_workspace(reasonix_workspace)
    reasonix_global_config = default_reasonix_global_config()
    reasonix_global_prompt = default_reasonix_prompt_path()

    status.reasonix_profile_workspace_path = reasonix_workspace
    status.reasonix_profile_config_path = reasonix_profile_config
    status.reasonix_profile_prompt_path = reasonix_profile_prompt
    status.reasonix_profile_launcher_path = None
    status.reasonix_profile_workspace_exists = os.path.isdir(reasonix_workspace)
    status.reasonix_profile_prompt_exists = os.path.exists(reasonix_profile_prompt)
    if os.path.exists(reasonix_profile_config):
        try:
            with open(reasonix_profile_config, 'r', encoding='utf-8') as f:
                status.reasonix_profile_installed = REASONIX_MARKER in f.read()
        except Exception:
            pass

    status.reasonix_global_config_path = reasonix_global_config
    status.reasonix_global_prompt_path = reasonix_global_prompt
    status.reasonix_global_config_exists = os.path.exists(reasonix_global_config)
    if os.path.exists(reasonix_global_config):
        try:
            with open(reasonix_global_config, 'r', encoding='utf-8') as f:
                content = f.read()
            if REASONIX_MARKER in content:
                status.reasonix_global_installed = True
                status.reasonix_global_injection_mode = "system_prompt_file"
        except Exception:
            pass

    return status
