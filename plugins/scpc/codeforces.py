from typing import Optional, List
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
    duration_seconds: int
    start_time_seconds: int
    relative_time_seconds: int

@dataclass
class CodeforcesUserRatingChange:
    contest_id: int
    contest_name: str
    handle: str
    new_rating: int
    old_rating: int
    rating_update_time_seconds: int

def extract_cf_timing(contest: CodeforcesContest):
    relative_secs = int(contest.relative_time_seconds or 0)
    duration_secs = int(contest.duration_seconds or 0)
    start_ts = int(contest.start_time_seconds or 0)
    if relative_secs < 0:
        return '即将开始', '据开始还剩', abs(relative_secs), duration_secs, start_ts
    if 0 <= relative_secs < duration_secs:
        return '进行中', '距离结束', max(duration_secs - relative_secs, 0), duration_secs, start_ts
    return None


def get_codeforces_contests(include_gym: bool = False, timeout: int = 10) -> Optional[List[CodeforcesContest]]:
    json_data = fetch_json(codeforces_contests_url(include_gym), timeout=timeout)
    if not json_data or json_data.get('status') != 'OK':
        return None
    records = json_data.get('result', [])
    contests: List[CodeforcesContest] = []
    for entry in records:
        try:
            contests.append(CodeforcesContest(
                id=int(entry.get('id', 0)),
                name=str(entry.get('name', '')),
                duration_seconds=int(entry.get('durationSeconds', 0)),
                start_time_seconds=int(entry.get('startTimeSeconds', 0)),
                relative_time_seconds=int(entry.get('relativeTimeSeconds', 0)),
            ))
        except Exception:
            continue
    return contests

def get_codeforces_user_rating(handle: str, timeout: int = 10) -> Optional[List[CodeforcesUserRatingChange]]:
    json_data = fetch_json(codeforces_user_rating_url(handle), timeout=timeout)
    if not json_data or json_data.get('status') != 'OK':
        return None
    records = json_data.get('result', [])
    changes: List[CodeforcesUserRatingChange] = []
    for entry in records:
        try:
            changes.append(CodeforcesUserRatingChange(
                contest_id=int(entry.get('contestId', 0)),
                contest_name=str(entry.get('contestName', '')),
                handle=str(entry.get('handle', handle)),
                new_rating=int(entry.get('newRating', 0)),
                old_rating=int(entry.get('oldRating', 0)),
                rating_update_time_seconds=int(entry.get('ratingUpdateTimeSeconds', 0)),
            ))
        except Exception:
            continue
    return changes