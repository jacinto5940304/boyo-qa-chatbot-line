import requests
from config import OPENAI_API_KEY


def generate_quiz_question(all_rules, asked_questions):
    past_q_text = "\n".join(f"- {q}" for q in asked_questions) if asked_questions else "（無）"
    prompt = (
        "你是一位基金會規章老師，請根據以下規章條文出 1 題單選測驗題，並提供三個選項與正確答案。"
        "題目需簡短清楚，選項避免模糊不清，不要加入條文原文，只根據條文出題。\n\n"
        "⚠️ 請**不要重複出現以下這些題目**：\n"
        f"{past_q_text}\n\n"
        f"規章條文如下：\n{all_rules}\n\n"
        "請輸出格式如下：\n"
        "題目：...\n選項：\nA. ...\nB. ...\nC. ...\n答案：A"
    )

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()["choices"][0]["message"]["content"]
        lines = data.strip().split("\n")
        q_line = [l for l in lines if l.startswith("題目：")][0]
        a_line = [l for l in lines if l.startswith("答案：")][0]
        o_lines = [l for l in lines if l.startswith(("A.", "B.", "C."))]

        question = q_line.replace("題目：", "").strip()
        options = "\n".join(o_lines).strip()
        answer = a_line.replace("答案：", "").strip()
        return question, options, answer
    else:
        return None, None, None
    
def format_options(options_str):
    parts = options_str.split(" ")
    result = []
    current = ""
    for p in parts:
        current += p + " "
        if "." in p:
            result.append(current.strip())
            current = ""
    return "\n".join(result)

