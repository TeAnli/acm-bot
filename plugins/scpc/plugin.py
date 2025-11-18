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
)
from .utils import (
    calculate_accept_ratio,
    format_contest_text,
    broadcast_text,
)

LOG = get_log()

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
        """定时任务检查 CF 比赛并在开始前限定时间内提醒"""
        LOG.info(f'检测群组和比赛任务 订阅比赛提醒的群组: {self.group_listeners}')
        if not any(self.group_listeners.values()):
            LOG.info('CF 比赛监听已禁用或未配置群组.')
            return
        await self._check_cf_contests_and_notify(threshold_hours=2)

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
