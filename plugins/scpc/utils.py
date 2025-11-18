from datetime import datetime
import math
from functools import wraps
from typing import Callable, Optional, Dict, Any
import requests
from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.core.event import BaseMessageEvent
from ncatbot.utils import get_log

_logger = get_log()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36 QIHU 360SE',
    'Content-Type': 'application/json',
}

def fetch_json(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """以统一 headers 发起 GET 请求并解析 JSON。失败返回 None。"""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except Exception as e:
        _logger.warning(f'HTTP 请求失败: {e}')
        return None
    if getattr(resp, 'status_code', 0) != 200:
        _logger.warning(f'请求 {url} 返回状态码异常: {getattr(resp, "status_code", "")} {getattr(resp, "text", "")}')
        return None
    try:
        return resp.json()
    except Exception as e:
        _logger.warning(f'JSON 解析失败: {e}')
        return None

def format_timestamp(timestamp: int, format: str = "%Y-%m-%d %H:%M") -> str:
    """ 将timestamp数字格式化 """
    return datetime.fromtimestamp(timestamp).strftime(format)

def format_hours(seconds: int, precision: int = 1) -> str:
    """将秒数转化为小时数, 并保留指定位数小数"""
    hours = seconds / 3600
    return f"{hours:.{precision}f}"

def format_relative_hours(seconds: int, precision: int = 1) -> str:
    """ 
        格式化相距时间
        规则: 
            1. 相聚时间 < 1天, 以小时数返回
            2. 相聚时间 < 7天, 以天数返回
            3. 相聚时间 < 1年, 以周数返回
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
        比赛状态图标和文字信息
    """
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
    """
    对洛谷,scpc,codeforces使用相同的格式化比赛信息输出
    参数:    
        - name: 比赛名称
        - contest_id: 比赛ID
        - state: '即将开始' | '进行中' | '已结束'
        - start_ts: 开始时间的timestamp
        - remaining_label: 距离比赛开始的标题
        - remaining_secs: 距离比赛开始的时间
        - duration_secs: 比赛持续时间
        - include_id: 是否要在比赛名称处加入id显示
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
    """
        解析JAVA未经格式化的Date内容
    """
    if value is None:
        return 0
    try:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            try:
                dt = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")
                return int(dt.timestamp())
            except Exception:
                pass
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
    """计算通过率 accept/total。total 为 0 时返回 0.0。"""
    if total_count == 0:
        return 0.0
    return accept_count / total_count

async def send_group_messages(api_client, group_id: int, messages: list[dict]):
    """发送原始消息数组到指定群聊，统一异常处理。"""
    try:
        await api_client.send_group_msg(group_id, messages)
    except Exception as e:
        _logger.warning(f'发送群消息失败: {e}')

async def broadcast_text(api_client, group_listeners: dict, text: str):
    """向开启监听的群聊广播文本消息。"""
    for gid, enabled in group_listeners.items():
        if enabled:
            await api_client.send_group_text(gid, text)
            
def require_sender_admin():
    """
    用于群聊命令的权限过滤装饰器：仅允许群管理员/群主使用被装饰的命令。
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self: NcatBotPlugin, event: BaseMessageEvent, *args, **kwargs):
            group_id = getattr(event, "group_id", None)
            user_id = getattr(event, "user_id", None)
            if group_id is None or user_id is None:
                return await func(self, event, *args, **kwargs)
            try:
                member_info = await self.api.get_group_member_info(
                    group_id=group_id,
                    user_id=user_id,
                )
                if member_info.role == "owner" or member_info.role == "admin":
                    return await func(self, event, *args, **kwargs)
                return await event.reply("您不是群管理员或群主，无法执行此命令。")
            except Exception as e:
                _logger.warning(f"获取发送者群角色失败: {e}")
                await event.reply("无法获取您的群成员信息，暂时无法执行该命令。")
                return
        return wrapper
    return decorator