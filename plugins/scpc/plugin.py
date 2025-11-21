from datetime import datetime

from ncatbot.core import GroupMessageEvent, Text
from ncatbot.plugin_system import NcatBotPlugin, group_admin_filter, group_filter
from ncatbot.plugin_system import command_registry
from ncatbot.utils import get_log

import random

from .codeforces import (
    get_codeforces_contests,
    get_codeforces_user_rating,
    extract_cf_timing,
)
from .scpc import (
    get_scpc_user_info,
    get_scpc_contests,
    extract_scpc_timing,
    scpc_login,
    get_scpc_contest_rank,
    get_scpc_recent_contests,
    get_scpc_recent_updated_problems,
)
from .utils import ( 
    calculate_accept_ratio,
    format_contest_text,
    broadcast_text,
    format_timestamp,
)

LOG = get_log()

DEFAULT_SCPC_USERNAME = "player281"
DEFAULT_SCPC_PASSWORD = "123456"

class SCPCPlugin(NcatBotPlugin):
    name = 'SCPC'
    version = '0.0.1'
    author = 'TeAnli'
    description = '专为西南科技大学 SCPC 团队 打造的 ncatbot 机器人插件'


    group_listeners = dict[str, bool]()
    cf_alerted_ids = set[int]()

    async def on_load(self):
        """注册定时任务, 每隔30min执行一次获取比赛信息"""
        LOG.info('SCPC 插件启动中')
        try:
            self.add_scheduled_task(
                self._listen_task,
                'cf_contest_watch',
                '30m',
            )
            LOG.info('已注册 CF 比赛监听任务 (每 30 分钟检查一次)')
        except Exception as e:
            LOG.warning(f'注册定时任务失败: {e}')
    
    async def _listen_task(self):
        LOG.info(f'检测群组和比赛任务 订阅比赛提醒的群组: {self.group_listeners}')
        if not any(self.group_listeners.values()):
            LOG.info('CF 比赛监听已禁用或未配置群组.')
            return
        await self._check_cf_contests_and_notify(threshold_hours=2)
        await self._check_scpc_contests_and_notify(threshold_hours=2)

    async def _check_cf_contests_and_notify(self, threshold_hours: int = 2):
        """检查 CF 比赛并在距开始限定时间内向所有监听群提醒."""
        contests = get_codeforces_contests()
        if not contests:
            LOG.warning('获取 CF 比赛失败：无数据或状态异常')
            return
        threshold_seconds = threshold_hours * 3600
        upcoming_texts = []
        # 遍历获取到的比赛列表
        for contest in contests:
            # 获取比赛id, 用于后续去重, 防止重复发送
            cid = contest.id
            timing = extract_cf_timing(contest)
            if timing:
                state, remaining_label, remaining_secs, duration, start_ts = timing
                if state == '即将开始' and remaining_secs <= threshold_seconds:
                    if cid in self.cf_alerted_ids:
                        continue
                    self.cf_alerted_ids.add(cid)

                    text = format_contest_text(
                        name=contest.name,
                        contest_id=cid,
                        state=state,
                        start_ts=start_ts,
                        remaining_label=remaining_label,
                        remaining_secs=remaining_secs,
                        duration_secs=duration,
                    )
                    upcoming_texts.append((remaining_secs, text))
        upcoming_texts.sort(key=lambda x: x[0])
        if not upcoming_texts:
            LOG.info('限定时间内无即将开始的 CF 比赛，不发送通知')
            return

        merged = '\n\n'.join([t for _, t in upcoming_texts])
        await broadcast_text(self.api, self.group_listeners, merged)

    async def _check_scpc_contests_and_notify(self, threshold_hours: int = 2):
        records = get_scpc_contests()
        if not records:
            LOG.warning('获取 SCPC 比赛失败：无数据或状态异常')
            return
        threshold_seconds = threshold_hours * 3600
        now_ts = int(datetime.now().timestamp())
        upcoming_texts = []
        for record in records:
            timing = extract_scpc_timing(record, now_ts)
            if not timing:
                continue
            name, state, remaining_label, remaining_secs, duration, start_ts, sort_key = timing
            if state == '即将开始' and remaining_secs <= threshold_seconds:
                text = format_contest_text(
                    name=name,
                    contest_id=None,
                    state=state,
                    start_ts=start_ts,
                    remaining_label=remaining_label,
                    remaining_secs=remaining_secs,
                    duration_secs=duration,
                    include_id=False,
                )
                upcoming_texts.append((remaining_secs, text))
        upcoming_texts.sort(key=lambda x: x[0])
        if not upcoming_texts:
            LOG.info('限定时间内无即将开始的 SCPC 比赛，不发送通知')
            return
        merged = '\n\n'.join([t for _, t in upcoming_texts])
        await broadcast_text(self.api, self.group_listeners, merged)

    @command_registry.command('来个男神', description='随机发送一张男神照片')
    @group_admin_filter
    @group_filter
    async def random_god_image(self, event: GroupMessageEvent):
        LOG.info(f'用户 {event.user_id} 请求随机图片')
        random_id = random.randint(1, 5)
        image_path = f'plugins/scpc/assets/image{random_id}.png'
        await self.api.send_group_image(event.group_id, image_path)

    @command_registry.command('添加比赛监听器', description='为当前群开启比赛监听任务')
    @group_admin_filter
    @group_filter
    async def add_contest_listener(self, event: GroupMessageEvent):
        LOG.info(f'用户 {event.user_id} 添加了比赛订阅 至 {event.group_id}')
        self.group_listeners[event.group_id] = True
        await self.api.send_group_text(event.group_id, '已为本群开启比赛监听任务')

    @command_registry.command('移除比赛监听器', description='为当前群关闭比赛监听任务')
    @group_admin_filter
    @group_filter
    async def remove_contest_listener(self, event: GroupMessageEvent):
        LOG.info(f'User {event} removed contest listener for contest')
        self.group_listeners[event.group_id] = False
        await self.api.send_group_text(event.group_id, '已为本群关闭比赛监听任务')

    @command_registry.command('scpc信息', description='查询scpc网站的个人信息')
    @group_filter
    async def get_user_info(self, event: GroupMessageEvent, username: str):
        data = get_scpc_user_info(username)
        if not data:
            LOG.warning(f'获取 SCPC 用户信息失败：{username}')
            await self.api.send_group_text(event.group_id, '暂时无法获取 SCPC 用户信息, 请稍后重试')
            return

        LOG.info(f'获取 SCPC 用户信息: {data}')
        total = int(getattr(data, 'total', 0))
        solved_list = getattr(data, 'solvedList', []) or []
        accept_ratio = '{:.2f}'.format(calculate_accept_ratio(total, len(solved_list)) * 100)
        nickname = getattr(data, 'nickname', username) or username
        signature = getattr(data, 'signature', '') or ''

        user_text = (
            f'SCPC 个人信息：\n'
            f'昵称: {nickname}\n'
            f'签名: {signature}\n'
            f'提交数: {total}\n'
            f'AC数: {len(solved_list)}\n'
            f'题目通过率: {accept_ratio}%'
        )
        await self.api.send_group_text(event.group_id, user_text)

    async def _get_codeforces_contests(self, group_id: str):
        contests = get_codeforces_contests()
        if contests is not None:
            LOG.info(f'获取 CF 比赛列表：共 {len(contests)} 场')

            collected = []
            for contest in contests:
                timing = extract_cf_timing(contest)
                if not timing:
                    continue
                state, remaining_label, time_remaining, duration, start_ts = timing

                text = format_contest_text(
                    name=contest.name,
                    contest_id=contest.id,
                    state=state,
                    start_ts=start_ts,
                    remaining_label=remaining_label,
                    remaining_secs=int(time_remaining),
                    duration_secs=int(duration),
                )
                collected.append((time_remaining, text))

            collected.sort(key=lambda x: x[0])
            texts = [t for _, t in collected]

            if texts:
                await self.api.send_group_text(group_id, '\n\n'.join(texts))
            else:
                await self.api.send_group_text(group_id, '近期暂无即将开始或进行中的 Codeforces 比赛')
        else:
            LOG.warning('获取 CF 比赛失败：请求异常或状态不正确')
            await self.api.send_group_text(group_id, '暂时无法获取 Codeforces 比赛信息, 请稍后重试')

    @command_registry.command('scpc比赛', description='获取SCPC比赛信息')
    @group_filter
    async def get_scpc_contests(self, event: GroupMessageEvent):
        records = get_scpc_contests()
        if records is None:
            LOG.warning('获取 SCPC 比赛失败：无数据')
            await self.api.send_group_text(event.group_id, '暂时无法获取 SCPC 比赛信息, 请稍后重试')
            return
        collected = []
        now_ts = int(datetime.now().timestamp())
        for record in records:
            timing = extract_scpc_timing(record, now_ts)
            if not timing:
                continue
            name, state, remaining_label, remaining_secs, duration, start_ts, sort_key = timing

            text = format_contest_text(
                name=name,
                contest_id=None,
                state=state,
                start_ts=start_ts,
                remaining_label=remaining_label,
                remaining_secs=remaining_secs,
                duration_secs=duration,
                include_id=False,
            )
            collected.append((sort_key, text))

        collected.sort(key=lambda x: x[0])
        texts = [t for _, t in collected]
        if texts:
            await self.api.send_group_text(event.group_id, '\n\n'.join(texts))
        else:
            await self.api.send_group_text(event.group_id, '近期暂无即将开始或进行中的 SCPC 比赛')
    @command_registry.command("scpc排行", description='获取SCPC最近一周过题排行')
    @group_filter
    async def get_scpc_rank(self, event: GroupMessageEvent):
        records = get_scpc_rank()
        if records is None:
            LOG.warning('获取 SCPC 排行失败：无数据')
            await self.api.send_group_text(event.group_id, '暂时无法获取 SCPC 排行信息, 请稍后重试')
            return
        collected = []
        for record in records:
            text = format_rank_text(
                username=record.username,
                avatar=record.avatar,
                titlename=record.titlename,
                titleColor=record.titleColor,
                ac=record.ac,
            )
            collected.append(text)
        if collected:
            await self.api.send_group_text(event.group_id, '\n\n'.join(collected))
        else:
            await self.api.send_group_text(event.group_id, '暂时无法获取 SCPC 排行信息, 请稍后重试')


    @command_registry.command('cf积分', description='获取codeforces比赛信息')
    @group_filter
    async def get_codeforces_user_rating(self, event: GroupMessageEvent, username: str):
        ratings = get_codeforces_user_rating(username)
        if ratings is not None:
            LOG.info(f'获取 CF 用户积分记录：{len(ratings)} 条')

            if not ratings:
                await self.api.send_group_text(event.group_id, f'用户 {username} 没有比赛记录。')
                return
                
            last_contest = ratings[-1]
            ratings_text = (
                f"新积分: {last_contest.newRating}\n"
            )

            await self.api.send_group_text(event.group_id, ratings_text.strip())
        else:
            LOG.warning('获取 CF 用户积分失败：请求异常或状态不正确')
            await self.api.send_group_text(event.group_id, '暂时无法获取 Codeforces 用户积分信息, 请稍后重试')

    @command_registry.command('cf比赛', description='获取codeforces比赛信息')
    @group_filter
    async def get_codeforces_contests(self, event: GroupMessageEvent):
        await self._get_codeforces_contests(event.group_id)

    @command_registry.command('scpc近期比赛', description='获取近期SCPC比赛信息')
    @group_filter
    async def get_recent_scpc_contests(self, event: GroupMessageEvent):
        records = get_scpc_recent_contests()
        if records is None:
            LOG.warning('获取 SCPC 近期比赛失败：无数据')
            await self.api.send_group_text(event.group_id, '暂时无法获取 SCPC 近期比赛信息, 请稍后重试')
            return
        collected = []
        now_ts = int(datetime.now().timestamp())
        for record in records:
            timing = extract_scpc_timing(record, now_ts)
            if not timing:
                continue
            name, state, remaining_label, remaining_secs, duration, start_ts, sort_key = timing
            text = format_contest_text(
                name=name,
                contest_id=None,
                state=state,
                start_ts=start_ts,
                remaining_label=remaining_label,
                remaining_secs=remaining_secs,
                duration_secs=duration,
                include_id=False,
            )
            collected.append((sort_key, text))
        collected.sort(key=lambda x: x[0])
        texts = [t for _, t in collected]
        if texts:
            await self.api.send_group_text(event.group_id, '\n\n'.join(texts))
        else:
            await self.api.send_group_text(event.group_id, '近期暂无即将开始或进行中的 SCPC 比赛')

    @command_registry.command('scpc近期更新题目', description='获取近期SCPC更新题目')
    @group_filter
    async def get_recent_scpc_updated_problems(self, event: GroupMessageEvent):
        items = get_scpc_recent_updated_problems()
        LOG.info(f'获取 SCPC 近期更新题目：{items} 条')
        if not items:
            LOG.warning('获取 SCPC 近期更新题目失败：无数据')
            await self.api.send_group_text(event.group_id, '暂时无法获取 SCPC 近期更新题目, 请稍后重试')
            return
        lines = []
        for p in items:
            time_str = format_timestamp(p.gmtModified) if isinstance(p.gmtModified, int) and p.gmtModified > 0 else str(p.gmtModified)
            lines.append(f"题目: {p.title} (ID: {p.problemId}) | 更新时间: {time_str}")
        await self.api.send_group_text(event.group_id, '\n'.join(lines))

    @command_registry.command('scpc比赛排行', description='获取指定比赛的过题排行，参数: 比赛ID [limit] [page]')
    @group_filter
    async def get_scpc_contest_rank_command(self, event: GroupMessageEvent, contest_id: int, limit: int = 50, page: int = 1):
        username = DEFAULT_SCPC_USERNAME
        password = DEFAULT_SCPC_PASSWORD
        token = scpc_login(username, password)
        if not token:
            await self.api.send_group_text(event.group_id, '登录SCPC失败，无法获取比赛排行（请检查默认凭据）')
            return
        ranks = get_scpc_contest_rank(contest_id=contest_id, token=token, current_page=page, limit=limit)
        if not ranks:
            await self.api.send_group_text(event.group_id, '未获取到比赛排行或比赛ID无效')
            return
        lines = []
        for u in ranks:
            line = f"#{u.rank} {u.username} ({u.realname}) | 奖项:{u.awardName} | AC:{u.ac} / 提交:{u.total} | 用时:{u.totalTime}s"
            lines.append(line)
        await self.api.send_group_text(event.group_id, '\n'.join(lines))
