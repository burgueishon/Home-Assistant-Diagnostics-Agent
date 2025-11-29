"""
Blaxel backend (local stub) for saving diagnostic snapshots.

Design:
- Requires FEATURE_BLAXEL=true to be used.
- If BLAXEL_API_KEY is set, you could extend this to send data to a real API.
- Currently stores snapshots in-memory for simplicity and hackathon safety.
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List

FEATURE_BLAXEL = os.getenv("FEATURE_BLAXEL", "false").lower() == "true"
BLAXEL_API_KEY = os.getenv("BLAXEL_API_KEY")

_SNAPSHOTS: List[Dict[str, Any]] = []


def save_snapshot(tool_name: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Save a diagnostic snapshot locally (no-op if feature disabled)."""
    if not FEATURE_BLAXEL:
        return
    # Ensure JSON-safe copies to avoid recursion/serialization issues
    try:
        safe_args = json.loads(json.dumps(args, default=str))
    except Exception:
        safe_args = {"data": str(args)}
    try:
        safe_result = json.loads(json.dumps(result, default=str))
    except Exception:
        safe_result = {"data": str(result)}

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool_name,
        "args": safe_args,
        "result": safe_result,
    }
    _SNAPSHOTS.append(entry)
    # Keep history bounded
    if len(_SNAPSHOTS) > 100:
        del _SNAPSHOTS[:-100]


def get_snapshots() -> Dict[str, Any]:
    """Return stored snapshots; if feature disabled or no key, return friendly error."""
    if not FEATURE_BLAXEL:
        return {"error": "Blaxel feature is disabled. Enable FEATURE_BLAXEL=true to use history."}
    if not BLAXEL_API_KEY:
        return {"error": "BLAXEL_API_KEY is not configured.", "snapshots": _SNAPSHOTS}
    return {"snapshots": _SNAPSHOTS}
