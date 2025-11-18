from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .utils import fetch_json

def codeforces_contests_url(include_gym: bool = False) -> str:
    return f'https://codeforces.com/api/contest.list?gym={str(include_gym).lower()}'

def codeforces_user_rating_url(username: str) -> str:
    return f'https://codeforces.com/api/user.rating?handle={username}'

@dataclass
class CodeforcesContest:
    id: int
    name: str
    durationSeconds: int
    startTimeSeconds: int
    relativeTimeSeconds: int

@dataclass
class CodeforcesUserRatingChange:
    contestId: int
    contestName: str
    handle: str
    newRating: int
    oldRating: int
    ratingUpdateTimeSeconds: int

def extract_cf_timing(contest: CodeforcesContest):
    rel = int(contest.relativeTimeSeconds or 0)
    duration = int(contest.durationSeconds or 0)
    start_ts = int(contest.startTimeSeconds or 0)
    if rel < 0:
        return '即将开始', '据开始还剩', abs(rel), duration, start_ts
    if 0 <= rel < duration:
        return '进行中', '距离结束', max(duration - rel, 0), duration, start_ts
    return None


def get_codeforces_contests(include_gym: bool = False, timeout: int = 10) -> Optional[List[CodeforcesContest]]:
    body = fetch_json(codeforces_contests_url(include_gym), timeout=timeout)
    if not body or body.get('status') != 'OK':
        return None
    raw = body.get('result', [])
    items: List[CodeforcesContest] = []
    for c in raw:
        try:
            items.append(CodeforcesContest(
                id=int(c.get('id', 0)),
                name=str(c.get('name', '')),
                durationSeconds=int(c.get('durationSeconds', 0)),
                startTimeSeconds=int(c.get('startTimeSeconds', 0)),
                relativeTimeSeconds=int(c.get('relativeTimeSeconds', 0)),
            ))
        except Exception:
            continue
    return items

def get_codeforces_user_rating(handle: str, timeout: int = 10) -> Optional[List[CodeforcesUserRatingChange]]:
    body = fetch_json(codeforces_user_rating_url(handle), timeout=timeout)
    if not body or body.get('status') != 'OK':
        return None
    raw = body.get('result', [])
    changes: List[CodeforcesUserRatingChange] = []
    for r in raw:
        try:
            changes.append(CodeforcesUserRatingChange(
                contestId=int(r.get('contestId', 0)),
                contestName=str(r.get('contestName', '')),
                handle=str(r.get('handle', handle)),
                newRating=int(r.get('newRating', 0)),
                oldRating=int(r.get('oldRating', 0)),
                ratingUpdateTimeSeconds=int(r.get('ratingUpdateTimeSeconds', 0)),
            ))
        except Exception:
            continue
    return changes