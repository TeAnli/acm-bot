
from ncatbot.core import BotClient, PrivateMessage
from ncatbot.utils import get_log
bot = BotClient()
logger = get_log()

# ========== 菜单功能 ==========
@bot.on_group_message()
async def on_group_message(msg: GroupMessage):
    pass

@bot.on_private_message()
async def on_private_message(msg: PrivateMessage):
    pass


# ========== 启动 BotClient ==========
if __name__ == '__main__':
    bot.run()