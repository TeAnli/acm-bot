import os
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any, Dict, List, Optional

import xlsxwriter
from httpx import AsyncClient
from ncatbot.utils import get_log

from ..utils.network import Method, fetch_json
from ..utils.renderer import renderer
from ..utils.webui import webui_helper
from ..utils.text import calculate_accept_ratio

from .platform import Contest, Platform

LOG = get_log()


def parse_scpc_time(value: Any) -> int:
    """
    解析来自后端GMT未经格式化的时间字段为时间戳
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


# ----------------------------
# region API URL 构建函数
# ----------------------------
def scpc_user_info_url(username: str) -> str:
    return f"http://scpc.fun/api/get-user-home-info?username={username}"


def scpc_contests_url(current_page: int = 0, limit: int = 10) -> str:
    return (
        f"http://scpc.fun/api/get-contest-list?currentPage={current_page}&limit={limit}"
    )


def scpc_recent_contest_url() -> str:
    return f"http://scpc.fun/api/get-recent-contest"


def scpc_recent_updated_problem_url():
    return f"http://scpc.fun/api/get-recent-updated-problem"


def scpc_recent_ac_rank_url():
    return f"http://scpc.fun/api/get-recent-seven-ac-rank"


def scpc_login_url() -> str:
    return f"http://scpc.fun/api/login"


def scpc_contest_rank() -> str:
    return f"http://scpc.fun/api/get-contest-rank"


# ----------------------------
# region 数据类定义
# ----------------------------
@dataclass
class ScpcUser:
    total: int  # 总提交数
    solved_list: List[Any]  # 通过题目列表
    nickname: str  # 昵称
    signature: str  # 个性签名
    avatar: str  # 头像地址
    username: str = ""  # 用户名 (Added for convenience)


@dataclass
class ScpcWeekACUser:
    username: str  # 用户名
    avatar: str  # 头像地址
    title_name: str  # 头衔名称
    title_color: str  # 16进制RGB
    ac: int  # 通过题目数量


@dataclass
class ACMInformation:
    error_count: int
    is_ac: bool = False
    ac_time: int = 0
    is_first_ac: bool = False


@dataclass
class ScpcContestRankUser:
    rank: int  # 排名
    award_name: str  # 奖项名称
    user_name: str  # 用户名
    real_name: str  # 真实姓名
    nick_name: str  # 昵称
    school: str  # 班级
    total: int  # 总尝试次数
    total_time: int  # 总耗时
    ac: int  # 通过题目数量
    information: Dict[int, ACMInformation]  # 题目提交信息，键为题目ID

    @classmethod
    def get_chinese_headers(cls) -> Dict[str, str]:
        return {
            "rank": "排名",
            "award_name": "奖项",
            "user_name": "用户名",
            "real_name": "真实姓名",
            "nick_name": "昵称",
            "school": "班级",
            "total_time": "耗时",
            "total": "总尝试次数",
            "ac": "通过数",
        }


@dataclass
class ScpcUpdatedProblem:
    id: int  # 记录 ID
    problem_id: str  # 题目 ID
    title: str  # 题目标题
    type: int  # 题目类型
    gmt_create: int  # 创建时间戳
    gmt_modified: int  # 修改时间戳
    url: str  # 题目页面链接


class SCPCPlatform(Platform):

    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self.token = None

    async def login(self):
        try:
            async with AsyncClient() as client:
                response = await client.post(
                    scpc_login_url(),
                    headers={
                        "Host": "scpc.fun",
                        "Origin": "http://scpc.fun",
                        "Referer": "http://scpc.fun/home",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
                        "Connection": "close",
                    },
                    json={
                        "password": self.password,
                        "username": self.username,
                    },
                )
            if "Authorization" in response.headers:
                self.token = response.headers["Authorization"]
            else:
                LOG.warning("SCPC login failed: No Authorization header")
        except Exception as e:
            LOG.error(f"SCPC login error: {e}")

    async def get_contest_rank(self, contest_id: int) -> List[ScpcContestRankUser]:
        if not self.token:
            await self.login()

        response = await fetch_json(
            scpc_contest_rank(),
            method=Method.POST,
            headers={
                "Content-Type": "application/json",
                "Host": "scpc.fun",
                "Origin": "http://scpc.fun",
                "Referer": "http://scpc.fun/home",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0",
                "Authorization": self.token or "",
            },
            payload={
                "currentPage": 0,
                "limit": 999999,
                "cid": contest_id,
                "forceRefresh": False,
                "removeStar": False,
                "concernedList": [],
                "keyword": None,
                "containsEnd": False,
                "time": None,
            },
        )
        records = (
            response.get("data", {}).get("records") or response.get("records") or []
        )
        rank_users: List[ScpcContestRankUser] = []
        for entry in records:
            submission_info = {}
            for data in entry["submissionInfo"]:
                information = entry["submissionInfo"][data]
                submission_info[data] = ACMInformation(
                    ac_time=int(information.get("ACTime", 0)),
                    is_ac=bool(information.get("isAC", False)),
                    error_count=int(information.get("errorNum", 0)),
                    is_first_ac=bool(information.get("isFirstAC", False)),
                )
            rank_users.append(
                ScpcContestRankUser(
                    rank=int(entry.get("rank", 0)),
                    award_name=str(entry.get("awardName", "")),
                    user_name=str(entry.get("username", "")),
                    real_name=str(entry.get("realname", "")),
                    nick_name=str(entry.get("nickname", "")),
                    school=str(entry.get("school", "")),
                    total=int(entry.get("total", 0)),
                    ac=int(entry.get("ac", 0)),
                    total_time=int(entry.get("totalTime", 0)),
                    information=submission_info,
                )
            )
        return rank_users

    async def get_week_rank(self) -> List[ScpcWeekACUser]:
        response = await fetch_json(scpc_recent_ac_rank_url())
        records = response.get("data", [])
        users: List[ScpcWeekACUser] = []
        for entry in records:
            users.append(
                ScpcWeekACUser(
                    username=str(entry.get("username", "")),
                    avatar="http://scpc.fun" + str(entry.get("avatar", "")),
                    title_name=str(entry.get("titleName") or ""),
                    title_color=str(entry.get("titleColor") or ""),
                    ac=int(entry.get("ac", 0)),
                )
            )
        return users

    async def get_user_info(self, username: str) -> Optional[ScpcUser]:
        response = await fetch_json(scpc_user_info_url(username))
        data_obj = response.get("data")
        if not data_obj:
            return None

        total = int(data_obj.get("total", 0))
        solved = data_obj.get("solvedList") or []
        nickname = str(data_obj.get("nickname") or username)
        signature = str(data_obj.get("signature") or "")
        avatar_val = str(data_obj.get("avatar", ""))
        if avatar_val and not avatar_val.startswith("http"):
            avatar_val = (
                "http://scpc.fun" + avatar_val
                if avatar_val.startswith("/")
                else "http://scpc.fun/" + avatar_val
            )
        return ScpcUser(
            total=total,
            solved_list=solved,
            nickname=nickname,
            signature=signature,
            avatar=avatar_val,
            username=username,
        )

    async def get_recent_contests(self) -> List[Contest]:
        """
        获取 SCPC 近期比赛并直接返回统一 `Contest` 列表
        """
        response = await fetch_json(scpc_recent_contest_url())
        if not response or "data" not in response:
            return []
        records = response.get("data") or []
        contest_list: List[Contest] = []
        for record in records:
            name = str(record.get("title") or "未命名比赛")
            start_time = record.get("startTime")
            duration_secs = int(record.get("duration") or 0)
            cid = int(
                record.get("id") or record.get("contestId") or record.get("cid") or 0
            )
            url = f"http://scpc.fun/contest/{cid}" if cid else "http://scpc.fun/contest"
            contest_list.append(
                Contest(
                    name=name,
                    id=cid,
                    start_time=parse_scpc_time(start_time),
                    duration=duration_secs,
                    url=url,
                )
            )
        return contest_list

    async def get_recent_updated_problems(self) -> List[ScpcUpdatedProblem]:
        response = await fetch_json(scpc_recent_updated_problem_url())
        records = response.get("data") or []
        problems: List[ScpcUpdatedProblem] = []
        for entry in records:
            problems.append(
                ScpcUpdatedProblem(
                    id=int(entry.get("id", 0)),
                    problem_id=str(entry.get("problemId", "")),
                    title=str(entry.get("title", "")),
                    type=int(entry.get("type", 0)),
                    gmt_create=parse_scpc_time(entry.get("gmtCreate")),
                    gmt_modified=parse_scpc_time(entry.get("gmtModified")),
                    url=f"http://scpc.fun/problem/{entry.get('problemId', '')}",
                )
            )
        return problems

    async def get_contests(self) -> List[Contest]:
        json_data = await fetch_json(scpc_contests_url())
        records = (
            json_data.get("data", {}).get("records") or json_data.get("records") or []
        )
        contests: List[Contest] = []
        for record in records:
            name = record.get("title") or record.get("contestName") or "未命名比赛"
            start_time = record.get("startTime")
            duration_secs = int(record.get("duration") or 0)
            cid = int(
                record.get("id") or record.get("contestId") or record.get("cid") or 0
            )
            url = f"http://scpc.fun/contest/{cid}" if cid else "http://scpc.fun/contest"
            contests.append(
                Contest(
                    name=str(name),
                    id=cid,
                    start_time=parse_scpc_time(start_time),
                    duration=duration_secs,
                    url=url,
                )
            )
        return contests


# ----------------------------
# region 核心功能函数
# ----------------------------


async def render_scpc_week_rank_image(users: list) -> Optional[str]:
    try:
        html = webui_helper.render_week_rank(users)
        out_path = os.path.abspath("plugins/acm/assets/scpc_week_rank.png")
        success = await renderer.render_html(html, out_path)
        return out_path if success else None
    except Exception as e:
        LOG.error(f"Render SCPC week rank failed: {e}")
        return None


async def render_scpc_updated_problems_image(problems: list) -> Optional[str]:
    try:
        html = webui_helper.render_updated_problems(problems)
        out_path = os.path.abspath("plugins/acm/assets/scpc_updated_problems.png")
        success = await renderer.render_html(html, out_path)
        return out_path if success else None
    except Exception as e:
        LOG.error(f"Render SCPC updated problems failed: {e}")
        return None


async def render_scpc_user_info_image(user: ScpcUser) -> Optional[str]:
    try:
        ac_count = len(user.solved_list)
        ratio = calculate_accept_ratio(ac_count, user.total)
        ratio_str = f"{ratio:.1f}%"

        html = webui_helper.render_user_info(
            user.nickname,
            user.signature,
            user.total,
            ac_count,
            ratio_str,
            user.username,
            user.avatar,
        )
        out_path = os.path.abspath(f"plugins/acm/assets/scpc_user_{user.username}.png")
        success = await renderer.render_html(html, out_path)
        return out_path if success else None
    except Exception as e:
        LOG.error(f"Render SCPC user info failed: {e}")
        return None


async def render_scpc_contests_image(contests: List[Contest]) -> Optional[str]:
    try:
        html = webui_helper.render_contests(contests)
        out_path = os.path.abspath("plugins/acm/assets/scpc_contests.png")
        success = await renderer.render_html(html, out_path)
        return out_path if success else None
    except Exception as e:
        LOG.error(f"Render SCPC contests failed: {e}")
        return None


async def generate_excel_contest_rank(
    rank_users: List[ScpcContestRankUser], contest_id: int
) -> Optional[str]:
    if not rank_users:
        return None

    try:
        filename = f"SCPC_{contest_id}.xlsx"
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()
        header_format = workbook.add_format(
            {
                "bold": True,
                "fg_color": "#D7E4BC",
                "border": 1,
                "align": "center",
                "font_size": 14,
            }
        )

        ac_format = workbook.add_format(
            {
                "fg_color": "#98FB98",
                "align": "center",
                "bold": True,
                "border": 1,
            }
        )
        first_ac_format = workbook.add_format(
            {
                "fg_color": "#4169E1",
                "font_size": 12,
                "align": "center",
                "bold": True,
                "border": 1,
            }
        )
        center_format = workbook.add_format({"align": "center"})

        field_names = [field.name for field in fields(rank_users[0])]
        field_names.pop()  # Remove 'information'
        chinese_headers = rank_users[0].get_chinese_headers()
        chinese_field_names = [
            chinese_headers[field_name] for field_name in field_names
        ]

        last_index = 0
        for col, chinese_name in enumerate(chinese_field_names):
            worksheet.write(0, col, chinese_name, header_format)
            last_index = col

        last_index += 1

        for problem, information in rank_users[0].information.items():
            worksheet.write(0, last_index, problem, header_format)
            last_index += 1

        for row, item in enumerate(rank_users, start=1):
            column = 0
            for col, field_name in enumerate(field_names):
                try:
                    value = getattr(item, field_name)
                    if isinstance(value, (int, float)):
                        worksheet.write_number(row, col, value, center_format)
                    else:
                        worksheet.write_string(row, col, str(value), center_format)

                except Exception as e:
                    LOG.error(
                        f"Error processing row {row} col {col} (field: {field_name}): {e}"
                    )
                    worksheet.write_string(row, col, "错误", center_format)

                column = col

            column += 1
            for problem, information in item.information.items():
                if information.is_ac:
                    if information.is_first_ac:
                        worksheet.write_string(row, column, f"率先AC", first_ac_format)
                    else:
                        worksheet.write_string(row, column, f"AC", ac_format)
                else:
                    worksheet.write_string(row, column, "")
                column += 1

        # 调整列宽
        for col, chinese_name in enumerate(chinese_field_names):
            # 考虑中文字符宽度，适当增加列宽
            width = max(len(chinese_name) + 12, 12)
            worksheet.set_column(col, col, width)

        workbook.close()
        return os.path.abspath(filename)
    except Exception as e:
        LOG.error(f"Generate Excel rank failed: {e}")
        return None
