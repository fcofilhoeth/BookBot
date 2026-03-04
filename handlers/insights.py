"""
handlers/insights.py - Handlers para insights e aprendizados soltos.
"""

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)
import database as db
import ai_engine as ai
import keyboards as kb

INSIGHT_CONTENT, INSIGHT_SOURCE, INSIGHT_CATEGORY = range(20, 23)


async def insights_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "💡 *Insights & Aprendizados*\n\nEscolha uma opção:",
            reply_markup=kb.insights_menu(), parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "💡 *Insights & Aprendizados*",
            reply_markup=kb.insights_menu(), parse_mode="Markdown")


async def insight_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💡 *Novo Insight*\n\nDigite o que aprendeu:", parse_mode="Markdown")
    return INSIGHT_CONTENT


async def insight_content_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_insight"] = {"content": update.message.text.strip()}
    await update.message.reply_text(
        "📍 Qual a *fonte*? (podcast, livro, conversa... ou /pular)", parse_mode="Markdown")
    return INSIGHT_SOURCE


async def insight_source_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["new_insight"]["source"] = "" if text == "/pular" else text
    await update.message.reply_text(
        "📂 Escolha a categoria:", reply_markup=kb.insight_category_options())
    return INSIGHT_CATEGORY


async def insight_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.replace("insightcat_", "")

    data = context.user_data["new_insight"]
    db.add_insight(
        user_id=update.effective_user.id,
        content=data["content"],
        source=data.get("source", ""),
        category=category
    )

    cat_emoji = {
        "reflexao": "🔮", "podcast": "🎙", "artigo": "📰",
        "conversa": "🗣", "video": "🎬", "geral": "📝"
    }.get(category, "📝")

    await query.edit_message_text(
        f"✅ Insight salvo!\n\n{cat_emoji} {data['content'][:200]}",
        reply_markup=kb.insights_menu(), parse_mode="Markdown")
    context.user_data.pop("new_insight", None)
    return ConversationHandler.END


async def insight_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_insight", None)
    await update.message.reply_text("❌ Cancelado.", reply_markup=kb.insights_menu())
    return ConversationHandler.END


async def insight_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.replace("insight_list_", "")
    user_id = update.effective_user.id

    if category == "all":
        insights = db.get_insights(user_id)
        title = "📋 Todos os Insights"
    else:
        insights = db.get_insights(user_id, category=category)
        names = {
            "reflexao": "🔮 Reflexões", "podcast": "🎙 Podcasts",
            "artigo": "📰 Artigos", "conversa": "🗣 Conversas", "video": "🎬 Vídeos"
        }
        title = names.get(category, category)

    if not insights:
        await query.edit_message_text(
            f"{title}\n\nNenhum insight encontrado.", reply_markup=kb.insights_menu())
        return

    cat_emoji = {
        "reflexao": "🔮", "podcast": "🎙", "artigo": "📰",
        "conversa": "🗣", "video": "🎬", "geral": "📝"
    }

    text_parts = [f"{title} ({len(insights)}):\n"]
    for i, ins in enumerate(insights[:10], 1):
        emoji = cat_emoji.get(ins["category"], "📝")
        preview = ins["content"][:120] + "..." if len(ins["content"]) > 120 else ins["content"]
        source = f" — _{ins['source']}_" if ins["source"] else ""
        text_parts.append(f"\n{emoji} *{i}.* {preview}{source}")

    if len(insights) > 10:
        text_parts.append(f"\n\n... e mais {len(insights) - 10}")

    await query.edit_message_text(
        "\n".join(text_parts), reply_markup=kb.insights_menu(), parse_mode="Markdown")


async def insight_ai_connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🤖 Analisando...")

    user_id = update.effective_user.id
    insights = db.get_insights(user_id, limit=20)

    if len(insights) < 3:
        await query.edit_message_text(
            "❌ Salve pelo menos 3 insights para a IA encontrar conexões.",
            reply_markup=kb.insights_menu())
        return

    await query.edit_message_text("🤖 Analisando seus insights e buscando conexões...")

    entries = [{"content": i["content"], "source": i.get("source", i["category"])} for i in insights]
    result = ai.suggest_connections(entries)

    await query.edit_message_text(
        f"🤖 *Conexões Encontradas*\n\n{result}",
        reply_markup=kb.insights_menu(), parse_mode="Markdown")


def get_insight_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(insight_add_start, pattern="^insight_add$")],
        states={
            INSIGHT_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, insight_content_received)],
            INSIGHT_SOURCE: [
                MessageHandler(filters.Regex("^/pular$"), insight_source_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, insight_source_received),
            ],
            INSIGHT_CATEGORY: [CallbackQueryHandler(insight_category_selected, pattern=r"^insightcat_")],
        },
        fallbacks=[CommandHandler("cancelar", insight_cancel)],
        per_message=False,
    )
