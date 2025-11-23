
import asyncio
from ncatbot.core import BotClient
from ncatbot.core.event import GroupMessageEvent
from ncatbot.utils import get_log

bot = BotClient()
LOG = get_log()

about_information = """✨ 关于"安心Bot" ✨
👤 作者: 不知名人士
🔖 版本: 0.1.0
⚙️ 目前基于轻量的 ncatbot QQ 机器人框架开发(后续版本将转向 nonebot2)
🖼️ 暂未支持图片数据展示（后续版本会添加）
🚫 请勿利用 "安心Bot" 刷屏，发表违规言论
🤖 本程序不支持 AI 问答，也不会添加，为了防止重要消息被刷"""

menu_information = """💖 安心Bot 菜单 💖
📖 使用说明:
ℹ️ 关于安心 - 展示关于安心Bot界面
🧩 命令:
/来个男神 - 随机发送一张男神帅照 (仅群聊管理员)

/cf比赛 - 获取 Codeforces 比赛信息
/cf积分 <用户名> - 获取指定用户的rating

/添加比赛监听器 - 添加定时任务, 在比赛开始前自动发送即将开始的比赛信息 (仅群聊管理员)
/移除比赛监听器 - 移除定时任务 (仅群聊管理员)

/scpc信息 <用户名> - 获取指定用户名 SCPC 网站信息
/scpc榜单图 - 获取scpc一周内过题数前十名榜单"""

@bot.on_group_message()
def group_message_handler(event: GroupMessageEvent):
    raw = (event.raw_message or "").strip()
    # 优先匹配带斜杠的标准命令，其次是中文关键词
    if "/菜单" == raw or "菜单" == raw:
        asyncio.create_task(bot.api.post_group_msg(event.group_id, text=menu_information))
        return
    if "/关于" == raw or "关于" == raw:
        asyncio.create_task(bot.api.post_group_msg(event.group_id, text=about_information))
        return


if __name__ == '__main__':
    LOG.info('机器人启动中...')
    bot.run()
    LOG.info('机器人已停止。')