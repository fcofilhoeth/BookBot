"""
ai_engine.py - Motor de IA conversacional + transcricao de audio.
"""

import os
import json
import tempfile
from openai import OpenAI

client = None
MODEL = "gpt-4o-mini"


def get_client():
    global client
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client


def _chat(system_prompt, user_prompt, max_tokens=1500):
    try:
        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro na IA: {str(e)}"


def _chat_json(system_prompt, user_prompt, max_tokens=1500):
    """Chamada a IA que retorna JSON parseado."""
    try:
        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}


# --- TRANSCRICAO DE AUDIO ---

def transcribe_audio(file_path):
    """Transcreve audio usando Whisper."""
    try:
        with open(file_path, "rb") as audio_file:
            transcript = get_client().audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="pt"
            )
        return transcript.text.strip()
    except Exception as e:
        return f"Erro na transcricao: {str(e)}"


# --- INTERPRETACAO DE INTENCAO ---

def interpret_message(user_message, context=""):
    """Interpreta a mensagem do usuario e identifica a intencao."""
    system = """Voce e um assistente de aprendizado pessoal. Analise a mensagem do usuario e identifique a intencao.

Retorne APENAS um JSON com:
{
    "intent": "uma das opcoes abaixo",
    "params": { parametros relevantes },
    "response": "resposta amigavel para o usuario"
}

Intencoes possiveis:
- "add_book": usuario quer adicionar livro. params: {"title": "", "author": "", "genre": ""}
- "add_citation": usuario quer salvar citacao/trecho de livro. params: {"content": "", "book_hint": ""}
- "add_summary": usuario quer salvar resumo. params: {"content": "", "book_hint": ""}
- "add_idea": usuario quer salvar ideia sobre livro. params: {"content": "", "book_hint": ""}
- "add_study": usuario quer registrar estudo/curso. params: {"title": "", "category": "", "source": ""}
- "add_study_note": usuario quer salvar nota de estudo. params: {"content": "", "study_hint": "", "note_type": "anotacao|conceito|duvida|resumo"}
- "add_insight": usuario quer salvar insight/aprendizado. params: {"content": "", "source": "", "category": "reflexao|podcast|artigo|conversa|video|geral"}
- "list_books": quer ver livros. params: {"status": "all|lendo|finalizado|pausado"}
- "list_studies": quer ver estudos. params: {}
- "list_insights": quer ver insights. params: {}
- "search": quer buscar algo. params: {"query": ""}
- "edit_entry": quer editar uma entrada. params: {"entry_hint": ""}
- "delete_entry": quer excluir uma entrada. params: {"entry_hint": ""}
- "stats": quer ver estatisticas. params: {}
- "generate_flashcards": quer gerar flashcards. params: {"source_hint": ""}
- "generate_insights": quer insights da IA sobre conteudo. params: {"source_hint": ""}
- "help": precisa de ajuda. params: {}
- "chat": conversa geral ou nao se encaixa nas outras. params: {}

Se a mensagem for ambigua, use "chat" e faca uma pergunta para esclarecer na response.
Extraia o maximo de informacao possivel dos parametros.
Responda sempre em portugues brasileiro."""

    prompt = f"Mensagem do usuario: {user_message}"
    if context:
        prompt += f"\n\nContexto atual: {context}"

    result = _chat_json(system, prompt)
    if "error" in result:
        return {"intent": "chat", "params": {}, "response": "Desculpe, tive um problema. Pode repetir?"}
    return result


# --- FUNCOES DE IA ---

def summarize_text(text, context=""):
    system = (
        "Voce e um assistente de estudos. Crie resumos claros e concisos "
        "em portugues brasileiro. Destaque os pontos-chave."
    )
    prompt = f"Contexto: {context}\n\nTexto:\n{text}" if context else f"Resuma:\n\n{text}"
    return _chat(system, prompt)


def generate_flashcards(text, num_cards=5):
    system = (
        "Voce e um especialista em aprendizado. "
        "Gere flashcards no formato JSON para revisao espacada. "
        "Responda APENAS com um JSON: {\"cards\": [{\"question\": \"...\", \"answer\": \"...\"}]} "
        "As perguntas devem testar compreensao profunda."
    )
    prompt = f"Gere {num_cards} flashcards a partir deste conteudo:\n\n{text}"
    result = _chat_json(system, prompt)
    return result.get("cards", [])


def generate_insights_from_entries(entries, book_title=""):
    system = (
        "Voce e um assistente intelectual. Analise as entradas e gere insights que: "
        "1) Conectem temas recorrentes, 2) Identifiquem padroes, "
        "3) Sugiram aplicacoes praticas, 4) Proponham perguntas para reflexao. "
        "Responda em portugues brasileiro."
    )
    entries_text = "\n\n".join([
        f"[{e.get('entry_type', 'nota').upper()}] {e['content']}"
        for e in entries
    ])
    return _chat(system, f"Livro: {book_title}\n\nEntradas:\n{entries_text}")


def suggest_connections(entries):
    system = (
        "Voce identifica conexoes entre ideias de diferentes fontes. "
        "Sugira conexoes interdisciplinares e padroes. Responda em portugues brasileiro."
    )
    items = "\n\n".join([
        f"[{e.get('source', '?')}] {e.get('content', '')[:200]}"
        for e in entries
    ])
    return _chat(system, f"Encontre conexoes:\n\n{items}")


def smart_response(user_message, context_data=""):
    """Resposta conversacional generica com contexto do usuario."""
    system = (
        "Voce e um assistente de aprendizado pessoal chamado Learning Agent. "
        "Voce ajuda a organizar livros, estudos e insights. "
        "Seja amigavel, direto e util. Responda em portugues brasileiro. "
        "Se o usuario pedir algo que voce pode fazer (salvar citacao, adicionar livro, etc), "
        "explique como e ofereca ajuda."
    )
    prompt = user_message
    if context_data:
        prompt = f"Dados do usuario:\n{context_data}\n\nMensagem: {user_message}"
    return _chat(system, prompt)
