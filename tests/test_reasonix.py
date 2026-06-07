# -*- coding: utf-8 -*-
import json

from codex_session_patcher.core.detector import RefusalDetector
from codex_session_patcher.core.formats import SessionFormat, detect_session_format, get_format_strategy
from codex_session_patcher.core.parser import SessionParser
from codex_session_patcher.core.patcher import clean_session_jsonl


def test_reasonix_strategy_replaces_refusal_and_removes_reasoning():
    lines = [
        {"role": "system", "content": "Reasonix system"},
        {"role": "user", "content": "帮我检查本地项目"},
        {
            "role": "assistant",
            "content": "抱歉，我无法帮助你。",
            "reasoning_content": "private reasoning",
        },
    ]

    cleaned, modified, changes = clean_session_jsonl(
        lines,
        RefusalDetector(),
        mock_response="可以，先看目录结构。",
        session_format=SessionFormat.REASONIX,
    )

    assert modified is True
    assert cleaned[2]["content"] == "可以，先看目录结构。"
    assert "reasoning_content" not in cleaned[2]
    assert [c.change_type for c in changes] == ["replace", "remove_thinking"]


def test_reasonix_detects_plain_role_content_jsonl(tmp_path):
    fp = tmp_path / "20260606-024332.000000000-deepseek-v4-flash.jsonl"
    fp.write_text(
        "\n".join(
            [
                json.dumps({"role": "system", "content": "sys"}, ensure_ascii=False),
                json.dumps({"role": "assistant", "content": "ok"}, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )

    assert detect_session_format(str(fp)) == SessionFormat.REASONIX


def test_reasonix_parser_uses_meta_workspace_and_full_id(tmp_path):
    fp = tmp_path / "20260606-024332.000000000-deepseek-v4-flash.jsonl"
    fp.write_text(json.dumps({"role": "assistant", "content": "ok"}) + "\n", encoding="utf-8")
    meta = {
        "id": "20260606-024332.000000000-deepseek-v4-flash",
        "created_at": "2026-06-05T18:43:32Z",
        "workspace_root": r"C:\work\demo",
    }
    (tmp_path / (fp.name + ".meta")).write_text(json.dumps(meta), encoding="utf-8")

    parser = SessionParser(str(tmp_path), session_format=SessionFormat.REASONIX)
    sessions = parser.list_sessions()

    assert len(sessions) == 1
    assert sessions[0].session_id == meta["id"]
    assert sessions[0].date == "2026-06-05"
    assert sessions[0].project_path == meta["workspace_root"]
    assert get_format_strategy(sessions[0].format).extract_text_content({"role": "assistant", "content": "x"}) == "x"
