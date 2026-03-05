import asyncio
import os
import random
from typing import TYPE_CHECKING

from ncatbot.core import BaseMessage, BaseMessageEvent, GroupMessageEvent
from ncatbot.core.helper.forward_constructor import ForwardConstructor
from ncatbot.core.event.message_segment import MessageArray, Text, Image
from ncatbot.utils import get_log, ncatbot_config

from .platforms.codeforces import (
    render_codeforces_rating_chart,
    render_codeforces_user_info_image,
)
from .platforms.scpc import (
    generate_excel_contest_rank,
    render_scpc_user_info_image,
    render_scpc_week_rank_image,
    render_scpc_updated_problems_image,
)
from .utils.ai import ask_deepseek, DEFAULT_SYSTEM_PROMPT
from .utils.webui import webui_helper
from .utils.renderer import renderer
if TYPE_CHECKING:
    from .plugin import SCPCPlugin

LOG = get_log()


async def send_random_image_logic(plugin: "SCPCPlugin", event: BaseMessageEvent):
    LOG.info(f"用户 {event.sender.user_id} 请求随机图片")
    random_id = random.randint(1, 5)
    image_path = f"plugins/acm/assets/image{random_id}.png"
    await event.reply(image_path)


async def enable_contest_reminders_logic(
    plugin: "SCPCPlugin", event: GroupMessageEvent
):
    LOG.info(f"用户 {event.sender.user_id} 添加了比赛订阅 至 {event.group_id}")
    plugin.group_listeners[event.group_id] = True
    await plugin.api.send_group_text("已为本群开启比赛监听任务")


async def disable_contest_reminders_logic(
    plugin: "SCPCPlugin", event: GroupMessageEvent
):
    LOG.info(f"用户 {event.sender.user_id} 移除了比赛订阅 至 {event.group_id}")
    plugin.group_listeners[event.group_id] = False
    await plugin.api.send_group_text(event.group_id, "已为本群关闭比赛监听任务")


async def get_user_info_logic(
    plugin: "SCPCPlugin", event: BaseMessageEvent, username: str
):
    data = await plugin.scpc_platform.get_user_info(username)
    if not data:
        LOG.warning(f"获取 SCPC 用户信息失败：{username}")
        await event.reply(f"未找到用户 {username} 的信息")
        return

    image_path = await render_scpc_user_info_image(data)
    if image_path:
        await event.reply(image=image_path)
    else:
        await event.reply("生成用户信息图片失败")


async def get_scpc_week_rank_logic(plugin: "SCPCPlugin", event: BaseMessageEvent):
    rank_data = await plugin.scpc_platform.get_week_rank()
    if not rank_data:
        await event.reply("获取本周排行失败")
        return
    image_path = await render_scpc_week_rank_image(rank_data)
    if image_path:
        await event.reply(image=image_path)
    else:
        await event.reply("生成排行图片失败")


async def get_codeforces_contests_logic(plugin: "SCPCPlugin", event: BaseMessageEvent):
    contests = await plugin.codeforces_platform.get_contests()
    if not contests:
        await event.reply("近期没有Codeforces比赛")
        return

    items = plugin._build_contest_texts(contests, False, "cf")
    if not items:
        await event.reply("近期没有Codeforces比赛")
        return

    msg = "🏆 Codeforces 近期比赛 🏆\n\n" + "\n\n".join([t for _, t in items])
    await event.reply(msg)


async def get_recent_scpc_contests_logic(
    plugin: "SCPCPlugin", event: BaseMessageEvent
):
    contests = await plugin.scpc_platform.get_recent_contests()
    if not contests:
        await event.reply("近期没有SCPC比赛")
        return

    items = plugin._build_contest_texts(contests, True, "scpc")
    if not items:
        await event.reply("近期没有SCPC比赛")
        return

    msg = "🏆 SCPC 近期比赛 🏆\n\n" + "\n\n".join([t for _, t in items])
    await event.reply(msg)


async def get_nowcoder_recent_contests_logic(
    plugin: "SCPCPlugin", event: BaseMessageEvent
):
    contests = await plugin.nowcoder_platform.get_contests()
    if not contests:
        await event.reply("近期没有牛客比赛")
        return

    items = plugin._build_contest_texts(contests, False, "nowcoder")
    if not items:
        await event.reply("近期没有牛客比赛")
        return

    msg = "🏆 牛客 近期比赛 🏆\n\n" + "\n\n".join([t for _, t in items])
    await event.reply(msg)


async def get_luogu_contests_logic(plugin: "SCPCPlugin", event: BaseMessageEvent):
    contests = await plugin.luogu_platform.get_contests()
    if not contests:
        await event.reply("近期没有洛谷比赛")
        return

    items = plugin._build_contest_texts(contests, False, "luogu")
    if not items:
        await event.reply("近期没有洛谷比赛")
        return

    msg = "🏆 洛谷 近期比赛 🏆\n\n" + "\n\n".join([t for _, t in items])
    await event.reply(msg)


async def get_recent_scpc_updated_problems_logic(
    plugin: "SCPCPlugin", event: BaseMessageEvent
):
    problems = await plugin.scpc_platform.get_recent_updated_problems()
    if not problems:
        await event.reply("近期没有更新题目")
        return

    image_path = await render_scpc_updated_problems_image(problems)

    try:
        fcr = ForwardConstructor(user_id=ncatbot_config.bt_uin, nickname="SCPC Bot")
        fcr.attach_text("📝 SCPC 近期更新题目 📝")

        if image_path:
            fcr.attach_image(image=image_path)

        for p in problems:
            content = f"[{p.problem_id}] {p.title}\n{p.url}"
            fcr.attach_text(content)

        forward = fcr.to_forward()
        await event.reply(forward)
    except Exception as e:
        LOG.error(f"Send forward message failed: {e}")
        if image_path:
            await event.reply(image=image_path)

        msg = "📝 SCPC 近期更新题目 📝\n\n"
        for p in problems:
            msg += f"[{p.problem_id}] {p.title}\n{p.url}\n\n"
        await event.reply(msg)


async def get_codeforces_user_info_logic(
    plugin: "SCPCPlugin", event: BaseMessageEvent, handle: str
):
    LOG.info(f"获取 CF 用户信息: {handle}")
    image_path = await render_codeforces_user_info_image(handle)
    if image_path:
        await event.reply(image=image_path)
    else:
        await event.reply(
            f"无法获取 Codeforces 用户 {handle} 的信息或生成图片失败"
        )


async def get_codeforces_rating_chart_logic(
    plugin: "SCPCPlugin", event: BaseMessageEvent, handle: str
):
    LOG.info(f"获取 CF Rating 图表: {handle}")
    image_path = await render_codeforces_rating_chart(handle)
    if image_path:
        await event.reply(image=image_path)
    else:
        await event.reply(
            f"无法获取 Codeforces 用户 {handle} 的 Rating 数据或生成图片失败"
        )


async def ai_chat_logic(plugin: "SCPCPlugin", event: BaseMessageEvent, question: str):
    LOG.info(f"User {event.user_id} asking AI: {question}")

    if not question:
        return

    answer = await ask_deepseek(
        question=question,
        api_key=plugin.config.get("deepseek_api_key", ""),
        system_prompt=plugin.config.get("ai_system_prompt", DEFAULT_SYSTEM_PROMPT),
        temperature=plugin.config.get("ai_temperature", 0.5),
        max_tokens=plugin.config.get("ai_max_tokens", 800),
    )

    # Construct reply
    reply = f"🤖 AI 回复:\n{answer}"
    await event.reply(reply)
    

async def get_scpc_contest_rank_logic(
    plugin: "SCPCPlugin", event: BaseMessageEvent, contest_id: int
):
    LOG.info(f"User {event.user_id} requesting rank for contest {contest_id}")

    rank_data = await plugin.scpc_platform.get_contest_rank(contest_id)
    if not rank_data:
        await event.reply("获取比赛排行失败")
        return
    path = await generate_excel_contest_rank(rank_data, contest_id)
    if path:
        try:
            await event.reply(image=path)
        except AttributeError:
            await event.reply(
                f"生成表格成功，但发送文件失败。路径: {path}"
            )
    else:
        await event.reply("生成排行表格失败")


async def get_all_recent_contests_logic(plugin: "SCPCPlugin", event: BaseMessageEvent):
    LOG.info(f"User {event.user_id} requesting all recent contests")

    tasks = [
        plugin.scpc_platform.get_recent_contests(),
        plugin.codeforces_platform.get_contests(),
        plugin.nowcoder_platform.get_contests(),
        plugin.luogu_platform.get_contests(),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scpc_contests = results[0] if not isinstance(results[0], Exception) else []
    cf_contests = results[1] if not isinstance(results[1], Exception) else []
    nowcoder_contests = results[2] if not isinstance(results[2], Exception) else []
    luogu_contests = results[3] if not isinstance(results[3], Exception) else []

    items = []
    if scpc_contests:
        items.extend(plugin._build_contest_texts(scpc_contests, True, "scpc"))
    if cf_contests:
        items.extend(plugin._build_contest_texts(cf_contests, False, "cf"))
    if nowcoder_contests:
        items.extend(plugin._build_contest_texts(nowcoder_contests, False, "nowcoder"))
    if luogu_contests:
        items.extend(plugin._build_contest_texts(luogu_contests, False, "luogu"))

    items.sort(key=lambda x: x[0])

    if not items:
        await event.reply("近期没有比赛")
        return

    header = "🏆 近期比赛预告 🏆\n"
    content = "\n\n".join([t for _, t in items])
    msg = header + content

    await event.reply(msg)


async def get_help_logic(plugin: "SCPCPlugin", event: BaseMessageEvent):

    commands_list = [
        {"name": "/help", "desc": "获取帮助信息", "is_admin": False},
        {"name": "/近期比赛", "desc": "获取所有平台近期比赛", "is_admin": False},
        {"name": "/随机老婆", "desc": "随机发送一张二次元图片", "is_admin": False},
        {"name": "/开启比赛提醒", "desc": "开启本群比赛提醒", "is_admin": True},
        {"name": "/关闭比赛提醒", "desc": "关闭本群比赛提醒", "is_admin": True},
        {"name": "/scpc用户 [username]", "desc": "获取SCPC用户信息", "is_admin": False},
        {"name": "/scpc排行", "desc": "获取SCPC本周排行", "is_admin": False},
        {"name": "/cf比赛", "desc": "获取Codeforces近期比赛", "is_admin": False},
        {"name": "/scpc近期比赛", "desc": "获取近期SCPC比赛信息", "is_admin": False},
        {"name": "/牛客比赛", "desc": "获取牛客近期比赛信息", "is_admin": False},
        {"name": "/洛谷比赛", "desc": "获取洛谷比赛信息", "is_admin": False},
        {
            "name": "/scpc近期更新题目",
            "desc": "获取近期SCPC更新题目",
            "is_admin": False,
        },
        {
            "name": "/cf用户 [handle]",
            "desc": "获取 Codeforces 用户信息",
            "is_admin": False,
        },
        {
            "name": "/cf分数 [handle]",
            "desc": "获取 Codeforces 用户 Rating 变化图",
            "is_admin": False,
        },
        {"name": "/ai [question]", "desc": "询问 AI 问题", "is_admin": False},
    ]

    html = webui_helper.render_help(commands_list, plugin.version)

    # Save to temp file
    temp_path = os.path.abspath(f"data/temp_help_{event.sender.user_id}.png")
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)

    success = await renderer.render_html(html, temp_path)

    if success:
        await event.reply(image=temp_path)
        try:
            os.remove(temp_path)
        except Exception:
            pass
    else:
        await event.reply(text="生成帮助图片失败")
