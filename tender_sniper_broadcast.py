"""
TENDER SNIPER - BROADCAST SCRIPT
Dijalankan oleh GitHub Actions setelah scraper
"""

import json
import os
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@tender_sniper_channel")

GUMROAD_URL = "https://gumroad.com/l/YOUR_TEMPLATE_LINK"
EMETERAI_URL = "https://e-meterai.co.id/?ref=YOUR_CODE"

def format_alert(tender):
    pagu = tender['nilai_pagu']
    profit = pagu * 0.12
    return f"""🎯 *TENDER SNIPER ALERT*
📌 *{tender['judul'][:100]}*
💰 *PAGU:* `{tender['nilai_pagu_formatted']}`
📍 *Lokasi:* {tender['satuan_kerja']}
🏗️ *Kategori:* {tender['kategori']}
⏰ *Deadline:* `{tender['tanggal_tutup']}`
💡 *Estimasi Profit:* Rp {profit:,.0f}
🔗 [Link Detail]({tender['link_detail']})"""

def build_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔓 Template Proposal (Rp 25.000)", url=GUMROAD_URL)],
        [InlineKeyboardButton("📜 Beli e-Meterai", url=EMETERAI_URL)]
    ])

async def broadcast():
    bot = Bot(token=BOT_TOKEN)

    with open("tenders_jatim.json", "r") as f:
        tenders = json.load(f)

    # Filter: only tenders not yet broadcasted (check against last_broadcast.json)
    sent_ids = set()
    try:
        with open("last_broadcast.json", "r") as f:
            sent_ids = set(json.load(f))
    except:
        pass

    new_tenders = [t for t in tenders if t.get('link_detail') not in sent_ids]

    for tender in new_tenders:
        try:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=format_alert(tender),
                parse_mode="Markdown",
                reply_markup=build_keyboard(),
                disable_web_page_preview=True
            )
            sent_ids.add(tender['link_detail'])
            print(f"[OK] Broadcasted: {tender['judul'][:40]}")
        except Exception as e:
            print(f"[ERR] {e}")

    # Save sent IDs
    with open("last_broadcast.json", "w") as f:
        json.dump(list(sent_ids), f)

if __name__ == "__main__":
    asyncio.run(broadcast())
