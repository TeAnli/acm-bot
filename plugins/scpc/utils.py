from datetime import datetime
import math

def format_timestamp(timestamp: int, format: str = "%Y-%m-%d %H:%M") -> str:
    """ 将tiemstamp数字格式化 """
    return datetime.fromtimestamp(timestamp).strftime(format)

def format_hours(seconds: int, precision: int = 1) -> str:
    """将秒数转化为小时数, 并保留指定位数小数"""
    hours = seconds / 3600
    return f"{hours:.{precision}f}"


def build_text_msg(text: str) -> dict:
    """构建 QQ Message 字符串"""
    return {"type": "text", "data": {"text": text}}


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
    # 没找到 state 的话 返回 特殊icon
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
    if total_count == 0:
        return 0.0
    return accept_count / total_count