# 🧠 Telegram Learning Agent Bot

Agente pessoal no Telegram para gerenciar leituras, estudos e aprendizados com IA (OpenAI).

## Funcionalidades

- **📚 Biblioteca** — Livros com citações, resumos e ideias
- **🎓 Estudos** — Cursos, disciplinas e tópicos com anotações
- **💡 Insights** — Aprendizados de podcasts, artigos, conversas
- **🃏 Flashcards** — Revisão espaçada (SM-2) com geração por IA
- **🔍 Busca Global** — Pesquise em todo seu conteúdo
- **🤖 IA** — Resumos, conexões entre ideias, flashcards automáticos

## Setup Rápido

### 1. Criar Bot no Telegram
- Fale com [@BotFather](https://t.me/botfather)
- Envie `/newbot` e copie o token

### 2. Configurar
```bash
cd telegram-learning-agent
python -m venv venv
source venv/bin/activate       # Linux/Mac
# venv\\Scripts\\activate       # Windows
pip install -r requirements.txt
cp .env.example .env
```

Edite o `.env` com suas chaves:
```
TELEGRAM_BOT_TOKEN=seu_token
OPENAI_API_KEY=sua_chave
```

### 3. Rodar
```bash
python bot.py
```

## Comandos

| Comando | Ação |
|---------|------|
| `/start` | Menu principal |
| `/livros` | Biblioteca |
| `/estudos` | Caderno de estudos |
| `/insights` | Insights |
| `/flashcards` | Revisar flashcards |
| `/buscar` | Busca global |
| `/stats` | Estatísticas |
| `/ajuda` | Ajuda |
| `/pular` | Pular campo opcional |
| `/cancelar` | Cancelar operação |

## Estrutura
```
├── bot.py              # Arquivo principal
├── database.py         # SQLite
├── ai_engine.py        # OpenAI
├── keyboards.py        # Teclados inline
├── handlers/
│   ├── books.py        # Livros
│   ├── studies.py      # Estudos
│   ├── insights.py     # Insights
│   ├── flashcards.py   # Flashcards
│   └── search.py       # Busca + Stats
├── .env.example
└── requirements.txt
```
