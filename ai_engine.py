"""
ai_engine.py - Integracao com OpenAI para funcionalidades inteligentes.
"""

import os
import json
from openai import OpenAI

client = None
MODEL = "gpt-4o-mini"


def get_client():
    global client
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return client


def _chat(system_prompt, user_prompt, max_tokens=1000):
    """Wrapper generico para chamadas a OpenAI."""
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


def summarize_text(text, context=""):
    """Gera um resumo conciso de um texto."""
    system = (
        "Voce e um assistente de estudos. Crie resumos claros, concisos e bem estruturados "
        "em portugues brasileiro. Use bullet points quando apropriado. "
        "Destaque os pontos-chave e conceitos principais."
    )
    prompt = f"Contexto: {context}\n\nTexto para resumir:\n{text}" if context else text
    return _chat(system, f"Resuma o seguinte texto:\n\n{prompt}")


def generate_flashcards(text, num_cards=5):
    """Gera flashcards a partir de um texto."""
    system = (
        "Voce e um especialista em tecnicas de aprendizado. "
        "Gere flashcards no formato JSON para revisao espacada. "
        "Responda APENAS com um array JSON valido, sem markdown, sem explicacao. "
        "Cada card deve ter 'question' e 'answer'. "
        "As perguntas devem testar compreensao profunda, nao apenas memorizacao."
    )
    prompt = (
        f"Gere {num_cards} flashcards a partir deste conteudo:\n\n{text}\n\n"
        "Responda SOMENTE com o JSON array: [{\"question\": \"...\", \"answer\": \"...\"}]"
    )
    result = _chat(system, prompt, max_tokens=1500)

    try:
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1] if "\n" in clean else clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        cards = json.loads(clean)
        if isinstance(cards, list):
            return [c for c in cards if "question" in c and "answer" in c]
    except (json.JSONDecodeError, KeyError):
        pass
    return []


def generate_insights_from_entries(entries, book_title=""):
    """Analisa entradas de um livro e gera insights conectados."""
    system = (
        "Voce e um assistente intelectual que ajuda a conectar ideias. "
        "Analise as citacoes, resumos e ideias fornecidos e gere insights que: "
        "1) Conectem temas recorrentes, "
        "2) Identifiquem padroes, "
        "3) Sugiram aplicacoes praticas, "
        "4) Proponham perguntas para reflexao. "
        "Responda em portugues brasileiro."
    )
    entries_text = "\n\n".join([
        f"[{e.get('entry_type', 'nota').upper()}] {e['content']}"
        for e in entries
    ])
    prompt = f"Livro: {book_title}\n\nEntradas salvas:\n{entries_text}"
    return _chat(system, prompt, max_tokens=1500)


def smart_search(query, content_items):
    """Busca semantica inteligente pelo conteudo salvo."""
    system = (
        "Voce e um assistente de busca inteligente. O usuario tem uma base de conhecimento pessoal. "
        "Analise a pergunta e os itens de conteudo fornecidos. "
        "Retorne os itens mais relevantes e explique a conexao com a pergunta. "
        "Responda em portugues brasileiro de forma clara e organizada."
    )
    items_text = "\n\n".join([
        f"[{item.get('type', '?')}] (ID:{item.get('id', '?')}) {item.get('content', '')[:300]}"
        for item in content_items
    ])
    prompt = f"Pergunta do usuario: {query}\n\nConteudo disponivel:\n{items_text}"
    return _chat(system, prompt, max_tokens=1500)


def explain_concept(concept, context=""):
    """Explica um conceito de forma didatica."""
    system = (
        "Voce e um professor paciente e didatico. "
        "Explique conceitos de forma clara, usando analogias quando possivel. "
        "Se houver contexto de estudo, conecte a explicacao ao material. "
        "Responda em portugues brasileiro."
    )
    prompt = f"Explique: {concept}"
    if context:
        prompt += f"\n\nContexto de estudo: {context}"
    return _chat(system, prompt)


def suggest_connections(entries):
    """Sugere conexoes entre diferentes conteudos salvos."""
    system = (
        "Voce e um assistente que identifica conexoes entre ideias de diferentes fontes. "
        "Analise os conteudos e sugira conexoes interdisciplinares, "
        "padroes e temas em comum. Responda em portugues brasileiro."
    )
    items = "\n\n".join([
        f"[{e.get('source', 'desconhecido')}] {e.get('content', '')[:200]}"
        for e in entries
    ])
    return _chat(system, f"Encontre conexoes entre estes conteudos:\n\n{items}", max_tokens=1500)
