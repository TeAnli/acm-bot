import datetime
import os

from jinja2 import Environment, FileSystemLoader

from .text import (
    extract_contest_timing,
    format_hours,
    format_relative_hours,
    format_timestamp,
    state_icon,
)


class WebUI:
    def __init__(self):
        self.template_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "templates"
        )
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        self.env.filters["datetime"] = lambda ts: datetime.datetime.fromtimestamp(
            ts
        ).strftime("%Y-%m-%d %H:%M")

    def _hex_to_rgb_str(self, h: str, default: str = "0,150,60") -> str:
        """
        将 16 进制颜色字符串转换为 RGB 字符串 (r,g,b)

        Args:
            h (str): 16 进制颜色字符串 (如 "#FF0000" 或 "FF0000")
            default (str): 转换失败时的默认值

        Returns:
            str: "r,g,b" 格式的字符串
        """
        h = (h or "").strip().lstrip("#")
        if len(h) != 6:
            return default
            
        try:
            return ",".join(str(int(h[i : i + 2], 16)) for i in (0, 2, 4))
        except Exception:
            return default

    def render_week_rank(self, users: list) -> str:
        """
        渲染周榜单图片

        Args:
            users (list): 包含 ScpcWeekACUser 对象的列表

        Returns:
            str: 渲染后的 HTML 字符串
        """
        user_data = []
        rank_colors = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32"}
        default_rank_color = "#64A5FF"

        for i, u in enumerate(users, start=1):
            title_rgb = self._hex_to_rgb_str(getattr(u, "title_color", ""))
            title_name = getattr(u, "title_name", "")
            username = getattr(u, "username", "")
            avatar = getattr(u, "avatar", "")
            ac = int(getattr(u, "ac", 0))

            user_data.append(
                {
                    "rank": i,
                    "rank_bg": rank_colors.get(i, default_rank_color),
                    "avatar": avatar,
                    "avatar_char": (username[:1] or " ").upper(),
                    "username": username,
                    "title_name": title_name,
                    "title_rgb": title_rgb,
                    "ac": ac,
                }
            )

        template = self.env.get_template("week_rank.html")
        return template.render(title="最近一周过题榜单", users=user_data)

    def render_user_info(
        self,
        nickname: str,
        signature: str,
        total: int,
        ac: int,
        accept_ratio: str,
        username: str,
        avatar: str,
    ) -> str:
        """
        渲染用户信息图片

        Args:
            nickname: 用户昵称
            signature: 签名
            total: 总提交数
            ac: 通过数
            accept_ratio: 通过率字符串 (如 "50.5%")
            username: 用户名
            avatar: 头像 URL

        Returns:
            str: 渲染后的 HTML 字符串
        """
        template = self.env.get_template("user_info.html")
        return template.render(
            title="SCPC 个人信息",
            nickname=nickname,
            signature=signature,
            total=total,
            ac=ac,
            accept_ratio=accept_ratio,
            username=username,
            avatar=avatar,
            avatar_char=(nickname[:1] or username[:1] or " ").upper(),
        )

    def render_contests(self, contests: list) -> str:
        """
        渲染比赛列表图片

        Args:
            contests: Contest 对象列表

        Returns:
            str: 渲染后的 HTML 字符串
        """
        now_ts = int(datetime.datetime.now().timestamp())
        contest_data = []
        for c in contests:
            t = extract_contest_timing(c, now_ts)
            if not t:
                continue
            state, remaining_label, remaining_secs, duration_secs, start_ts, _ = t

            contest_data.append(
                {
                    "icon": state_icon(state),
                    "state": state,
                    "name": c.name,
                    "id": c.id,
                    "start_str": format_timestamp(start_ts),
                    "remaining_label": remaining_label,
                    "remaining_str": format_relative_hours(remaining_secs, precision=1),
                    "duration_str": format_hours(duration_secs, precision=1),
                }
            )

        template = self.env.get_template("contests.html")
        return template.render(title="SCPC 比赛信息", contests=contest_data)

    def render_cf_user_info(self, user) -> str:
        """
        渲染 Codeforces 用户信息

        Args:
            user: CodeforcesUser 对象

        Returns:
            str: 渲染后的 HTML 字符串
        """
        template = self.env.get_template("cf_user_info.html")
        return template.render(title=f"Codeforces 用户信息 - {user.handle}", user=user)

    def render_cf_rating_chart(self, handle: str, history: list) -> str:
        """
        渲染 Codeforces Rating 图表

        Args:
            handle: 用户 Handle
            history: Rating 历史列表

        Returns:
            str: 渲染后的 HTML 字符串
        """
        labels = []
        data = []
        point_meta = []

        for h in history:
            dt = datetime.datetime.fromtimestamp(h.rating_update_time_seconds)
            labels.append(dt.strftime("%Y-%m-%d"))
            data.append(h.new_rating)
            point_meta.append(
                {
                    "contest": h.contest_name,
                    "rank": h.rank,
                    "old": h.old_rating,
                    "new": h.new_rating,
                }
            )

        template = self.env.get_template("cf_rating_chart.html")
        return template.render(
            title=f"Rating 记录表 - {handle}",
            handle=handle,
            labels=labels,
            data=data,
            meta=point_meta,
        )

    def render_help(self, commands: list, version: str) -> str:
        """
        渲染帮助菜单

        Args:
            commands: 命令列表
            version: 版本号

        Returns:
            str: 渲染后的 HTML 字符串
        """
        template = self.env.get_template("help.html")
        return template.render(title="帮助菜单", commands=commands, version=version)

    def render_updated_problems(self, problems: list) -> str:
        """
        渲染近期更新题目

        Args:
            problems: ScpcUpdatedProblem 对象列表

        Returns:
            str: 渲染后的 HTML 字符串
        """
        template = self.env.get_template("updated_problems.html")
        return template.render(title="SCPC 近期更新题目", problems=problems)


webui_helper = WebUI()