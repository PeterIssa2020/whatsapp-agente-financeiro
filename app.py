import os
import json
import logging
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

SYSTEM_PROMPT = """
Você é um agente de orientação financeira familiar, focado na classe C brasileira.

Seu papel é responder dúvidas sobre:
- financiamento de casa, carro, moto e bens
- empréstimos pessoais e consignados
- parcelamentos no cartão
- organização do orçamento familiar

Use linguagem simples, direta e popular.
Frases curtas. Nada de termos técnicos.
Explique como se fosse WhatsApp.

Sempre responda em 4 blocos:
1️⃣ VALE A PENA?
2️⃣ VANTAGENS
3️⃣ DESVANTAGENS
4️⃣ COMO ECONOMIZAR

Toda resposta deve terminar com uma dica simples de economia.
"""

LLM_API_URL = os.getenv("LLM_API_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def call_llm(text: str) -> str:
    """
    Chama a API do LLM configurada em LLM_API_URL com LLM_API_KEY.
    Faz parsing defensivo da resposta para retornar sempre uma string.
    """
    if not LLM_API_URL or not LLM_API_KEY:
        raise RuntimeError("LLM_API_URL e LLM_API_KEY devem estar configurados nas variáveis de ambiente")

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        "temperature": 0.4
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        logger.exception("Falha na requisição ao LLM")
        raise

    try:
        data = resp.json()
    except ValueError:
        logger.exception("Resposta do LLM não é JSON válido")
        raise

    # Parsing defensivo para diferentes formatos comuns
    try:
        if isinstance(data, dict):
            # OpenAI-like: {"choices":[{"message":{"content":"..."}}]}
            choices = data.get("choices")
            if choices and isinstance(choices, list) and len(choices) > 0:
                first = choices[0]
                if isinstance(first, dict):
                    # new style: message.content
                    message = first.get("message")
                    if isinstance(message, dict) and "content" in message:
                        return message["content"]
                    # older style: text
                    if "text" in first:
                        return first["text"]
            # Some APIs return text directly
            if "text" in data and isinstance(data["text"], str):
                return data["text"]
            # fallback: try top-level output
            if "output" in data and isinstance(data["output"], str):
                return data["output"]
        # If nothing matched, return prettified JSON as fallback
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        logger.exception("Erro ao processar a resposta do LLM")
        raise


@app.post("/whatsapp")
def whatsapp():
    body = (request.form.get("Body") or "").strip()
    resp = MessagingResponse()

    if not body:
        resp.message(
            "Oi! Por favor, escreva sua pergunta sobre finanças (por exemplo: 'Vale a pena financiar um carro?')."
        )
        return str(resp)

    try:
        answer = call_llm(body)
    except Exception:
        logger.exception("Erro ao chamar o LLM")
        answer = "Tive um problema 😕 Pode repetir sua pergunta de forma mais simples?"

    resp.message(answer)
    return str(resp)


@app.get("/health")
def health():
    return "ok", 200


if __name__ == "__main__":
    # apenas para execução local: usa porta 5000 por padrão
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
