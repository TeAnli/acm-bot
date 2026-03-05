import os
from dataclasses import dataclass
from typing import List, Optional

from ncatbot.utils import get_log

from ..utils.webui import webui_helper
from ..utils.network import fetch_json
from ..utils.renderer import renderer
from .platform import Contest, Platform

LOG = get_log()
def codeforces_contests_url(include_gym: bool = False) -> str:
    """
    返回 Codeforces 比赛列表 API 的 URL

    Args:
        include_gym (str): 是否包含 Gym 比赛，默认 False
    """
    return f"https://codeforces.com/api/contest.list?gym={str(include_gym).lower()}"


def codeforces_user_rating_url(username: str) -> str:
    """
    返回指定用户的 rating 变更记录 API 的 URL

    Args:
        username (str): Codeforces 用户名 (handle)
    """
    return f"https://codeforces.com/api/user.rating?handle={username}"


def codeforces_user_info_url(username: str) -> str:
    """
    返回指定用户信息 API 的 URL
    """
    return f"https://codeforces.com/api/user.info?handles={username}"


@dataclass
class CodeforcesUser:
    handle: str
    rating: int
    max_rating: int
    rank: str
    max_rank: str
    avatar: str
    title_photo: str
    contribution: int
    friend_of_count: int
    organization: str
    country: str
    city: str


@dataclass
class CodeforcesUserRating:
    contest_id: int  # 比赛ID
    contest_name: str  # 比赛名称
    handle: str  # 用户名
    new_rating: int  # 新评分
    old_rating: int  # 旧评分
    rating_update_time_seconds: int  # 评分更新时间（时间戳）
    rank: int  # 排名


class CodeforcesPlatform(Platform):

    async def get_contests(self) -> List[Contest]:
        response = await fetch_json(codeforces_contests_url())
        records = response.get("result", [])
        contests: List[Contest] = []
        for entry in records:
            if entry.get("phase") == "BEFORE":
                contests.append(
                    Contest(
                        name=str(entry.get("name", "")),
                        id=int(entry.get("id", 0)),
                        start_time=int(entry.get("startTimeSeconds", 0)),
                        duration=int(entry.get("durationSeconds", 0)),
                        url=f"https://codeforces.com/contest/{int(entry.get('id', 0))}",
                    )
                )
        return contests

    async def get_user_info(self, handle: str) -> Optional[CodeforcesUser]:
        response = await fetch_json(codeforces_user_info_url(handle))
        if not response or response.get("status") != "OK":
            return None

        result = response.get("result", [])
        if not result:
            return None

        data = result[0]
        return CodeforcesUser(
            handle=data.get("handle", ""),
            rating=data.get("rating", 0),
            max_rating=data.get("maxRating", 0),
            rank=data.get("rank", ""),
            max_rank=data.get("maxRank", ""),
            avatar=data.get("avatar", ""),
            title_photo=data.get("titlePhoto", ""),
            contribution=data.get("contribution", 0),
            friend_of_count=data.get("friendOfCount", 0),
            organization=data.get("organization", ""),
            country=data.get("country", ""),
            city=data.get("city", ""),
        )

    async def get_user_rating_history(self, handle: str) -> List[CodeforcesUserRating]:
        response = await fetch_json(codeforces_user_rating_url(handle))
        if not response or response.get("status") != "OK":
            return []

        records = response.get("result", [])
        history: List[CodeforcesUserRating] = []
        for entry in records:
            history.append(
                CodeforcesUserRating(
                    contest_id=int(entry.get("contestId", 0)),
                    contest_name=str(entry.get("contestName", "")),
                    handle=str(entry.get("handle", "")),
                    new_rating=int(entry.get("newRating", 0)),
                    old_rating=int(entry.get("oldRating", 0)),
                    rating_update_time_seconds=int(
                        entry.get("ratingUpdateTimeSeconds", 0)
                    ),
                    rank=int(entry.get("rank", 0)),
                )
            )
        return history


async def render_codeforces_user_info_image(handle: str) -> Optional[str]:
    platform = CodeforcesPlatform()
    user = await platform.get_user_info(handle)
    if not user:
        return None

    try:
        html = webui_helper.render_cf_user_info(user)
        out_path = os.path.abspath(f"plugins/acm/assets/cf_user_{handle}.png")
        success = await renderer.render_html(html, out_path)
        return out_path if success else None
    except Exception as e:
        LOG.error(f"Render CF user info failed: {e}")
        return None


async def render_codeforces_rating_chart(handle: str) -> Optional[str]:
    platform = CodeforcesPlatform()
    history = await platform.get_user_rating_history(handle)
    if not history:
        return None

    try:
        html = webui_helper.render_cf_rating_chart(handle, history)
        out_path = os.path.abspath(f"plugins/acm/assets/cf_rating_{handle}.png")
        success = await renderer.render_html(html, out_path)
        return out_path if success else None
    except Exception as e:
        LOG.error(f"Render CF rating chart failed: {e}")
        return None
