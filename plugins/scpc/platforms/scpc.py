from typing import Optional, List, Any
from dataclasses import dataclass
from ..utils import fetch_json
from ..utils import parse_scpc_time
from ..utils import Contest
from ..utils import (
    extract_contest_timing,
    format_timestamp,
    format_hours,
    format_relative_hours,
    state_icon,
)
from ncatbot.utils import get_log
import os
from playwright.async_api import async_playwright

import requests


def scpc_user_info_url(username: str) -> str:
    """
    返回查询 SCPC 用户主页信息的 API 地址

    Args:
    - username: SCPC 用户名
    """
    return f"http://scpc.fun/api/get-user-home-info?username={username}"


def scpc_contests_url(current_page: int = 0, limit: int = 10) -> str:
    """
    返回查询 SCPC 比赛列表的 API 地址

    Args:
    - current_page: 页码，从 0 开始
    - limit: 每页条目数
    """
    return (
        f"http://scpc.fun/api/get-contest-list?currentPage={current_page}&limit={limit}"
    )


def scpc_recent_contest() -> str:
    """
    返回查询 SCPC 近期比赛的 API 地址
    """
    return f"http://scpc.fun/api/get-recent-contest"


def scpc_recent_updated_problem():
    """
    返回查询 SCPC 近期更新题目的 API 地址
    """
    return f"http://scpc.fun/api/get-recent-updated-problem"


def scpc_recent_ac_rank():
    """
    返回查询 SCPC 最近一周过题排行的 API 地址
    """
    return f"http://scpc.fun/api/get-recent-seven-ac-rank"


def scpc_login_url() -> str:
    """
    返回 SCPC 登录接口的 API 地址
    """
    return f"http://scpc.fun/api/login"


@dataclass
class ScpcUser:
    total: int  # 总提交数
    solved_list: List[Any]  # 通过题目列表
    nickname: str  # 昵称
    signature: str  # 个性签名
    avatar: str  # 头像地址


@dataclass
class ScpcWeekACUser:
    username: str  # 用户名
    avatar: str  # 头像地址
    title_name: str  # 头衔名称
    title_color: str  # 16进制RGB
    ac: int  # 通过题目数量


@dataclass
class ScpcContestRankUser:
    rank: int  # 排名
    award_name: str  # 奖项名称
    uid: str  # 用户 ID
    username: str  # 用户名
    real_name: str  # 真实姓名
    gender: str  # 性别
    avatar: str  # 头像地址
    total: int  # 总提交数
    ac: int  # 通过题目数量
    total_time: int  # 总耗时（秒）


@dataclass
class ScpcUpdatedProblem:
    id: int  # 记录 ID
    problem_id: str  # 题目 ID
    title: str  # 题目标题
    type: int  # 题目类型
    gmt_create: int  # 创建时间戳
    gmt_modified: int  # 修改时间戳
    url: str  # 题目页面链接


def scpc_login(username: str, password: str) -> Optional[str]:
    """
    登录 SCPC 并返回授权 Token

    Args:
    - username: 用户名
    - password: 密码

    Returns:
    - 授权 Token登录失败返回 None
    """
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
    if response.status_code != 200:
        return None
    return response.headers.get("Authorization")


def get_scpc_contest_rank(
    contest_id: int,
    token: str,
    current_page: int = 1,
    limit: int = 50,
) -> Optional[List[ScpcContestRankUser]]:
    """
    获取指定比赛的过题排行榜

    Args:
    - contest_id: 比赛 ID
    - token: 授权 Token
    - current_page: 页码
    - limit: 每页条目数

    Returns:
    - `ScpcContestRankUser` 列表请求失败或解析失败返回 None
    """
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
    if response.status_code != 200:
        return None
    try:
        json_data = response.json()
    except Exception:
        return None

    records = json_data.get("data", {}).get("records") or json_data.get("records") or []
    rank_users: List[ScpcContestRankUser] = []
    for record in records:
        try:
            avatar_val = str(record.get("avatar", "") or "")
            if avatar_val and not avatar_val.startswith("http"):
                avatar_val = (
                    "https://scpc.fun" + avatar_val
                    if avatar_val.startswith("/")
                    else "https://scpc.fun/" + avatar_val
                )
            rank_users.append(
                ScpcContestRankUser(
                    rank=int(record.get("rank", 0)),
                    award_name=str(record.get("awardName", "") or ""),
                    uid=str(record.get("uid", "") or ""),
                    username=str(record.get("username", "") or ""),
                    real_name=str(record.get("realname", "") or ""),
                    gender=str(record.get("gender", "") or ""),
                    avatar=avatar_val,
                    total=int(record.get("total", 0)),
                    ac=int(record.get("ac", 0)),
                    total_time=int(record.get("totalTime", 0)),
                )
            )
        except Exception:
            continue
    return rank_users


def get_scpc_rank() -> Optional[List[ScpcWeekACUser]]:
    """
    获取 SCPC 最近一周过题排行列表

    返回:
    - `ScpcWeekACUser` 列表失败返回 None
    """
    json_data = fetch_json(scpc_recent_ac_rank())
    if not json_data or "data" not in json_data:
        return None
    records = json_data.get("data") or []
    users: List[ScpcWeekACUser] = []
    for entry in records:
        try:
            username = entry.get("username") or ""
            avatar = str(entry.get("avatar") or "")
            avatar = (
                "http://scpc.fun" + avatar
                if avatar.startswith("/")
                else "http://scpc.fun/" + avatar
            )
            title_name = entry.get("titleName") or ""
            title_color = entry.get("titleColor") or ""
            ac = int(entry.get("ac", 0))
            users.append(
                ScpcWeekACUser(
                    username=username,
                    avatar=avatar,
                    title_name=title_name,
                    title_color=title_color,
                    ac=ac,
                )
            )
        except Exception:
            continue
    return users


def get_scpc_user_info(username: str) -> Optional[ScpcUser]:
    """
    获取 SCPC 用户主页信息并解析为 `ScpcUser`

    Args:
    - username: 用户名
    """
    json_data = fetch_json(scpc_user_info_url(username))
    if not json_data or "data" not in json_data:
        return None
    data_obj = json_data.get("data") or {}
    total = int(data_obj.get("total", 0))
    solved = data_obj.get("solvedList") or []
    nickname = str(data_obj.get("nickname") or username)
    signature = str(data_obj.get("signature") or "")
    avatar_val = str(data_obj.get("avatar", "") or "")
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
    )


async def render_scpc_week_rank_image(users: list) -> str | None:
    try:

        def hex_to_rgb_str(h: str, default: str = "0,150,60"):
            h = (h or "").strip().lstrip("#")
            if len(h) == 6:
                try:
                    r = int(h[0:2], 16)
                    g = int(h[2:4], 16)
                    b = int(h[4:6], 16)
                    return f"{r},{g},{b}"
                except Exception:
                    return default
            return default

        rows = []
        for i, u in enumerate(users, start=1):
            title_rgb = hex_to_rgb_str(getattr(u, "title_color", ""))
            title_name = getattr(u, "title_name", "") or ""
            username = getattr(u, "username", "") or ""
            avatar = getattr(u, "avatar", "") or ""
            ac = int(getattr(u, "ac", 0))
            rank_color = (
                "#FFD700"
                if i == 1
                else ("#C0C0C0" if i == 2 else ("#CD7F32" if i == 3 else "#64A5FF"))
            )
            pill_html = (
                ""
                if not title_name
                else f"<div class='pill' style='color:rgb({title_rgb});border-color:rgb({title_rgb});background:rgba({title_rgb},0.12)'>{title_name}</div>"
            )
            rows.append(
                f"""
                <div class='row'>
                  <div class='rank' style='background:{rank_color}'>{i}</div>
                  <div class='avatar-wrap'>
                    <img class='avatar' src='{avatar}' onerror="this.style.display='none'; this.parentNode.classList.add('fallback')"/>
                    <div class='avatar-fallback'>{(username[:1] or ' ').upper()}</div>
                  </div>
                  <div class='user'><span class='username'>{username}</span>{pill_html}</div>
                  <div class='ac'>AC {ac}</div>
                </div>
                """
            )
        html = f"""
        <html>
          <head>
            <meta charset='utf-8'/>
            <style>
              :root {{ --w: 680px; }}
              body {{ margin:0; background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif; }}
              .card {{ width:var(--w); padding:16px 20px 20px; background:#fff; }}
              .header {{ display:flex; align-items:center; justify-content:space-between; gap:10px; padding:14px 8px; background:#f5f8ff; border-radius:12px; color:#173172; font-weight:600; font-size:22px; }}
              .list {{ margin-top:8px; display:flex; flex-direction:column; gap:8px; }}
              .row {{ display:grid; grid-template-columns: 36px 56px 1fr 80px; align-items:center; gap:10px; padding:10px 10px; border-radius:12px; background:#fbfdff; border:1px solid #eef3ff; }}
              .rank {{ width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#000; font-weight:600; }}
              .avatar-wrap {{ position:relative; width:56px; height:56px; border-radius:50%; overflow:hidden; background:#eee; display:flex; align-items:center; justify-content:center; }}
              .avatar {{ width:100%; height:100%; object-fit:cover; display:block; }}
              .avatar-fallback {{ display:none; width:100%; height:100%; border-radius:50%; background:#789; color:#fff; font-weight:700; font-size:22px; align-items:center; justify-content:center; }}
              .avatar-wrap.fallback .avatar-fallback {{ display:flex; }}
              .user {{ display:flex; align-items:center; gap:8px; }}
              .username {{ color:#222; font-size:18px; font-weight:600; }}
              .pill {{ display:inline-block; max-width:200px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding:6px 12px; border-radius:12px; border:2px solid; font-size:14px; font-weight:600; flex-shrink:0; }}
              .ac {{ color:#0a9c54; font-weight:800; font-size:22px; justify-self:end; }}
              .note {{ color:#6b7280; font-weight:500; font-size:12px; }}
            </style>
          </head>
          <body>
            <div class='card'>
              <div class='header'>
                <span>最近一周过题榜单</span>
                <span class='note'>图片来源于安心Bot</span>
              </div>
              <div class='list'>
                {''.join(rows)}
              </div>
            </div>
          </body>
        </html>
        """
        out_path = os.path.abspath("plugins/scpc/assets/scpc_week_rank.png")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 720, "height": 600})
            await page.set_content(html)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            card = page.locator(".card")
            try:
                await card.wait_for(state="visible")
            except Exception:
                pass
            try:
                h = await page.evaluate(
                    "document.querySelector('.card')?.getBoundingClientRect().height || 600"
                )
                await page.set_viewport_size({"width": 720, "height": int(h) + 40})
            except Exception:
                pass
            ok = False
            try:
                await card.screenshot(path=out_path)
                ok = os.path.exists(out_path)
            except Exception:
                ok = False
            if not ok:
                try:
                    await page.screenshot(path=out_path, full_page=False)
                    ok = os.path.exists(out_path)
                except Exception:
                    ok = False
            await browser.close()
        return out_path if ok else None
    except Exception:
        return None


async def render_scpc_user_info_image(
    nickname: str,
    signature: str,
    total: int,
    ac: int,
    accept_ratio: str,
    username: str,
    avatar: str,
) -> str | None:
    try:
        title = "SCPC 个人信息"
        html = f"""
        <html>
          <head>
            <meta charset='utf-8'/>
            <style>
              :root {{ --w: 680px; }}
              body {{ margin:0; background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif; }}
              .card {{ width:var(--w); padding:16px 20px 20px; background:#fff; }}
              .header {{ display:flex; align-items:center; justify-content:space-between; gap:10px; padding:14px 8px; background:#f5f8ff; border-radius:12px; color:#173172; font-weight:600; font-size:22px; }}
              .note {{ color:#6b7280; font-weight:500; font-size:12px; }}
              .profile {{ display:grid; grid-template-columns: 72px 1fr; align-items:center; gap:14px; padding:14px 8px; }}
              .avatar-wrap {{ position:relative; width:72px; height:72px; border-radius:50%; overflow:hidden; background:#f3f4f6; display:flex; align-items:center; justify-content:center; border:2px solid #c7d2fe; box-shadow:0 2px 6px rgba(0,0,0,0.08); }}
              .avatar {{ width:100%; height:100%; object-fit:cover; display:block; }}
              .avatar-fallback {{ display:none; width:100%; height:100%; border-radius:50%; background:#64748b; color:#fff; font-weight:800; font-size:28px; align-items:center; justify-content:center; }}
              .avatar-wrap.fallback .avatar-fallback {{ display:flex; }}
              .nickname {{ color:#111827; font-size:22px; font-weight:800; }}
              .handle {{ color:#6b7280; font-size:14px; font-weight:600; margin-left:8px; }}
              .signature {{ color:#6b7280; font-size:14px; margin-top:4px; }}
              .stats {{ margin-top:10px; display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px; }}
              .stat {{ background:#fbfdff; border:1px solid #eef3ff; border-radius:12px; padding:12px; display:flex; flex-direction:column; gap:6px; }}
              .stat-label {{ color:#6b7280; font-size:12px; }}
              .stat-value {{ color:#111827; font-size:20px; font-weight:800; }}
            </style>
          </head>
          <body>
            <div class='card'>
              <div class='header'>
                <span>{title}</span>
                <span class='note'>图片来源于安心Bot</span>
              </div>
              <div class='profile'>
                <div class='avatar-wrap'>
                  <img class='avatar' src='{avatar}' onerror="this.style.display='none'; this.parentNode.classList.add('fallback')"/>
                  <div class='avatar-fallback'>{(nickname[:1] or username[:1] or ' ').upper()}</div>
                </div>
                <div>
                  <div class='nickname'>{nickname}<span class='handle'>@{username}</span></div>
                  <div class='signature'>{signature}</div>
                </div>
              </div>
              <div class='stats'>
                <div class='stat'><div class='stat-label'>提交数</div><div class='stat-value'>{total}</div></div>
                <div class='stat'><div class='stat-label'>AC数</div><div class='stat-value'>{ac}</div></div>
                <div class='stat'><div class='stat-label'>通过率</div><div class='stat-value'>{accept_ratio}%</div></div>
              </div>
            </div>
          </body>
        </html>
        """
        out_path = os.path.abspath(f"plugins/scpc/assets/scpc_user_{username}.png")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 720, "height": 600})
            await page.set_content(html)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            card = page.locator(".card")
            try:
                await card.wait_for(state="visible")
            except Exception:
                pass
            try:
                h = await page.evaluate(
                    "document.querySelector('.card')?.getBoundingClientRect().height || 600"
                )
                await page.set_viewport_size({"width": 720, "height": int(h) + 40})
            except Exception:
                pass
            ok = False
            try:
                await card.screenshot(path=out_path)
                ok = os.path.exists(out_path)
            except Exception:
                ok = False
            if not ok:
                try:
                    await page.screenshot(path=out_path, full_page=False)
                    ok = os.path.exists(out_path)
                except Exception:
                    ok = False
            await browser.close()
        return out_path if ok else None
    except Exception:
        return None


async def render_scpc_contests_image(contests: List[Contest]) -> str | None:
    try:
        now_ts = int(__import__("datetime").datetime.now().timestamp())
        rows = []
        for c in contests:
            t = extract_contest_timing(c, now_ts)
            if not t:
                continue
            state, remaining_label, remaining_secs, duration_secs, start_ts, _ = t
            icon = state_icon(state)
            start_str = format_timestamp(start_ts)
            remaining_str = format_relative_hours(remaining_secs, precision=1)
            duration_str = format_hours(duration_secs, precision=1)
            cid = c.contest_id or ""
            id_pill = "" if not cid else f"<span class='pill'>ID {cid}</span>"
            rows.append(
                f"""
                <div class='row'>
                  <div class='title'>
                    <span class='state'>{icon} {state}</span>
                    <span class='name'>{c.name}</span>
                    {id_pill}
                  </div>
                  <div class='meta'>开始: {start_str} · {remaining_label}: {remaining_str} · 时长: {duration_str} 小时</div>
                </div>
                """
            )
        html = f"""
        <html>
          <head>
            <meta charset='utf-8'/>
            <style>
              :root {{ --w: 680px; }}
              body {{ margin:0; background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif; }}
              .card {{ width:var(--w); padding:16px 20px 20px; background:#fff; }}
              .header {{ display:flex; align-items:center; justify-content:space-between; gap:10px; padding:14px 8px; background:#f5f8ff; border-radius:12px; color:#173172; font-weight:600; font-size:22px; }}
              .note {{ color:#6b7280; font-weight:500; font-size:12px; }}
              .list {{ margin-top:8px; display:flex; flex-direction:column; gap:8px; }}
              .row {{ display:flex; flex-direction:column; gap:6px; padding:10px 10px; border-radius:12px; background:#fbfdff; border:1px solid #eef3ff; }}
              .title {{ display:flex; align-items:center; gap:8px; }}
              .state {{ color:#0f172a; font-weight:700; }}
              .name {{ color:#111827; font-size:16px; font-weight:700; }}
              .pill {{ display:inline-block; padding:4px 10px; border-radius:12px; border:1px solid #c7d2fe; color:#3730a3; background:#eef2ff; font-size:12px; font-weight:600; }}
              .meta {{ color:#6b7280; font-size:13px; }}
            </style>
          </head>
          <body>
            <div class='card'>
              <div class='header'>
                <span>SCPC 比赛信息</span>
                <span class='note'>图片来源于安心Bot</span>
              </div>
              <div class='list'>
                {''.join(rows)}
              </div>
            </div>
          </body>
        </html>
        """
        out_path = os.path.abspath("plugins/scpc/assets/scpc_contests.png")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 720, "height": 600})
            await page.set_content(html)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            card = page.locator(".card")
            try:
                await card.wait_for(state="visible")
            except Exception:
                pass
            try:
                h = await page.evaluate(
                    "document.querySelector('.card')?.getBoundingClientRect().height || 600"
                )
                await page.set_viewport_size({"width": 720, "height": int(h) + 40})
            except Exception:
                pass
            ok = False
            try:
                await card.screenshot(path=out_path)
                ok = os.path.exists(out_path)
            except Exception:
                ok = False
            if not ok:
                try:
                    await page.screenshot(path=out_path, full_page=False)
                    ok = os.path.exists(out_path)
                except Exception:
                    ok = False
            await browser.close()
        return out_path if ok else None
    except Exception:
        return None


def get_scpc_contests(
    current_page: int = 0, limit: int = 10
) -> Optional[List[Contest]]:
    """
    获取 SCPC 比赛列表并直接返回统一 `Contest` 列表
    """
    json_data = fetch_json(scpc_contests_url(current_page, limit))
    if not json_data:
        return None
    records = json_data.get("data", {}).get("records") or json_data.get("records") or []
    contests: List[Contest] = []
    for record in records:
        try:
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
                    contest_id=cid,
                    start_ts=parse_scpc_time(start_time),
                    duration_secs=duration_secs,
                    url=url,
                )
            )
        except Exception:
            continue
    return contests


def get_scpc_recent_contests() -> Optional[List[Contest]]:
    """
    获取 SCPC 近期比赛并直接返回统一 `Contest` 列表
    """
    json_data = fetch_json(scpc_recent_contest())
    if not json_data:
        return None
    records = json_data.get("data") or []
    contest_list: List[Contest] = []
    for record in records:
        try:
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
                    contest_id=cid,
                    start_ts=parse_scpc_time(start_time),
                    duration_secs=duration_secs,
                    url=url,
                )
            )
        except Exception:
            continue
    return contest_list


def get_scpc_recent_updated_problems() -> Optional[List[ScpcUpdatedProblem]]:
    """
    获取 SCPC 近期更新题目并解析为 `ScpcUpdatedProblem` 列表

    Returns:
    - `ScpcUpdatedProblem` 列表失败返回 None
    """
    body = fetch_json(scpc_recent_updated_problem())
    if not body:
        return None
    raw = body.get("data") or []
    items: List[ScpcUpdatedProblem] = []
    for r in raw:
        try:
            rid = int(r.get("id", 0))
            pid = str(r.get("problemId", "") or "")
            title = str(r.get("title", "") or "")
            typ = int(r.get("type", 0))
            created = parse_scpc_time(r.get("gmtCreate"))
            modified = parse_scpc_time(r.get("gmtModified"))
            url = f"http://scpc.fun/problem/{pid}" if pid else "http://scpc.fun/problem"
            items.append(
                ScpcUpdatedProblem(
                    id=rid,
                    problem_id=pid,
                    title=title,
                    type=typ,
                    gmt_create=created,
                    gmt_modified=modified,
                    url=url,
                )
            )
        except Exception:
            continue
    return items


LOG = get_log()
