from datetime import datetime
from dataclasses import dataclass
from os import name

from ncatbot.core import GroupMessageEvent
from ncatbot.plugin_system import NcatBotPlugin, group_admin_filter, group_filter
from ncatbot.plugin_system import command_registry
from ncatbot.utils import get_log

import random
import requests
import os

from .platforms.codeforces import (
    get_codeforces_contests,
    get_codeforces_user_rating,
)
from .platforms.scpc import (
    generate_excel_contest_rank,
    get_scpc_user_info,
    get_scpc_contests,
    scpc_login,
    get_scpc_contest_rank,
    get_scpc_recent_contests,
    get_scpc_recent_updated_problems,
    get_scpc_rank as fetch_scpc_week_rank,
    render_scpc_week_rank_image,
    render_scpc_user_info_image,
    render_scpc_contests_image,
)
from .utils import (
    calculate_accept_ratio,
    format_contest_text,
    broadcast_text,
    format_timestamp,
    Contest,
    extract_contest_timing,
)
from .platforms.nowcoder import (
    get_nowcoder_recent_contests,
)

LOG = get_log()

DEFAULT_SCPC_USERNAME = "player281"
DEFAULT_SCPC_PASSWORD = "123456"


@dataclass
class ContestWithSource:
    source: str
    contest: Contest


PROVIDERS = [
    ("cf", get_codeforces_contests),
    ("scpc", get_scpc_contests),
    ("nowcoder", get_nowcoder_recent_contests),
]


def get_aggregated_contests(
    include_cf: bool = True,
    include_scpc: bool = True,
    include_nowcoder: bool = True,
    timeout_cf: int = 10,
    scpc_limit: int = 10,
) -> list[ContestWithSource]:
    now_ts = int(datetime.now().timestamp())
    items: list[tuple[int, ContestWithSource]] = []
    for source, fetch in PROVIDERS:
        if source == "cf" and not include_cf:
            continue
        if source == "scpc" and not include_scpc:
            continue
        if source == "nowcoder" and not include_nowcoder:
            continue
        if source == "cf":
            lst = fetch(timeout=timeout_cf) or []
        elif source == "scpc":
            lst = fetch(limit=scpc_limit) or []
        else:
            lst = fetch() or []
        for c in lst:
            timing = extract_contest_timing(c, now_ts)
            if timing:
                sort_key = timing[-1]
                items.append((sort_key, ContestWithSource(source, c)))
    items.sort(key=lambda x: x[0])
    return [it[1] for it in items]


class SCPCPlugin(NcatBotPlugin):
    name = "SCPC"
    version = "0.0.2"
    author = "TeAnli"
    description = "专为西南科技大学 SCPC 团队 打造的 ncatbot 机器人插件"

    group_listeners = dict[str, bool]()
    cf_alerted_ids = set[int]()

    async def on_load(self):
        """
        注册比赛监听的定时任务 (每 30 分钟执行一次)
        """
        LOG.info("SCPC 插件启动中")
        try:
            self.add_scheduled_task(
                self._listen_task,
                "cf_contest_watch",
                "30m",
            )
            LOG.info("已注册 CF 比赛监听任务 (每 30 分钟检查一次)")
        except Exception as e:
            LOG.warning(f"注册定时任务失败: {e}")

    async def _listen_task(self):
        """
        定时任务主体: 检查 CF 与 SCPC 比赛, 在开始前限定时间内提醒开启监听的群
        """
        LOG.info(f"检测群组和比赛任务 订阅比赛提醒的群组: {self.group_listeners}")
        if not any(self.group_listeners.values()):
            LOG.info("CF 比赛监听已禁用或未配置群组.")
            return
        await self._check_cf_contests_and_notify(threshold_hours=2)
        await self._check_scpc_contests_and_notify(threshold_hours=2)

    async def _send_upcoming_notifications(
        self, upcoming_texts: list[tuple[int, str]], empty_log_message: str
    ):
        """
        对即将开始的比赛提醒进行统一排序与广播处理

        Args:
        - upcoming_texts: 元组列表 (remaining_secs, text)
        - empty_log_message: 当无提醒时的日志信息
        """
        upcoming_texts.sort(key=lambda x: x[0])
        if not upcoming_texts:
            LOG.info(empty_log_message)
            return
        merged = "\n\n".join([t for _, t in upcoming_texts])
        await broadcast_text(self.api, self.group_listeners, merged)

    def _format_single_contest(
        self,
        c: Contest,
        now_ts: int,
        include_id: bool,
        source_label: str | None = None,
        skip_verify_name: bool = False,
    ) -> tuple[int, str] | None:
        if skip_verify_name and ("验题" in c.name):
            return None
        timing = extract_contest_timing(c, now_ts)
        if not timing:
            return None
        state, remaining_label, remaining_secs, duration_secs, start_ts, sort_key = (
            timing
        )
        text = format_contest_text(
            name=c.name,
            contest_id=c.contest_id,
            state=state,
            start_ts=start_ts,
            remaining_label=remaining_label,
            remaining_secs=remaining_secs,
            duration_secs=duration_secs,
            include_id=include_id,
            contest_url=c.url,
        )
        if source_label:
            text = f"{text}\n来源: {source_label}"
        return sort_key, text

    def _build_contest_texts(
        self,
        contests: list[Contest],
        include_id: bool,
        source: str | None = None,
        skip_verify_name: bool = False,
    ) -> list[tuple[int, str]]:
        now_ts = int(datetime.now().timestamp())
        source_map = {"cf": "Codeforces", "scpc": "SCPC", "nowcoder": "牛客"}
        label = source_map.get(source, source) if source else None
        items: list[tuple[int, str]] = []
        for c in contests:
            formatted = self._format_single_contest(
                c, now_ts, include_id, label, skip_verify_name
            )
            if formatted:
                items.append(formatted)
        items.sort(key=lambda x: x[0])
        return items

    async def _check_cf_contests_and_notify(self, threshold_hours: int = 2):
        """
        检查 CF 比赛, 筛选在 `threshold_hours` 小时内即将开始的比赛, 并向监听群提醒

        Args:
        - threshold_hours: 提醒的时间阈值 (小时)
        """
        contests = get_codeforces_contests()
        if not contests:
            LOG.warning("获取 CF 比赛失败：无数据或状态异常")
            return
        threshold_seconds = threshold_hours * 3600
        upcoming_texts = []
        now_ts = int(datetime.now().timestamp())
        for c in contests:
            cid = c.contest_id
            timing = extract_contest_timing(c, now_ts)
            if not timing:
                continue
            state, remaining_label, remaining_secs, duration, start_ts, _ = timing
            if state == "即将开始" and remaining_secs <= threshold_seconds:
                if cid in self.cf_alerted_ids:
                    continue
                if cid is not None:
                    self.cf_alerted_ids.add(cid)
                text = format_contest_text(
                    name=c.name,
                    contest_id=c.contest_id,
                    state=state,
                    start_ts=start_ts,
                    remaining_label=remaining_label,
                    remaining_secs=remaining_secs,
                    duration_secs=duration,
                    contest_url=c.url,
                )
                upcoming_texts.append((remaining_secs, text))
        await self._send_upcoming_notifications(
            upcoming_texts,
            "限定时间内无即将开始的 CF 比赛，不发送通知",
        )

    async def _check_scpc_contests_and_notify(self, threshold_hours: int = 2):
        """
        检查 SCPC 比赛, 筛选在 `threshold_hours` 小时内即将开始的比赛, 并向监听群提醒

        Args:
        - threshold_hours: 提醒的时间阈值 (小时)
        """
        records = get_scpc_contests()
        if not records:
            LOG.warning("获取 SCPC 比赛失败：无数据或状态异常")
            return
        threshold_seconds = threshold_hours * 3600
        now_ts = int(datetime.now().timestamp())
        upcoming_texts = []
        for r in records:
            if "验题" in r.name:
                continue
            timing = extract_contest_timing(r, now_ts)
            if not timing:
                continue
            state, remaining_label, remaining_secs, duration, start_ts, _ = timing
            if state == "即将开始" and remaining_secs <= threshold_seconds:
                text = format_contest_text(
                    name=r.name,
                    contest_id=None,
                    state=state,
                    start_ts=start_ts,
                    remaining_label=remaining_label,
                    remaining_secs=remaining_secs,
                    duration_secs=duration,
                    include_id=False,
                    contest_url=r.url,
                )
                upcoming_texts.append((remaining_secs, text))
        await self._send_upcoming_notifications(
            upcoming_texts,
            "限定时间内无即将开始的 SCPC 比赛，不发送通知",
        )

    @command_registry.command("来个男神", description="随机发送一张男神照片")
    @group_admin_filter
    @group_filter
    async def random_god_image(self, event: GroupMessageEvent):
        LOG.info(f"用户 {event.user_id} 请求随机图片")
        random_id = random.randint(1, 5)
        image_path = f"plugins/scpc/assets/image{random_id}.png"
        await self.api.send_group_image(event.group_id, image_path)

    @command_registry.command("添加比赛监听器", description="为当前群开启比赛监听任务")
    @group_admin_filter
    @group_filter
    async def add_contest_listener(self, event: GroupMessageEvent):
        LOG.info(f"用户 {event.user_id} 添加了比赛订阅 至 {event.group_id}")
        self.group_listeners[event.group_id] = True
        await self.api.send_group_text(event.group_id, "已为本群开启比赛监听任务")

    @command_registry.command("移除比赛监听器", description="为当前群关闭比赛监听任务")
    @group_admin_filter
    @group_filter
    async def remove_contest_listener(self, event: GroupMessageEvent):
        LOG.info(f"User {event} removed contest listener for contest")
        self.group_listeners[event.group_id] = False
        await self.api.send_group_text(event.group_id, "已为本群关闭比赛监听任务")

    @command_registry.command("scpc信息", description="查询scpc网站的个人信息")
    @group_filter
    async def get_user_info(self, event: GroupMessageEvent, username: str):
        data = get_scpc_user_info(username)
        if not data:
            LOG.warning(f"获取 SCPC 用户信息失败：{username}")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 用户信息, 请稍后重试"
            )
            return

        LOG.info(f"获取 SCPC 用户信息: {data}")
        total = int(getattr(data, "total", 0))
        solved_list = getattr(data, "solved_list", []) or []
        accept_ratio = "{:.2f}".format(
            calculate_accept_ratio(total, len(solved_list)) * 100
        )
        nickname = getattr(data, "nickname", username) or username
        signature = getattr(data, "signature", "") or ""
        avatar = getattr(data, "avatar", "") or ""
        img_path = await render_scpc_user_info_image(
            nickname=nickname,
            signature=signature,
            total=total,
            ac=len(solved_list),
            accept_ratio=accept_ratio,
            username=username,
            avatar=avatar,
        )
        if img_path:
            await self.api.send_group_image(event.group_id, img_path)
            return
        user_text = (
            f"SCPC 个人信息：\n"
            f"昵称: {nickname}\n"
            f"签名: {signature}\n"
            f"提交数: {total}\n"
            f"AC数: {len(solved_list)}\n"
            f"题目通过率: {accept_ratio}%"
        )
        await self.api.send_group_text(event.group_id, user_text)

    async def _get_codeforces_contests(self, group_id: str):
        """
        概述:
        拉取 CF 比赛列表并格式化后发送到指定群

        参数:
        - group_id: 目标群组 ID
        """
        contests = get_codeforces_contests()
        if contests is None:
            LOG.warning("获取 CF 比赛失败：请求异常或状态不正确")
            await self.api.send_group_text(
                group_id, "暂时无法获取 Codeforces 比赛信息, 请稍后重试"
            )
            return
        LOG.info(f"获取 CF 比赛列表：共 {len(contests)} 场")
        texts = self._build_contest_texts(contests, include_id=True, source="cf")
        if texts:
            await self.api.send_group_text(group_id, "\n\n".join([t for _, t in texts]))
        else:
            await self.api.send_group_text(
                group_id, "近期暂无即将开始或进行中的 Codeforces 比赛"
            )

    @command_registry.command("scpc比赛", description="获取SCPC比赛信息")
    @group_filter
    async def get_scpc_contests(self, event: GroupMessageEvent):
        records = get_scpc_contests()
        if records is None:
            LOG.warning("获取 SCPC 比赛失败：无数据")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 比赛信息, 请稍后重试"
            )
            return
        img_path = await render_scpc_contests_image(records)
        if img_path:
            await self.api.send_group_image(event.group_id, img_path)
            return
        texts = self._build_contest_texts(
            records, include_id=False, source="scpc", skip_verify_name=True
        )
        if texts:
            await self.api.send_group_text(
                event.group_id, "\n\n".join([t for _, t in texts])
            )
        else:
            await self.api.send_group_text(
                event.group_id, "近期暂无即将开始或进行中的 SCPC 比赛"
            )

    @command_registry.command("scpc排行", description="获取SCPC最近一周过题排行")
    @group_filter
    async def get_scpc_week_rank_command(self, event: GroupMessageEvent):
        records = fetch_scpc_week_rank()
        if records is None:
            LOG.warning("获取 SCPC 排行失败：无数据")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 排行信息, 请稍后重试"
            )
            return
        img_path = await render_scpc_week_rank_image(records)
        if img_path:
            await self.api.send_group_image(event.group_id, img_path)
            return
        lines = []
        for i, record in enumerate(records, start=1):
            lines.append(f"#{i} {record.username} | AC:{record.ac}")
        await self.api.send_group_text(event.group_id, "\n".join(lines))

    @command_registry.command("cf积分", description="获取codeforces比赛信息")
    @group_filter
    async def get_codeforces_user_rating(self, event: GroupMessageEvent, username: str):
        ratings = get_codeforces_user_rating(username)
        if ratings is not None:
            LOG.info(f"获取 CF 用户积分记录：{len(ratings)} 条")

            if not ratings:
                await self.api.send_group_text(
                    event.group_id, f"用户 {username} 没有比赛记录"
                )
                return

            last_contest = ratings[-1]
            ratings_text = f"新积分: {last_contest.new_rating}\n"

            await self.api.send_group_text(event.group_id, ratings_text.strip())
        else:
            LOG.warning("获取 CF 用户积分失败：请求异常或状态不正确")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 Codeforces 用户积分信息, 请稍后重试"
            )

    @command_registry.command("cf比赛", description="获取codeforces比赛信息")
    @group_filter
    async def get_codeforces_contests(self, event: GroupMessageEvent):
        await self._get_codeforces_contests(event.group_id)

    @command_registry.command("scpc近期比赛", description="获取近期SCPC比赛信息")
    @group_filter
    async def get_recent_scpc_contests(self, event: GroupMessageEvent):
        records = get_scpc_recent_contests()
        if records is None:
            LOG.warning("获取 SCPC 近期比赛失败：无数据")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 近期比赛信息, 请稍后重试"
            )
            return
        texts = self._build_contest_texts(records, include_id=False, source="scpc")
        if texts:
            await self.api.send_group_text(
                event.group_id, "\n\n".join([t for _, t in texts])
            )
        else:
            await self.api.send_group_text(
                event.group_id, "近期暂无即将开始或进行中的 SCPC 比赛"
            )

    @command_registry.command("scpc近期更新题目", description="获取近期SCPC更新题目")
    @group_filter
    async def get_recent_scpc_updated_problems(self, event: GroupMessageEvent):
        items = get_scpc_recent_updated_problems()
        LOG.info(f"获取 SCPC 近期更新题目：{items} 条")
        if not items:
            LOG.warning("获取 SCPC 近期更新题目失败：无数据")
            await self.api.send_group_text(
                event.group_id, "暂时无法获取 SCPC 近期更新题目, 请稍后重试"
            )
            return
        lines = []
        for p in items:
            time_str = (
                format_timestamp(p.gmt_modified)
                if isinstance(p.gmt_modified, int) and p.gmt_modified > 0
                else str(p.gmt_modified)
            )
            lines.append(
                f"题目: {p.title}\nID: {p.problem_id}\n更新时间: {time_str}\n地址: {p.url}"
            )
        await self.api.send_group_text(event.group_id, "\n".join(lines))

    @command_registry.command("牛客比赛", description="获取牛客近期比赛信息")
    @group_filter
    async def get_nowcoder_recent_contests_command(self, event: GroupMessageEvent):
        contests = get_nowcoder_recent_contests()
        if not contests:
            await self.api.send_group_text(
                event.group_id, "暂时无法获取牛客近期比赛信息, 请稍后重试"
            )
            return
        texts = self._build_contest_texts(contests, include_id=True, source="nowcoder")
        await self.api.send_group_text(
            event.group_id, "\n\n".join([t for _, t in texts])
        )

    @command_registry.command("近期比赛", description="统一展示CF/SCPC/牛客的近期比赛")
    @group_filter
    async def get_aggregated_contests_command(self, event: GroupMessageEvent):
        items = get_aggregated_contests(
            include_cf=True, include_scpc=True, include_nowcoder=True
        )
        if not items:
            await self.api.send_group_text(
                event.group_id, "近期暂无即将开始或进行中的比赛"
            )
            return
        collected = []
        for item in items:
            formatted = self._build_contest_texts(
                [item.contest],
                include_id=True,
                source=item.source,
                skip_verify_name=(item.source == "scpc"),
            )
            if formatted:
                collected.extend(formatted)
        collected.sort(key=lambda x: x[0])
        await self.api.send_group_text(
            event.group_id, "\n\n".join([t for _, t in collected])
        )

    @command_registry.command(
        "生成比赛排行", description="生成指定比赛的排行榜Excel表格"
    )
    @group_filter
    async def get_scpc_contest_rank_command(
        self, event: GroupMessageEvent, contest_id: int
    ):
        username = DEFAULT_SCPC_USERNAME
        password = DEFAULT_SCPC_PASSWORD
        token = scpc_login(username, password)
        if not token:
            await self.api.send_group_text(
                event.group_id, "登录SCPC失败，无法获取比赛排行 (请通知开发者)"
            )
            return
        ranks = get_scpc_contest_rank(contest_id=contest_id, token=token)
        if not ranks:
            await self.api.send_group_text(
                event.group_id, "未获取到比赛排行或比赛ID无效"
            )
        else:
            excel_path = generate_excel_contest_rank(
                rank_users=ranks, contest_id=contest_id
            )
            await self.api.send_group_file(event.group_id, file=excel_path)
            pass
