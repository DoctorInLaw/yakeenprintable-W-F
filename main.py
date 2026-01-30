import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)
import fitz  # PyMuPDF

# --- Bot Configuration ---
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"

# --- NEW: ADMIN CONFIGURATION ---
# Add the Telegram User IDs of admins allowed to use the bot.
# Find your ID by talking to @userinfobot on Telegram.
ADMIN_IDS = [123456789, 987654321]  # <-- Replace with your actual admin User ID(s)

# --- HARDCODED WATERMARK SETTINGS ---
WATERMARK_TEXT = "NOTES BY @PRINTABLEYAKEEN ON TG"
WATERMARK_FONT_SIZE = 20
WATERMARK_ROTATION = 45
WATERMARK_COLOR = (0.8, 0.0, 0.0)  # Dark Red
WATERMARK_OPACITY = 0.4            # 40% transparent

# --- Helper Function (No changes here) ---
def add_watermark_and_flatten(input_pdf_path: str, output_pdf_path: str):
    doc = fitz.open(input_pdf_path)
    for page in doc:
        rect = page.rect
        text_length = fitz.get_text_length(WATERMARK_TEXT, fontname="helv", fontsize=WATERMARK_FONT_SIZE)
        text_pos = fitz.Point((rect.width - text_length) / 2, (rect.height) / 2)
        page.insert_text(
            text_pos,
            WATERMARK_TEXT,
            fontname="helv",
            fontsize=WATERMARK_FONT_SIZE,
            rotate=WATERMARK_ROTATION,
            color=WATERMARK_COLOR,
            opacity=WATERMARK_OPACITY,
            overlay=True,
        )
    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()

# --- MODIFIED: Bot Handlers ---

async def start(update: Update, context: CallbackContext):
    """Sends a welcome message and checks if the user is an admin."""
    if update.message.from_user.id in ADMIN_IDS:
        await update.message.reply_text(
            "Welcome, Admin! This bot automatically watermarks any PDF you send."
        )
    else:
        await update.message.reply_text("Sorry, this is a private bot.")

async def process_pdf(update: Update, context: CallbackContext):
    """Receives a PDF, verifies the user, processes it, and sends it back with the original filename."""
    # --- MODIFICATION 1: Admin-only check ---
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    if not update.message.document or update.message.document.mime_type != 'application/pdf':
        return # Ignore non-PDF messages from admins

    await update.message.reply_text("Processing...")

    # --- MODIFICATION 2: Preserve original filename ---
    original_filename = update.message.document.file_name
    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)
    
    # Define the path using the original filename
    file_path = os.path.join(download_dir, original_filename)

    # Download the file
    file = await update.message.document.get_file()
    await file.download_to_drive(file_path)

    try:
        # Process the file. The output overwrites the input path.
        add_watermark_and_flatten(file_path, file_path)

        # Send the processed PDF back with the correct original filename
        await update.message.reply_document(
            document=open(file_path, 'rb'),
            filename=original_filename
        )
        
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")
        print(f"Error processing PDF for file '{original_filename}': {e}")
        
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

# --- Main Bot Function (No changes here) ---
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.Document.PDF, process_pdf))
    print("Secure bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
