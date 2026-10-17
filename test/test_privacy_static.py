"""فحوص ثابتة لادعاء «المعالجة في الذاكرة دون حفظ»."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


def test_no_disk_writes_logging_or_shared_cache():
    for name in ("app.py", "core.py", "charts.py", "ui.py"):
        s = _src(name)
        for bad in ("tempfile", "import logging", "print(", "cache_data", "cache_resource",
                    "NamedTemporaryFile", "shutil"):
            assert bad not in s, f"{name} يحتوي {bad}"
        assert not re.search(r"open\([^)]*['\"][wa]b?\+?['\"]", s), f"{name} يكتب ملفاً"


def test_user_text_is_escaped_before_html():
    app = _src("app.py")
    assert 'ui.esc(m.get("name"' in app and 'ui.esc(m.get("customer_no"' in app
    assert "ui.esc(s[:48])" in app


def test_usage_stats_disabled_and_pdfs_ignored():
    assert "gatherUsageStats = false" in _src(os.path.join(".streamlit", "config.toml"))
    assert "*.pdf" in _src(".gitignore")
