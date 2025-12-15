from ncatbot.core import BotClient
from ncatbot.utils import get_log

bot = BotClient()
LOG = get_log()

if __name__ == "__main__":
    LOG.info("机器人启动中...")
    bot.run()
    LOG.info("机器人已停止。")
