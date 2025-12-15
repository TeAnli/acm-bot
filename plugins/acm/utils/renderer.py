import asyncio
import os
import time
from typing import Optional

from ncatbot.utils import get_log
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright

# Constants
MAX_CONCURRENT_RENDERS = 5
RENDER_WIDTH = 720
RENDER_TIMEOUT = 30.0

LOG = get_log()


class PlaywrightRenderer:
    def __init__(self):
        self._p: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._init_lock = asyncio.Lock()
        self._render_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RENDERS)
        self._browser_failed = False
        self._last_browser_fail_time = 0.0
        self._browser_retry_interval = 300.0
        self._page_count = 0
        self._max_pages = 50

    async def _is_browser_healthy(self) -> bool:
        """检查浏览器健康状态"""
        if not self._browser:
            return False
        try:
            contexts = self._browser.contexts
            if not contexts:
                return True
            total_pages = sum(len(ctx.pages) for ctx in contexts)
            if total_pages >= self._max_pages:
                LOG.warning(f"浏览器打开的页面数过多: {total_pages}/{self._max_pages}")
                return False
            return True
        except Exception as e:
            LOG.warning(f"浏览器健康检查失败: {e}")
            return False

    async def _reinit_browser(self):
        """重新初始化浏览器"""
        async with self._init_lock:
            if self._context:
                try:
                    await self._context.close()
                except Exception:
                    pass
                finally:
                    self._context = None

            if self._browser:
                try:
                    await self._browser.close()
                    LOG.info("已关闭旧浏览器实例")
                except Exception as e:
                    LOG.warning(f"关闭旧浏览器失败: {e}")
                finally:
                    self._browser = None

            if self._p:
                try:
                    await self._p.stop()
                except Exception:
                    pass
                self._p = None

            self._browser_failed = False
            self._last_browser_fail_time = 0.0
            self._page_count = 0

    async def _ensure_browser(self) -> Optional[Browser]:
        """确保浏览器实例存在"""
        if self._browser and self._context:
            return self._browser

        if self._browser_failed:
            if (
                time.time() - self._last_browser_fail_time
                < self._browser_retry_interval
            ):
                return None
            LOG.info("浏览器初始化冷却时间已过，尝试重新初始化...")
            self._browser_failed = False

        async with self._init_lock:
            if self._browser and self._context:
                return self._browser

            if self._browser_failed:
                if (
                    time.time() - self._last_browser_fail_time
                    < self._browser_retry_interval
                ):
                    return None
                self._browser_failed = False

            try:
                if not self._p:
                    self._p = await async_playwright().start()

                if not self._browser:
                    try:
                        self._browser = await self._p.chromium.launch(headless=True)
                    except Exception as e:
                        LOG.warning(
                            f"使用默认参数启动浏览器失败，尝试使用 --no-sandbox: {e}"
                        )
                        self._browser = await self._p.chromium.launch(
                            args=["--no-sandbox"], headless=True
                        )

                if not self._context:
                    self._context = await self._browser.new_context(
                        viewport={"width": RENDER_WIDTH, "height": 600}
                    )

                LOG.info("Playwright 浏览器初始化成功")
                self._page_count = 0
                return self._browser
            except Exception as e:
                LOG.error(f"初始化 Playwright 浏览器失败: {e}")
                self._browser_failed = True
                self._last_browser_fail_time = time.time()
                if self._p:
                    try:
                        await self._p.stop()
                    except Exception:
                        pass
                    self._p = None
                return None

    async def close(self):
        """关闭渲染器并清理资源"""
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                LOG.warning(f"关闭浏览器失败: {e}")
            finally:
                self._browser = None

        if self._p:
            try:
                await self._p.stop()
            except Exception as e:
                LOG.warning(f"停止 Playwright 失败: {e}")
            finally:
                self._p = None

    async def render_html(
        self, html_content: str, output_path: str, viewport_width: int = RENDER_WIDTH
    ) -> bool:
        """
        将 HTML 文本渲染并保存为图片

        Args:
            html_content: HTML 内容
            output_path: 图片保存路径
            viewport_width: 视口宽度

        Returns:
            bool: 是否成功
        """
        async with self._render_semaphore:
            try:
                return await asyncio.wait_for(
                    self._render_html_impl(html_content, output_path, viewport_width),
                    timeout=RENDER_TIMEOUT,
                )
            except asyncio.TimeoutError:
                LOG.error(f"HTML 渲染超时（{RENDER_TIMEOUT}s）")
                return False
            except Exception as e:
                LOG.error(f"HTML 渲染失败: {e}", exc_info=True)
                return False

    async def _render_html_impl(
        self, html_content: str, output_path: str, viewport_width: int
    ) -> bool:
        browser = await self._ensure_browser()
        if not browser:
            LOG.error("浏览器未初始化，无法渲染 HTML")
            return False

        if not await self._is_browser_healthy():
            LOG.warning("浏览器健康检查失败，尝试重新初始化...")
            await self._reinit_browser()
            browser = await self._ensure_browser()
            if not browser:
                LOG.error("浏览器重新初始化失败")
                return False

        page = None
        page_created = False
        try:
            # Reuse context for faster page creation
            if self._context:
                page = await self._context.new_page()
            else:
                # Fallback if context is somehow missing
                page = await browser.new_page(
                    viewport={"width": viewport_width, "height": 600}
                )

            self._page_count += 1
            page_created = True

            # Reset viewport size for this page if needed (though context has default)
            await page.set_viewport_size({"width": viewport_width, "height": 600})

            await page.set_content(html_content)
            try:
                await page.wait_for_load_state("domcontentloaded")
                # Removed networkidle wait for speed
            except Exception:
                pass

            # 尝试等待内容元素可见
            target_selector = ".card"
            target = page.locator(target_selector)
            
            try:
                await target.wait_for(state="visible", timeout=2000)
            except Exception:
                # 尝试回退到 .container
                target_selector = ".container"
                target = page.locator(target_selector)
                try:
                    await target.wait_for(state="visible", timeout=2000)
                except Exception:
                    # 最后回退到 body
                    target_selector = "body"
                    target = page.locator(target_selector)

            # 动态调整高度
            try:
                h = await page.evaluate(
                    f"document.querySelector('{target_selector}')?.getBoundingClientRect().height || 600"
                )
                await page.set_viewport_size(
                    {"width": viewport_width, "height": int(h) + 40}
                )
            except Exception:
                pass

            # 截图
            ok = False
            try:
                await target.screenshot(path=output_path)
                ok = os.path.exists(output_path)
            except Exception:
                ok = False

            if not ok:
                try:
                    await page.screenshot(path=output_path, full_page=False)
                    ok = os.path.exists(output_path)
                except Exception:
                    ok = False

            return ok

        finally:
            if page:
                try:
                    await page.close()
                except Exception as e:
                    LOG.warning(f"关闭页面时出错: {e}")

            if page_created:
                self._page_count = max(0, self._page_count - 1)
