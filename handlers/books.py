"""
handlers/books.py - Handlers para gerenciamento de livros.
"""

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
import database as db
import ai_engine as ai
import keyboards as kb

(BOOK_TITLE, BOOK_AUTHOR, BOOK_GENRE, BOOK_STATUS,
 ENTRY_CONTENT, ENTRY_PAGE, ENTRY_CHAPTER) = range(7)


async def books_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "📚 *Biblioteca de Livros*\n\nEscolha uma opção:",
            reply_markup=kb.books_menu(), parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "📚 *Biblioteca de Livros*\n\nEscolha uma opção:",
            reply_markup=kb.books_menu(), parse_mode="Markdown")


async def book_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📚 *Novo Livro*\n\nDigite o *título* do livro:", parse_mode="Markdown")
    return BOOK_TITLE


async def book_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_book"] = {"title": update.message.text.strip()}
    await update.message.reply_text(
        "✍️ Quem é o *autor*? (ou envie /pular)", parse_mode="Markdown")
    return BOOK_AUTHOR


async def book_author_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_book"]["author"] = "" if text == "/pular" else text
    await update.message.reply_text(
        "📂 Qual o *gênero*? (ou envie /pular)\n\nEx: Ficção, Negócios, Filosofia, Técnico...",
        parse_mode="Markdown")
    return BOOK_GENRE


async def book_genre_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_book"]["genre"] = "" if text == "/pular" else text

    book_data = context.user_data["new_book"]
    book_id = db.add_book(
        user_id=update.effective_user.id,
        title=book_data["title"],
        author=book_data.get("author", ""),
        genre=book_data.get("genre", ""),
        status="lendo"
    )

    book = db.get_book(book_id, update.effective_user.id)
    text_msg = (
        f"✅ *Livro adicionado!*\n\n"
        f"📕 *{book['title']}*\n"
        f"✍️ {book['author'] or 'Autor não informado'}\n"
        f"📂 {book['genre'] or 'Gênero não informado'}\n"
        f"📖 Status: Lendo"
    )
    await update.message.reply_text(
        text_msg, reply_markup=kb.book_detail(book_id), parse_mode="Markdown")
    context.user_data.pop("new_book", None)
    return ConversationHandler.END


async def book_add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_book", None)
    await update.message.reply_text("❌ Adição cancelada.", reply_markup=kb.books_menu())
    return ConversationHandler.END


async def book_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    status = data.replace("book_list_", "")
    user_id = update.effective_user.id

    if status == "all":
        books = db.get_books(user_id)
        title = "📋 Todos os Livros"
    else:
        books = db.get_books(user_id, status=status)
        status_names = {"lendo": "📖 Lendo", "finalizado": "✅ Finalizados", "pausado": "⏸ Pausados"}
        title = status_names.get(status, status)

    if not books:
        await query.edit_message_text(
            f"{title}\n\nNenhum livro encontrado.", reply_markup=kb.books_menu())
        return

    await query.edit_message_text(
        f"{title} ({len(books)}):", reply_markup=kb.book_list_keyboard(books))


async def book_detail_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    book_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id
    book = db.get_book(book_id, user_id)

    if not book:
        await query.edit_message_text("❌ Livro não encontrado.", reply_markup=kb.books_menu())
        return

    entries = db.get_book_entries(book_id, user_id)
    citacoes = sum(1 for e in entries if e["entry_type"] == "citacao")
    resumos = sum(1 for e in entries if e["entry_type"] == "resumo")
    ideias = sum(1 for e in entries if e["entry_type"] == "ideia")

    status_map = {
        "lendo": "📖 Lendo", "finalizado": "✅ Finalizado",
        "pausado": "⏸ Pausado", "quero_ler": "📌 Quero Ler"
    }
    stars = "⭐" * book["rating"] if book["rating"] else "Sem avaliação"

    text = (
        f"📕 *{book['title']}*\n"
        f"✍️ {book['author'] or 'N/A'} | 📂 {book['genre'] or 'N/A'}\n"
        f"📊 {status_map.get(book['status'], book['status'])} | {stars}\n\n"
        f"💬 {citacoes} citações | 📝 {resumos} resumos | 💡 {ideias} ideias\n"
        f"📅 Adicionado: {book['created_at'][:10]}"
    )
    await query.edit_message_text(
        text, reply_markup=kb.book_detail(book_id), parse_mode="Markdown")


async def book_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split("_")[-1])
    await query.edit_message_text(
        "🔄 Escolha o novo status:", reply_markup=kb.book_status_options(book_id))


async def book_status_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    status = parts[1]
    book_id = int(parts[2])
    user_id = update.effective_user.id

    db.update_book_status(book_id, user_id, status)
    await query.answer("✅ Status atualizado!")
    query.data = f"book_detail_{book_id}"
    await book_detail_view(update, context)


async def book_rate_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split("_")[-1])
    await query.edit_message_text(
        "⭐ Avalie o livro:", reply_markup=kb.book_rating_options(book_id))


async def book_rate_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    rating = int(parts[1])
    book_id = int(parts[2])

    db.rate_book(book_id, update.effective_user.id, rating)
    await query.answer(f"{'⭐' * rating} Avaliação salva!")
    query.data = f"book_detail_{book_id}"
    await book_detail_view(update, context)


async def book_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split("_")[-1])
    book = db.get_book(book_id, update.effective_user.id)
    if book:
        await query.edit_message_text(
            f"🗑 Tem certeza que deseja excluir *{book['title']}*?\n\n"
            "Todas as entradas serão perdidas!",
            reply_markup=kb.confirm_delete("book", book_id), parse_mode="Markdown")


async def book_delete_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    book_id = int(parts[-1])
    db.delete_book(book_id, update.effective_user.id)
    await query.edit_message_text("✅ Livro excluído.", reply_markup=kb.books_menu())


async def entry_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    entry_type = parts[2]
    book_id = int(parts[3])

    context.user_data["new_entry"] = {"book_id": book_id, "entry_type": entry_type}
    type_names = {"citacao": "💬 Citação", "resumo": "📝 Resumo", "ideia": "💡 Ideia"}
    await query.edit_message_text(
        f"{type_names[entry_type]}\n\nDigite o conteúdo da {entry_type}:")
    return ENTRY_CONTENT


async def entry_content_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_entry"]["content"] = update.message.text.strip()
    await update.message.reply_text("📄 Qual a *página*? (ou /pular)", parse_mode="Markdown")
    return ENTRY_PAGE


async def entry_page_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_entry"]["page"] = "" if text == "/pular" else text
    await update.message.reply_text("📖 Qual o *capítulo*? (ou /pular)", parse_mode="Markdown")
    return ENTRY_CHAPTER


async def entry_chapter_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    entry_data = context.user_data["new_entry"]
    entry_data["chapter"] = "" if text == "/pular" else text

    user_id = update.effective_user.id
    db.add_book_entry(
        book_id=entry_data["book_id"],
        user_id=user_id,
        entry_type=entry_data["entry_type"],
        content=entry_data["content"],
        page=entry_data.get("page", ""),
        chapter=entry_data.get("chapter", "")
    )

    type_emoji = {"citacao": "💬", "resumo": "📝", "ideia": "💡"}.get(entry_data["entry_type"], "📝")
    await update.message.reply_text(
        f"✅ {type_emoji} Salvo com sucesso!",
        reply_markup=kb.book_detail(entry_data["book_id"]))
    context.user_data.pop("new_entry", None)
    return ConversationHandler.END


async def entry_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    book_id = context.user_data.get("new_entry", {}).get("book_id")
    context.user_data.pop("new_entry", None)
    if book_id:
        await update.message.reply_text("❌ Cancelado.", reply_markup=kb.book_detail(book_id))
    else:
        await update.message.reply_text("❌ Cancelado.", reply_markup=kb.books_menu())
    return ConversationHandler.END


async def entry_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = int(query.data.split("_")[-1])
    await query.edit_message_text(
        "📄 Filtrar por tipo:", reply_markup=kb.entry_type_filter(book_id))


async def entry_list_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    entry_type = parts[1] if parts[1] != "all" else None
    book_id = int(parts[2])
    user_id = update.effective_user.id

    entries = db.get_book_entries(book_id, user_id, entry_type)
    book = db.get_book(book_id, user_id)

    if not entries:
        await query.edit_message_text(
            f"📕 *{book['title']}*\n\nNenhuma entrada encontrada.",
            reply_markup=kb.book_detail(book_id), parse_mode="Markdown")
        return

    type_emoji = {"citacao": "💬", "resumo": "📝", "ideia": "💡"}
    text_parts = [f"📕 *{book['title']}* — Entradas ({len(entries)}):\n"]

    for i, e in enumerate(entries[:10], 1):
        emoji = type_emoji.get(e["entry_type"], "📝")
        page_info = f" (p.{e['page']})" if e["page"] else ""
        chapter_info = f" — Cap. {e['chapter']}" if e["chapter"] else ""
        content_preview = e["content"][:150] + "..." if len(e["content"]) > 150 else e["content"]
        text_parts.append(f"\n{emoji} *{i}.* {content_preview}{page_info}{chapter_info}")

    if len(entries) > 10:
        text_parts.append(f"\n\n... e mais {len(entries) - 10} entradas")

    await query.edit_message_text(
        "\n".join(text_parts),
        reply_markup=kb.book_detail(book_id), parse_mode="Markdown")


async def book_ai_insights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🤖 Gerando insights...")

    book_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id
    book = db.get_book(book_id, user_id)
    entries = db.get_book_entries(book_id, user_id)

    if not entries:
        await query.edit_message_text(
            "❌ Adicione citações, resumos ou ideias primeiro para gerar insights.",
            reply_markup=kb.book_detail(book_id))
        return

    await query.edit_message_text("🤖 Analisando suas anotações...")
    result = ai.generate_insights_from_entries(entries, book["title"])

    await query.edit_message_text(
        f"🤖 *Insights — {book['title']}*\n\n{result}",
        reply_markup=kb.book_detail(book_id), parse_mode="Markdown")


async def book_ai_flashcards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🃏 Gerando flashcards...")

    book_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id
    book = db.get_book(book_id, user_id)
    entries = db.get_book_entries(book_id, user_id)

    if not entries:
        await query.edit_message_text(
            "❌ Adicione conteúdo primeiro para gerar flashcards.",
            reply_markup=kb.book_detail(book_id))
        return

    await query.edit_message_text("🃏 Gerando flashcards com IA...")
    all_content = "\n\n".join([e["content"] for e in entries])
    cards = ai.generate_flashcards(all_content, num_cards=5)

    if not cards:
        await query.edit_message_text(
            "❌ Não foi possível gerar flashcards. Tente novamente.",
            reply_markup=kb.book_detail(book_id))
        return

    count = 0
    for card in cards:
        db.add_flashcard(user_id, card["question"], card["answer"], "book", book_id)
        count += 1

    text = f"✅ *{count} flashcards criados!*\n\n"
    for i, card in enumerate(cards, 1):
        text += f"🃏 *{i}.* {card['question']}\n"
    text += "\nUse /flashcards ou o menu para revisar."

    await query.edit_message_text(
        text, reply_markup=kb.book_detail(book_id), parse_mode="Markdown")


def get_book_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(book_add_start, pattern="^book_add$")],
        states={
            BOOK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_title_received)],
            BOOK_AUTHOR: [
                MessageHandler(filters.Regex("^/pular$"), book_author_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_author_received),
            ],
            BOOK_GENRE: [
                MessageHandler(filters.Regex("^/pular$"), book_genre_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, book_genre_received),
            ],
        },
        fallbacks=[CommandHandler("cancelar", book_add_cancel)],
        per_message=False,
    )


def get_entry_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(
            entry_add_start, pattern=r"^entry_add_(citacao|resumo|ideia)_\d+$")],
        states={
            ENTRY_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, entry_content_received)],
            ENTRY_PAGE: [
                MessageHandler(filters.Regex("^/pular$"), entry_page_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, entry_page_received),
            ],
            ENTRY_CHAPTER: [
                MessageHandler(filters.Regex("^/pular$"), entry_chapter_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, entry_chapter_received),
            ],
        },
        fallbacks=[CommandHandler("cancelar", entry_cancel)],
        per_message=False,
    )
