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

    def _hex_to_rgb_str(self, h: str, default: str = "0,150,60") -> str:
        h = (h).strip().lstrip("#")
        if len(h) == 6:
            try:
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                return f"{r},{g},{b}"
            except Exception:
                return default
        return default

    def render_week_rank(self, users: list) -> str:
        user_data = []
        for i, u in enumerate(users, start=1):
            title_rgb = self._hex_to_rgb_str(getattr(u, "title_color", ""))
            title_name = getattr(u, "title_name", "")
            username = getattr(u, "username", "")
            avatar = getattr(u, "avatar", "")
            ac = int(getattr(u, "ac", 0))

            rank_color = (
                "#FFD700"
                if i == 1
                else ("#C0C0C0" if i == 2 else ("#CD7F32" if i == 3 else "#64A5FF"))
            )

            user_data.append(
                {
                    "rank": i,
                    "rank_bg": rank_color,
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
        template = self.env.get_template("cf_user_info.html")
        return template.render(title=f"Codeforces 用户信息 - {user.handle}", user=user)

    def render_cf_rating_chart(self, handle: str, history: list) -> str:
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
        template = self.env.get_template("help.html")
        return template.render(title="帮助菜单", commands=commands, version=version)


# Global instance
webui = WebUI()
