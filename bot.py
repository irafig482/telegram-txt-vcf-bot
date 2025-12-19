import os
import math
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📂 Kirim file TXT (1 nomor per baris)\n"
        "Saya akan mengubahnya menjadi beberapa file VCF."
    )

async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    content = await file.download_as_bytearray()
    numbers = [n.strip() for n in content.decode().splitlines() if n.strip()]

    sessions[update.effective_user.id] = {"numbers": numbers}
    await update.message.reply_text("✍️ Masukkan NAMA KONTAK")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in sessions:
        return

    s = sessions[uid]
    text = update.message.text.strip()

    if "contact_name" not in s:
        s["contact_name"] = text
        await update.message.reply_text("🔢 Mulai dari nomor berapa?")
        return

    if "start_number" not in s:
        if not text.isdigit():
            await update.message.reply_text("❌ Harus angka")
            return
        s["start_number"] = int(text)
        await update.message.reply_text("📦 1 VCF berisi berapa kontak?")
        return

    if "per_vcf" not in s:
        if not text.isdigit():
            await update.message.reply_text("❌ Harus angka")
            return
        s["per_vcf"] = int(text)
        await update.message.reply_text("📝 Masukkan NAMA FILE VCF")
        return

    if "vcf_name" not in s:
        s["vcf_name"] = text
        await show_preview(update, context, s)

async def show_preview(update, context, s):
    total = len(s["numbers"])
    total_files = math.ceil(total / s["per_vcf"])

    msg = (
        "📊 PREVIEW PEMBUATAN VCF\n\n"
        f"📱 Total nomor : {total}\n"
        f"📦 Kontak/VCF : {s['per_vcf']}\n"
        f"📁 Total file : {total_files}\n\n"
        f"👤 Nama kontak : {s['contact_name']} ({s['start_number']} →)\n"
        f"📝 Nama file : {s['vcf_name']}_X.vcf\n\n"
        "Lanjutkan?"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Buat VCF", callback_data="create")],
        [InlineKeyboardButton("❌ Batal", callback_data="cancel")]
    ])

    await update.message.reply_text(msg, reply_markup=keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if uid not in sessions:
        return

    if query.data == "cancel":
        sessions.pop(uid)
        await query.edit_message_text("❌ Dibatalkan.")
        return

    if query.data == "create":
        await query.edit_message_text("⏳ Membuat file VCF...")
        await create_vcf_files(query.message, context, sessions[uid])
        sessions.pop(uid)

async def create_vcf_files(message, context, s):
    numbers = s["numbers"]
    per_vcf = s["per_vcf"]
    counter = s["start_number"]

    total_files = math.ceil(len(numbers) / per_vcf)

    for i in range(total_files):
        chunk = numbers[i*per_vcf:(i+1)*per_vcf]
        filename = f"{s['vcf_name']}_{i+1}.vcf"

        with open(filename, "w") as f:
            for num in chunk:
                f.write(
                    "BEGIN:VCARD\n"
                    "VERSION:3.0\n"
                    f"N:{s['contact_name']} {counter};;;;\n"
                    f"FN:{s['contact_name']} {counter}\n"
                    f"TEL;TYPE=CELL:{num}\n"
                    "END:VCARD\n"
                )
                counter += 1

        await context.bot.send_document(
            chat_id=message.chat_id,
            document=open(filename, "rb"),
            caption=f"✅ {filename}"
        )
        os.remove(filename)

def main():
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.TEXT, handle_txt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
