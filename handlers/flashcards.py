"""
handlers/flashcards.py - Revisao espacada com algoritmo SM-2.
"""

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
import database as db
import keyboards as kb

FC_QUESTION, FC_ANSWER = range(30, 32)


async def flashcards_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    due = db.get_due_flashcards(user_id)

    if query:
        await query.answer()
        await query.edit_message_text(
            f"🃏 *Flashcards*\n\n📬 {len(due)} cards pendentes para revisão",
            reply_markup=kb.flashcards_menu(), parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"🃏 *Flashcards*\n\n📬 {len(due)} cards pendentes",
            reply_markup=kb.flashcards_menu(), parse_mode="Markdown")


async def fc_review_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    cards = db.get_due_flashcards(user_id, limit=1)

    if not cards:
        await query.edit_message_text(
            "✅ Nenhum flashcard pendente! Volte mais tarde.",
            reply_markup=kb.flashcards_menu())
        return

    card = cards[0]
    context.user_data["reviewing_card"] = card

    await query.edit_message_text(
        f"🃏 *Flashcard #{card['id']}*\n\n❓ {card['question']}",
        reply_markup=kb.flashcard_answer_options(card["id"]), parse_mode="Markdown")


async def fc_show_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card_id = int(query.data.split("_")[-1])
    card = context.user_data.get("reviewing_card")

    if not card or card["id"] != card_id:
        await query.edit_message_text(
            "❌ Card não encontrado.", reply_markup=kb.flashcards_menu())
        return

    await query.edit_message_text(
        f"🃏 *Flashcard #{card['id']}*\n\n"
        f"❓ {card['question']}\n\n"
        f"✅ *Resposta:* {card['answer']}\n\n"
        "Como foi?",
        reply_markup=kb.flashcard_difficulty(card_id), parse_mode="Markdown")


async def fc_rate_difficulty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    difficulty = parts[2]
    card_id = int(parts[3])

    card = context.user_data.get("reviewing_card")
    if not card or card["id"] != card_id:
        await query.edit_message_text("❌ Erro.", reply_markup=kb.flashcards_menu())
        return

    # Algoritmo SM-2 simplificado
    ef = card.get("ease_factor", 2.5)
    interval = card.get("interval_days", 1)
    reps = card.get("repetitions", 0)

    if difficulty == "hard":
        ef = max(1.3, ef - 0.3)
        interval = 1
        reps = 0
    elif difficulty == "medium":
        ef = max(1.3, ef - 0.1)
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 3
        else:
            interval = int(interval * ef)
        reps += 1
    else:  # easy
        ef = ef + 0.1
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 4
        else:
            interval = int(interval * ef)
        reps += 1

    db.update_flashcard_review(card_id, ef, interval, reps)

    diff_emoji = {"hard": "😰", "medium": "🤔", "easy": "😊"}
    await query.edit_message_text(
        f"{diff_emoji.get(difficulty, '')} Próxima revisão em *{interval} dia(s)*",
        parse_mode="Markdown")

    # Mostra proximo card automaticamente
    user_id = update.effective_user.id
    next_cards = db.get_due_flashcards(user_id, limit=1)

    if next_cards:
        card = next_cards[0]
        context.user_data["reviewing_card"] = card
        await query.message.reply_text(
            f"🃏 *Flashcard #{card['id']}*\n\n❓ {card['question']}",
            reply_markup=kb.flashcard_answer_options(card["id"]), parse_mode="Markdown")
    else:
        await query.message.reply_text(
            "🎉 Revisão completa! Todos os cards foram revisados.",
            reply_markup=kb.flashcards_menu())


async def fc_add_manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🃏 *Novo Flashcard*\n\nDigite a *pergunta*:", parse_mode="Markdown")
    return FC_QUESTION


async def fc_question_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_fc"] = {"question": update.message.text.strip()}
    await update.message.reply_text("✅ Agora digite a *resposta*:", parse_mode="Markdown")
    return FC_ANSWER


async def fc_answer_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fc_data = context.user_data["new_fc"]
    db.add_flashcard(
        user_id=update.effective_user.id,
        question=fc_data["question"],
        answer=update.message.text.strip()
    )
    await update.message.reply_text("✅ Flashcard criado!", reply_markup=kb.flashcards_menu())
    context.user_data.pop("new_fc", None)
    return ConversationHandler.END


async def fc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_fc", None)
    await update.message.reply_text("❌ Cancelado.", reply_markup=kb.flashcards_menu())
    return ConversationHandler.END


def get_fc_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(fc_add_manual_start, pattern="^fc_add_manual$")],
        states={
            FC_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, fc_question_received)],
            FC_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, fc_answer_received)],
        },
        fallbacks=[CommandHandler("cancelar", fc_cancel)],
        per_message=False,
    )
