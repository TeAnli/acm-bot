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


async def fetch_html(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> str:
    """
    通过 GET 请求获取 HTML 文本信息

    Args:
        url (str): 目标 URL 地址
        headers (Optional[Dict[str, str]]): HTTP 请求头，默认使用 DEFAULT_HEADERS
        timeout (float): 请求超时时间(秒)，默认 30.0

    Returns:
        str: 获取到的 HTML 文本内容。如果请求失败，返回空字符串。
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
    发送 HTTP 请求并获取 JSON 数据

    Args:
        url (str): 目标 URL 地址
        headers (Optional[Dict[str, str]]): HTTP 请求头，默认使用 DEFAULT_HEADERS
        payload (Optional[Dict[str, Any]]): 请求体数据 (JSON 格式)，仅用于 POST/PUT 等方法
        method (Method): HTTP 请求方法 (GET, POST, etc.)，默认 Method.GET
        timeout (float): 请求超时时间(秒)，默认 30.0

    Returns:
        Dict[str, Any]: 解析后的 JSON 字典。如果请求失败或解析错误，返回空字典 {}。
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
