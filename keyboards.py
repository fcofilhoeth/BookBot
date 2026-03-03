"""
keyboards.py - Teclados inline reutilizaveis.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():
    keyboard = [
        [InlineKeyboardButton("📚 Biblioteca", callback_data="menu_books"),
         InlineKeyboardButton("🎓 Estudos", callback_data="menu_studies")],
        [InlineKeyboardButton("💡 Insights", callback_data="menu_insights"),
         InlineKeyboardButton("🃏 Flashcards", callback_data="menu_flashcards")],
        [InlineKeyboardButton("🔍 Buscar", callback_data="menu_search"),
         InlineKeyboardButton("📊 Estatísticas", callback_data="menu_stats")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_to_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Menu Principal", callback_data="back_main")]
    ])


def books_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Novo Livro", callback_data="book_add")],
        [InlineKeyboardButton("📖 Lendo", callback_data="book_list_lendo"),
         InlineKeyboardButton("✅ Finalizados", callback_data="book_list_finalizado")],
        [InlineKeyboardButton("⏸ Pausados", callback_data="book_list_pausado"),
         InlineKeyboardButton("📋 Todos", callback_data="book_list_all")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def book_detail(book_id):
    keyboard = [
        [InlineKeyboardButton("💬 Citação", callback_data=f"entry_add_citacao_{book_id}"),
         InlineKeyboardButton("📝 Resumo", callback_data=f"entry_add_resumo_{book_id}")],
        [InlineKeyboardButton("💡 Ideia", callback_data=f"entry_add_ideia_{book_id}"),
         InlineKeyboardButton("📄 Ver Entradas", callback_data=f"entry_list_{book_id}")],
        [InlineKeyboardButton("🔄 Status", callback_data=f"book_status_{book_id}"),
         InlineKeyboardButton("⭐ Avaliar", callback_data=f"book_rate_{book_id}")],
        [InlineKeyboardButton("🤖 Gerar Insights IA", callback_data=f"book_ai_insights_{book_id}")],
        [InlineKeyboardButton("🃏 Gerar Flashcards", callback_data=f"book_ai_flashcards_{book_id}")],
        [InlineKeyboardButton("🗑 Excluir Livro", callback_data=f"book_delete_{book_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_books")],
    ]
    return InlineKeyboardMarkup(keyboard)


def book_status_options(book_id):
    keyboard = [
        [InlineKeyboardButton("📖 Lendo", callback_data=f"bstatus_lendo_{book_id}"),
         InlineKeyboardButton("✅ Finalizado", callback_data=f"bstatus_finalizado_{book_id}")],
        [InlineKeyboardButton("⏸ Pausado", callback_data=f"bstatus_pausado_{book_id}"),
         InlineKeyboardButton("📌 Quero Ler", callback_data=f"bstatus_quero_ler_{book_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"book_detail_{book_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def book_rating_options(book_id):
    keyboard = [
        [InlineKeyboardButton(f"{'⭐' * i}", callback_data=f"brate_{i}_{book_id}") for i in range(1, 6)]
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"book_detail_{book_id}")])
    return InlineKeyboardMarkup(keyboard)


def book_list_keyboard(books):
    keyboard = []
    for book in books[:15]:
        status_emoji = {"lendo": "📖", "finalizado": "✅", "pausado": "⏸", "quero_ler": "📌"}.get(book["status"], "📕")
        stars = "⭐" * book.get("rating", 0) if book.get("rating") else ""
        label = f"{status_emoji} {book['title'][:30]} {stars}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"book_detail_{book['id']}")])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="menu_books")])
    return InlineKeyboardMarkup(keyboard)


def entry_type_filter(book_id):
    keyboard = [
        [InlineKeyboardButton("Todas", callback_data=f"entries_all_{book_id}"),
         InlineKeyboardButton("💬 Citações", callback_data=f"entries_citacao_{book_id}")],
        [InlineKeyboardButton("📝 Resumos", callback_data=f"entries_resumo_{book_id}"),
         InlineKeyboardButton("💡 Ideias", callback_data=f"entries_ideia_{book_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data=f"book_detail_{book_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def studies_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Novo Estudo", callback_data="study_add")],
        [InlineKeyboardButton("🔄 Em Andamento", callback_data="study_list_em_andamento"),
         InlineKeyboardButton("✅ Concluídos", callback_data="study_list_concluido")],
        [InlineKeyboardButton("📋 Todos", callback_data="study_list_all")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def study_category_options():
    keyboard = [
        [InlineKeyboardButton("🎓 Curso", callback_data="studycat_curso"),
         InlineKeyboardButton("📚 Disciplina", callback_data="studycat_disciplina")],
        [InlineKeyboardButton("🔬 Tópico", callback_data="studycat_topico"),
         InlineKeyboardButton("💻 Tutorial", callback_data="studycat_tutorial")],
    ]
    return InlineKeyboardMarkup(keyboard)


def study_detail(study_id):
    keyboard = [
        [InlineKeyboardButton("📝 Anotação", callback_data=f"snote_add_anotacao_{study_id}"),
         InlineKeyboardButton("🧠 Conceito", callback_data=f"snote_add_conceito_{study_id}")],
        [InlineKeyboardButton("❓ Dúvida", callback_data=f"snote_add_duvida_{study_id}"),
         InlineKeyboardButton("📄 Resumo", callback_data=f"snote_add_resumo_{study_id}")],
        [InlineKeyboardButton("📋 Ver Notas", callback_data=f"snote_list_{study_id}")],
        [InlineKeyboardButton("🔄 Status", callback_data=f"study_status_{study_id}")],
        [InlineKeyboardButton("🃏 Gerar Flashcards", callback_data=f"study_ai_flashcards_{study_id}")],
        [InlineKeyboardButton("🗑 Excluir", callback_data=f"study_delete_{study_id}")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_studies")],
    ]
    return InlineKeyboardMarkup(keyboard)


def study_list_keyboard(studies):
    keyboard = []
    for s in studies[:15]:
        cat_emoji = {"curso": "🎓", "disciplina": "📚", "topico": "🔬", "tutorial": "💻"}.get(s["category"], "📝")
        status_emoji = {"em_andamento": "🔄", "concluido": "✅", "pausado": "⏸"}.get(s["status"], "")
        label = f"{cat_emoji}{status_emoji} {s['title'][:35]}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"study_detail_{s['id']}")])
    keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data="menu_studies")])
    return InlineKeyboardMarkup(keyboard)


def insights_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Novo Insight", callback_data="insight_add")],
        [InlineKeyboardButton("📋 Ver Todos", callback_data="insight_list_all")],
        [InlineKeyboardButton("🔮 Reflexão", callback_data="insight_list_reflexao"),
         InlineKeyboardButton("🎙 Podcast", callback_data="insight_list_podcast")],
        [InlineKeyboardButton("📰 Artigo", callback_data="insight_list_artigo"),
         InlineKeyboardButton("🗣 Conversa", callback_data="insight_list_conversa")],
        [InlineKeyboardButton("🎬 Vídeo", callback_data="insight_list_video")],
        [InlineKeyboardButton("🤖 Conectar Ideias (IA)", callback_data="insight_ai_connect")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def insight_category_options():
    keyboard = [
        [InlineKeyboardButton("🔮 Reflexão", callback_data="insightcat_reflexao"),
         InlineKeyboardButton("🎙 Podcast", callback_data="insightcat_podcast")],
        [InlineKeyboardButton("📰 Artigo", callback_data="insightcat_artigo"),
         InlineKeyboardButton("🗣 Conversa", callback_data="insightcat_conversa")],
        [InlineKeyboardButton("🎬 Vídeo", callback_data="insightcat_video"),
         InlineKeyboardButton("📝 Geral", callback_data="insightcat_geral")],
    ]
    return InlineKeyboardMarkup(keyboard)


def flashcards_menu():
    keyboard = [
        [InlineKeyboardButton("🔄 Revisar Pendentes", callback_data="fc_review")],
        [InlineKeyboardButton("➕ Criar Manual", callback_data="fc_add_manual")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def flashcard_answer_options(card_id):
    keyboard = [
        [InlineKeyboardButton("👀 Ver Resposta", callback_data=f"fc_show_{card_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def flashcard_difficulty(card_id):
    keyboard = [
        [InlineKeyboardButton("😰 Difícil", callback_data=f"fc_diff_hard_{card_id}"),
         InlineKeyboardButton("🤔 Médio", callback_data=f"fc_diff_medium_{card_id}"),
         InlineKeyboardButton("😊 Fácil", callback_data=f"fc_diff_easy_{card_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_delete(item_type, item_id):
    keyboard = [
        [InlineKeyboardButton("✅ Confirmar", callback_data=f"confirm_del_{item_type}_{item_id}"),
         InlineKeyboardButton("❌ Cancelar", callback_data=f"cancel_del_{item_type}_{item_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)
