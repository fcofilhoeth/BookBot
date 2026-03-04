"""
handlers/agent.py - Agente conversacional que interpreta texto livre e audios.
"""

import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
import ai_engine as ai


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa qualquer mensagem de texto livre com IA."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Monta contexto para a IA
    ctx = _build_context(user_id, context)

    # Interpreta a intencao
    result = ai.interpret_message(text, ctx)
    intent = result.get("intent", "chat")
    params = result.get("params", {})
    response = result.get("response", "")

    # Roteia para a acao correta
    if intent == "add_book":
        await _handle_add_book(update, context, params, response)
    elif intent in ("add_citation", "add_summary", "add_idea"):
        entry_type_map = {"add_citation": "citacao", "add_summary": "resumo", "add_idea": "ideia"}
        await _handle_add_entry(update, context, params, response, entry_type_map[intent])
    elif intent == "add_study":
        await _handle_add_study(update, context, params, response)
    elif intent == "add_study_note":
        await _handle_add_study_note(update, context, params, response)
    elif intent == "add_insight":
        await _handle_add_insight(update, context, params, response)
    elif intent == "list_books":
        await _handle_list_books(update, context, params, response)
    elif intent == "list_studies":
        await _handle_list_studies(update, context, params, response)
    elif intent == "list_insights":
        await _handle_list_insights(update, context, params, response)
    elif intent == "search":
        await _handle_search(update, context, params, response)
    elif intent == "edit_entry":
        await _handle_edit_entry(update, context, params, response)
    elif intent == "delete_entry":
        await _handle_delete_entry(update, context, params, response)
    elif intent == "stats":
        from handlers.search import show_stats
        await show_stats(update, context)
    elif intent == "generate_flashcards":
        await _handle_generate_flashcards(update, context, params, response)
    elif intent == "generate_insights":
        await _handle_generate_insights(update, context, params, response)
    elif intent == "help":
        await _handle_help(update, context)
    else:
        # Conversa geral
        if response:
            await update.message.reply_text(response)
        else:
            general = ai.smart_response(text, ctx)
            await update.message.reply_text(general)


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe audio, transcreve com Whisper e mostra para confirmacao."""
    await update.message.reply_text("🎙️ Transcrevendo seu áudio...")

    voice = update.message.voice or update.message.audio
    if not voice:
        await update.message.reply_text("Nao consegui identificar o audio.")
        return

    # Baixa o arquivo
    file = await context.bot.get_file(voice.file_id)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name
        await file.download_to_drive(tmp_path)

    # Transcreve
    transcription = ai.transcribe_audio(tmp_path)

    # Limpa arquivo temporario
    try:
        os.unlink(tmp_path)
    except:
        pass

    if transcription.startswith("Erro"):
        await update.message.reply_text(f"❌ {transcription}")
        return

    # Salva transcricao para edicao
    context.user_data["pending_transcription"] = transcription

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar e processar", callback_data="audio_confirm"),
         InlineKeyboardButton("✏️ Editar texto", callback_data="audio_edit")],
        [InlineKeyboardButton("❌ Descartar", callback_data="audio_discard")],
    ])

    await update.message.reply_text(
        f"🎙️ *Transcrição:*\n\n_{transcription}_\n\n"
        "O que deseja fazer?",
        reply_markup=keyboard, parse_mode="Markdown"
    )


async def handle_audio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback dos botoes de audio."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "audio_confirm":
        transcription = context.user_data.pop("pending_transcription", "")
        if not transcription:
            await query.edit_message_text("❌ Transcrição expirada. Envie o áudio novamente.")
            return

        await query.edit_message_text(f"🎙️ _{transcription}_\n\n🤖 Processando...", parse_mode="Markdown")

        # Processa como texto normal
        # Criamos um fake update para reusar a logica
        ctx = _build_context(update.effective_user.id, context)
        result = ai.interpret_message(transcription, ctx)
        intent = result.get("intent", "chat")
        params = result.get("params", {})
        response = result.get("response", "")

        # Para simplificar, enviamos a resposta da IA e executamos a acao
        await _execute_intent_from_callback(query, context, intent, params, response, transcription)

    elif data == "audio_edit":
        context.user_data["waiting_audio_edit"] = True
        transcription = context.user_data.get("pending_transcription", "")
        await query.edit_message_text(
            f"✏️ *Texto atual:*\n_{transcription}_\n\n"
            "Envie o texto corrigido:",
            parse_mode="Markdown"
        )

    elif data == "audio_discard":
        context.user_data.pop("pending_transcription", None)
        await query.edit_message_text("❌ Transcrição descartada.")


async def handle_audio_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe texto editado do audio."""
    if not context.user_data.get("waiting_audio_edit"):
        return False

    context.user_data.pop("waiting_audio_edit", None)
    new_text = update.message.text.strip()
    context.user_data["pending_transcription"] = new_text

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar e processar", callback_data="audio_confirm"),
         InlineKeyboardButton("✏️ Editar novamente", callback_data="audio_edit")],
        [InlineKeyboardButton("❌ Descartar", callback_data="audio_discard")],
    ])

    await update.message.reply_text(
        f"✏️ *Texto atualizado:*\n\n_{new_text}_\n\nConfirmar?",
        reply_markup=keyboard, parse_mode="Markdown"
    )
    return True


# --- HANDLERS DE EDICAO/EXCLUSAO ---

async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callbacks de edicao e exclusao de entradas."""
    query = update.callback_query
    await query.answer()
    data = query.data

    user_id = update.effective_user.id

    if data.startswith("edit_bentry_"):
        entry_id = int(data.split("_")[-1])
        context.user_data["editing_entry"] = {"type": "book_entry", "id": entry_id}
        await query.edit_message_text(
            "✏️ Envie o novo texto para esta entrada:"
        )

    elif data.startswith("del_bentry_"):
        entry_id = int(data.split("_")[-1])
        db.delete_book_entry(entry_id, user_id)
        await query.edit_message_text("✅ Entrada excluída com sucesso!")

    elif data.startswith("del_snote_"):
        note_id = int(data.split("_")[-1])
        db.delete_study_note(note_id, user_id)
        await query.edit_message_text("✅ Nota excluída com sucesso!")

    elif data.startswith("del_insight_"):
        insight_id = int(data.split("_")[-1])
        db.delete_insight(insight_id, user_id)
        await query.edit_message_text("✅ Insight excluído com sucesso!")

    elif data.startswith("del_book_"):
        book_id = int(data.split("_")[-1])
        db.delete_book(book_id, user_id)
        await query.edit_message_text("✅ Livro excluído com sucesso!")

    elif data.startswith("del_study_"):
        study_id = int(data.split("_")[-1])
        db.delete_study(study_id, user_id)
        await query.edit_message_text("✅ Estudo excluído com sucesso!")


async def handle_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe novo texto para entrada sendo editada."""
    editing = context.user_data.get("editing_entry")
    if not editing:
        return False

    user_id = update.effective_user.id
    new_text = update.message.text.strip()

    if editing["type"] == "book_entry":
        from database import get_db
        with get_db() as conn:
            conn.execute(
                "UPDATE book_entries SET content=? WHERE id=? AND user_id=?",
                (new_text, editing["id"], user_id)
            )
        await update.message.reply_text(f"✅ Entrada atualizada!\n\n📝 _{new_text}_", parse_mode="Markdown")

    context.user_data.pop("editing_entry", None)
    return True


# --- FUNCOES INTERNAS ---

def _build_context(user_id, context):
    """Constroi contexto do usuario para a IA."""
    parts = []

    # Livro ativo
    active_book = context.user_data.get("active_book")
    if active_book:
        parts.append(f"Livro ativo: {active_book.get('title', '?')} (ID:{active_book.get('id', '?')})")

    # Estudo ativo
    active_study = context.user_data.get("active_study")
    if active_study:
        parts.append(f"Estudo ativo: {active_study.get('title', '?')} (ID:{active_study.get('id', '?')})")

    # Livros recentes
    books = db.get_books(user_id)
    if books:
        book_list = ", ".join([f"{b['title']} (ID:{b['id']})" for b in books[:5]])
        parts.append(f"Livros do usuario: {book_list}")

    # Estudos recentes
    studies = db.get_studies(user_id)
    if studies:
        study_list = ", ".join([f"{s['title']} (ID:{s['id']})" for s in studies[:5]])
        parts.append(f"Estudos do usuario: {study_list}")

    return "\n".join(parts)


async def _handle_add_book(update, context, params, response):
    user_id = update.effective_user.id
    title = params.get("title", "").strip()

    if not title:
        await update.message.reply_text(
            response or "📚 Qual o título do livro que quer adicionar?"
        )
        return

    author = params.get("author", "")
    genre = params.get("genre", "")
    book_id = db.add_book(user_id, title, author, genre)
    book = db.get_book(book_id, user_id)
    context.user_data["active_book"] = book

    text = (
        f"✅ *Livro adicionado!*\n\n"
        f"📕 *{title}*\n"
        f"✍️ {author or 'N/A'} | 📂 {genre or 'N/A'}\n"
        f"📖 Status: Lendo\n\n"
        f"_Este livro está ativo. Envie citações, resumos ou ideias e vou salvar nele automaticamente!_"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def _handle_add_entry(update, context, params, response, entry_type):
    user_id = update.effective_user.id
    content = params.get("content", "").strip()
    book_hint = params.get("book_hint", "")

    if not content:
        await update.message.reply_text(response or "📝 Qual o conteúdo que quer salvar?")
        return

    # Tenta encontrar o livro
    book = _find_book(user_id, book_hint, context)

    if not book:
        books = db.get_books(user_id)
        if not books:
            await update.message.reply_text(
                "📚 Você ainda não tem livros cadastrados. Adicione um primeiro!\n"
                "Exemplo: _\"Adicionar o livro Sapiens do Yuval Harari\"_",
                parse_mode="Markdown"
            )
            return
        # Mostra lista para escolher
        keyboard = []
        for b in books[:8]:
            keyboard.append([InlineKeyboardButton(
                f"📕 {b['title'][:40]}",
                callback_data=f"save_entry_{entry_type}_{b['id']}"
            )])
        context.user_data["pending_entry"] = {"type": entry_type, "content": content}
        await update.message.reply_text(
            f"📝 Em qual livro salvar esta {_type_name(entry_type)}?\n\n"
            f"_{content[:100]}{'...' if len(content) > 100 else ''}_",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        return

    entry_id = db.add_book_entry(book["id"], user_id, entry_type, content)
    emoji = {"citacao": "💬", "resumo": "📝", "ideia": "💡"}.get(entry_type, "📝")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Editar", callback_data=f"edit_bentry_{entry_id}"),
         InlineKeyboardButton("🗑 Excluir", callback_data=f"del_bentry_{entry_id}")]
    ])

    await update.message.reply_text(
        f"{emoji} *{_type_name(entry_type)} salva!*\n\n"
        f"📕 {book['title']}\n"
        f"_{content[:200]}{'...' if len(content) > 200 else ''}_",
        reply_markup=keyboard, parse_mode="Markdown"
    )


async def _handle_add_study(update, context, params, response):
    user_id = update.effective_user.id
    title = params.get("title", "").strip()

    if not title:
        await update.message.reply_text(response or "🎓 Qual o nome do estudo/curso?")
        return

    category = params.get("category", "geral")
    source = params.get("source", "")
    study_id = db.add_study(user_id, title, category, source)
    study = db.get_study(study_id, user_id)
    context.user_data["active_study"] = study

    cat_emoji = {"curso": "🎓", "disciplina": "📚", "topico": "🔬", "tutorial": "💻"}.get(category, "📝")
    await update.message.reply_text(
        f"✅ *Estudo criado!*\n\n"
        f"{cat_emoji} *{title}*\n"
        f"📍 {source or 'N/A'}\n\n"
        f"_Este estudo está ativo. Envie anotações e vou salvar nele!_",
        parse_mode="Markdown"
    )


async def _handle_add_study_note(update, context, params, response):
    user_id = update.effective_user.id
    content = params.get("content", "").strip()
    note_type = params.get("note_type", "anotacao")

    if not content:
        await update.message.reply_text(response or "📝 Qual o conteúdo da nota?")
        return

    study = _find_study(user_id, params.get("study_hint", ""), context)

    if not study:
        studies = db.get_studies(user_id)
        if not studies:
            await update.message.reply_text("🎓 Você não tem estudos cadastrados. Crie um primeiro!")
            return
        keyboard = []
        for s in studies[:8]:
            keyboard.append([InlineKeyboardButton(
                f"🎓 {s['title'][:40]}",
                callback_data=f"save_snote_{note_type}_{s['id']}"
            )])
        context.user_data["pending_snote"] = {"type": note_type, "content": content}
        await update.message.reply_text(
            "📝 Em qual estudo salvar esta nota?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    note_id = db.add_study_note(study["id"], user_id, note_type, content)
    await update.message.reply_text(
        f"✅ *Nota salva!*\n\n🎓 {study['title']}\n_{content[:200]}_",
        parse_mode="Markdown"
    )


async def _handle_add_insight(update, context, params, response):
    user_id = update.effective_user.id
    content = params.get("content", "").strip()

    if not content:
        await update.message.reply_text(response or "💡 Qual o insight/aprendizado?")
        return

    source = params.get("source", "")
    category = params.get("category", "geral")
    insight_id = db.add_insight(user_id, content, source, category)

    cat_emoji = {"reflexao": "🔮", "podcast": "🎙", "artigo": "📰",
                 "conversa": "🗣", "video": "🎬", "geral": "📝"}.get(category, "📝")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Excluir", callback_data=f"del_insight_{insight_id}")]
    ])

    await update.message.reply_text(
        f"{cat_emoji} *Insight salvo!*\n\n_{content[:300]}_",
        reply_markup=keyboard, parse_mode="Markdown"
    )


async def _handle_list_books(update, context, params, response):
    user_id = update.effective_user.id
    status = params.get("status", "all")
    books = db.get_books(user_id, status=None if status == "all" else status)

    if not books:
        await update.message.reply_text("📚 Nenhum livro encontrado.")
        return

    text_parts = [f"📚 *Seus Livros* ({len(books)}):\n"]
    status_emoji = {"lendo": "📖", "finalizado": "✅", "pausado": "⏸", "quero_ler": "📌"}

    keyboard = []
    for b in books[:10]:
        emoji = status_emoji.get(b["status"], "📕")
        stars = "⭐" * b.get("rating", 0) if b.get("rating") else ""
        entries = db.get_book_entries(b["id"], user_id)
        text_parts.append(f"\n{emoji} *{b['title']}* {stars}\n   ✍️ {b['author'] or 'N/A'} | 📝 {len(entries)} entradas")
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {b['title'][:35]}",
            callback_data=f"book_detail_{b['id']}"
        )])

    keyboard.append([InlineKeyboardButton("⬅️ Menu", callback_data="back_main")])
    await update.message.reply_text(
        "\n".join(text_parts),
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def _handle_list_studies(update, context, params, response):
    user_id = update.effective_user.id
    studies = db.get_studies(user_id)

    if not studies:
        await update.message.reply_text("🎓 Nenhum estudo encontrado.")
        return

    text_parts = [f"🎓 *Seus Estudos* ({len(studies)}):\n"]
    for s in studies[:10]:
        cat_emoji = {"curso": "🎓", "disciplina": "📚", "topico": "🔬", "tutorial": "💻"}.get(s["category"], "📝")
        notes = db.get_study_notes(s["id"], user_id)
        text_parts.append(f"\n{cat_emoji} *{s['title']}*\n   📍 {s['source'] or 'N/A'} | 📝 {len(notes)} notas")

    await update.message.reply_text("\n".join(text_parts), parse_mode="Markdown")


async def _handle_list_insights(update, context, params, response):
    user_id = update.effective_user.id
    insights = db.get_insights(user_id, limit=10)

    if not insights:
        await update.message.reply_text("💡 Nenhum insight encontrado.")
        return

    cat_emoji = {"reflexao": "🔮", "podcast": "🎙", "artigo": "📰",
                 "conversa": "🗣", "video": "🎬", "geral": "📝"}
    text_parts = [f"💡 *Seus Insights* ({len(insights)}):\n"]
    for ins in insights:
        emoji = cat_emoji.get(ins["category"], "📝")
        preview = ins["content"][:120] + "..." if len(ins["content"]) > 120 else ins["content"]
        text_parts.append(f"\n{emoji} _{preview}_")

    await update.message.reply_text("\n".join(text_parts), parse_mode="Markdown")


async def _handle_search(update, context, params, response):
    user_id = update.effective_user.id
    query = params.get("query", "").strip()

    if not query:
        await update.message.reply_text("🔍 O que deseja buscar?")
        return

    results = db.search_all(user_id, query)
    total = sum(len(v) for v in results.values())

    if total == 0:
        await update.message.reply_text(f"🔍 Nenhum resultado para *\"{query}\"*", parse_mode="Markdown")
        return

    text_parts = [f"🔍 *Resultados para \"{query}\"* ({total}):\n"]

    if results["books"]:
        for b in results["books"][:3]:
            text_parts.append(f"\n📕 *{b['title']}* — {b['author'] or 'N/A'}")

    if results["book_entries"]:
        for e in results["book_entries"][:3]:
            preview = e["content"][:100] + "..." if len(e["content"]) > 100 else e["content"]
            text_parts.append(f"\n📝 [{e.get('book_title', '?')}] _{preview}_")

    if results["study_notes"]:
        for n in results["study_notes"][:3]:
            preview = n["content"][:100] + "..." if len(n["content"]) > 100 else n["content"]
            text_parts.append(f"\n🎓 [{n.get('study_title', '?')}] _{preview}_")

    if results["insights"]:
        for i in results["insights"][:3]:
            preview = i["content"][:100] + "..." if len(i["content"]) > 100 else i["content"]
            text_parts.append(f"\n💡 _{preview}_")

    await update.message.reply_text("\n".join(text_parts), parse_mode="Markdown")


async def _handle_edit_entry(update, context, params, response):
    user_id = update.effective_user.id
    hint = params.get("entry_hint", "")

    # Busca entradas recentes
    books = db.get_books(user_id)
    recent_entries = []
    for book in books[:5]:
        entries = db.get_book_entries(book["id"], user_id)
        for e in entries[:5]:
            e["book_title"] = book["title"]
            recent_entries.append(e)

    if not recent_entries:
        await update.message.reply_text("📝 Nenhuma entrada encontrada para editar.")
        return

    # Se tem hint, filtra
    if hint:
        filtered = [e for e in recent_entries if hint.lower() in e["content"].lower()]
        if filtered:
            recent_entries = filtered

    keyboard = []
    text_parts = ["✏️ *Qual entrada quer editar?*\n"]
    for e in recent_entries[:6]:
        emoji = {"citacao": "💬", "resumo": "📝", "ideia": "💡"}.get(e["entry_type"], "📝")
        preview = e["content"][:60] + "..." if len(e["content"]) > 60 else e["content"]
        text_parts.append(f"\n{emoji} [{e.get('book_title', '')}] _{preview}_")
        keyboard.append([
            InlineKeyboardButton(f"✏️ {preview[:30]}", callback_data=f"edit_bentry_{e['id']}"),
            InlineKeyboardButton("🗑", callback_data=f"del_bentry_{e['id']}")
        ])

    await update.message.reply_text(
        "\n".join(text_parts),
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def _handle_delete_entry(update, context, params, response):
    # Redireciona para edicao que mostra botoes de exclusao tambem
    await _handle_edit_entry(update, context, params, response)


async def _handle_generate_flashcards(update, context, params, response):
    user_id = update.effective_user.id
    source_hint = params.get("source_hint", "")

    book = _find_book(user_id, source_hint, context)
    if not book:
        await update.message.reply_text(response or "🃏 De qual livro/estudo quer gerar flashcards?")
        return

    entries = db.get_book_entries(book["id"], user_id)
    if not entries:
        await update.message.reply_text(f"❌ O livro *{book['title']}* não tem entradas ainda.", parse_mode="Markdown")
        return

    await update.message.reply_text("🃏 Gerando flashcards com IA...")
    all_content = "\n\n".join([e["content"] for e in entries])
    cards = ai.generate_flashcards(all_content, num_cards=5)

    if not cards:
        await update.message.reply_text("❌ Não foi possível gerar flashcards.")
        return

    for card in cards:
        db.add_flashcard(user_id, card["question"], card["answer"], "book", book["id"])

    text = f"✅ *{len(cards)} flashcards criados!*\n\n"
    for i, c in enumerate(cards, 1):
        text += f"🃏 *{i}.* {c['question']}\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def _handle_generate_insights(update, context, params, response):
    user_id = update.effective_user.id
    source_hint = params.get("source_hint", "")

    book = _find_book(user_id, source_hint, context)
    if not book:
        await update.message.reply_text(response or "🤖 De qual livro quer gerar insights?")
        return

    entries = db.get_book_entries(book["id"], user_id)
    if not entries:
        await update.message.reply_text(f"❌ O livro *{book['title']}* não tem entradas.", parse_mode="Markdown")
        return

    await update.message.reply_text("🤖 Analisando suas anotações...")
    result = ai.generate_insights_from_entries(entries, book["title"])
    await update.message.reply_text(f"🤖 *Insights — {book['title']}*\n\n{result}", parse_mode="Markdown")


async def _handle_help(update, context):
    text = (
        "🧠 *Learning Agent — O que posso fazer:*\n\n"
        "Você pode conversar comigo naturalmente! Exemplos:\n\n"
        "📚 *Livros:*\n"
        "_\"Adicionar o livro Sapiens do Yuval Harari\"_\n"
        "_\"Salvar citação: O homem é um animal que...\"_\n"
        "_\"Quero salvar um resumo do capítulo 3\"_\n"
        "_\"Me mostra meus livros\"_\n\n"
        "🎓 *Estudos:*\n"
        "_\"Começar estudo de Python na Udemy\"_\n"
        "_\"Anotar: decorators são funções que...\"_\n\n"
        "💡 *Insights:*\n"
        "_\"Aprendi no podcast que...\"_\n"
        "_\"Insight: produtividade não é sobre fazer mais\"_\n\n"
        "✏️ *Editar/Excluir:*\n"
        "_\"Editar minha última citação\"_\n"
        "_\"Excluir a entrada sobre...\"_\n\n"
        "🎙️ *Áudio:* Envie um áudio e eu transcrevo!\n\n"
        "🃏 _\"Gerar flashcards do livro Sapiens\"_\n"
        "🔍 _\"Buscar sobre produtividade\"_\n"
        "📊 _\"Minhas estatísticas\"_\n\n"
        "Ou use os menus com /start"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_save_entry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para salvar entrada em livro especifico."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("save_entry_"):
        parts = data.split("_")
        entry_type = parts[2]
        book_id = int(parts[3])
        pending = context.user_data.pop("pending_entry", None)

        if not pending:
            await query.edit_message_text("❌ Dados expirados. Tente novamente.")
            return

        entry_id = db.add_book_entry(book_id, user_id, entry_type, pending["content"])
        book = db.get_book(book_id, user_id)
        emoji = {"citacao": "💬", "resumo": "📝", "ideia": "💡"}.get(entry_type, "📝")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Editar", callback_data=f"edit_bentry_{entry_id}"),
             InlineKeyboardButton("🗑 Excluir", callback_data=f"del_bentry_{entry_id}")]
        ])

        context.user_data["active_book"] = book
        await query.edit_message_text(
            f"{emoji} *Salvo!*\n\n📕 {book['title']}\n_{pending['content'][:200]}_",
            reply_markup=keyboard, parse_mode="Markdown"
        )

    elif data.startswith("save_snote_"):
        parts = data.split("_")
        note_type = parts[2]
        study_id = int(parts[3])
        pending = context.user_data.pop("pending_snote", None)

        if not pending:
            await query.edit_message_text("❌ Dados expirados.")
            return

        db.add_study_note(study_id, user_id, note_type, pending["content"])
        study = db.get_study(study_id, user_id)
        context.user_data["active_study"] = study
        await query.edit_message_text(
            f"✅ *Nota salva!*\n\n🎓 {study['title']}\n_{pending['content'][:200]}_",
            parse_mode="Markdown"
        )


async def _execute_intent_from_callback(query, context, intent, params, response, transcription):
    """Executa intencao a partir de callback (audio confirmado)."""
    user_id = query.from_user.id

    if intent == "add_book":
        title = params.get("title", transcription[:50])
        author = params.get("author", "")
        genre = params.get("genre", "")
        book_id = db.add_book(user_id, title, author, genre)
        book = db.get_book(book_id, user_id)
        context.user_data["active_book"] = book
        await query.edit_message_text(
            f"✅ *Livro adicionado!*\n📕 *{title}*\n✍️ {author or 'N/A'}",
            parse_mode="Markdown"
        )

    elif intent in ("add_citation", "add_summary", "add_idea"):
        entry_type = {"add_citation": "citacao", "add_summary": "resumo", "add_idea": "ideia"}[intent]
        content = params.get("content", transcription)
        book = context.user_data.get("active_book")
        if book:
            entry_id = db.add_book_entry(book["id"], user_id, entry_type, content)
            emoji = {"citacao": "💬", "resumo": "📝", "ideia": "💡"}.get(entry_type, "📝")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Editar", callback_data=f"edit_bentry_{entry_id}"),
                 InlineKeyboardButton("🗑 Excluir", callback_data=f"del_bentry_{entry_id}")]
            ])
            await query.edit_message_text(
                f"{emoji} *Salvo em {book['title']}!*\n\n_{content[:200]}_",
                reply_markup=keyboard, parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"📝 Conteúdo capturado, mas nenhum livro ativo.\n\n_{content[:200]}_\n\n"
                "Use /livros ou diga qual livro para salvar.",
                parse_mode="Markdown"
            )

    elif intent == "add_insight":
        content = params.get("content", transcription)
        source = params.get("source", "audio")
        category = params.get("category", "geral")
        db.add_insight(user_id, content, source, category)
        await query.edit_message_text(f"💡 *Insight salvo!*\n\n_{content[:300]}_", parse_mode="Markdown")

    else:
        # Resposta generica
        if response:
            await query.edit_message_text(f"🎙️ _{transcription}_\n\n🤖 {response}", parse_mode="Markdown")
        else:
            await query.edit_message_text(f"🎙️ _{transcription}_\n\n✅ Recebido!", parse_mode="Markdown")


# --- HELPERS ---

def _find_book(user_id, hint, context):
    """Tenta encontrar livro por hint ou livro ativo."""
    if context.user_data.get("active_book"):
        return context.user_data["active_book"]

    if hint:
        books = db.get_books(user_id)
        hint_lower = hint.lower()
        for b in books:
            if hint_lower in b["title"].lower():
                context.user_data["active_book"] = b
                return b
    return None


def _find_study(user_id, hint, context):
    """Tenta encontrar estudo por hint ou estudo ativo."""
    if context.user_data.get("active_study"):
        return context.user_data["active_study"]

    if hint:
        studies = db.get_studies(user_id)
        hint_lower = hint.lower()
        for s in studies:
            if hint_lower in s["title"].lower():
                context.user_data["active_study"] = s
                return s
    return None


def _type_name(entry_type):
    return {"citacao": "Citação", "resumo": "Resumo", "ideia": "Ideia"}.get(entry_type, entry_type)
