# Reasonix Session Patcher

本目录是基于 `ryfineZ/codex-session-patcher` 的 Reasonix Desktop 适配版，重点适配本机桌面版会话，而不是旧版 `manager.html/server.py` 管理器。

## 本机适配点

- 默认扫描：`%APPDATA%\reasonix\sessions`
- 支持 Reasonix Desktop JSONL：顶层 `role/content`，可清理同一行内的 `reasoning_content`
- 读取旁路元数据：`*.jsonl.meta`，用于显示工作区路径与完整会话 ID
- Web UI 默认优先显示 `Reasonix Desktop` 标签页
- 独立配置：`%APPDATA%\reasonix-session-patcher\config.json`，不复用旧版 `%APPDATA%\reasonix\sessions\manager.html/server.py`
- 保留上游 Codex / Claude Code / OpenCode 兼容能力

## 启动

双击：

```bat
G:\codex-session-patcher-reasonix\start_reasonix_session_patcher.bat
```

或命令行：

```powershell
cd /d G:\codex-session-patcher-reasonix
.\.venv\Scripts\python.exe -m codex_session_patcher.cli --web --host 127.0.0.1 --port 47833
```

访问：`http://127.0.0.1:47833/`

## CLI 快速预览

```powershell
cd /d G:\codex-session-patcher-reasonix
.\.venv\Scripts\python.exe -m codex_session_patcher.cli --format reasonix --latest --dry-run --show-content
```

## 说明

工具只读取/写入 Reasonix 会话文件和自身配置/备份，不读取 `credentials`、浏览器 Login Data 等敏感凭据文件。清理前会为会话 JSONL 创建 `.bak` 备份。
