from ncatbot.plugin_system import NcatBotPlugin
from ncatbot.plugin_system import command_registry

from ncatbot.core.event import BaseMessageEvent

from ncatbot.utils import get_log

from enum import Enum

_logger = get_log()

class LikeCount(Enum):
    DEFAULT_LIKE_COUNT = 10
    SVIP_LIKE_COUNT = 20
    MAX_LIKE_COUNT = 50


class AutoLikePlugin(NcatBotPlugin):
    name = "AutoLikePlugin"
    version = "0.0.1"
    author = "TeAnli"
    description = "自动点赞插件, 支持命令点赞和定时点赞"

    @command_registry.command("点赞", description="对你的名片进行点赞")
    async def like_command(self, event: BaseMessageEvent):
        status = await self.api.get_status()
        _logger.info(f"User {event.user_id} liked their profile. Status: {status}")
        
        await self.api.send_like(event.user_id, LikeCount.MAX_LIKE_COUNT)