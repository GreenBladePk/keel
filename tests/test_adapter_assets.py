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


def test_settings_fragment_declares_pretooluse():
    with open(os.path.join(ADAPTER, "settings.hooks.json")) as f:
        cfg = json.load(f)
    assert "PreToolUse" in cfg["hooks"]
    pre = json.dumps(cfg["hooks"]["PreToolUse"])
    assert "pre_tool_use.sh" in pre and "Edit" in pre


def test_scopes_example_parses():
    p = os.path.join(ADAPTER, ".keel", "scopes.example.json")
    data = json.load(open(p))
    assert isinstance(data, list) and data and "pattern" in data[0] and "scope_tags" in data[0]


def test_settings_fragment_declares_posttooluse():
    with open(os.path.join(ADAPTER, "settings.hooks.json")) as f:
        cfg = json.load(f)
    assert "PostToolUse" in cfg["hooks"]
    assert "post_tool_use.sh" in json.dumps(cfg["hooks"]["PostToolUse"])
