from dataclasses import dataclass

from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry
from ncatbot.core.event import BaseMessageEvent

from ncatbot.utils import get_log

import random
import requests
from . import api

_logger = get_log()


@dataclass
class UserInfo:
    username: str
    signature: str
    solvedList: list[str]
    total: int


class SCPCPlugin(NcatBotPlugin):
    name = 'SCPC'
    version = '0.0.1'
    author = 'TeAnli'
    description = '专为西南科技大学 SCPC 竞赛平台 打造的 ncatbot 机器人插件'

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
        await self.api.send_group_msg(event.group_id, [ 
            { 
                "type": "text", 
                "data": { 
                    "text" : f"""SCPC 个人信息：
用户名: {data["username"]}
签名: {data["signature"]}
提交数: {data["total"]}
AC数: {len(data["solvedList"])}
题目通过率: {"{:.2f}".format(caculate_accept_ratio(data["total"], len(data["solvedList"]))) * 100}%"""
                } 
            },
        ])


def parse_user_info(data: dict) -> UserInfo:
    return UserInfo(
        username = data['username'],
        signature = data['signature'],
        solvedList = data['solvedList'],
        total = data['total']
    )


def caculate_accept_ratio(total_count: int, accept_count: int) -> int:
    if total_count == 0:
        return 0
    return accept_count / total_count
