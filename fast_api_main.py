python
# main.py (kısaltılmış)

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader
import ollama
import json

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")

VALID_KEYS = {"buraya_api_keyin"}

def verify_key(key: str = Depends(api_key_header)):
    if key not in VALID_KEYS:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return key

SYSTEM_PROMPT = """
Sen bir siber güvenlik uzmanısın. Sana gelen ham güvenlik olaylarını analiz edip
şu formatta JSON döndürüyorsun:

{
  "severity": "critical|high|medium|low|info",
  "attack_type": "saldırı kategorisi",
  "summary": "2-3 cümle özet",
  "iocs": ["ip", "hash", "domain listesi"],
  "recommended_action": "yapılması gereken",
  "false_positive_likelihood": "low|medium|high"
}

Yanıtın sadece geçerli JSON olsun, başka bir şey ekleme.
"""

@app.post("/api/ingest")
async def ingest_event(event: dict, _: str = Depends(verify_key)):
    # Olayı OpenClaw'a ilet
    openclaw_result = await forward_to_openclaw(event)

    # Severity 1-2 ise AI değerlendirmesini de çalıştır
    if event.get("severity", 3) <= 2:
        prompt = f"Şu güvenlik olayını değerlendir:\n{json.dumps(event, indent=2)}"
        response = ollama.chat(
            model="mistral",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ]
        )
        ai_assessment = json.loads(response["message"]["content"])
        return {"status": "ok", "ai_assessment": ai_assessment}

    return {"status": "ok", "ai_assessment": None}
