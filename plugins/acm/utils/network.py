from enum import Enum
from typing import Dict, Optional, Any

from httpx import AsyncClient
from ncatbot.utils import get_log

LOG = get_log()


class Method(Enum):
    POST = "POST"
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"


DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    "Connection": "close",
}


async def fetch_html(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 30.0) -> str:
    """
    直接通过GET请求获取HTML文本信息

    Args:
        url: 目标url地址
        headers: HTTP请求头
        timeout: 请求超时时间(秒)

    Returns:
        HTML文本信息
    """
    if headers is None:
        headers = DEFAULT_HEADERS

    try:
        async with AsyncClient(timeout=timeout) as client:
            response = await client.get(url=url, headers=headers)
            response.raise_for_status()
            return response.text
    except Exception as e:
        LOG.error(f"Failed to fetch HTML from {url}: {e}")
        return ""


async def fetch_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    method: Method = Method.GET,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """
    通过自定义请求获取请求数据

    Args:
        url: 目标url地址
        headers: HTTP请求头
        payload: 请求数据
        method: 请求方式
        timeout: 请求超时时间(秒)

    Returns:
        JSON数据转义后的字典
    """
    if headers is None:
        headers = DEFAULT_HEADERS

    try:
        async with AsyncClient(timeout=timeout) as client:
            response = await client.request(
                url=url, json=payload, headers=headers, method=method.value
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        LOG.error(f"Error fetching JSON from {url}: {e}")
        return {}
