import os
import time
import base64
import logging
import urllib.request
import json
import re
from PIL import Image

logger = logging.getLogger(__name__)

# Load all keywords from rules for context matching
# Load keywords separated by category
def get_forensic_keywords_by_category():
    transaction_keywords = set()
    betting_keywords = set()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        with open(os.path.join(base_dir, "rules", "transactionSignals.json"), "r") as f:
            ts = json.load(f)
            for role, words in ts.get("roles", {}).items():
                if isinstance(words, list):
                    transaction_keywords.update(words)
    except:
        pass
        
    try:
        with open(os.path.join(base_dir, "rules", "bettingSignals.json"), "r") as f:
            bs = json.load(f)
            for item in bs.get("brand_rules", []):
                betting_keywords.add(item.get("term", ""))
            for list_name in ["betting_phrases", "casino_phrases", "sportsbook_ui_phrases", "fantasy_ui_phrases", "wallet_phrases"]:
                for item in bs.get(list_name, []):
                    betting_keywords.add(item.get("phrase", ""))
    except:
        pass
        
    return {
        "transaction": {k.lower() for k in transaction_keywords if k},
        "betting": {k.lower() for k in betting_keywords if k}
    }

FORENSIC_CATEGORIES = get_forensic_keywords_by_category()

def extract_categorized_keywords(ocr_text):
    text_lower = ocr_text.lower()
    results = {"transaction": [], "betting": []}
    
    for kw in FORENSIC_CATEGORIES["transaction"]:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            results["transaction"].append(kw)
            
    for kw in FORENSIC_CATEGORIES["betting"]:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            results["betting"].append(kw)
            
    return {
        "transaction": list(set(results["transaction"])),
        "betting": list(set(results["betting"]))
    }



LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")


def get_lm_studio_active_model(base_url: str = "http://127.0.0.1:1234/v1") -> str:
    """Fetches the currently loaded model ID from LM Studio."""
    try:
        req = urllib.request.Request(f"{base_url}/models", headers={"User-Agent": "Python"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = data.get("data", [])
            for m in models:
                m_id = m.get("id", "")
                if "embed" not in m_id:
                    return m_id
            if models:
                return models[0].get("id")
    except Exception:
        pass
    return None


def call_lm_studio_vision(image_path: str, prompt_text: str, base_url: str = "http://127.0.0.1:1234/v1") -> str:
    """Calls local LM Studio Vision API (OpenAI compatible format)."""
    try:
        model_id = get_lm_studio_active_model(base_url)
        if not model_id:
            return None

        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            "max_tokens": 150,
            "temperature": 0.2
        }

        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=60.0) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if "choices" in res_data and len(res_data["choices"]) > 0:
                summary = res_data["choices"][0]["message"]["content"].strip().replace("\n", " ")
                logger.info(f"LM Studio Vision ({model_id}) generated summary for {image_path}: {summary}")
                return summary
    except Exception as e:
        logger.warning(f"LM Studio Vision request failed: {e}")
    return None


def generate_segment_summary(
    image_path: str = None, 
    ocr_text: str = "", 
    qr_detected: bool = False, 
    banking_score: float = 0.0, 
    crypto_score: float = 0.0, 
    betting_score: float = 0.0,
    timeout_seconds: float = 12.0
) -> str:
    """
    Generates a concise 1-2 sentence forensic summary of a segment proof-frame screenshot.
    Priority 1: Local LM Studio Vision API (http://127.0.0.1:1234) if active.
    Priority 2: Rule-based OCR fallback.
    """
    prompt_text = (
        "You are a digital forensics expert analyzing screenshots from a video recording of a suspected illegal betting or financial site. "
        "Provide a concise 1-2 sentence forensic summary of what this screenshot displays (e.g. login interface, UPI QR code deposit gateway, "
        f"betting odds slip, wallet balance, or error popup). Extracted OCR text context: '{ocr_text[:300]}'. Be objective and direct."
    )

    # Extract matched keywords by category
    categorized = extract_categorized_keywords(ocr_text) if ocr_text else {"transaction": [], "betting": []}
    bet_str = ", ".join(categorized["betting"]).title() if categorized["betting"] else "None detected"
    tx_str = ", ".join(categorized["transaction"]).title() if categorized["transaction"] else "None detected"

    # ── Priority 1: Check Local LM Studio Vision Server ──
    if image_path and os.path.exists(image_path):
        # Local models like LLaVA 1.5 perform better with very simple, direct instructions
        local_prompt = (
            f"[OCR BACKGROUND CONTEXT]: {ocr_text[:300]}\n"
            f"[BETTING SIGNALS MATCHED]: {bet_str}\n"
            f"[TRANSACTION SIGNALS MATCHED]: {tx_str}\n\n"
            "[INSTRUCTION]: You are a forensic analyst. Write a 4-5 line summary combining the visual context of this screenshot with the matched keywords. Assume it is a betting, casino, or financial site. Identify the website name, describe modals, and categorize the content."
        )
        lm_raw_text = call_lm_studio_vision(image_path, local_prompt, LM_STUDIO_URL)
        if lm_raw_text:
            return (
                "**Extracted Keywords**\n\n"
                f"* **Betting Signals:** {bet_str}\n"
                f"* **Transaction Signals:** {tx_str}\n\n"
                "**Screenshot Summary**\n"
                f"{lm_raw_text}"
            )



    # ── Priority 2: Fallback Rule-Based Summary ──
    parts = []
    if qr_detected:
        parts.append("A scannable QR code was identified on screen")
        
    if banking_score >= 50:
        parts.append("High-confidence banking or payment interface detected")
    elif banking_score >= 20:
        parts.append("General financial keywords present")
        
    if crypto_score >= 50:
        parts.append("High-confidence cryptocurrency wallet or deposit interface detected")
        
    if betting_score >= 50:
        parts.append("High-confidence betting odds or casino match interface observed")
    elif betting_score >= 20:
        parts.append("General sports or gaming keywords present")
        
    if not parts:
        parts.append("General navigation and UI interaction frame")
        
    fallback_summary = ". ".join(parts) + "."
    
    return (
        "**Extracted Keywords**\n\n"
        f"* **Betting Signals:** {bet_str}\n"
        f"* **Transaction Signals:** {tx_str}\n\n"
        "**Screenshot Summary**\n"
        f"*(Automated heuristic detection)* {fallback_summary}"
    )
