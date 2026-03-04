"""
bot.py - Ponto de entrada do Telegram Learning Agent Bot.
Versao original com menus inline.
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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN nao definido no .env")


WELCOME_TEXT = (
    "\U0001f9e0 *Learning Agent \u2014 Seu Assistente de Aprendizado*\n\n"
    "Ol\u00e1! Sou seu agente pessoal para organizar leituras, estudos e aprendizados.\n\n"
    "*O que posso fazer:*\n\n"
    "\U0001f4da *Biblioteca* \u2014 Gerencie livros, salve cita\u00e7\u00f5es, resumos e ideias\n"
    "\U0001f393 *Estudos* \u2014 Organize cursos e t\u00f3picos com anota\u00e7\u00f5es e conceitos\n"
    "\U0001f4a1 *Insights* \u2014 Capture aprendizados de podcasts, conversas, artigos\n"
    "\U0001f0cf *Flashcards* \u2014 Revis\u00e3o espa\u00e7ada com IA para fixar conhecimento\n"
    "\U0001f50d *Busca* \u2014 Encontre qualquer coisa que voc\u00ea salvou\n"
    "\U0001f916 *IA* \u2014 Resumos autom\u00e1ticos, conex\u00f5es entre ideias e flashcards\n\n"
    "Escolha uma op\u00e7\u00e3o abaixo para come\u00e7ar:"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_TEXT, reply_markup=kb.main_menu(), parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "\U0001f4d6 *Comandos Dispon\u00edveis*\n\n"
        "/start \u2014 Menu principal\n"
        "/livros \u2014 Biblioteca de livros\n"
        "/estudos \u2014 Caderno de estudos\n"
        "/insights \u2014 Insights e aprendizados\n"
        "/flashcards \u2014 Revisar flashcards\n"
        "/buscar \u2014 Busca global\n"
        "/stats \u2014 Estat\u00edsticas\n"
        "/ajuda \u2014 Esta mensagem\n\n"
        "\U0001f4a1 *Dicas:*\n"
        "\u2022 Use /pular para pular campos opcionais\n"
        "\u2022 Use /cancelar para cancelar qualquer opera\u00e7\u00e3o\n"
        "\u2022 A IA gera flashcards e insights automaticamente"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def main_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Roteia callbacks que nao sao capturados pelos ConversationHandlers."""
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

    # Livros
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

    # Estudos
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

    # Insights
    elif data.startswith("insight_list_"):
        await insight_list(update, context)
    elif data == "insight_ai_connect":
        await insight_ai_connect(update, context)

    # Flashcards
    elif data == "fc_review":
        await fc_review_start(update, context)
    elif data.startswith("fc_show_"):
        await fc_show_answer(update, context)
    elif data.startswith("fc_diff_"):
        await fc_rate_difficulty(update, context)

    # Confirmacoes de exclusao
    elif data.startswith("confirm_del_book_"):
        await book_delete_execute(update, context)
    elif data.startswith("confirm_del_study_"):
        await study_delete_execute(update, context)
    elif data.startswith("cancel_del_"):
        await query.answer("Cancelado")
        await query.edit_message_text("\u274c Exclus\u00e3o cancelada.", reply_markup=kb.main_menu())


def main():
    db.init_db()
    logger.info("Database initialized")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Conversation handlers (devem vir ANTES dos callback genericos)
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

    # Callback router (captura todos os botoes inline)
    app.add_handler(CallbackQueryHandler(main_callback_router), group=1)

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
