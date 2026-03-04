"""
handlers/studies.py - Handlers para gerenciamento de estudos.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
import database as db
import ai_engine as ai
import keyboards as kb

STUDY_TITLE, STUDY_SOURCE, STUDY_CATEGORY, NOTE_CONTENT = range(10, 14)


async def studies_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🎓 *Caderno de Estudos*\n\nEscolha uma opção:",
            reply_markup=kb.studies_menu(), parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "🎓 *Caderno de Estudos*\n\nEscolha uma opção:",
            reply_markup=kb.studies_menu(), parse_mode="Markdown")


async def study_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎓 *Novo Estudo*\n\nDigite o *título*:", parse_mode="Markdown")
    return STUDY_TITLE


async def study_title_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_study"] = {"title": update.message.text.strip()}
    await update.message.reply_text(
        "📍 Qual a *fonte*? (plataforma, professor, etc. ou /pular)", parse_mode="Markdown")
    return STUDY_SOURCE


async def study_source_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_study"]["source"] = "" if text == "/pular" else text
    await update.message.reply_text(
        "📂 Escolha a categoria:", reply_markup=kb.study_category_options())
    return STUDY_CATEGORY


async def study_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.replace("studycat_", "")

    study_data = context.user_data["new_study"]
    study_id = db.add_study(
        user_id=update.effective_user.id,
        title=study_data["title"],
        category=category,
        source=study_data.get("source", "")
    )

    cat_emoji = {"curso": "🎓", "disciplina": "📚", "topico": "🔬", "tutorial": "💻"}.get(category, "📝")
    await query.edit_message_text(
        f"✅ Estudo criado!\n\n{cat_emoji} *{study_data['title']}*\n"
        f"📍 {study_data.get('source') or 'N/A'}",
        reply_markup=kb.study_detail(study_id), parse_mode="Markdown")
    context.user_data.pop("new_study", None)
    return ConversationHandler.END


async def study_add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_study", None)
    await update.message.reply_text("❌ Cancelado.", reply_markup=kb.studies_menu())
    return ConversationHandler.END


async def study_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    status = query.data.replace("study_list_", "")
    user_id = update.effective_user.id

    if status == "all":
        studies = db.get_studies(user_id)
        title = "📋 Todos os Estudos"
    else:
        studies = db.get_studies(user_id, status=status)
        names = {"em_andamento": "🔄 Em Andamento", "concluido": "✅ Concluídos"}
        title = names.get(status, status)

    if not studies:
        await query.edit_message_text(
            f"{title}\n\nNenhum estudo encontrado.", reply_markup=kb.studies_menu())
        return

    await query.edit_message_text(
        f"{title} ({len(studies)}):", reply_markup=kb.study_list_keyboard(studies))


async def study_detail_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    study_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id
    study = db.get_study(study_id, user_id)

    if not study:
        await query.edit_message_text("❌ Estudo não encontrado.", reply_markup=kb.studies_menu())
        return

    notes = db.get_study_notes(study_id, user_id)
    cat_emoji = {"curso": "🎓", "disciplina": "📚", "topico": "🔬", "tutorial": "💻"}.get(study["category"], "📝")
    status_map = {"em_andamento": "🔄 Em Andamento", "concluido": "✅ Concluído", "pausado": "⏸ Pausado"}

    text = (
        f"{cat_emoji} *{study['title']}*\n"
        f"📍 {study['source'] or 'N/A'}\n"
        f"📊 {status_map.get(study['status'], study['status'])}\n\n"
        f"📝 {len(notes)} notas salvas\n"
        f"📅 Criado: {study['created_at'][:10]}"
    )
    await query.edit_message_text(
        text, reply_markup=kb.study_detail(study_id), parse_mode="Markdown")


async def study_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    study_id = int(query.data.split("_")[-1])
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Em Andamento", callback_data=f"sstatus_em_andamento_{study_id}"),
         InlineKeyboardButton("✅ Concluído", callback_data=f"sstatus_concluido_{study_id}")],
        [InlineKeyboardButton("⏸ Pausado", callback_data=f"sstatus_pausado_{study_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"study_detail_{study_id}")],
    ])
    await query.edit_message_text("🔄 Escolha o novo status:", reply_markup=keyboard)


async def study_status_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    status = parts[1]
    study_id = int(parts[2])
    db.update_study_status(study_id, update.effective_user.id, status)
    query.data = f"study_detail_{study_id}"
    await study_detail_view(update, context)


async def study_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    study_id = int(query.data.split("_")[-1])
    study = db.get_study(study_id, update.effective_user.id)
    if study:
        await query.edit_message_text(
            f"🗑 Excluir *{study['title']}*? Todas as notas serão perdidas!",
            reply_markup=kb.confirm_delete("study", study_id), parse_mode="Markdown")


async def study_delete_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    study_id = int(query.data.split("_")[-1])
    db.delete_study(study_id, update.effective_user.id)
    await query.edit_message_text("✅ Estudo excluído.", reply_markup=kb.studies_menu())


async def study_note_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    note_type = parts[2]
    study_id = int(parts[3])

    context.user_data["new_snote"] = {"study_id": study_id, "note_type": note_type}
    type_names = {"anotacao": "📝 Anotação", "conceito": "🧠 Conceito", "duvida": "❓ Dúvida", "resumo": "📄 Resumo"}

    await query.edit_message_text(f"{type_names.get(note_type, note_type)}\n\nDigite o conteúdo:")
    return NOTE_CONTENT


async def study_note_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_data = context.user_data["new_snote"]
    db.add_study_note(
        study_id=note_data["study_id"],
        user_id=update.effective_user.id,
        note_type=note_data["note_type"],
        content=update.message.text.strip()
    )
    await update.message.reply_text(
        "✅ Nota salva!", reply_markup=kb.study_detail(note_data["study_id"]))
    context.user_data.pop("new_snote", None)
    return ConversationHandler.END


async def study_note_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    study_id = context.user_data.get("new_snote", {}).get("study_id")
    context.user_data.pop("new_snote", None)
    if study_id:
        await update.message.reply_text("❌ Cancelado.", reply_markup=kb.study_detail(study_id))
    else:
        await update.message.reply_text("❌ Cancelado.", reply_markup=kb.studies_menu())
    return ConversationHandler.END


async def study_note_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    study_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id
    study = db.get_study(study_id, user_id)
    notes = db.get_study_notes(study_id, user_id)

    if not notes:
        await query.edit_message_text(
            f"🎓 *{study['title']}*\n\nNenhuma nota salva.",
            reply_markup=kb.study_detail(study_id), parse_mode="Markdown")
        return

    type_emoji = {"anotacao": "📝", "conceito": "🧠", "duvida": "❓", "resumo": "📄"}
    text_parts = [f"🎓 *{study['title']}* — Notas ({len(notes)}):\n"]

    for i, n in enumerate(notes[:10], 1):
        emoji = type_emoji.get(n["note_type"], "📝")
        preview = n["content"][:150] + "..." if len(n["content"]) > 150 else n["content"]
        text_parts.append(f"\n{emoji} *{i}.* {preview}")

    await query.edit_message_text(
        "\n".join(text_parts),
        reply_markup=kb.study_detail(study_id), parse_mode="Markdown")


async def study_ai_flashcards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🃏 Gerando...")

    study_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id
    study = db.get_study(study_id, user_id)
    notes = db.get_study_notes(study_id, user_id)

    if not notes:
        await query.edit_message_text(
            "❌ Adicione notas primeiro.", reply_markup=kb.study_detail(study_id))
        return

    await query.edit_message_text("🃏 Gerando flashcards com IA...")
    all_content = "\n\n".join([n["content"] for n in notes])
    cards = ai.generate_flashcards(all_content, num_cards=5)

    if not cards:
        await query.edit_message_text(
            "❌ Falha ao gerar. Tente novamente.", reply_markup=kb.study_detail(study_id))
        return

    for card in cards:
        db.add_flashcard(user_id, card["question"], card["answer"], "study", study_id)

    text = f"✅ *{len(cards)} flashcards criados!*\n\n"
    for i, c in enumerate(cards, 1):
        text += f"🃏 *{i}.* {c['question']}\n"

    await query.edit_message_text(
        text, reply_markup=kb.study_detail(study_id), parse_mode="Markdown")


def get_study_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(study_add_start, pattern="^study_add$")],
        states={
            STUDY_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, study_title_received)],
            STUDY_SOURCE: [
                MessageHandler(filters.Regex("^/pular$"), study_source_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, study_source_received),
            ],
            STUDY_CATEGORY: [CallbackQueryHandler(study_category_selected, pattern=r"^studycat_")],
        },
        fallbacks=[CommandHandler("cancelar", study_add_cancel)],
        per_message=False,
    )


def get_study_note_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(
            study_note_start, pattern=r"^snote_add_(anotacao|conceito|duvida|resumo)_\d+$")],
        states={
            NOTE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, study_note_content)],
        },
        fallbacks=[CommandHandler("cancelar", study_note_cancel)],
        per_message=False,
    )
