from ncatbot.utils import get_log
from .network import fetch_json, Method

LOG = get_log()
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

DEFAULT_SYSTEM_PROMPT = (
    "你是一名ACM算法竞赛高手。请用纯文本回答，严禁使用Markdown格式（不要使用```代码块```或**加粗**）。"
    "回答必须极简、高效、直击要点。如果涉及复杂代码或长篇解释，请仅提供核心思路并附上OI-Wiki等权威资料的链接，避免长篇大论。"
)


async def ask_deepseek(
    question: str,
    api_key: str,
    system_prompt: str,
    temperature: float = 0.5,
    max_tokens: int = 800,
) -> str:
    """
    调用 Deepseek API 进行问答

    Args:
        question (str): 用户提问内容
        api_key (str): Deepseek API Key
        system_prompt (str): 系统提示词
        temperature (float): 随机性参数 (0.0 - 2.0)，默认 0.5
        max_tokens (int): 最大生成 Token 数，默认 800

    Returns:
        str: AI 回复内容或错误提示信息
    """
    if not api_key:
        return "请先在插件配置中配置有效的 Deepseek API Key"
    
    # 简单的 Key 格式预检查（假设 sk- 开头且长度足够）
    if api_key.startswith("sk-") and len(api_key) < 10:
        return "Deepseek API Key 格式看似无效，请检查配置"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {"role": "user", "content": question},
        ],
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
    }

    try:
        response = await fetch_json(
            url=DEEPSEEK_API_URL,
            headers=headers,
            payload=payload,
            method=Method.POST,
            timeout=60.0,
        )

        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        elif "error" in response:
            error_msg = response["error"].get("message", "未知错误")
            LOG.error(f"Deepseek API returned error: {error_msg}")
            return f"API 调用失败: {error_msg}"
        else:
            LOG.error(f"Deepseek API returned unexpected format: {response}")
            return "API 返回格式异常，请查看日志"

    except Exception as e:
        LOG.error(f"Deepseek API request failed: {e}")
        return f"请求发生错误: {str(e)}"
