import os
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)
import fitz  # PyMuPDF

# --- CONFIGURATION (from Environment Variables) ---
# Read Bot Token and Admin IDs securely from the hosting environment.
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")

try:
    # Convert the comma-separated string of admin IDs to a list of integers.
    ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip()]
except ValueError:
    print("FATAL ERROR: ADMIN_IDS environment variable contains non-integer values.")
    sys.exit(1)

# --- HARDCODED WATERMARK SETTINGS ---
# Customize your watermark's appearance here!
WATERMARK_TEXT = "NOTES BY @YAKEENPRINTABLE ON TG"
WATERMARK_FONT_SIZE = 20
WATERMARK_ROTATION = 45
WATERMARK_COLOR = (0.8, 0.0, 0.0)  # Dark Red (R, G, B from 0.0 to 1.0)
WATERMARK_OPACITY = 0.4            # 40% transparent (from 0.0 to 1.0)

# --- HELPER FUNCTION ---
def add_watermark_and_flatten(input_pdf_path: str, output_pdf_path: str):
    """Adds the predefined text watermark to a PDF and flattens it."""
    doc = fitz.open(input_pdf_path)
    for page in doc:
        rect = page.rect
        text_length = fitz.get_text_length(WATERMARK_TEXT, fontname="helv", fontsize=WATERMARK_FONT_SIZE)
        
        # Position the watermark in the center of the page
        text_pos = fitz.Point((rect.width - text_length) / 2, (rect.height) / 2)
        
        # Insert the watermark text with all the defined settings
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
    # Save the changes, flattening the file to make the watermark permanent
    doc.save(output_pdf_path, garbage=4, deflate=True)
    doc.close()

# --- TELEGRAM BOT HANDLERS ---
async def start(update: Update, context: CallbackContext):
    """Handles the /start command and provides a different message to admins vs. others."""
    if update.message.from_user.id in ADMIN_IDS:
        await update.message.reply_text("Welcome, Admin! This bot automatically watermarks any PDF you send.")
    else:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")

async def process_pdf(update: Update, context: CallbackContext):
    """The main function that processes incoming PDFs."""
    # 1. SECURITY: Check if the user is an authorized admin.
    if update.message.from_user.id not in ADMIN_IDS:
        print(f"Denied access for unauthorized user: {update.message.from_user.id}")
        return

    # Ignore messages that aren't PDFs
    if not update.message.document or update.message.document.mime_type != 'application/pdf':
        return

    await update.message.reply_text("Processing your PDF...")
    
    # 2. FILENAME PRESERVATION: Get the original filename from the message.
    original_filename = update.message.document.file_name
    download_dir = "downloads"
    os.makedirs(download_dir, exist_ok=True)
    file_path = os.path.join(download_dir, original_filename)
    
    file = await update.message.document.get_file()
    await file.download_to_drive(file_path)

    try:
        # Perform the watermarking, overwriting the downloaded file with the new version.
        add_watermark_and_flatten(file_path, file_path)
        
        # Send the processed PDF back to the user with its original name.
        await update.message.reply_document(
            document=open(file_path, 'rb'),
            filename=original_filename
        )
        
    except Exception as e:
        # Inform the user if something goes wrong.
        await update.message.reply_text(f"An error occurred while processing your file: {e}")
        print(f"ERROR processing '{original_filename}': {e}")
        
    finally:
        # 3. CACHE CLEANUP: This block is guaranteed to run, ensuring files are always deleted.
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up temporary file: {file_path}")

# --- MAIN BOT FUNCTION ---
def main():
    """Starts the bot and sets up the handlers."""
    # Safety check: ensure essential environment variables are set before starting.
    if not BOT_TOKEN or not ADMIN_IDS:
        print("FATAL ERROR: TELEGRAM_BOT_TOKEN and ADMIN_IDS must be set in the environment.")
        sys.exit(1)

    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register the handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.Document.PDF, process_pdf))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
