"""
TENDER SNIPER - TELEGRAM MONETIZATION BOT
Library: python-telegram-bot (v20+)
Features: Auto-post tender alerts with monetization buttons
"""

import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# CONFIGURATION - GANTI DENGAN TOKEN BOT ANDA
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Dapatkan dari @BotFather
CHANNEL_ID = "@tender_sniper_channel"  # Channel publik untuk broadcast

# MONETIZATION LINKS - GANTI DENGAN LINK ANDA
GUMROAD_TEMPLATE_URL = "https://gumroad.com/l/YOUR_TEMPLATE_LINK"  # Template Proposal Rp 25.000
TRAKTEER_TEMPLATE_URL = "https://trakteer.id/YOUR_LINK/tip"  # Alternatif Trakteer
EMETERAI_AFFILIATE_URL = "https://e-meterai.co.id/?ref=YOUR_CODE"  # Affiliate e-Meterai

# SUPABASE CONFIG (opsional, untuk dedup)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

def format_tender_alert(tender):
    """
    Format pesan dengan URGENCY dan FOMO
    """
    # Hitung sisa hari
    try:
        tutup = datetime.strptime(tender['tanggal_tutup'], "%d-%m-%Y %H:%M")
        sisa = (tutup - datetime.now()).days
        urgency = "🔴 HARI INI TUTUP!" if sisa <= 0 else f"⚠️ {sisa} HARI LAGI"
    except:
        urgency = "⚠️ CEK DEADLINE"

    # Hitung estimasi keuntungan (asumsi 10-15% markup)
    pagu = tender['nilai_pagu']
    estimasi_profit = pagu * 0.12

    message = f"""
🎯 *TENDER SNIPER ALERT*
━━━━━━━━━━━━━━━━━━━━━

📌 *{tender['judul'][:100]}*

💰 *PAGU:* `{tender['nilai_pagu_formatted']}`
📍 *Lokasi:* {tender['satuan_kerja']}
🏗️ *Kategori:* {tender['kategori']}
⏰ *Deadline:* `{tender['tanggal_tutup']}`
{urgency}

💡 *Estimasi Keuntungan:* Rp {estimasi_profit:,.0f}
🔗 *Link Detail:* [Klik Disini]({tender['link_detail']})

━━━━━━━━━━━━━━━━━━━━━
🚀 *BUTUH TEMPLATE PROPOSAL?*
Klik tombol di bawah untuk download template siap pakai + HPS format.

⚡ *BUTUH E-METERAI?*
Beli e-Meterai online tanpa antri.
"""
    return message

def build_monetization_keyboard():
    """
    Inline keyboard dengan monetization buttons
    """
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔓 Download Template Proposal & HPS (Rp 25.000)", 
                url=GUMROAD_TEMPLATE_URL
            )
        ],
        [
            InlineKeyboardButton(
                text="📜 Beli e-Meterai Online", 
                url=EMETERAI_AFFILIATE_URL
            )
        ],
        [
            InlineKeyboardButton(
                text="📢 Join Channel Tender", 
                url=f"https://t.me/{CHANNEL_ID.replace('@', '')}"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler command /start"""
    welcome = """
🎯 *TENDER SNIPER BOT*
Bot ini mengirimkan tender pemerintah dengan pagu < Rp 200 juta secara OTOMATIS.

✅ *Cara kerja:*
• Scrape LPSE setiap 1 jam
• Filter tender < Rp 200 juta
• Kirim ke channel dengan alert urgency

💰 *Monetisasi:*
• Template Proposal: Rp 25.000
• e-Meterai Online: Komisi affiliate

📢 *Join channel:* {channel}

Ketik /help untuk info lebih lanjut.
    """.format(channel=CHANNEL_ID)

    await update.message.reply_text(welcome, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler command /help"""
    help_text = """
📖 *PANDUAN TENDER SNIPER*

*Perintah:*
/start - Mulai bot
/help - Bantuan
/status - Cek status scraper
/latest - 5 tender terbaru

*Cara Menang Tender:*
1. Klik link detail tender
2. Download template proposal (Rp 25.000)
3. Siapkan dokumen lengkap
4. Submit sebelum deadline

*Butuh bantuan?* Hubungi admin.
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def broadcast_tender(tender, application):
    """
    Kirim tender ke channel dengan monetization buttons
    Dipanggil oleh scraper cron job
    """
    try:
        message = format_tender_alert(tender)
        keyboard = build_monetization_keyboard()

        await application.bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

        print(f"[BOT] Broadcasted: {tender['judul'][:40]}...")
        return True

    except Exception as e:
        print(f"[BOT ERROR] Broadcast failed: {e}")
        return False

async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /latest - tampilkan 5 tender terbaru dari file"""
    try:
        with open("tenders_jatim.json", "r") as f:
            tenders = json.load(f)

        if not tenders:
            await update.message.reply_text("❌ Belum ada data tender. Scraper sedang berjalan...")
            return

        # Ambil 5 terbaru
        latest = tenders[:5]

        for t in latest:
            msg = format_tender_alert(t)
            keyboard = build_monetization_keyboard()
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=keyboard)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler /status - cek status sistem"""
    try:
        with open("tenders_jatim.json", "r") as f:
            tenders = json.load(f)

        status = f"""
📊 *STATUS TENDER SNIPER*

📁 Total tender tersimpan: {len(tenders)}
⏰ Last update: {datetime.now().strftime('%d-%m-%Y %H:%M')}
🤖 Bot status: ONLINE
📢 Channel: {CHANNEL_ID}

Sistem berjalan otomatis setiap 1 jam.
        """
        await update.message.reply_text(status, parse_mode="Markdown")

    except:
        await update.message.reply_text("❌ Data belum tersedia. Scraper pertama sedang berjalan...")

def main():
    """Entry point"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("latest", latest_command))
    application.add_handler(CommandHandler("status", status_command))

    print("[BOT] Tender Sniper Bot started. Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
