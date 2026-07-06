"""
AI 服务封装模块
通过 OpenAI 兼容 API 调用阿里云百炼 / Qwen 等大模型。
需要在 .env 中设置 LLM_API_KEY（DashScope API Key）。
获取 API Key: https://bailian.console.aliyun.com/
"""
import json
import logging
from typing import Optional

import httpx

from app.core.config import LLM_API_KEY, LLM_API_URL, LLM_MODEL

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


def is_available() -> bool:
    """检查 AI 服务是否可用"""
    return bool(LLM_API_KEY and LLM_API_KEY != "sk-your-bailian-api-key-here")


def _get_client() -> Optional[httpx.Client]:
    """获取 HTTP 客户端"""
    if not is_available():
        return None
    base_url = LLM_API_URL or _DEFAULT_BASE_URL
    return httpx.Client(
        base_url=base_url,
        headers={
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=60.0,
    )


def chat_json(
    system_prompt: str,
    user_message: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
) -> dict:
    """
    调用 LLM，要求返回 JSON 格式的结果。
    """
    client = _get_client()
    if not client:
        raise RuntimeError(
            "AI 服务未配置。请在 .env 中设置 LLM_API_KEY。\n"
            "获取 API Key: https://bailian.console.aliyun.com/ → API Key 管理"
        )

    model_name = model or LLM_MODEL or "qwen-plus"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM API 调用失败: {e.response.status_code} {e.response.text}")
        raise RuntimeError(f"AI 服务调用失败（HTTP {e.response.status_code}），请检查 API Key 和网络连接")
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"LLM 返回内容解析失败: {e}")
        raise ValueError("AI 返回内容格式异常，请重试")
    except Exception as e:
        logger.error(f"LLM 调用异常: {e}")
        raise RuntimeError(f"AI 服务调用失败：{str(e)}")
    finally:
        client.close()
