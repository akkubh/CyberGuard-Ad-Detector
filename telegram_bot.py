"""
telegram_bot.py
───────────────
CyberGuard Telegram Bot — Nuh Police Cyber Crime Unit

WHY TELEGRAM:
Most Indian scams are forwarded on WhatsApp and Telegram. Instead of
expecting victims to install a Chrome extension, this bot lets anyone:
  1. Forward a suspicious message directly to the bot
  2. Send a screenshot of a scam ad
  3. Get an instant AI risk assessment
  4. Report to police with one tap

SETUP:
  1. Message @BotFather on Telegram → /newbot → get your token
  2. pip install python-telegram-bot requests
  3. Set env var: TELEGRAM_BOT_TOKEN=your_token_here
  4. python telegram_bot.py

TECHNICAL NOTE:
python-telegram-bot uses long-polling — it continuously asks Telegram's
servers "any new messages?" every few seconds. For production, switch to
webhooks (set_webhook) which is more efficient and works on free-tier servers.

The bot sends text to our FastAPI /analyze endpoint — the same ML model
used by the Chrome Extension. It also calls /analyze-image for screenshots.
"""

import os
import logging
import requests
import base64
from io import BytesIO

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cyberguard-bot")

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        CallbackQueryHandler, ContextTypes, filters
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

API_BASE  = os.environ.get("CYBERGUARD_API_URL", "http://localhost:8000")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


# ── HELPERS ──────────────────────────────────────────────────────────────────
def analyze_text(text: str) -> dict:
    try:
        r = requests.post(f"{API_BASE}/analyze", json={"text": text, "url": ""}, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e), "risk_score": 0, "verdict": "API_ERROR"}

def analyze_image_b64(b64: str) -> dict:
    try:
        r = requests.post(f"{API_BASE}/analyze-image", json={"image": b64}, timeout=20)
        return r.json()
    except Exception as e:
        return {"error": str(e), "risk_score": 0, "verdict": "API_ERROR"}

def submit_report(result: dict, user: dict, comment: str = "") -> dict:
    try:
        r = requests.post(f"{API_BASE}/report", json={
            "reporter_name":    f"Telegram: {user.get('first_name','')} ({user.get('id','')})",
            "comment":          comment,
            "url":              result.get("url", ""),
            "risk_score":       result.get("risk_score", 0),
            "verdict":          result.get("verdict", ""),
            "fraud_category":   result.get("fraud_category", ""),
            "flagged_keywords": result.get("flagged_keywords", {}),
            "evidence_text":    result.get("ocr_text", "") or result.get("text_snippet", ""),
        }, timeout=10)
        return r.json()
    except Exception as e:
        return {"report_id": "OFFLINE", "message": str(e)}

def format_result_message(result: dict) -> str:
    score = result.get("risk_score", 0)
    if score >= 80:   emoji, level = "🔴", "CRITICAL RISK"
    elif score >= 60: emoji, level = "🟠", "HIGH RISK"
    elif score >= 35: emoji, level = "🟡", "CAUTION"
    else:             emoji, level = "🟢", "LIKELY SAFE"

    verdict  = result.get("verdict", "UNKNOWN")
    category = result.get("fraud_category", "Unknown")
    kw_map   = result.get("flagged_keywords", {})
    kw_total = sum(len(v) for v in kw_map.values())

    lines = [
        f"{emoji} *CyberGuard Analysis*",
        f"",
        f"*Risk Score:* `{score}%`  —  {level}",
        f"*Verdict:* `{verdict}`",
        f"*Fraud Type:* {category}",
        f"*Red Flags:* {kw_total} suspicious phrases",
    ]

    if kw_map:
        lines.append("")
        lines.append("*Flagged Patterns:*")
        for cat, kws in list(kw_map.items())[:3]:
            lines.append(f"  • {cat}: `{', '.join(kws[:3])}`")

    if result.get("ocr_text"):
        lines.append(f"\n_OCR confidence: {result.get('ocr_confidence', 0):.0f}%_")

    return "\n".join(lines)


# ── COMMAND HANDLERS ──────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡️ *CyberGuard — Nuh Police Cyber Crime Unit*\n\n"
        "I can analyse suspicious advertisements for fraud.\n\n"
        "*How to use:*\n"
        "• Forward any suspicious message to me\n"
        "• Send a screenshot of a suspicious ad\n"
        "• Type `/help` for more options\n\n"
        "_Developed by Ankita Bhargava for Nuh Police internship_",
        parse_mode="Markdown"
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*CyberGuard Commands:*\n\n"
        "/start — Welcome message\n"
        "/help  — This help text\n"
        "/stats — Today's fraud statistics\n\n"
        "*Just send me:*\n"
        "• Any text message → I'll analyse it\n"
        "• Any image/screenshot → OCR + analysis\n"
        "• A URL → I'll check it for phishing\n\n"
        "*Risk Levels:*\n"
        "🟢 0–30%: Likely safe\n"
        "🟡 31–60%: Caution advised\n"
        "🟠 61–80%: High risk\n"
        "🔴 81–100%: Critical — likely scam",
        parse_mode="Markdown"
    )

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{API_BASE}/reports/stats", timeout=5)
        s = r.json()
        await update.message.reply_text(
            f"📊 *CyberGuard Statistics*\n\n"
            f"Total reports filed: `{s.get('total_reports', 0)}`\n"
            f"High risk detections: `{s.get('high_risk', 0)}`\n"
            f"Reports today: `{s.get('filed_today', 0)}`\n"
            f"Avg risk score: `{s.get('avg_risk_score', 0)}%`",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("Stats unavailable — backend may be offline.")


# ── MESSAGE HANDLER ───────────────────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text or len(text) < 10:
        return

    msg = await update.message.reply_text("🔍 Analysing...")

    result = analyze_text(text)
    reply  = format_result_message(result)

    # Store result in context for report button callback
    context.user_data["last_result"] = result

    keyboard = []
    if result.get("risk_score", 0) > 40:
        keyboard.append([
            InlineKeyboardButton("🚔 Report to Nuh Police", callback_data="report"),
            InlineKeyboardButton("ℹ️ Details", callback_data="details"),
        ])
    else:
        keyboard.append([InlineKeyboardButton("ℹ️ Details", callback_data="details")])

    await msg.edit_text(reply, parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image/screenshot analysis via OCR."""
    msg = await update.message.reply_text("🔍 Reading image text (OCR)...")

    # Get highest-res version of photo
    photo  = update.message.photo[-1]
    f      = await photo.get_file()
    buf    = BytesIO()
    await f.download_to_memory(buf)
    b64    = base64.b64encode(buf.getvalue()).decode()

    result = analyze_image_b64(b64)
    context.user_data["last_result"] = result

    if result.get("verdict") == "UNREADABLE":
        await msg.edit_text("⚠️ Could not read text from image. Try a clearer screenshot.")
        return

    reply   = format_result_message(result)
    ocr_txt = result.get("ocr_text", "")[:150]
    if ocr_txt:
        reply += f"\n\n_Extracted text: \"{ocr_txt}...\"_"

    keyboard = []
    if result.get("risk_score", 0) > 40:
        keyboard.append([InlineKeyboardButton("🚔 Report to Nuh Police", callback_data="report")])

    await msg.edit_text(reply, parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)


# ── CALLBACK HANDLER (inline buttons) ────────────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await query.answer()

    result = context.user_data.get("last_result", {})

    if query.data == "report":
        rep = submit_report(result, query.from_user.__dict__)
        await query.message.reply_text(
            f"✅ *Report Filed Successfully*\n\n"
            f"Report ID: `{rep.get('report_id', 'N/A')}`\n"
            f"Status: Filed with Nuh Police Cyber Crime Unit\n\n"
            f"_Thank you for helping fight cyber fraud._",
            parse_mode="Markdown"
        )

    elif query.data == "details":
        kw_map = result.get("flagged_keywords", {})
        if kw_map:
            detail = "*All Flagged Keywords:*\n\n"
            for cat, kws in kw_map.items():
                detail += f"*{cat}:*\n"
                detail += "\n".join(f"  • `{kw}`" for kw in kws) + "\n\n"
        else:
            detail = "No specific risk keywords found."
        await query.message.reply_text(detail, parse_mode="Markdown")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def run_bot():
    if not TELEGRAM_AVAILABLE:
        print("Install: pip install python-telegram-bot requests")
        return
    if not BOT_TOKEN:
        print("Set env: TELEGRAM_BOT_TOKEN=your_token_here")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    log.info("CyberGuard bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
