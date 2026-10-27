"""Optional cloud language-model enhancement.

The application remains fully usable offline. This adapter only sends retrieved
snippets to a provider after the user explicitly enables cloud enhancement.
"""
import os


def is_configured():
    return bool(os.getenv("OPENAI_API_KEY"))


def answer_with_evidence(question, evidence):
    """Return a grounded answer or None if cloud enhancement is unavailable."""
    if not is_configured():
        return None
    try:
        from openai import OpenAI
        client = OpenAI()
        prompt = (
            "你是课程资料整理助手。只能依据下方资料回答，不得补充资料外事实。"
            "若证据不足，明确回答“资料不足，无法确定”。回答后用 [来源 n] 标出依据。\n\n"
            f"问题：{question}\n\n资料：\n{evidence}"
        )
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-6-astra"),
            input=prompt,
        )
        text = (response.output_text or "").strip()
        return text or None
    except Exception:
        # Do not break the local study flow because a cloud provider is unavailable.
        return None
