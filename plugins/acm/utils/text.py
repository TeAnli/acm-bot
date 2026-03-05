import math
from datetime import datetime

from ..platforms.platform import Contest


def format_timestamp(timestamp: int, formatter: str = "%Y-%m-%d %H:%M") -> str:
    """
    将时间戳格式化为指定的日期时间字符串

    Args:
        timestamp: 时间戳（秒）
        formatter: 时间格式字符串

    Returns:
        格式化后的时间字符串
    """
    return datetime.fromtimestamp(timestamp).strftime(formatter)


def format_hours(seconds: int, precision: int = 1) -> str:
    """
    将秒数转换为小时数，保留指定小数位

    Args:
        seconds: 秒数
        precision: 小数位数

    Returns:
        小时数字符串
    """
    hours = seconds / 3600
    return f"{hours:.{precision}f}"


def format_relative_hours(seconds: int, precision: int = 1) -> str:
    """
    将秒数格式化为相对时间描述：小时/天/周

    参数:
        seconds: 秒数
        precision: 小数位数（用于小时）

    返回:
        相对时间字符串
    """
    hours = seconds / 3600
    if hours >= 24 * 7:
        weeks = math.ceil(hours / (24 * 7))
        return f"{weeks} 周"
    if hours >= 24:
        days = math.ceil(hours / 24)
        return f"{days} 天"
    return f"{hours:.{precision}f} 小时"


def state_icon(state: str) -> str:
    """
    根据比赛状态返回对应图标

    Args:
        state: 比赛状态（即将开始/进行中/已结束）

    Returns:
        对应状态的图标字符串
    """
    mapping = {
        "即将开始": "⏳",
        "进行中": "🟢",
        "已结束": "🔴",
    }
    return mapping.get(state, "ℹ️")


def calculate_accept_ratio(passed: int, total: int) -> float:
    """
    计算通过率
    """
    if total == 0:
        return 0.0
    return (passed / total) * 100


async def broadcast_text(api_client, group_listeners: dict, text: str):
    """
    向已开启监听的群聊广播文本消息

    Args:
    - api_client: 机器人 API 客户端
    - group_listeners: 群组监听开关映射（group_id -> enabled）
    - text: 要广播的文本内容
    """
    for gid, enabled in group_listeners.items():
        if enabled:
            await api_client.send_group_text(gid, text)


def extract_contest_timing(contest: "Contest", now_ts: int):
    """
    根据统一 Contest 对象计算比赛状态与剩余时间。

    Args:
    - contest: 统一比赛对象。
    - now_ts: 当前时间戳（秒）。

    Returns:
    - (state, remaining_label, remaining_secs, duration_secs, start_ts, sort_key)
    - 比赛已结束返回 None。
    """
    start_ts = int(contest.start_time or 0)
    duration = int(contest.duration or 0)
    if start_ts <= 0 or duration <= 0:
        return None
    end_ts = start_ts + duration
    
    if now_ts < start_ts:
        return (
            "即将开始",
            "据开始还剩",
            start_ts - now_ts,
            duration,
            start_ts,
            start_ts - now_ts,
        )
    if start_ts <= now_ts < end_ts:
        return (
            "进行中",
            "距离结束",
            end_ts - now_ts,
            duration,
            start_ts,
            end_ts - now_ts,
        )
    return None
