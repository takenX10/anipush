import requests
import custom_config
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    CallbackContext,
    ApplicationBuilder,
    ConversationHandler,
    MessageHandler,
    filters
)

from custom_logging import set_logger
from db_interactor import upsert_user_telegram_anilist, get_user_info_by_telegram_id

ASK_ANILIST_USERNAME = range(1)

log = set_logger("TELEGRAM_BOT")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info("HELP called by "+str(user.id) + " "+str(update.effective_user.username))
    onboarding_message_text = (
        "<b>❓ Need help with Anipush?</b>\n"
        "<i>Work in progress...\n\n"
        "Use /start to register your Anilist username.\n"
        "Use /change-anilist-username to update your Anilist username.</i>"
    )
    log.info("Sending help message to "+str(user.id))
    await update.message.reply_text(onboarding_message_text, parse_mode="HTML")


def set_bot_commands():
    url = f"https://api.telegram.org/bot{custom_config.BOT_TOKEN}/setMyCommands"

    commands = [
        {"command": "help", "description":"Get a full bot description"},
        {"command": "start", "description":"Start the bot for the first time"},
        {"command": "status", "description":"Get the user status"},
        {"command": "change-anilist-username", "description":"Change your referred anilist username"},
    ]

    requests.post(url, json={"commands": commands})

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info(f"START called by {user.id} {user.username}")
    await update.message.reply_text(
        "<b>👋 Welcome to Anipush!</b>\n\n"
        "To get started, please send me your <b>Anilist username</b>.",
        parse_mode="HTML"
    )
    return ASK_ANILIST_USERNAME

async def receive_anilist_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    anilist_username = update.message.text.strip()
    upsert_user_telegram_anilist(user.id, anilist_username)
    log.info(f"Saved anilist username '{anilist_username}' for telegram_id {user.id}")
    await update.message.reply_text(
        f"<b>✅ Thank you!</b>\nYour Anilist username <b>{anilist_username}</b> has been saved.",
        parse_mode="HTML"
    )
    return ConversationHandler.END

async def change_anilist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info(f"CHANGE_ANILIST called by {user.id} {user.username}")
    await update.message.reply_text(
        "<b>✏️ Change Anilist Username</b>\n\n"
        "Please send me your <b>new Anilist username</b>.",
        parse_mode="HTML"
    )
    return ASK_ANILIST_USERNAME

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log.info(f"STATUS called by {user.id} {user.username}")
    info = get_user_info_by_telegram_id(user.id)
    if not info:
        await update.message.reply_text(
            "<b>ℹ️ No user info found.</b>\nUse /start to register your Anilist username.",
            parse_mode="HTML"
        )
        return
    msg = (
        f"<b>👤 Your Anipush Status</b>\n\n"
        f"<b>Anilist username:</b> {info['anilist_username'] or '<i>Not set</i>'}\n"
        f"<b>Anilist ID:</b> {info['anilist_id'] or '<i>Not set</i>'}\n"
        f"<b>Last activity checked:</b> {info['last_activity_checked'] or '<i>Never</i>'}"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


def init_telegram_bot():
    app = ApplicationBuilder().token(custom_config.BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start_command),
            CommandHandler("change-anilist-username", change_anilist_command)
        ],
        states={
            ASK_ANILIST_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_anilist_username)]
        },
        fallbacks=[]
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    set_bot_commands()
    #app.job_queue.run_repeating(followup_check, interval=timedelta(seconds=15))
    log.info("Bot avviato...")
    app.run_polling()