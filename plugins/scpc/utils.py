from datetime import datetime
import math


def format_timestamp(ts: int, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format a Unix timestamp to a readable datetime string."""
    return datetime.fromtimestamp(ts).strftime(fmt)


def format_hours(seconds: int, precision: int = 1) -> str:
    """Convert seconds to hours string with given precision."""
    hours = seconds / 3600
    return f"{hours:.{precision}f}"


def build_text_msg(text: str) -> dict:
    """Build a text message payload for group messaging API."""
    return {"type": "text", "data": {"text": text}}


def format_relative_hours(seconds: int, precision: int = 1) -> str:
    hours = seconds / 3600
    if hours >= 24 * 7:
        weeks = math.ceil(hours / (24 * 7))
        return f"{weeks} 周"
    if hours >= 24:
        days = math.ceil(hours / 24)
        return f"{days} 天"
    return f"{hours:.{precision}f} 小时"


def state_icon(state: str) -> str:
    """Return an icon for contest state."""
    mapping = {
        "即将开始": "⏳",
        "进行中": "🟢",
        "已结束": "🔴",
    }
    return mapping.get(state, "ℹ️")


def parse_scpc_time(value) -> int:
    """Parse SCPC time which may be ISO string or timestamp seconds, return seconds."""
    if value is None:
        return 0
    try:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            # Try strict ISO with timezone like 2027-07-08T23:09:00.000+0000
            try:
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
                return int(dt.timestamp())
            except Exception:
                pass
            # Fallback: fromisoformat with Z or +00:00 variations
            try:
                v = value.replace("Z", "+00:00")
                dt = datetime.fromisoformat(v)
                return int(dt.timestamp())
            except Exception:
                pass
    except Exception:
        pass
    return 0