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


def format_contest_text(name: str,
                        contest_id: int | None,
                        state: str,
                        start_ts: int,
                        remaining_label: str,
                        remaining_secs: int,
                        duration_secs: int,
                        include_id: bool = True) -> str:
    """Build a unified contest message string for CF/SCPC/Luogu.
    - name: contest name
    - contest_id: optional numeric id for display
    - state: '即将开始' | '进行中' | '已结束'
    - start_ts: start timestamp in seconds
    - remaining_label: label before remaining time string
    - remaining_secs: seconds remaining to start/end
    - duration_secs: contest duration in seconds
    - include_id: whether to include ID in the display name
    """
    icon = state_icon(state)
    start_time_str = format_timestamp(start_ts)
    duration_hours = format_hours(duration_secs, precision=1)
    remaining_str = format_relative_hours(remaining_secs, precision=1)

    title_line = f"{name}" if not include_id or contest_id is None else f"{name} (ID: {contest_id})"
    return (
        f"比赛名称:\n"
        f"{title_line}\n"
        f"状态: {icon} {state}\n"
        f"开始时间: {start_time_str}\n"
        f"{remaining_label}: {remaining_str}\n"
        f"比赛时长: {duration_hours} 小时"
    )


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


def calculate_accept_ratio(total_count: int, accept_count: int) -> float:
    if total_count == 0:
        return 0.0
    return accept_count / total_count