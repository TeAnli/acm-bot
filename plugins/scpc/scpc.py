from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .utils import fetch_json
from .utils import parse_scpc_time

def user_info_url(username: str) -> str:
    """SCPC 用户主页信息 API"""
    return f'http://scpc.fun/api/get-user-home-info?username={username}'

def scpc_contests_url(current_page: int = 0, limit: int = 10) -> str:
    """SCPC 比赛列表 API"""
    return f'http://scpc.fun/api/get-contest-list?currentPage={current_page}&limit={limit}'

def scpc_recent_contest() -> str:
    """SCPC 近期比赛 API"""
    return f'http://scpc.fun/api/get-recent-contest'

def scpc_recent_updated_problem():
    """SCPC 近期更新题目 API"""
    return f'http://scpc.fun/api/get-recent-updated-problem'

def scpc_recent_ac_rank():
    """SCPC 最近一周过题排行 API"""
    return f'http://scpc.fun/api/get-recent-seven-ac-rank'

@dataclass
class ScpcUser:
    total: int
    solvedList: List[Any]
    nickname: str
    signature: str

@dataclass
class ScpcContest:
    name: str
    startTime: Any
    endTime: Any
    duration: int

def get_scpc_user_info(username: str, timeout: int = 10) -> Optional[ScpcUser]:
    """获取 SCPC 用户主页信息"""
    body = fetch_json(user_info_url(username), timeout=timeout)
    if not body or 'data' not in body:
        return None
    d = body.get('data') or {}
    total = int(d.get('total', 0))
    solved = d.get('solvedList') or []
    nickname = str(d.get('nickname') or username)
    signature = str(d.get('signature') or '')
    return ScpcUser(total=total, solvedList=solved, nickname=nickname, signature=signature)

def get_scpc_contests(current_page: int = 0, limit: int = 10, timeout: int = 10) -> Optional[List[ScpcContest]]:
    """获取 SCPC 比赛列表"""
    body = fetch_json(scpc_contests_url(current_page, limit), timeout=timeout)
    if not body:
        return None
    raw = (
        body.get('data', {}).get('records')
        or body.get('records')
        or []
    )
    items: List[ScpcContest] = []
    for r in raw:
        try:
            name = r.get('title') or r.get('contestName') or '未命名比赛'
            start = r.get('startTime')
            end = r.get('endTime')
            duration = int(r.get('duration') or 0)
            items.append(ScpcContest(name=str(name), startTime=start, endTime=end, duration=duration))
        except Exception:
            continue
    return items

def extract_scpc_timing(record: ScpcContest, now_ts: int):
    """
    根据 SCPC 比赛记录计算展示所需的时间信息。
    """
    name = record.name
    start_ts = parse_scpc_time(record.startTime)
    end_ts = parse_scpc_time(record.endTime)
    duration = int(record.duration or (max(end_ts - start_ts, 0) if start_ts and end_ts else 0))
    if start_ts and now_ts < start_ts:
        state = '即将开始'
        remaining_label = '据开始还剩'
        remaining_secs = start_ts - now_ts
        sort_key = remaining_secs
    elif start_ts and end_ts and start_ts <= now_ts < end_ts:
        state = '进行中'
        remaining_label = '距离结束'
        remaining_secs = max(end_ts - now_ts, 0)
        sort_key = remaining_secs
    else:
        return None
    return name, state, remaining_label, remaining_secs, duration, start_ts, sort_key