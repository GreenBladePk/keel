import json
import os

ADAPTER = os.path.join(os.path.dirname(__file__), "..", "adapters", "claude-code")


def test_settings_fragment_declares_both_hooks():
    with open(os.path.join(ADAPTER, "settings.hooks.json")) as f:
        cfg = json.load(f)
    hooks = cfg["hooks"]
    assert "SessionStart" in hooks and "UserPromptSubmit" in hooks
    cmds = json.dumps(cfg)
    assert "session_start.sh" in cmds and "user_prompt_submit.sh" in cmds
    assert "${CLAUDE_PROJECT_DIR}" in cmds


def test_mcp_json_parses_and_points_at_keel():
    with open(os.path.join(ADAPTER, ".mcp.json")) as f:
        cfg = json.load(f)
    assert "mcpServers" in cfg and "keel" in cfg["mcpServers"]


def test_readme_and_skill_exist_nonempty():
    for name in ("README.md", "SKILL.md"):
        p = os.path.join(ADAPTER, name)
        assert os.path.getsize(p) > 200, f"{name} too small"
