"""
bot.py - Ponto de entrada do Telegram Learning Agent Bot.
Hibrido: menus inline + agente conversacional com IA + audio.
"""

import os
import logging
from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

import database as db
import keyboards as kb

from handlers.books import (
    books_menu, book_list, book_detail_view, book_status_menu, book_status_change,
    book_rate_menu, book_rate_set, book_delete_confirm, book_delete_execute,
    entry_list_menu, entry_list_view, book_ai_insights, book_ai_flashcards,
    get_book_conv_handler, get_entry_conv_handler
)
from handlers.studies import (
    studies_menu, study_list, study_detail_view, study_status_menu, study_status_change,
    study_delete_confirm, study_delete_execute, study_note_list, study_ai_flashcards,
    get_study_conv_handler, get_study_note_conv_handler
)
from handlers.insights import (
    insights_menu, insight_list, insight_ai_connect,
    get_insight_conv_handler
)
from handlers.flashcards import (
    flashcards_menu, fc_review_start, fc_show_answer, fc_rate_difficulty,
    get_fc_conv_handler
)
from handlers.search import show_stats, get_search_conv_handler

from handlers.agent import (
    handle_text_message, handle_voice_message, handle_audio_callback,
    handle_audio_edit, handle_edit_callback, handle_edit_text,
    handle_save_entry_callback
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN nao definido no .env")


WELCOME_TEXT = (
    "\U0001f9e0 *Learning Agent*\n\n"
    "Sou seu agente pessoal de aprendizado.\n\n"
    "*Converse comigo naturalmente:*\n"
    "\U0001f4da _\"Adicionar o livro Sapiens\"_\n"
    "\U0001f4ac _\"Salvar citacao: O homem e...\"_\n"
    "\U0001f4a1 _\"Aprendi no podcast que...\"_\n"
    "\U0001f50d _\"Buscar sobre produtividade\"_\n"
    "\U0001f399 Ou envie um *audio* que eu transcrevo!\n\n"
    "*Ou use os menus abaixo:*"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_TEXT, reply_markup=kb.main_menu(), parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from handlers.agent import _handle_help
    await _handle_help(update, context)


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteia mensagens de texto: edicao pendente > audio edit > agente IA."""
    if await handle_edit_text(update, context):
        return
    if await handle_audio_edit(update, context):
        return
    await handle_text_message(update, context)


async def main_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteia todos os callbacks inline."""
    query = update.callback_query
    data = query.data

    if data == "back_main":
        await query.answer()
        await query.edit_message_text(
            WELCOME_TEXT, reply_markup=kb.main_menu(), parse_mode="Markdown")

    elif data == "menu_books":
        await books_menu(update, context)
    elif data == "menu_studies":
        await studies_menu(update, context)
    elif data == "menu_insights":
        await insights_menu(update, context)
    elif data == "menu_flashcards":
        await flashcards_menu(update, context)
    elif data == "menu_stats":
        await show_stats(update, context)
    elif data == "menu_search":
        await query.answer()
        await query.edit_message_text("\U0001f50d Digite o que deseja buscar:")

    elif data.startswith("audio_"):
        await handle_audio_callback(update, context)

    elif data.startswith("save_entry_") or data.startswith("save_snote_"):
        await handle_save_entry_callback(update, context)

    elif data.startswith("edit_bentry_") or data.startswith("del_bentry_") or \
         data.startswith("del_snote_") or data.startswith("del_insight_") or \
         data.startswith("del_book_") or data.startswith("del_study_"):
        await handle_edit_callback(update, context)

    elif data.startswith("book_list_"):
        await book_list(update, context)
    elif data.startswith("book_detail_"):
        await book_detail_view(update, context)
    elif data.startswith("book_status_"):
        await book_status_menu(update, context)
    elif data.startswith("bstatus_"):
        await book_status_change(update, context)
    elif data.startswith("book_rate_"):
        await book_rate_menu(update, context)
    elif data.startswith("brate_"):
        await book_rate_set(update, context)
    elif data.startswith("book_delete_"):
        await book_delete_confirm(update, context)
    elif data.startswith("book_ai_insights_"):
        await book_ai_insights(update, context)
    elif data.startswith("book_ai_flashcards_"):
        await book_ai_flashcards(update, context)
    elif data.startswith("entry_list_"):
        await entry_list_menu(update, context)
    elif data.startswith("entries_"):
        await entry_list_view(update, context)

    elif data.startswith("study_list_"):
        await study_list(update, context)
    elif data.startswith("study_detail_"):
        await study_detail_view(update, context)
    elif data.startswith("study_status_"):
        await study_status_menu(update, context)
    elif data.startswith("sstatus_"):
        await study_status_change(update, context)
    elif data.startswith("study_delete_"):
        await study_delete_confirm(update, context)
    elif data.startswith("snote_list_"):
        await study_note_list(update, context)
    elif data.startswith("study_ai_flashcards_"):
        await study_ai_flashcards(update, context)

    elif data.startswith("insight_list_"):
        await insight_list(update, context)
    elif data == "insight_ai_connect":
        await insight_ai_connect(update, context)

    elif data == "fc_review":
        await fc_review_start(update, context)
    elif data.startswith("fc_show_"):
        await fc_show_answer(update, context)
    elif data.startswith("fc_diff_"):
        await fc_rate_difficulty(update, context)

    elif data.startswith("confirm_del_book_"):
        await book_delete_execute(update, context)
    elif data.startswith("confirm_del_study_"):
        await study_delete_execute(update, context)
    elif data.startswith("cancel_del_"):
        await query.answer("Cancelado")
        await query.edit_message_text("\u274c Cancelado.", reply_markup=kb.main_menu())


def main():
    db.init_db()
    logger.info("Database initialized")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Conversation handlers (menus)
    app.add_handler(get_book_conv_handler(), group=0)
    app.add_handler(get_entry_conv_handler(), group=0)
    app.add_handler(get_study_conv_handler(), group=0)
    app.add_handler(get_study_note_conv_handler(), group=0)
    app.add_handler(get_insight_conv_handler(), group=0)
    app.add_handler(get_fc_conv_handler(), group=0)
    app.add_handler(get_search_conv_handler(), group=0)

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("livros", books_menu))
    app.add_handler(CommandHandler("estudos", studies_menu))
    app.add_handler(CommandHandler("insights", insights_menu))
    app.add_handler(CommandHandler("flashcards", flashcards_menu))
    app.add_handler(CommandHandler("stats", show_stats))

    # Audio/voz
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice_message))

    # Texto livre -> agente IA
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, text_router
    ), group=1)

    # Callback router
    app.add_handler(CallbackQueryHandler(main_callback_router), group=2)

    logger.info("Bot starting... (modo hibrido: menus + agente IA + audio)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
