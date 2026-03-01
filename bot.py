import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
from supabase import create_client
import json

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clientes
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

# Histórico de conversa por usuário
conversation_history = {}

def get_system_prompt(user_id: str) -> str:
    return f"""Você é um assistente pessoal de banco de livros via Telegram.

O user_id do usuário é: {user_id}

Você tem acesso a funções para gerenciar livros. Use-as quando necessário.

FLUXO:
1. Ao iniciar → mostre o menu:
   📖 Novo Livro - para adicionar um livro
   📚 Meus Livros - para ver seus livros
   🔍 Pesquisar Livro - para buscar um livro

2. Novo livro → pergunte o nome → chame criar_livro → guarde o id retornado → aguarde registros

3. Durante leitura use o livro_id atual:
   - "citação [texto]" → salvar_registro tipo=citacao
   - "resumo [texto]" → salvar_registro tipo=resumo  
   - "ideia do livro [texto]" → salvar_registro tipo=ideia_livro
   - "minha ideia [texto]" → salvar_registro tipo=minha_ideia
   - "salvar" ou "pausar" → confirme e mostre menu

4. Meus livros → chame buscar_livros → liste os resultados
5. Ver registros → chame ver_registros com livro_id
6. Pesquisar → chame pesquisar_livro com termo

REGRAS:
- SEMPRE execute a função imediatamente
- NUNCA invente dados
- Após criar_livro GUARDE o id retornado para usar em salvar_registro
- Mostre TODO o conteudo retornado pelas funções
- Responda em português
- Use emojis para tornar a experiência agradável"""

# Definição das funções para o OpenAI
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "criar_livro",
            "description": "Salva um novo livro no banco de dados",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_livro": {
                        "type": "string",
                        "description": "Nome do livro"
                    }
                },
                "required": ["nome_livro"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_livros",
            "description": "Busca todos os livros do usuário",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "salvar_registro",
            "description": "Salva uma citação, resumo, ideia do livro ou minha ideia",
            "parameters": {
                "type": "object",
                "properties": {
                    "livro_id": {
                        "type": "string",
                        "description": "ID do livro atual"
                    },
                    "tipo": {
                        "type": "string",
                        "enum": ["citacao", "resumo", "ideia_livro", "minha_ideia"],
                        "description": "Tipo do registro"
                    },
                    "conteudo": {
                        "type": "string",
                        "description": "Texto completo do registro"
                    }
                },
                "required": ["livro_id", "tipo", "conteudo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_registros",
            "description": "Busca todos os registros de um livro específico",
            "parameters": {
                "type": "object",
                "properties": {
                    "livro_id": {
                        "type": "string",
                        "description": "ID do livro"
                    }
                },
                "required": ["livro_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pesquisar_livro",
            "description": "Pesquisa um livro pelo nome",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Termo de busca"
                    }
                },
                "required": ["termo"]
            }
        }
    }
]

def executar_funcao(nome: str, args: dict, user_id: str) -> str:
    """Executa a função chamada pelo OpenAI"""
    try:
        if nome == "criar_livro":
            import time
            livro_id = str(int(time.time() * 1000))
            result = supabase.table("livros").insert({
                "id": livro_id,
                "user_id": user_id,
                "nome_livro": args["nome_livro"],
                "status": "ativo",
                "data_criacao": __import__('datetime').datetime.now().strftime("%d/%m/%Y")
            }).execute()
            return json.dumps({"id": livro_id, "nome_livro": args["nome_livro"], "status": "salvo com sucesso"})

        elif nome == "buscar_livros":
            result = supabase.table("livros").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            if not result.data:
                return json.dumps([])
            return json.dumps(result.data)

        elif nome == "salvar_registro":
            import time
            registro_id = str(int(time.time() * 1000))
            result = supabase.table("registros").insert({
                "id": registro_id,
                "livro_id": args["livro_id"],
                "user_id": user_id,
                "tipo": args["tipo"],
                "conteudo": args["conteudo"],
                "data": __import__('datetime').datetime.now().strftime("%d/%m/%Y"),
                "origem": "texto"
            }).execute()
            return json.dumps({"status": "salvo com sucesso", "tipo": args["tipo"]})

        elif nome == "ver_registros":
            result = supabase.table("registros").select("*").eq("livro_id", args["livro_id"]).order("created_at").execute()
            if not result.data:
                return json.dumps([])
            return json.dumps(result.data)

        elif nome == "pesquisar_livro":
            result = supabase.table("livros").select("*").eq("user_id", user_id).ilike("nome_livro", f"%{args['termo']}%").execute()
            if not result.data:
                return json.dumps([])
            return json.dumps(result.data)

    except Exception as e:
        logger.error(f"Erro na função {nome}: {e}")
        return json.dumps({"erro": str(e)})

async def processar_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa cada mensagem recebida"""
    user_id = str(update.effective_user.id)
    texto = update.message.text

    # Inicializa histórico se necessário
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Adiciona mensagem do usuário ao histórico
    conversation_history[user_id].append({
        "role": "user",
        "content": texto
    })

    # Limita histórico a 20 mensagens
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    try:
        # Envia para o OpenAI com as funções disponíveis
        messages = [
            {"role": "system", "content": get_system_prompt(user_id)}
        ] + conversation_history[user_id]

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        # Processa chamadas de função em loop até ter resposta final
        while msg.tool_calls:
            # Adiciona resposta do assistente com tool_calls
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in msg.tool_calls
                ]
            })

            # Executa cada função chamada
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                resultado = executar_funcao(func_name, func_args, user_id)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": resultado
                })

            # Chama o OpenAI novamente com os resultados
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
            msg = response.choices[0].message

        # Resposta final
        resposta = msg.content

        # Salva no histórico
        conversation_history[user_id].append({
            "role": "assistant",
            "content": resposta
        })

        await update.message.reply_text(resposta)

    except Exception as e:
        logger.error(f"Erro: {e}")
        await update.message.reply_text("Ocorreu um erro. Tente novamente.")

def main():
    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_mensagem))
    logger.info("Bot iniciado!")
    app.run_polling()

if __name__ == "__main__":
    main()
