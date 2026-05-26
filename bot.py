import os
import re
import json
import logging
import httpx
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from celery import Celery
import google.generativeai as genai

from dotenv import load_dotenv
load_dotenv()

# Configura Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FinBotTelegramDaemon")

# Carrega chaves
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8000")

# Inicializa cliente do Celery
try:
    celery_client = Celery("finbot_workers", broker=REDIS_URL)
    logger.info("Conectado ao Redis/Celery Broker.")
except Exception as e:
    logger.error(f"Erro ao conectar ao Celery Broker: {str(e)}")

# Configura Gemini (apenas para texto síncrono local)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    logger.error("Chave do Gemini ausente no Bot!")

SYSTEM_PROMPT_COGNITIVE = """
Você é o cérebro cognitivo do FinBot 2.0. Sua tarefa é analisar a mensagem atual do usuário, juntamente com o estado anterior da conversa (se houver), e classificar as intenções do usuário.

Intenções permitidas:
1. "registrar_transacao": Lançar um gasto/despesa, ganho/receita ou compra no cartão.
2. "cadastrar_cartao": Adicionar um novo cartão de crédito.
3. "cadastrar_meta": Criar um limite de gastos ou meta de economia.
4. "casual": Saudação, resposta genérica, agradecimento, conversa fiada.

Regras de Classificação e Extração:
- Se a mensagem for uma saudação (ex: "oi", "olá", "bom dia"), a intenção é "casual".
- Se o usuário expressar o desejo de cadastrar um cartão (ex: "quero cadastrar um cartão", "adicionar cartão"), a intenção é "cadastrar_cartao".
- Se o usuário expressar o desejo de cadastrar uma meta (ex: "quero cadastrar uma meta", "nova meta"), a intenção é "cadastrar_meta".
- Se a intenção for cadastrar um cartão ou meta, extraia todos os campos possíveis. Se campos estiverem faltando, defina "completo" como false e escreva em "mensagem_pergunta" o que está faltando de forma amigável.
- Se o estado anterior indica um fluxo ativo (ex: "cadastrar_cartao"), use a nova mensagem para preencher os campos que faltavam desse fluxo.
- Se a nova mensagem for para cancelar (ex: "cancelar", "desistir"), não continue o fluxo.

Campos para "cadastrar_cartao":
- nome: Nome do cartão (ex: Nubank, Inter) (string ou null)
- limite: Limite total (float ou null)
- dia_fechamento: Dia de fechamento da fatura (int ou null)
- dia_vencimento: Dia de vencimento da fatura (int ou null)
- bandeira: Bandeira (ex: Visa, Mastercard, Elo) (string ou null)

Campos para "cadastrar_meta":
- titulo: Título da meta (ex: Reserva de Emergência) (string ou null)
- valor_alvo: Valor total/alvo (float ou null)
- categoria_nome: Categoria específica (Alimentação, Transporte, Lazer, Cartão, Fixas, Renda, Outros) ou "Geral" (string ou null)
- tipo: "gasto" (limitar despesa) ou "economia" (poupar/reserva) (string ou null)
- data_limite: "Mensal" ou uma data no formato YYYY-MM-DD (string ou null)

Campos para "registrar_transacao":
- tipo: "receita" (ganhos) ou "despesa" (gasto em débito/dinheiro) ou "cartão" (gasto no crédito) ou "cartão parcelado" (string)
- valor: Valor da transação (float)
- categoria: Alimentação, Transporte, Lazer, Cartão, Fixas, Renda, Outros (string)
- descricao: Descrição curta (string)
- parcelado: boolean
- total_parcelas: int ou null (se parcelado)

Retorne estritamente um JSON no formato:
{
  "intents": [
    {
      "tipo": "registrar_transacao" | "cadastrar_cartao" | "cadastrar_meta" | "casual",
      "dados": { ... },
      "completo": true | false,
      "mensagem_pergunta": "Sua resposta ou pergunta ao usuário"
    }
  ]
}
Responda APENAS o JSON bruto. Não coloque ```json ou tags markdown.
"""

def limpar_e_carregar_json(texto: str) -> dict:
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, texto, re.DOTALL)
    texto_limpo = match.group(1) if match else texto
    return json.loads(texto_limpo.strip())

# ==================== HELPERS DE CONEXÃO ====================
async def obter_usuario_uuid(chat_id: int, user_name: str) -> str:
    """Busca ou cria o usuário na API e retorna seu UUID do banco."""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{API_GATEWAY_URL}/api/v1/usuarios",
            json={"id_telegram": chat_id, "nome": user_name},
            timeout=10.0
        )
        return res.json()["id"]

# ==================== HANDLERS COMUNS ====================

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    nome = user.full_name or user.first_name
    
    # Reseta estados
    context.user_data.clear()
    
    try:
        await obter_usuario_uuid(chat_id, nome)
    except Exception as e:
        logger.error(f"Erro ao registrar usuário via API Gateway: {str(e)}")
        
    mensagem = (
        f"👋 Olá, {nome}!\n\n"
        f"Bem-vindo ao **FinBot 2.0 (Fintech Core)**! 🚀\n\n"
        f"✍️ **Envie texto:** 'paguei 30 de gasolina hoje'\n"
        f"🎙️ **Envie áudio:** 'Farmácia deu cinquenta reais no crédito'\n"
        f"📄 **Envie PDF:** Envie a sua fatura em PDF para ler todos os gastos!\n\n"
        f"✨ **Cadastros Interativos:**\n"
        f"💳 Cadastrar Cartão: Digite 'cadastrar cartão'\n"
        f"🎯 Cadastrar Meta: Digite 'cadastrar meta'\n"
        f"❌ Cancelar cadastro ativo: /cancelar"
    )
    await update.message.reply_text(mensagem, parse_mode="Markdown")

async def comando_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Fluxo ativo cancelado com sucesso. O que gostaria de fazer agora?")

# ==================== TRANSAÇÕES TEXTO E VOZ ====================

async def tratar_mensagem_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    user_name = user.full_name or user.first_name
    
    is_voice = update.message.voice is not None
    
    if is_voice:
        await update.message.reply_text("🎙️ *Áudio recebido!* Processando em background...", parse_mode="Markdown")
        try:
            voice = update.message.voice
            file_id = voice.file_id
            arquivo_telegram = await context.bot.get_file(file_id)
            
            os.makedirs("temp", exist_ok=True)
            temp_path = f"temp/{file_id}.ogg"
            await arquivo_telegram.download_to_drive(temp_path)
            
            with open(temp_path, "rb") as f:
                audio_bytes = f.read()
                
            os.remove(temp_path)
            audio_hex = audio_bytes.hex()
            
            celery_client.send_task(
                "tasks.processar_audio_telegram",
                args=[chat_id, user_name, audio_hex]
            )
            logger.info(f"Áudio do usuário {user_name} enviado para fila Celery.")
        except Exception as e:
            logger.error(f"Erro ao despachar áudio para o Celery: {str(e)}")
            await update.message.reply_text("❌ Erro ao enviar áudio para processamento. Tente mais tarde.")
        return

    # Processamento de texto
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    texto_usuario = update.message.text

    # Verifica comando rápido de cancelamento em texto
    if texto_usuario.lower().strip() in ["cancelar", "cancel"]:
        context.user_data.clear()
        await update.message.reply_text("❌ Fluxo ativo cancelado com sucesso.")
        return

    # Reconstrói estado anterior para a IA
    fluxo_ativo = context.user_data.get("fluxo_ativo")
    dados_coletados = context.user_data.get("dados_coletados", {})
    
    prompt_contexto = ""
    if fluxo_ativo:
        prompt_contexto = (
            f"\n\n[ESTADO ANTERIOR DA CONVERSA]\n"
            f"- Fluxo Ativo: {fluxo_ativo}\n"
            f"- Dados coletados até agora: {json.dumps(dados_coletados)}"
        )
        
    try:
        # Chamada cognitiva ao Gemini
        resposta = model.generate_content(f"{SYSTEM_PROMPT_COGNITIVE}{prompt_contexto}\n\nMensagem do usuário: '{texto_usuario}'")
        logger.info(f"Retorno do Gemini: {resposta.text}")
        dados_resposta = limpar_e_carregar_json(resposta.text)
        
        intents = dados_resposta.get("intents", [])
        if not intents:
            # Fallback conversacional simples
            res_conversa = model.generate_content(
                f"Você é o FinBot 2.0. Responda de forma amigável em português, dando dicas de uso:\n'{texto_usuario}'"
            )
            await update.message.reply_text(res_conversa.text)
            return
            
        for intent in intents:
            tipo_intent = intent.get("tipo")
            dados = intent.get("dados", {})
            completo = intent.get("completo", False)
            mensagem_pergunta = intent.get("mensagem_pergunta", "")
            
            # --- CASO 1: CASUAL ---
            if tipo_intent == "casual":
                await update.message.reply_text(mensagem_pergunta)
                
            # --- CASO 2: CADASTRAR CARTÃO ---
            elif tipo_intent == "cadastrar_cartao":
                # Mescla dados coletados
                novos_dados = {**dados_coletados, **{k: v for k, v in dados.items() if v is not None}}
                
                if completo:
                    # Todos os campos estão presentes! Salva no Supabase via API Gateway
                    try:
                        user_uuid = await obter_usuario_uuid(chat_id, user_name)
                        payload = {
                            "id_usuario": user_uuid,
                            "nome": novos_dados.get("nome"),
                            "limite": float(novos_dados.get("limite", 0)),
                            "dia_fechamento": int(novos_dados.get("dia_fechamento", 5)),
                            "dia_vencimento": int(novos_dados.get("dia_vencimento", 12)),
                            "bandeira": novos_dados.get("bandeira", "Outra")
                        }
                        
                        async with httpx.AsyncClient() as client:
                            res = await client.post(f"{API_GATEWAY_URL}/api/v1/cartoes", json=payload, timeout=10.0)
                            
                        if res.status_code == 201:
                            await update.message.reply_text(
                                f"💳 **Cartão cadastrado com sucesso!**\n\n"
                                f"💳 **Nome:** {payload['nome']}\n"
                                f"💰 **Limite:** R$ {payload['limite']:,.2f}\n"
                                f"📅 **Vencimento/Fechamento:** Dia {payload['dia_vencimento']} / Dia {payload['dia_fechamento']}\n"
                                f"🏷️ **Bandeira:** {payload['bandeira']}"
                            )
                            # Limpa fluxo
                            context.user_data.clear()
                        else:
                            await update.message.reply_text("❌ Falha ao salvar cartão no Supabase. Tente novamente.")
                    except Exception as e:
                        logger.error(f"Erro ao salvar cartão via API: {str(e)}")
                        await update.message.reply_text("⚠️ Ocorreu um erro ao salvar o cartão no banco de dados. Verifique a API.")
                else:
                    # Ainda faltam dados. Atualiza o estado
                    context.user_data["fluxo_ativo"] = "cadastrar_cartao"
                    context.user_data["dados_coletados"] = novos_dados
                    await update.message.reply_text(mensagem_pergunta)
                    
            # --- CASO 3: CADASTRAR META ---
            elif tipo_intent == "cadastrar_meta":
                # Mescla dados coletados
                novos_dados = {**dados_coletados, **{k: v for k, v in dados.items() if v is not None}}
                
                if completo:
                    # Todos os campos estão presentes! Salva no Supabase via API Gateway
                    try:
                        user_uuid = await obter_usuario_uuid(chat_id, user_name)
                        payload = {
                            "id_usuario": user_uuid,
                            "categoria_nome": novos_dados.get("categoria_nome", "Geral"),
                            "titulo": novos_dados.get("titulo"),
                            "valor_alvo": float(novos_dados.get("valor_alvo", 0)),
                            "tipo": novos_dados.get("tipo", "gasto"),
                            "data_limite": novos_dados.get("data_limite", "Mensal")
                        }
                        
                        async with httpx.AsyncClient() as client:
                            res = await client.post(f"{API_GATEWAY_URL}/api/v1/metas", json=payload, timeout=10.0)
                            
                        if res.status_code == 201:
                            await update.message.reply_text(
                                f"🎯 **Meta cadastrada com sucesso!**\n\n"
                                f"🎯 **Título:** {payload['titulo']}\n"
                                f"💰 **Valor Alvo:** R$ {payload['valor_alvo']:,.2f}\n"
                                f"📂 **Categoria:** {payload['categoria_nome']}\n"
                                f"🏷️ **Tipo:** {payload['tipo'].capitalize()}\n"
                                f"📅 **Data Limite:** {payload['data_limite']}"
                            )
                            # Limpa fluxo
                            context.user_data.clear()
                        else:
                            await update.message.reply_text("❌ Falha ao salvar meta no Supabase. Tente novamente.")
                    except Exception as e:
                        logger.error(f"Erro ao salvar meta via API: {str(e)}")
                        await update.message.reply_text("⚠️ Ocorreu um erro ao salvar a meta no banco de dados. Verifique a API.")
                else:
                    # Ainda faltam dados. Atualiza o estado
                    context.user_data["fluxo_ativo"] = "cadastrar_meta"
                    context.user_data["dados_coletados"] = novos_dados
                    await update.message.reply_text(mensagem_pergunta)
                    
            # --- CASO 4: TRANSAÇÃO FINANCEIRA ---
            elif tipo_intent == "registrar_transacao":
                valor = dados.get("valor")
                if not valor or valor <= 0:
                    await update.message.reply_text("⚠️ Não consegui entender o valor. Pode repetir o valor da transação?")
                    continue
                    
                try:
                    user_uuid = await obter_usuario_uuid(chat_id, user_name)
                    payload = {
                        "id_usuario": user_uuid,
                        "categoria_nome": dados.get("categoria", "Outros"),
                        "descricao": dados.get("descricao", "Transação"),
                        "valor": dados.get("valor"),
                        "tipo": dados.get("tipo"),
                        "parcelado": dados.get("parcelado", False),
                        "total_parcelas": dados.get("total_parcelas")
                    }
                    
                    async with httpx.AsyncClient() as client:
                        res_tx = await client.post(
                            f"{API_GATEWAY_URL}/api/v1/transacoes",
                            json=payload,
                            timeout=10.0
                        )
                        
                    if res_tx.status_code == 201:
                        tipo_emoji = "💵" if dados.get("tipo") == "receita" else "🛒"
                        confirmacao = (
                            f"✅ **Lançamento Registrado!**\n\n"
                            f"{tipo_emoji} **Tipo:** {dados.get('tipo').capitalize()}\n"
                            f"📝 **Descrição:** {dados.get('descricao')}\n"
                            f"💰 **Valor:** R$ {dados.get('valor'):,.2f}\n"
                            f"📂 **Categoria:** {dados.get('categoria')}"
                        )
                        if dados.get("parcelado"):
                            confirmacao += f" (parcelado em {dados.get('total_parcelas')}x)"
                            
                        await update.message.reply_text(confirmacao, parse_mode="Markdown")
                    else:
                        await update.message.reply_text("❌ Falha ao salvar transação no banco de dados.")
                except Exception as e:
                    logger.error(f"Erro ao salvar transação via API: {str(e)}")
                    await update.message.reply_text("⚠️ Erro de conexão com o banco de dados. Transação não gravada.")
                    
    except Exception as e:
        logger.error(f"Erro ao processar resposta cognitiva: {str(e)}")
        # Fallback de erro amigável
        try:
            res_conversa = model.generate_content(
                f"Você é o FinBot 2.0. Diga ao usuário de forma curta e amigável que não entendeu o comando e sugira um exemplo:\n'{texto_usuario}'"
            )
            await update.message.reply_text(res_conversa.text)
        except Exception:
            await update.message.reply_text("⚠️ Desculpe, tive dificuldades para entender o comando. Pode repetir ou tentar de outra forma?")

async def tratar_fatura_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat_id = user.id
    user_name = user.full_name or user.first_name
    
    await update.message.reply_text("📄 *Fatura PDF Recebida!* Iniciando OCR e extração em lote no background...", parse_mode="Markdown")
    
    try:
        document = update.message.document
        file_id = document.file_id
        arquivo_telegram = await context.bot.get_file(file_id)
        
        os.makedirs("temp", exist_ok=True)
        temp_path = f"temp/{file_id}.pdf"
        await arquivo_telegram.download_to_drive(temp_path)
        
        with open(temp_path, "rb") as f:
            pdf_bytes = f.read()
            
        os.remove(temp_path)
        pdf_hex = pdf_bytes.hex()
        
        celery_client.send_task(
            "tasks.processar_fatura_pdf",
            args=[chat_id, user_name, pdf_hex]
        )
        logger.info(f"Fatura PDF de {user_name} enviada para Celery tasks.")
    except Exception as e:
        logger.error(f"Erro ao disparar tarefa de fatura PDF: {str(e)}")
        await update.message.reply_text("❌ Ocorreu um erro ao enviar seu arquivo para processamento.")

def main():
    if not TELEGRAM_TOKEN:
        logger.error("Token do Telegram ausente! Abortando.")
        return
    logger.info("Iniciando Daemon do Bot Telegram...")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Comandos básicos
    application.add_handler(CommandHandler("start", comando_start))
    application.add_handler(CommandHandler("cancelar", comando_cancelar))
    
    # PDF fatura
    application.add_handler(MessageHandler(filters.Document.PDF, tratar_fatura_pdf))
    
    # Handler geral único para Texto e Voz (toda a inteligência flui através daqui!)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, tratar_mensagem_usuario))
    application.add_handler(MessageHandler(filters.VOICE, tratar_mensagem_usuario))
    
    application.run_polling()

if __name__ == "__main__":
    main()
