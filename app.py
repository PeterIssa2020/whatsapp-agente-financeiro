import os
import json
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(_name_)

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

def call_llm(text):
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
    r = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

@app.post("/whatsapp")
def whatsapp():
    body = (request.form.get("Body") or "").strip()
    resp = MessagingResponse()

    try:
        answer = call_llm(body)
    except Exception:
        answer = "Tive um problema 😕 Pode repetir sua pergunta de forma mais simples?"

    resp.message(answer)
    return str(resp)

@app.get("/health")
def health():
    return "ok", 200
