import asyncio
import logging
import requests
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    CallbackContext,
    ApplicationBuilder,
    ConversationHandler,
    MessageHandler,
    filters,
    BotCommand
)
from telegram import Update
import custom_config
from db_interactor import add_user, check_and_update_telegram_user, get_user_info_by_telegram_id, update_anilist_username


from custom_logging import set_logger
from daemon_connectors import main_daemon_job

log = set_logger("TELEGRAM_BOT", logging.INFO)


ASK_ANILIST_USERNAME = range(1)


def set_bot_commands():
    url = f"https://api.telegram.org/bot{custom_config.BOT_TOKEN}/setMyCommands"

    commands = [
        {"command": "help", "description": "Get a full bot description"},
        {"command": "start", "description": "Start the bot for the first time"},
        {"command": "status", "description": "Get the user status"},
        {"command": "change-anilist-username",
            "description": "Change your referred anilist username"},
    ]

    requests.post(url, json={"commands": commands}, timeout=30)


async def help_command(update: Update, _ : ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        log.info("HELP called but user is None")
        return
    if update.message is None:
        log.info("HELP called but message is None")
        return
    log.info("HELP called by "+str(user.id) + " "+str(user.username))
    if not check_and_update_telegram_user(user.id, user.username):
        return
    onboarding_message_text = (
        "<b>❓ Need help with Anipush?</b>\n"
        "<i>Work in progress...\n\n"
        "Use /start to register your Anilist username.\n"
        "Use /changeusername to update your Anilist username.</i>"
    )
    log.info("Sending help message to "+str(user.id))
    await update.message.reply_text(onboarding_message_text, parse_mode="HTML")


async def start_command(update: Update, _ : ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        log.info("START called but user is None")
        return
    if update.message is None:
        log.info("START called but message is None")
        return
    log.info(f"START called by {user.id} {user.username}")
    if not check_and_update_telegram_user(user.id, user.username):
        add_user(user.id, user.username or "redacted")
    info = get_user_info_by_telegram_id(user.id)
    if info and info.get("anilist_id", -1) != -1:
        await update.message.reply_text(
            "<b>ℹ️ You are already registered with Anilist.</b>\nUse /changeusername if you want to update your Anilist username.",
            parse_mode="HTML"
        )
        return
    await update.message.reply_text(
        "<b>👋 Welcome to Anipush!</b>\n\n"
        "To get started, please send me your <b>Anilist username</b>.",
        parse_mode="HTML"
    )
    return ASK_ANILIST_USERNAME


async def receive_anilist_username(update: Update, _ : ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        log.info("RECEIVE_ANILIST_USERNAME called but user is None")
        return
    if update.message is None:
        log.info("RECEIVE_ANILIST_USERNAME called but message is None")
        return
    if update.message.text is None or len(update.message.text) == "":
        log.info("RECEIVE_ANILIST_USERNAME called but username is None")
        return
    anilist_username = update.message.text.strip()
    update_anilist_username(user.id, anilist_username)
    log.info(
        f"Saved anilist username '{anilist_username}' for telegram_id {user.id}")
    await update.message.reply_text(
        f"<b>✅ Thank you!</b>\n\nYour Anilist username <b>{anilist_username}</b> has been saved.",
        parse_mode="HTML"
    )
    return ConversationHandler.END


async def change_anilist_command(update: Update, _ : ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        log.info("CHANGE_ANILIST called but user is None")
        return
    if update.message is None:
        log.info("CHANGE_ANILIST called but message is None")
        return
    log.info(f"CHANGE_ANILIST called by {user.id} {user.username}")
    await update.message.reply_text(
        "<b>✏️ Change Anilist Username</b>\n\n"
        "Please send me your <b>new Anilist username</b>.",
        parse_mode="HTML"
    )
    return ASK_ANILIST_USERNAME


async def status_command(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        log.info("STATUS called but user is None")
        return
    if update.message is None:
        log.info("STATUS called but message is None")
        return
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


async def process_users_job(_: CallbackContext):
    log.info("[JOB] Running process_users_with_missing_anilist_id...")
    await asyncio.get_event_loop().run_in_executor(None, main_daemon_job)


def init_telegram_bot():
    app = ApplicationBuilder().token(custom_config.BOT_TOKEN).build()
    if app.job_queue is None:
        raise Exception("Job Queue is none, returning")
    logging.getLogger("telegram").setLevel(logging.INFO)
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("help", help_command),
            CommandHandler("start", start_command),
            CommandHandler("changeusername", change_anilist_command),
            CommandHandler("status", status_command)
        ],
        states={
            ASK_ANILIST_USERNAME: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, receive_anilist_username)]
        },
        fallbacks=[]
    )

    commands = [
        BotCommand("help", "Get help"),
        BotCommand("start", "Create your account into the platform"),
        BotCommand("status", "Get your user status"),
        BotCommand("changeusername", "Change your anilist username")
    ]
    app.bot.set_my_commands(commands)
    app.add_handler(conv_handler)
    set_bot_commands()
    app.job_queue.run_repeating(process_users_job, interval=60, first=5)
    log.info("Bot avviato...")

    app.run_polling()
