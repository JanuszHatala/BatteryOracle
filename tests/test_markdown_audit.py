import pytest
import db
import llm_manager
import parser


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test_markdown_audit.db"))
    db.init_db()

def test_profile_audit_prompt_enforces_markdown_standards():
    prompt = llm_manager.get_prompt_template("profile_audit")
    assert "```bash" in prompt
    assert "GitHub Flavored Markdown" in prompt or "GFM" in prompt
    assert "pipe table" in prompt

def test_profile_comparison_prompt_enforces_markdown_standards():
    prompt = llm_manager.get_prompt_template("profile_comparison")
    assert "```bash" in prompt
    assert "GitHub Flavored Markdown" in prompt or "GFM" in prompt
    assert "pipe table" in prompt

def test_sanitize_ai_output_preserves_fenced_code_blocks_and_tables():
    raw_markdown = (
        "### 1. Header\n\n"
        "| Task | Action | Impact |\n"
        "| :--- | :--- | :--- |\n"
        "| Test | Do test | None |\n\n"
        "```bash\n"
        "adb shell dumpsys deviceidle whitelist -com.example.test\n"
        "```\n"
    )
    sanitized = parser.sanitize_ai_output(raw_markdown)
    assert "```bash\nadb shell dumpsys deviceidle whitelist -com.example.test\n```" in sanitized
    assert "| Task | Action | Impact |" in sanitized
