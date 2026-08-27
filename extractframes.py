import av
import os
import sys
import shutil
import logging
import re
import json

import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image

from collections import Counter

# Importing internal project modules responsible for
# scoring, verdict generation, summaries, and betting analysis
from engine.scoring import score_segment
from engine.final_verdict import generate_final_verdict
from engine.final_summary import generate_final_summary
from engine.final_summary import load_segment_verdicts
from engine.betting_classifier import run_betting_analysis
from engine.run_crypto_betting_analysis import run_analysis as run_crypto_betting_analysis# -------------------- KEYWORDS & COLORS --------------------
CATEGORIZED_KEYWORDS = {
    "Financial": [
        "deposit", "withdraw", "withdrawal", "wallet", "cashier", 
        "balance", "transfer", "payout", "topup", "add money", 
        "bank", "upi", "upi id", "gateway", "currency", "inr", "usd", 
        "crypto", "usdt", "usdc", "bitcoin", "btc", "ethereum", "eth", "tron", "bnb",
        "transaction", "my transactions", "recharge", "imps", "neft", "rtgs", "ecs", "ach",
        "gpay", "google pay", "phonepe", "phone pe", "paytm", "pay tm", "amazon pay", "bhim",
        "razorpay", "cashfree", "payu", "ccavenue", "billdesk", "rupay", "visa", "mastercard",
        "available balance", "winning balance", "deposit balance", "bonus balance",
        "beneficiary", "account number", "reference number", "transaction id",
        "qr", "qr code", "scan & pay", "scan qr"
    ],
    "Gaming": [
        "casino", "slot", "slots", "roulette", "blackjack", "poker", 
        "baccarat", "sports", "live sports", "fantasy", "betting", 
        "odds", "match", "tournament", "jackpot", "table games", 
        "crash game", "aviator", "mines", "spin"
    ],
    "Rewards": [
        "bonus", "referral", "rewards", "cashback", "spin", "wheel", 
        "promo", "promotion", "free bet", "vip", "welcome bonus", 
        "deposit bonus", "loyalty", "points", "claim"
    ],
    "Authentication": [
        "login", "sign in", "signin", "register", "sign up", "signup", 
        "kyc", "verify", "verification", "otp", "password", "account", 
        "forgot password", "join now", "register now", "phone number", "phone", "mobile", "mobile number", "email", "e-mail"
    ],
    "Legal": [
        "terms", "privacy", "policy", "license", "terms of service", 
        "responsible gaming", "18+", "anti-money laundering", "aml", 
        "disclaimer", "curacao", "malta", "isom"
    ],
    "Social": [
        "telegram", "whatsapp", "discord", "instagram", "facebook", 
        "twitter", "support", "contact us", "live chat", "channel"
    ]
}

CATEGORY_COLORS_BGR = {
    "Financial": (0, 200, 0),       
    "Gaming": (255, 120, 0),        
    "Rewards": (0, 215, 255),       
    "Authentication": (0, 0, 230),  
    "Legal": (180, 50, 180),        
    "Social": (255, 190, 0),        
    "Payment_Indicator": (0, 0, 255)
}

PAYMENT_INDICATOR_PATTERNS = {
    "UPI_ID": r"[a-zA-Z0-9.\-_]+@(upi|okicici|ybl|paytm|ibl|axl|sbi|kotak|barodampay|icici|hdfcbank|okaxis|oksbi|okhdfcbank)",
    "PAYMENT_GATEWAY": r"(razorpay|cashfree|stripe|paytm|phonepe|google pay|gpay|payu|instamojo|paypal|ccavenue|billdesk)",
    "QR_CODE": r"(qr code|scan and pay|scan & pay|upi qr|scan to pay|scan qr|scan code)",
    "BANK_TRANSFER": r"(bank transfer|imps|neft|rtgs|ecs|ach|account number|ifsc|account name|beneficiary)",
    "WALLET": r"(paytm wallet|phonepe wallet|mobikwik|freecharge|crypto wallet|usdt trc20|bep20|binance pay|coinbase)"
}

def draw_text_bounding_boxes(rgb, data, offset_x=0, offset_y=0, scale_factor=1.0):
    if not data or 'text' not in data:
        return
        
    n_boxes = len(data['text'])
    words = [str(w).strip().lower() for w in data['text']]
    
    # Check multi-word phrases and single words
    for category, keywords in CATEGORIZED_KEYWORDS.items():
        color = CATEGORY_COLORS_BGR.get(category, (0, 255, 0))
        for keyword in keywords:
            kw_parts = keyword.split()
            kw_len = len(kw_parts)
            
            for i in range(n_boxes - kw_len + 1):
                if all(words[i+j] == kw_parts[j] for j in range(kw_len)):
                    lefts = [data['left'][i+j] for j in range(kw_len)]
                    tops = [data['top'][i+j] for j in range(kw_len)]
                    rights = [data['left'][i+j] + data['width'][i+j] for j in range(kw_len)]
                    bottoms = [data['top'][i+j] + data['height'][i+j] for j in range(kw_len)]
                    
                    x = int(min(lefts) / scale_factor) + offset_x
                    y = int(min(tops) / scale_factor) + offset_y
                    w = int((max(rights) - min(lefts)) / scale_factor)
                    h = int((max(bottoms) - min(tops)) / scale_factor)
                    
                    cv2.rectangle(rgb, (x-2, y-2), (x + w + 2, y + h + 2), color, 2)
                    
    # Check regex patterns
    color = CATEGORY_COLORS_BGR.get("Payment_Indicator", (0, 0, 255))
    for i in range(n_boxes):
        word = words[i]
        if not word:
            continue
        for cat_name, pattern in PAYMENT_INDICATOR_PATTERNS.items():
            if re.search(pattern, word):
                x = int(data['left'][i] / scale_factor) + offset_x
                y = int(data['top'][i] / scale_factor) + offset_y
                w = int(data['width'][i] / scale_factor)
                h = int(data['height'][i] / scale_factor)
                cv2.rectangle(rgb, (x-2, y-2), (x + w + 2, y + h + 2), color, 2)
                break


# -------------------- TESSERACT SETUP --------------------

# Get the absolute path of the current project directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build the relative path to the bundled Tesseract executable
TESSERACT_PATH = os.path.join(BASE_DIR, "tools", "tesseract", "tesseract.exe")

# Ensure Tesseract exists before continuing
if os.name == "nt" and os.path.exists(TESSERACT_PATH):
    # Windows: use bundled tesseract.exe
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

elif os.name != "nt":
    # Docker / Linux: use system tesseract
    pytesseract.pytesseract.tesseract_cmd = "tesseract"

else:
    raise FileNotFoundError(
        "Tesseract not found. Please ensure tools/tesseract exists on Windows."
    )


# -------------------- LOGGING CONFIG --------------------

# Configure logging to show timestamps and message severity
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# -------------------- PRE-COMPILED REGEX PATTERNS --------------------
# Compiled once at module load — avoids recompilation on every frame

AMOUNT_PATTERN = re.compile(r"(₹|\$|€|£)\s?\d+(?:[,]\d+)*(?:\.\d+)?")
DIGIT_PATTERN  = re.compile(r"\d")
CLEAN_LOWER    = re.compile(r"[^a-z0-9₹$€£]")
CLEAN_SPACES   = re.compile(r"\s+")
VOWEL_ONLY     = re.compile(r"[aeiou]+")


# -------------------- TEXT UTILITIES --------------------

# Normalizes OCR text to make matching easier later
# Converts to lowercase and removes special characters
def normalizeText(text):
    text = text.lower()
    text = CLEAN_LOWER.sub(" ", text)
    text = CLEAN_SPACES.sub(" ", text).strip()
    return text


# Splits text into individual tokens (words)
def extractTokens(text):
    return set(text.split()) if text else set()


# Cleans tokens by removing very short, numeric,
# or meaningless vowel-only strings
def cleanTokens(tokens):
    return {
        t for t in tokens
        if len(t) >= 4
        and not t.isdigit()
        and not VOWEL_ONLY.fullmatch(t)
    }


# Selects anchor tokens which are longer alphabetic words
# These are used to detect screen stability
def anchorTokens(tokens):
    return {t for t in tokens if t.isalpha() and len(t) >= 6}


# -------------------- OCR PREPROCESSING --------------------

# Prepares image for OCR by improving contrast and clarity
def preprocess_for_ocr(rgb):
    # Convert RGB frame to grayscale
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    # Upscale image to help OCR accuracy
    gray = cv2.resize(
        gray, None,
        fx=2, fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    # Apply slight blur to reduce noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Apply adaptive thresholding to enhance text regions
    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        3,
        2
    )

    return gray, thresh


# Extracts the region of interest where payment details
# usually appear in mobile UIs
def extract_payment_roi(rgb):
    h, w, _ = rgb.shape
    y1 = int(0.30 * h)
    y2 = int(0.80 * h)
    x1 = int(0.10 * w)
    x2 = int(0.90 * w)
    return rgb[y1:y2, x1:x2]


# -------------------- STATE EXTRACTION --------------------

# Extracts currency amounts from OCR text
def extract_amounts(text):
    return AMOUNT_PATTERN.findall(text)


# Detects QR codes present in the frame
def extract_qr_text(rgb):
    detector = cv2.QRCodeDetector()

    data, points, _ = detector.detectAndDecode(rgb)

    # Must actually decode content
    if not data or not data.strip():
        return None, None

    # Must have a valid QR box
    if points is None:
        return None, None

    return data.strip(), points


# Attempts to extract payee or beneficiary names from text
def extract_counterparties(text):
    parties = []
    tokens = text.split()
    for i, tok in enumerate(tokens[:-1]):
        if tok in {"to", "from", "payee", "receiver", "beneficiary"}:
            nxt = tokens[i + 1]
            if nxt.isalpha() and len(nxt) >= 3:
                parties.append(nxt)
    return parties


# -------------------- SEGMENT HANDLING --------------------

# Initializes a new segment when screen content changes
def startSegment(startTime, frameIndex):
    return {
        "startTime": startTime,
        "endTime": startTime,
        "frames": [frameIndex],
        "tokens": set(),
        "anchor_freq": {},
        "ocr_text": "",
        "frame_texts": [],
        "qrTexts": [],
        "amounts": Counter(),
        "counterparties": Counter()
    }


# Attaches the proof frame (middle frame of the segment) — this is the
# single image used later by the evidence report as visual proof for
# whatever verdict was computed for that segment
def attachProofFrame(segment, frames_dir):
    mid_idx = segment["frames"][len(segment["frames"]) // 2]
    segment["proof_frame"] = os.path.join(frames_dir, f"frame{mid_idx}.jpg")
    return segment


# Writes segment details to a text file for debugging and analysis
def writeSegments(segments,output_dir):
   with open(
        os.path.join(output_dir, "segments_output.txt"),
        "w",
        encoding="utf-8"
    ) as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"SEGMENT {i}\n")
            f.write(f"Time: {seg['startTime']:.2f}s → {seg['endTime']:.2f}s\n")
            f.write(f"Frames: {seg['frames']}\n")
            f.write("Tokens: " + " ".join(sorted(seg["tokens"])) + "\n\n")


# -------------------- MAIN PIPELINE --------------------

def extractFrames(videoPath, outputDir="frames", sampleSeconds=0.5, progress_callback=None, video_name=None):
    # Create a unique output folder for this video
    if not video_name:
        video_name = os.path.splitext(
            os.path.basename(videoPath)
        )[0]

    output_dir = os.path.join(
        "outputs",
        video_name
    )

    os.makedirs(output_dir, exist_ok=True)
    frames_dir = os.path.join(
        output_dir,
        "frames"
    )

    os.makedirs(frames_dir, exist_ok=True)
    # Ensure outputs directory exists for logs and reports
    os.makedirs("outputs", exist_ok=True)

    logging.info(f"Opening video: {videoPath}")


    # Remove old OCR and segment logs if they exist
    for name in ["ocr_output.txt", "segments_output.txt"]:
        path = os.path.join("outputs", name)
        if os.path.exists(path):
            os.remove(path)

    # Load transaction signal rules
    with open("rules/transactionSignals.json", "r", encoding="utf-8") as f:
        rules = json.load(f)

    # Open video container using PyAV
    container = av.open(videoPath)
    stream = container.streams.video[0]
    if stream.duration:
        total_duration = float(stream.duration * stream.time_base)
    elif container.duration:
        total_duration = float(container.duration) / 1e6
    else:
        total_duration = None

    nextTime = 0.0
    frameIndex = 0

    segments = []
    currentSegment = None

    # Thresholds used to detect screen changes
    similarityThreshold = 0.75
    lowCount = 0
    maxLow = 5

    tesseract_config = "--oem 1 --psm 6"

    # ---- Hash-skip state: track previous frame for pixel comparison ----
    frames_since_last_ocr = 0
    MAX_REUSE_FRAMES = 3
    prev_gray_small = None
    prev_norm_text  = ""
    PIXEL_DIFF_THRESHOLD = 0.02   # 2% mean pixel change triggers new OCR

    # ---- OCR lines collected in memory, flushed once after loop ----
    ocr_lines = []

    for packet in container.demux(stream):
        for frame in packet.decode():

            # Skip frames without timestamps
            if frame.pts is None:
                continue

            ts = float(frame.pts * stream.time_base)

            if progress_callback and total_duration and total_duration > 0:
                progress = min(1.0, max(0.0, ts / total_duration))
                progress_callback(progress)

            # Sample frames based on time interval
            if ts < nextTime:
                continue
            nextTime = ts + sampleSeconds

            rgb = frame.to_ndarray(format="rgb24")

            # ---------- CHEAP PIXEL HASH CHECK ----------
            # Resize to 64x64 grayscale for fast comparison
            raw_gray_small = cv2.resize(
                cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY),
                (64, 64)
            )

            if prev_gray_small is not None:
                pixel_diff = np.mean(
                    np.abs(raw_gray_small.astype(np.float32) - prev_gray_small.astype(np.float32))
                ) / 255.0
                frame_changed = pixel_diff >= PIXEL_DIFF_THRESHOLD
            else:
                frame_changed = True

            prev_gray_small = raw_gray_small

            if frame_changed or frames_since_last_ocr >= MAX_REUSE_FRAMES:
                # ---------- OCR (DUAL PASS STRATEGY) ----------
                gray, processed = preprocess_for_ocr(rgb)

                # First OCR pass on processed image
                data = pytesseract.image_to_data(
                    processed,
                    lang="eng",
                    config=tesseract_config,
                    output_type=Output.DICT
                )
                text = " ".join([str(w) for w in data["text"] if str(w).strip()])

                # Second OCR pass only if raw text is not truly empty
                # and still missing digits or payment keywords
                if (
                    len(text.strip()) >= 15
                    and not DIGIT_PATTERN.search(text)
                    and "paid" not in text.lower()
                ):
                    data = pytesseract.image_to_data(
                        gray,
                        lang="eng",
                        config=(
                            "--oem 1 --psm 6 "
                            "-c tessedit_char_whitelist="
                            "₹0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                        ),
                        output_type=Output.DICT
                    )
                    text = " ".join([str(w) for w in data["text"] if str(w).strip()])

                norm_text = normalizeText(text)
                draw_text_bounding_boxes(rgb, data, scale_factor=2.0)

                # ---------- ROI OCR FOR PAYMENT AREA ----------
                # Only run ROI pass if frame has meaningful content but
                # still missing amount and payment keywords
                if (
                    len(text.strip()) >= 15
                    and not extract_amounts(norm_text)
                    and not any(k in norm_text for k in ("paid", "payment", "success"))
                ):
                    roi = extract_payment_roi(rgb)
                    roi_gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
                    roi_gray = cv2.resize(
                        roi_gray, None,
                        fx=2, fy=2,
                        interpolation=cv2.INTER_CUBIC
                    )

                    roi_data = pytesseract.image_to_data(
                        roi_gray,
                        lang="eng",
                        config="--oem 1 --psm 6",
                        output_type=Output.DICT
                    )
                    
                    roi_text = " ".join([str(w) for w in roi_data["text"] if str(w).strip()])

                    if roi_text.strip():
                        norm_text += " " + normalizeText(roi_text)
                        
                        h, w, _ = rgb.shape
                        y1 = int(0.30 * h)
                        x1 = int(0.10 * w)
                        draw_text_bounding_boxes(rgb, roi_data, offset_x=x1, offset_y=y1, scale_factor=2.0)

                prev_norm_text = norm_text
                frames_since_last_ocr = 0

            else:
                # Frame almost identical to previous — reuse OCR result
                norm_text = prev_norm_text
                frames_since_last_ocr += 1
                

            # Token extraction
            tokens = cleanTokens(extractTokens(norm_text))
            frameAnchors = anchorTokens(tokens)

            # Initialize first segment
            if currentSegment is None:
                currentSegment = startSegment(ts, frameIndex)
                similarity = 1.0
                lowCount = 0

            # ---------- SMART QR DETECTION ----------
            # Skip QR scan only when segment is stable AND QR already found.
            # Always scan on new/changing screens.
            already_has_qr = bool(currentSegment.get("qrTexts"))
            screen_stable  = lowCount == 0 and len(currentSegment["frames"]) > 5

            if not (already_has_qr and screen_stable):
               qr_text, qr_points = extract_qr_text(rgb)

               if qr_text:

                    if (
                        qr_text.lower().startswith("upi://")
                        or "pay" in qr_text.lower()
                        or "payment" in qr_text.lower()
                    ):
                        currentSegment["qrTexts"].append(qr_text)
                        if qr_points is not None:
                            qr_points = qr_points.astype(int)
                            cv2.polylines(rgb, [qr_points], True, (0, 255, 0), 5)

            # Compute anchor stability for segmentation
            stable_anchors = {
                a for a, c in currentSegment["anchor_freq"].items()
                if c >= 3
            }

            if not stable_anchors:
                similarity = 1.0
            else:
                matched = sum(1 for a in stable_anchors if a in frameAnchors)
                similarity = matched / len(stable_anchors)

            # Count consecutive low similarity frames
            lowCount = lowCount + 1 if similarity < similarityThreshold else 0

            # Start a new segment if screen changes
            if lowCount >= maxLow:
                currentSegment["endTime"] = ts
                attachProofFrame(currentSegment, frames_dir)
                segments.append(currentSegment)
                currentSegment = startSegment(ts, frameIndex)
                lowCount = 0
            else:
                currentSegment["endTime"] = ts
                currentSegment["frames"].append(frameIndex)

            # Collect structured signals
            for amt in extract_amounts(norm_text):
                currentSegment["amounts"][amt] += 1

            for p in extract_counterparties(norm_text):
                currentSegment["counterparties"][p] += 1

            for a in frameAnchors:
                currentSegment["anchor_freq"][a] = (
                    currentSegment["anchor_freq"].get(a, 0) + 1
                )

            # Aggregate text content
            currentSegment["tokens"].update(tokens)
            currentSegment["ocr_text"] += " " + norm_text
            currentSegment["frame_texts"].append(norm_text)

            # Collect per-frame OCR output in memory (flushed after loop)
            ocr_lines.append(f"FRAME {frameIndex}\n")
            ocr_lines.append(f"TIME {ts:.3f} seconds\n")
            if norm_text.strip():
                ocr_lines.append("OCR TEXT\n")
                ocr_lines.append(norm_text)
            ocr_lines.append("\n\n")

            # Save extracted frame image at reduced quality (debug only)
            Image.fromarray(rgb).save(
                os.path.join(
                    frames_dir,
                    f"frame{frameIndex}.jpg"
                ),
                quality=75
            )

            logging.info(
                f"Frame {frameIndex} at {ts:.2f}s | similarity={similarity:.2f} | lowCount={lowCount}"
            )

            frameIndex += 1

    # Flush all OCR lines to disk in a single write
    with open(
        os.path.join(output_dir, "ocr_output.txt"),
        "w",
        encoding="utf-8"
    ) as out:
        out.write("".join(ocr_lines))

    # Append last segment
    if currentSegment:
        attachProofFrame(currentSegment, frames_dir)
        segments.append(currentSegment)

    writeSegments(segments,output_dir)

    # -------------------- SCORING --------------------

    results = []

    # Score each segment using transaction rules
    for seg in segments:
        res = score_segment(seg, rules)
        results.append(res)

    from engine.scoring import write_segment_verdicts

    # Save segment verdicts as JSON
    write_segment_verdicts(
        segments=segments,
        segment_scores=results,
        output_dir=output_dir
    )

    # -------------------- BETTING ANALYSIS --------------------

    run_betting_analysis(
        segments=segments,
        segment_verdicts_path=os.path.join(
            output_dir,
            "segment_verdicts.json"
        ),
        rules_path="rules/bettingSignals.json",
        output_dir=output_dir
    )

    run_crypto_betting_analysis(
        segments=segments,
        segment_verdicts_path=os.path.join(
            output_dir,
            "segment_verdicts.json"
        ),
        output_path=os.path.join(
            output_dir,
            "crypto_betting_attribution.json"
        )
    )

    # -------------------- FINAL REPORTS --------------------

    generate_final_verdict(
        segments=segments,
        results=results,
        frame_dir=frames_dir,
        output_path=os.path.join(
            output_dir,
            "final_verdict_report.txt"
        )
        
    )

    segments_summary = load_segment_verdicts(
        os.path.join(
            output_dir,
            "segment_verdicts.json"
        )
    )
    generate_final_summary(
        segments_summary,
        output_dir=output_dir,
        video_name=video_name
    )

    logging.info(f"Frames saved: {frameIndex}")
    logging.info(f"Segments detected: {len(segments)}")
    logging.info("Final verdict report generated")
    logging.info("Final summary generated")


if __name__ == "__main__":
    extractFrames(sys.argv[1])
