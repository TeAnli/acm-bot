from dataclasses import dataclass
from datetime import datetime

from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.core.event import BaseMessageEvent

from ncatbot.utils import get_log

import random
import requests
from . import api
from .utils import format_timestamp, format_hours, build_text_msg, format_relative_hours, state_icon

_logger = get_log()


@dataclass
class UserInfo:
    username: str
    signature: str
    solvedList: list[str]
    total: int


@dataclass
class Contest:
    id: int
    name: str
    type: str
    phase: str
    frozen: bool
    duration: int
    start_time: int
    relative_time: int

class SCPCPlugin(NcatBotPlugin):
    name = 'SCPC'
    version = '0.0.1'
    author = 'TeAnli'
    description = '专为西南科技大学 SCPC 竞赛平台 打造的 ncatbot 机器人插件'

    async def _send(self, group_id, messages):
        """统一的群消息发送函数，集中异常处理与日志记录"""
        try:
            await self.api.send_group_msg(group_id, messages)
        except Exception as e:
            _logger.warning(f'Send group message failed: {e}')

    async def _send_text(self, group_id, text: str):
        await self._send(group_id, [build_text_msg(text)])

    @command_registry.command('来个男神', description='随机发送一张男神照片')
    async def random_god_image(self, event: BaseMessageEvent):
        _logger.info(f'User {event.user_id} requested a random male god image.')
        random_id = random.randint(1, 5)
        await self.api.send_group_image(event.group_id, f'plugins/scpc/assets/image{random_id}.png')

    @command_registry.command('scpc信息', description='查询scpc网站的个人信息')
    async def get_user_info(self, event: BaseMessageEvent, username: str):
        user_info_url = api.user_info_url(username)
        response = requests.get(user_info_url, headers=api.headers)
        data = response.json()['data']
        _logger.info(f'Fetching SCPC user info: {data}')
        accept_ratio = "{:.2f}".format(calculate_accept_ratio(data['total'], len(data['solvedList'])) * 100)
        user_text = (
            f"SCPC 个人信息：\n"
            f"昵称: {data['nickname']}\n"
            f"签名: {data['signature']}\n"
            f"提交数: {data['total']}\n"
            f"AC数: {len(data['solvedList'])}\n"
            f"题目通过率: {accept_ratio}%"
        )
        await self._send_text(event.group_id, user_text)
    
    @command_registry.command("cf比赛", description='获取codeforces比赛信息')
    async def get_codeforces_contests(self, event: BaseMessageEvent):

        contests_url = api.codeforces_contests_url()
        response = requests.get(contests_url, headers=api.headers)
        if response.status_code == 200 and response.json()['status'] == 'OK':
            data = response.json()['result']
            _logger.info(f'Fetching Codeforces contests: {response.json()}')

            # 收集即将开始与进行中的比赛
            collected = []  # (time_remaining_seconds, formatted_text)
            for contest in data:
                rel = contest.get('relativeTimeSeconds', 0)
                duration = contest.get('durationSeconds', 0)

                if rel < 0:
                    state = '即将开始'
                    time_remaining = abs(rel)
                    remaining_label = '据开始还剩'
                elif 0 <= rel < duration:
                    state = '进行中'
                    time_remaining = max(duration - rel, 0)
                    remaining_label = '距离结束'
                else:
                    # 已结束的比赛不展示
                    continue

                start_time = format_timestamp(contest['startTimeSeconds'])
                duration_hours = format_hours(duration, precision=1)
                remaining_str = format_relative_hours(time_remaining, precision=1)

                icon = state_icon(state)
                text = (
                    f"比赛名称:\n"
                    f"{contest['name']} (ID: {contest['id']})\n"
                    f"状态: {icon} {state}\n"
                    f"开始时间: {start_time}\n"
                    f"{remaining_label}: {remaining_str}\n"
                    f"比赛时长: {duration_hours} 小时"
                )
                collected.append((time_remaining, text))

            # 按剩余时间升序排序，最近的比赛排在最前
            collected.sort(key=lambda x: x[0])
            texts = [t for _, t in collected]

            if texts:
                await self._send_text(event.group_id, "\n\n".join(texts))
            else:
                await self._send_text(event.group_id, "近期暂无即将开始或进行中的 Codeforces 比赛")
        else:
            _logger.warning(f'Failed to fetch Codeforces contests: {response.text}')
            await self._send_text(event.group_id, "暂时无法获取 Codeforces 比赛信息, 请稍后重试")

    @command_registry.command("scpc比赛", description="获取SCPC比赛信息")
    async def get_scpc_contests(self, event: BaseMessageEvent):
        """从 SCPC 平台获取比赛列表，展示即将开始与进行中的比赛。"""
        contests_url = api.scpc_contests_url()
        try:
            response = requests.get(contests_url, headers=api.headers, timeout=10)
        except Exception as e:
            _logger.warning(f'Fetch SCPC contests failed: {e}')
            await self._send_text(event.group_id, "暂时无法获取 SCPC 比赛信息, 请稍后重试")
            return

        if response.status_code != 200:
            _logger.warning(f'SCPC contests bad status: {response.status_code} {response.text}')
            await self._send_text(event.group_id, "暂时无法获取 SCPC 比赛信息, 请稍后重试")
            return

        # 兼容多种返回结构：data.records 或 records
        body = {}
        try:
            body = response.json()
        except Exception:
            pass
        records = (
            body.get('data', {}).get('records')
            or body.get('records')
            or []
        )

        from .utils import parse_scpc_time

        collected = []  # (sort_key, text)
        now_ts = int(datetime.now().timestamp())
        for record in records:
            # 字段兼容：title/contestName，duration 秒，startTime/endTime 支持 ISO 或秒
            name = record.get('title') or record.get('contestName') or '未命名比赛'
            start_ts = parse_scpc_time(record.get('startTime'))
            end_ts = parse_scpc_time(record.get('endTime'))
            duration = int(record.get('duration') or max(end_ts - start_ts, 0))

            # 计算状态与剩余时间
            if start_ts and now_ts < start_ts:
                state = '即将开始'
                remaining_label = '据开始还剩'
                time_remaining = start_ts - now_ts
                sort_key = time_remaining
            elif start_ts and end_ts and start_ts <= now_ts < end_ts:
                state = '进行中'
                remaining_label = '距离结束'
                time_remaining = max(end_ts - now_ts, 0)
                sort_key = time_remaining
            else:
                # 已结束的比赛暂不展示
                continue

            start_time_str = format_timestamp(start_ts)
            duration_str = format_hours(duration, precision=1)
            remaining_str = format_relative_hours(time_remaining, precision=1)
            icon = state_icon(state)

            text = (
                f"比赛名称:\n"
                f"{name}\n"
                f"状态: {icon} {state}\n"
                f"开始时间: {start_time_str}\n"
                f"{remaining_label}: {remaining_str}\n"
                f"比赛时长: {duration_str} 小时"
            )
            collected.append((sort_key, text))

        collected.sort(key=lambda x: x[0])
        texts = [t for _, t in collected]
        if texts:
            await self._send_text(event.group_id, "\n\n".join(texts))
        else:
            await self._send_text(event.group_id, "近期暂无即将开始或进行中的 SCPC 比赛")


def calculate_accept_ratio(total_count: int, accept_count: int) -> float:
    if total_count == 0:
        return 0.0
    return accept_count / total_count

