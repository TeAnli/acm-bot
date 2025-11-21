from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .utils import fetch_json
from .utils import parse_scpc_time

import requests

def scpc_user_info_url(username: str) -> str:
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

def scpc_contest_rank_url(contest_id: int) -> str:
    """SCPC 比赛过题排行 API"""
    return f'http://scpc.fun/api/get-contest-rank?contestId={contest_id}'

def scpc_login_url() -> str:
    """SCPC 登录 API"""
    return f'http://scpc.fun/api/login'

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

@dataclass
class ScpcWeekACUser:
    username: str
    avatar: str
    titlename: str
    titleColor: str # 16进制RGB
    ac: int

@dataclass
class ScpcContestRankUser:
    rank: int
    awardName: str
    uid: str
    username: str
    realname: str
    gender: str
    avatar: str
    total: int
    ac: int
    totalTime: int   

@dataclass
class ScpcUpdatedProblem:
    id: int
    problemId: str
    title: str
    type: int
    gmtCreate: int
    gmtModified: int

    
def scpc_login(username: str, password: str) -> Optional[str]:
    response = requests.post(
        scpc_login_url(),
        headers={
            "Content-Type": "application/json",
            "Host": "scpc.fun",
            "Origin": "http://scpc.fun",
            "Referer": "http://scpc.fun/home",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
        },
        json={
            "password": password,
            "username": username,
        },
    )
    if getattr(response, "status_code", 0) != 200:
        return None
    return response.headers.get("Authorization")

def get_scpc_contest_rank(
    contest_id: int,
    token: str,
    current_page: int = 1,
    limit: int = 50,
) -> Optional[List[ScpcContestRankUser]]:
    response = requests.post(
        "http://scpc.fun/api/get-contest-rank",
        headers={
            "Content-Type": "application/json",
            "Host": "scpc.fun",
            "Origin": "http://scpc.fun",
            "Referer": "http://scpc.fun/home",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
            "Authorization": token,
        },
        json={
            "currentPage": current_page,
            "limit": limit,
            "cid": contest_id,
            "forceRefresh": False,
            "removeStar": False,
            "concernedList": [],
            "keyword": None,
            "containsEnd": False,
            "time": None,
        },
    )
    if getattr(response, "status_code", 0) != 200:
        return None
    try:
        json_data = response.json()
    except Exception:
        return None
    records = (
        json_data.get("data", {}).get("records")
        or json_data.get("records")
        or []
    )
    rank_users: List[ScpcContestRankUser] = []
    for record in records:
        try:
            rank_users.append(
                ScpcContestRankUser(
                    rank=int(record.get("rank", 0)),
                    awardName=str(record.get("awardName", "") or ""),
                    uid=str(record.get("uid", "") or ""),
                    username=str(record.get("username", "") or ""),
                    realname=str(record.get("realname", "") or ""),
                    gender=str(record.get("gender", "") or ""),
                    avatar=str(record.get("avatar", "") or ""),
                    total=int(record.get("total", 0)),
                    ac=int(record.get("ac", 0)),
                    totalTime=int(record.get("totalTime", 0)),
                )
            )
        except Exception:
            continue
    return rank_users

def get_scpc_rank() -> Optional[List[ScpcWeekACUser]]:
    """获取 SCPC 最近一周过题排行"""
    json_data = fetch_json(scpc_recent_ac_rank())
    if not json_data or 'data' not in json_data:
        return None
    records = json_data.get('data') or []
    users: List[ScpcWeekACUser] = []
    for entry in records:
        try:
            username = entry.get('username') or ''
            avatar = entry.get('avatar') or ''
            titlename = entry.get('titlename') or ''
            titleColor = entry.get('titleColor') or ''
            ac = int(entry.get('ac', 0))
            users.append(ScpcWeekACUser(username=username, avatar=avatar, titlename=titlename, titleColor=titleColor, ac=ac))
        except Exception:
            continue
    return users

def get_scpc_user_info(username: str) -> Optional[ScpcUser]:
    """获取 SCPC 用户主页信息"""
    json_data = fetch_json(scpc_user_info_url(username))
    if not json_data or 'data' not in json_data:
        return None
    data_obj = json_data.get('data') or {}
    total = int(data_obj.get('total', 0))
    solved = data_obj.get('solvedList') or []
    nickname = str(data_obj.get('nickname') or username)
    signature = str(data_obj.get('signature') or '')
    return ScpcUser(total=total, solvedList=solved, nickname=nickname, signature=signature)

def get_scpc_contests(current_page: int = 0, limit: int = 10) -> Optional[List[ScpcContest]]:
    """获取 SCPC 比赛列表"""
    json_data = fetch_json(scpc_contests_url(current_page, limit))
    if not json_data:
        return None
    records = (
        json_data.get('data', {}).get('records')
        or json_data.get('records')
        or []
    )
    contests: List[ScpcContest] = []
    for record in records:
        try:
            name = record.get('title') or record.get('contestName') or '未命名比赛'
            start_time = record.get('startTime')
            end_time = record.get('endTime')
            duration_secs = int(record.get('duration') or 0)
            contests.append(ScpcContest(name=str(name), startTime=start_time, endTime=end_time, duration=duration_secs))
        except Exception:
            continue
    return contests

def get_scpc_recent_contests() -> Optional[List[ScpcContest]]:
    json_data = fetch_json(scpc_recent_contest())
    if not json_data:
        return None
    records = json_data.get('data') or []
    contest_list: List[ScpcContest] = []
    for record in records:
        try:
            name = str(record.get('title') or '未命名比赛')
            start_time = record.get('startTime')
            end_time = record.get('endTime')
            duration_secs = int(record.get('duration') or 0)
            contest_list.append(ScpcContest(name=name, startTime=start_time, endTime=end_time, duration=duration_secs))
        except Exception:
            continue
    return contest_list

def get_scpc_recent_updated_problems() -> Optional[List[ScpcUpdatedProblem]]:
    body = fetch_json(scpc_recent_updated_problem())
    print(body)
    if not body:
        return None
    raw = body.get('data') or []
    items: List[ScpcUpdatedProblem] = []
    for r in raw:
        try:
            rid = int(r.get('id', 0))
            pid = str(r.get('problemId', '') or '')
            title = str(r.get('title', '') or '')
            typ = int(r.get('type', 0))
            created = parse_scpc_time(r.get('gmtCreate'))
            modified = parse_scpc_time(r.get('gmtModified'))
            items.append(ScpcUpdatedProblem(id=rid, problemId=pid, title=title, type=typ, gmtCreate=created, gmtModified=modified))
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