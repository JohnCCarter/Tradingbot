# Tradingbot test suite
import pytest

def test_dummy():
    assert True

def test_no_old_file_references():
    """Verifierar att inga referenser till gamla filnamn finns kvar i kodbasen."""
    import os
    import re
    old_files = [
        'core.py', 'data.py', 'test_tradingbot.py',
        'strategy_performance.js', 'dashboard.html', 'script.sh', 'script_start.sh'
    ]
    for root, dirs, files in os.walk(os.path.dirname(__file__) + '/../'):
        for file in files:
            if file.endswith(('.py', '.js', '.html')) and 'archive' not in root:
                with open(os.path.join(root, file), encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for old in old_files:
                        assert not re.search(rf"\b{re.escape(old)}\b", content), f"Referens till {old} hittad i {file}"

def test_all_init_py_exists():
    """Verifierar att __init__.py finns i alla modulmappar enligt refaktorplanen."""
    import os
    base = os.path.dirname(__file__) + '/../'
    required = [
        '', 'static', 'scripts', 'tests', 'archive'
    ]
    for sub in required:
        path = os.path.join(base, sub, '__init__.py')
        assert os.path.isfile(path), f"Saknar __init__.py i {sub or '.'}"
