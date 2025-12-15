import asyncio
from datetime import datetime
from typing import Dict, List, Set, Tuple

from ncatbot.core.event import GroupMessageEvent
from ncatbot.plugin_system import (
    NcatBotPlugin,
    command_registry,
    group_admin_filter,
    group_filter,
)
from ncatbot.utils import get_log

from . import commands
from .platforms.codeforces import CodeforcesPlatform
from .platforms.luogu import LuoguPlatform
from .platforms.nowcoder import NowcoderPlatform
from .platforms.platform import Contest
from .platforms.scpc import SCPCPlatform
from .utils.ai import DEFAULT_SYSTEM_PROMPT

LOG = get_log()


class SCPCPlugin(NcatBotPlugin):
    name = "ACM"
    version = "0.0.3"
    author = "TeAnli"
    description = "专为西南科技大学 SCPC 团队 打造的 ncatbot 机器人插件"

    group_listeners: Dict[str, bool] = {}
    cf_alerted_ids: Set[int] = set()

    codeforces_platform = CodeforcesPlatform()
    scpc_platform = SCPCPlatform("player281", "123456")
    nowcoder_platform = NowcoderPlatform()
    luogu_platform = LuoguPlatform()

    # ----------------------------
    # region 插件生命周期方法
    # ----------------------------
    async def on_load(self):
        """
        注册比赛监听的定时任务 (每 30 分钟执行一次)
        """
        LOG.info("SCPC 插件启动中")

        # 注册配置项
        self.register_config("deepseek_api_key", "sk-")
        self.register_config(
            "ai_system_prompt",
            DEFAULT_SYSTEM_PROMPT,
        )
        self.register_config("ai_temperature", 0.5)
        self.register_config("ai_max_tokens", 800)

        self.add_scheduled_task(
            self._contest_listener_task,
            "interval_task",
            "1h",
        )

    async def _contest_listener_task(self):
        if not any(self.group_listeners.values()):
            return

        tasks = [
            self.scpc_platform.get_recent_contests(),
            self.codeforces_platform.get_contests(),
            self.nowcoder_platform.get_contests(),
            self.luogu_platform.get_contests(),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        scpc_contests = results[0] if not isinstance(results[0], Exception) else []
        cf_contests = results[1] if not isinstance(results[1], Exception) else []
        nowcoder_contests = results[2] if not isinstance(results[2], Exception) else []
        luogu_contests = results[3] if not isinstance(results[3], Exception) else []

        items = []
        if scpc_contests:
            items.extend(self._build_contest_texts(scpc_contests, True, "scpc"))
        if cf_contests:
            items.extend(self._build_contest_texts(cf_contests, False, "cf"))
        if nowcoder_contests:
            items.extend(
                self._build_contest_texts(nowcoder_contests, False, "nowcoder")
            )
        if luogu_contests:
            items.extend(self._build_contest_texts(luogu_contests, False, "luogu"))

        items.sort(key=lambda x: x[0])

        if not items:
            return

        header = "🏆 近期比赛预告 🏆\n"
        content = "\n\n".join([t for _, t in items])
        msg = header + content

        for group_id, enabled in self.group_listeners.items():
            if enabled:
                try:
                    await self.api.send_group_text(group_id, msg)
                except Exception as e:
                    LOG.error(f"Failed to send contest list to group {group_id}: {e}")

    def _format_single_contest(
        self,
        c: Contest,
        now_ts: int,
        include_id: bool = False,
    ) -> str:
        start_str = datetime.fromtimestamp(c.start_time).strftime("%Y-%m-%d %H:%M")

        hours = c.duration // 3600
        minutes = (c.duration % 3600) // 60
        duration_str = f"{hours}小时"
        if minutes > 0:
            duration_str += f"{minutes}分"

        status = "未开始"
        if c.start_time <= now_ts < c.start_time + c.duration:
            status = "进行中"
        elif now_ts >= c.start_time + c.duration:
            status = "已结束"

        lines = [
            f"比赛: {c.name}",
            f"时间: {start_str}",
            f"时长: {duration_str}",
            f"状态: {status}",
            f"链接: {c.url}",
        ]
        if include_id:
            lines.insert(1, f"ID: {c.id}")

        return "\n".join(lines)

    def _build_contest_texts(
        self, contests: List[Contest], include_id: bool, source: str
    ) -> List[Tuple[int, str]]:
        now_ts = int(datetime.now().timestamp())
        result = []
        for c in contests:
            text = self._format_single_contest(c, now_ts, include_id)
            result.append((c.start_time, text))
        return result

    # ----------------------------
    # region 命令注册
    # ----------------------------

    @command_registry.command("随机老婆", description="随机发送一张二次元图片")
    @group_filter
    async def send_random_image(self, event: GroupMessageEvent):
        await commands.send_random_image_logic(self, event)

    @command_registry.command("开启比赛提醒", description="开启本群比赛提醒")
    @group_admin_filter
    async def enable_contest_reminders(self, event: GroupMessageEvent):
        await commands.enable_contest_reminders_logic(self, event)

    @command_registry.command("关闭比赛提醒", description="关闭本群比赛提醒")
    @group_admin_filter
    async def disable_contest_reminders(self, event: GroupMessageEvent):
        await commands.disable_contest_reminders_logic(self, event)

    @command_registry.command("scpc用户", description="获取SCPC用户信息")
    @group_filter
    async def get_user_info(self, event: GroupMessageEvent, username: str):
        await commands.get_user_info_logic(self, event, username)

    @command_registry.command("scpc排行", description="获取SCPC本周排行")
    @group_filter
    async def get_scpc_week_rank(self, event: GroupMessageEvent):
        await commands.get_scpc_week_rank_logic(self, event)

    @command_registry.command("cf比赛", description="获取Codeforces近期比赛")
    @group_filter
    async def get_codeforces_contests(self, event: GroupMessageEvent):
        await commands.get_codeforces_contests_logic(self, event)

    @command_registry.command("scpc近期比赛", description="获取近期SCPC比赛信息")
    @group_filter
    async def get_recent_scpc_contests(self, event: GroupMessageEvent):
        await commands.get_recent_scpc_contests_logic(self, event)

    @command_registry.command("牛客比赛", description="获取牛客近期比赛信息")
    @group_filter
    async def get_nowcoder_recent_contests(self, event: GroupMessageEvent):
        await commands.get_nowcoder_recent_contests_logic(self, event)

    @command_registry.command("洛谷比赛", description="获取洛谷比赛信息")
    @group_filter
    async def get_luogu_contests(self, event: GroupMessageEvent):
        await commands.get_luogu_contests_logic(self, event)

    @command_registry.command("scpc近期更新题目", description="获取近期SCPC更新题目")
    @group_filter
    async def get_recent_scpc_updated_problems(self, event: GroupMessageEvent):
        await commands.get_recent_scpc_updated_problems_logic(self, event)

    @command_registry.command("cf用户", description="获取 Codeforces 用户信息")
    @group_filter
    async def get_codeforces_user_info(self, event: GroupMessageEvent, handle: str):
        await commands.get_codeforces_user_info_logic(self, event, handle)

    @command_registry.command(
        "cf分数", description="获取 Codeforces 用户 Rating 变化图"
    )
    @group_filter
    async def get_codeforces_rating_chart(self, event: GroupMessageEvent, handle: str):
        await commands.get_codeforces_rating_chart_logic(self, event, handle)

    @command_registry.command("ai", description="询问 AI 问题")
    @group_filter
    async def ai_chat(self, event: GroupMessageEvent, question: str):
        await commands.ai_chat_logic(self, event, question)

    @command_registry.command("help", description="获取帮助信息")
    @group_filter
    async def get_help(self, event: GroupMessageEvent):
        await commands.get_help_logic(self, event)

    # ----------------------------
    @command_registry.command("scpc比赛排行", description="生成比赛的排行榜Excel表格")
    @group_filter
    async def get_scpc_contest_rank(self, event: GroupMessageEvent, contest_id: int):
        await commands.get_scpc_contest_rank_logic(self, event, contest_id)
