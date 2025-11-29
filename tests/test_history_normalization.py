import importlib.util
from pathlib import Path


def _load_app_module():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("gradio_app_app", app_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module


def test_normalize_history_handles_tuples_and_dicts():
    app_module = _load_app_module()
    _normalize_history = app_module._normalize_history
    raw = [
        ("user1", "assist1"),
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
    ]
    normalized = _normalize_history(raw)
    assert normalized == [
        {"role": "user", "content": "user1"},
        {"role": "assistant", "content": "assist1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
    ]
