"""
handlers/search.py - Busca global e estatisticas.
"""

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
import database as db
import keyboards as kb

SEARCH_QUERY = 40


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🔍 *Busca Global*\n\nDigite o termo de busca:", parse_mode="Markdown")
    else:
        await update.message.reply_text("🔍 Digite o que deseja buscar:")
    return SEARCH_QUERY


async def search_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    term = update.message.text.strip()
    user_id = update.effective_user.id

    results = db.search_all(user_id, term)

    total = sum(len(v) for v in results.values())
    if total == 0:
        await update.message.reply_text(
            f"🔍 Nenhum resultado para *\"{term}\"*",
            reply_markup=kb.back_to_main(), parse_mode="Markdown")
        return ConversationHandler.END

    text_parts = [f"🔍 *Resultados para \"{term}\"* ({total} encontrados):\n"]

    if results["books"]:
        text_parts.append("\n📚 *Livros:*")
        for b in results["books"][:5]:
            text_parts.append(f"  • {b['title']} — {b['author'] or 'N/A'}")

    if results["book_entries"]:
        text_parts.append("\n📝 *Entradas de Livros:*")
        for e in results["book_entries"][:5]:
            preview = e["content"][:80] + "..." if len(e["content"]) > 80 else e["content"]
            text_parts.append(f"  • [{e.get('book_title', '?')}] {preview}")

    if results["studies"]:
        text_parts.append("\n🎓 *Estudos:*")
        for s in results["studies"][:5]:
            text_parts.append(f"  • {s['title']}")

    if results["study_notes"]:
        text_parts.append("\n📝 *Notas de Estudo:*")
        for n in results["study_notes"][:5]:
            preview = n["content"][:80] + "..." if len(n["content"]) > 80 else n["content"]
            text_parts.append(f"  • [{n.get('study_title', '?')}] {preview}")

    if results["insights"]:
        text_parts.append("\n💡 *Insights:*")
        for i in results["insights"][:5]:
            preview = i["content"][:80] + "..." if len(i["content"]) > 80 else i["content"]
            text_parts.append(f"  • {preview}")

    await update.message.reply_text(
        "\n".join(text_parts), reply_markup=kb.back_to_main(), parse_mode="Markdown")
    return ConversationHandler.END


async def search_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Busca cancelada.", reply_markup=kb.main_menu())
    return ConversationHandler.END


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    if query:
        await query.answer()

    s = db.get_stats(user_id)

    text = (
        "📊 *Suas Estatísticas*\n\n"
        f"📚 *Biblioteca*\n"
        f"  Total: {s['total_books']} livros\n"
        f"  📖 Lendo: {s['books_reading']}\n"
        f"  ✅ Finalizados: {s['books_finished']}\n"
        f"  📝 Entradas: {s['total_entries']}\n\n"
        f"🎓 *Estudos*\n"
        f"  Total: {s['total_studies']} estudos\n"
        f"  📝 Notas: {s['total_notes']}\n\n"
        f"💡 *Insights:* {s['total_insights']}\n\n"
        f"🃏 *Flashcards*\n"
        f"  Total: {s['total_flashcards']}\n"
        f"  📬 Pendentes: {s['due_flashcards']}"
    )

    if query:
        await query.edit_message_text(
            text, reply_markup=kb.back_to_main(), parse_mode="Markdown")
    else:
        await update.message.reply_text(
            text, reply_markup=kb.back_to_main(), parse_mode="Markdown")


def get_search_conv_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(search_start, pattern="^menu_search$"),
            CommandHandler("buscar", search_start),
        ],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_execute)],
        },
        fallbacks=[CommandHandler("cancelar", search_cancel)],
        per_message=False,
    )
