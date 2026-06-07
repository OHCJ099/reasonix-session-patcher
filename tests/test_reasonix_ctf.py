# -*- coding: utf-8 -*-
import os
from pathlib import Path


def test_reasonix_profile_installer_writes_reasonix_toml(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path / 'AppData'))
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'LocalAppData'))
    from codex_session_patcher.ctf_config.installer import ReasonixCTFInstaller
    from codex_session_patcher.ctf_config.status import check_ctf_status

    installer = ReasonixCTFInstaller()
    ok, msg = installer.install(custom_prompt='Reasonix CTF Prompt')
    assert ok, msg

    config = Path(installer.profile_config_path)
    prompt = Path(installer.profile_prompt_path)
    launcher = Path(installer.profile_launcher_path)
    assert config.exists()
    assert prompt.read_text(encoding='utf-8') == 'Reasonix CTF Prompt'
    text = config.read_text(encoding='utf-8')
    assert '[agent]' in text
    assert 'system_prompt_file = "prompts/ctf_optimized.md"' in text
    assert launcher.exists()
    launcher_text = launcher.read_text(encoding='ascii')
    assert 'taskkill /IM reasonix-desktop.exe /F' in launcher_text
    assert 'start "" /D "%~dp0"' in launcher_text

    status = check_ctf_status()
    assert status.reasonix_profile_installed is True
    assert status.reasonix_profile_prompt_exists is True
    assert status.reasonix_profile_config_path == str(config)

    ok, msg = installer.uninstall()
    assert ok, msg
    assert check_ctf_status().reasonix_profile_installed is False


def test_reasonix_global_installer_injects_appdata_config(tmp_path, monkeypatch):
    appdata = tmp_path / 'AppData'
    monkeypatch.setenv('APPDATA', str(appdata))
    from codex_session_patcher.ctf_config.installer import ReasonixCTFInstaller
    from codex_session_patcher.ctf_config.status import check_ctf_status

    reasonix_dir = appdata / 'reasonix'
    reasonix_dir.mkdir(parents=True)
    config = reasonix_dir / 'config.toml'
    config.write_text('config_version = 2\n\n[agent]\nmax_steps = 0\n', encoding='utf-8')

    installer = ReasonixCTFInstaller()
    ok, msg = installer.install_global(custom_prompt='Reasonix Global Prompt')
    assert ok, msg

    text = config.read_text(encoding='utf-8')
    assert '[agent]' in text
    assert 'system_prompt_file' in text
    assert '.codex' not in text
    assert 'reasonix' in text.lower()
    assert Path(installer.global_prompt_path).read_text(encoding='utf-8') == 'Reasonix Global Prompt'

    status = check_ctf_status()
    assert status.reasonix_global_installed is True
    assert status.reasonix_global_config_path == str(config)

    ok, msg = installer.uninstall_global()
    assert ok, msg
    assert 'system_prompt_file' not in config.read_text(encoding='utf-8')
    assert check_ctf_status().reasonix_global_installed is False
