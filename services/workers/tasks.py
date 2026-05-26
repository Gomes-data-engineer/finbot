import os
import re
import json
import logging
import datetime
import httpx
import google.generativeai as genai
from celery_app import app

# Configuração do Logger
logger = logging.getLogger("FinBotWorkers")

# Configura Gemini API
gemini_key = os.environ.get("GEMINI_API_KEY")
if gemini_key:
    genai.configure(api_key=gemini_key)
    logger.info("Gemini configurado no Worker.")
else:
    logger.error("Chave do Gemini ausente no Worker!")

model = genai.GenerativeModel("gemini-2.5-flash")

SYSTEM_PROMPT = """
Você é o FinBot 2.0, assistente de inteligência artificial financeira.
Analise a gravação de voz e retorne os dados estruturados em formato JSON bruto.

Categorias disponíveis:
- Alimentação
- Transporte
- Lazer
- Cartão
- Fixas
- Renda
- Outros

Intenções de transações:
- "despesa" (gastos correntes no débito/dinheiro)
- "receita" (salários, rendas)
- "cartão" (despesa simples no crédito)
- "cartão parcelado" (compra parcelada no crédito)

Retorne estritamente um JSON no formato:
{
  "tipo": "despesa" | "receita" | "cartão" | "cartão parcelado",
  "valor": 12.34,
  "categoria": "Nome da Categoria",
  "descricao": "breve descrição",
  "parcelado": true | false,
  "total_parcelas": int ou null
}
Responda APENAS o JSON.
"""

SYSTEM_PROMPT_PDF = """
Você é o processador de faturas do FinBot. Leia este PDF da fatura do cartão de crédito e extraia todos os lançamentos individuais de compras de forma estruturada.
Para cada compra na fatura, identifique:
- data da compra no formato YYYY-MM-DD.
- descrição do estabelecimento (ex: "Uber *Trip", "Supermercado Pão de Açúcar").
- valor absoluto da compra (float positivo, ex: 34.50).
- categoria sugerida dentre as permitidas: Alimentação, Transporte, Lazer, Cartão, Fixas, Outros.

Retorne estritamente um JSON no formato:
{
  "transacoes": [
    {
      "data": "YYYY-MM-DD",
      "descricao": "...",
      "valor": 12.34,
      "categoria": "Alimentação" | "Transporte" | "Lazer" | "Cartão" | "Fixas" | "Outros"
    }
  ]
}
Responda APENAS o JSON bruto, sem tags markdown ou comentários.
"""

def enviar_mensagem_telegram(chat_id: int, texto: str):
    """Envia mensagem de texto diretamente para o chat do usuário no Telegram."""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.warning("Token do Telegram ausente. Não foi possível notificar o usuário.")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": "Markdown"
        }
        with httpx.Client() as client:
            client.post(url, json=payload, timeout=15.0)
        logger.info(f"Notificação Telegram enviada com sucesso para chat_id {chat_id}.")
    except Exception as e:
        logger.error(f"Erro ao enviar notificação para Telegram: {str(e)}")

def limpar_e_carregar_json(texto: str) -> dict:
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, texto, re.DOTALL)
    texto_limpo = match.group(1) if match else texto
    return json.loads(texto_limpo.strip())


@app.task(name="tasks.processar_audio_telegram")
def processar_audio_telegram(chat_id: int, user_name: str, audio_hex: str):
    """
    Tarefa Celery que decodifica o áudio enviado pelo Telegram,
    transcreve e categoriza usando o Gemini, salva no banco Supabase V2
    e notifica o usuário do resultado final.
    """
    logger.info(f"Iniciando processamento de áudio assíncrono para {user_name} ({chat_id})")
    
    try:
        audio_bytes = bytes.fromhex(audio_hex)
    except Exception as e:
        logger.error(f"Erro ao decodificar áudio Hex: {str(e)}")
        enviar_mensagem_telegram(chat_id, "❌ Ocorreu um erro técnico ao processar seu áudio.")
        return
        
    try:
        conteudo_ia = [
            {
                "mime_type": "audio/ogg",
                "data": audio_bytes
            },
            SYSTEM_PROMPT
        ]
        
        logger.info("Chamando Gemini API...")
        resposta = model.generate_content(conteudo_ia)
        logger.info(f"Resposta Gemini: {resposta.text}")
        
        dados = limpar_e_carregar_json(resposta.text)
        
        tipo = dados.get("tipo")
        valor = dados.get("valor", 0.0)
        categoria = dados.get("categoria", "Outros")
        descricao = dados.get("descricao", "Sem descrição")
        parcelado = dados.get("parcelado", False)
        total_parcelas = dados.get("total_parcelas")
        
        if not valor or valor <= 0:
            enviar_mensagem_telegram(chat_id, "⚠️ Não identifiquei um valor válido no áudio. Pode repetir por favor?")
            return
            
        from supabase import create_client
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise Exception("Credenciais do Supabase ausentes no Worker.")
            
        supabase = create_client(supabase_url, supabase_key)
        
        user_res = supabase.table("usuarios").select("*").eq("id_telegram", chat_id).execute()
        if not user_res.data:
            user_insert = supabase.table("usuarios").insert({"id_telegram": chat_id, "nome": user_name}).execute()
            user_id = user_insert.data[0]["id"]
        else:
            user_id = user_res.data[0]["id"]
            
        cats = supabase.table("categorias").select("*").execute().data
        cat_id = None
        for c in cats:
            if c["nome"].lower().strip() == categoria.lower().strip():
                cat_id = c["id"]
                break
        if not cat_id:
            for c in cats:
                if c["nome"].lower().strip() == "outros":
                    cat_id = c["id"]
                    break
                    
        id_cartao = None
        if "cartão" in tipo:
            cartoes = supabase.table("cartoes").select("*").eq("id_usuario", user_id).execute().data
            if cartoes:
                id_cartao = cartoes[0]["id"]
            else:
                novo_cartao = {
                    "id_usuario": user_id,
                    "nome": "Cartão Padrão",
                    "limite": 5000.00,
                    "dia_fechamento": 5,
                    "dia_vencimento": 12
                }
                res_card = supabase.table("cartoes").insert(novo_cartao).execute()
                id_cartao = res_card.data[0]["id"]
                
        id_conta = None
        if not id_cartao:
            contas = supabase.table("contas").select("*").eq("id_usuario", user_id).execute().data
            if contas:
                id_conta = contas[0]["id"]
            else:
                nova_conta = {
                    "id_usuario": user_id,
                    "nome": "Conta Principal",
                    "tipo": "corrente",
                    "saldo": 0.00
                }
                res_conta = supabase.table("contas").insert(nova_conta).execute()
                id_conta = res_conta.data[0]["id"]
                
        valor_ajustado = -abs(valor) if tipo in ["despesa", "cartão", "cartão parcelado"] else abs(valor)
        registros_a_inserir = []
        data_atual = datetime.date.today()
        
        if parcelado and total_parcelas and total_parcelas > 1:
            parc_insert = supabase.table("parcelamentos").insert({
                "total_parcelas": total_parcelas,
                "valor_total": abs(valor),
                "descricao": descricao
            }).execute()
            id_parc = parc_insert.data[0]["id"]
            
            valor_parc = round(valor_ajustado / total_parcelas, 2)
            
            for i in range(1, total_parcelas + 1):
                m = (data_atual.month - 1 + i - 1)
                y = data_atual.year + m // 12
                m = m % 12 + 1
                comp_date = datetime.date(y, m, 1)
                
                id_fatura = None
                if id_cartao:
                    fats = supabase.table("faturas").select("*").eq("id_cartao", id_cartao).eq("mes_referencia", comp_date.isoformat()).execute().data
                    if fats:
                        id_fatura = fats[0]["id"]
                    else:
                        new_fat = supabase.table("faturas").insert({
                            "id_cartao": id_cartao,
                            "mes_referencia": comp_date.isoformat(),
                            "valor_total": 0.0,
                            "status": "aberta"
                        }).execute()
                        id_fatura = new_fat.data[0]["id"]
                        
                registros_a_inserir.append({
                    "id_usuario": user_id,
                    "id_conta": id_conta if not id_cartao else None,
                    "id_fatura": id_fatura,
                    "id_categoria": cat_id,
                    "id_parcelamento": id_parc,
                    "parcela_atual": i,
                    "descricao": f"{descricao} ({i}/{total_parcelas})",
                    "valor": valor_parc,
                    "data_competencia": comp_date.isoformat()
                })
        else:
            id_fatura = None
            if id_cartao:
                fats = supabase.table("faturas").select("*").eq("id_cartao", id_cartao).eq("mes_referencia", data_atual.replace(day=1).isoformat()).execute().data
                if fats:
                    id_fatura = fats[0]["id"]
                else:
                    new_fat = supabase.table("faturas").insert({
                        "id_cartao": id_cartao,
                        "mes_referencia": data_atual.replace(day=1).isoformat(),
                        "valor_total": 0.0,
                        "status": "aberta"
                    }).execute()
                    id_fatura = new_fat.data[0]["id"]
                    
            registros_a_inserir.append({
                "id_usuario": user_id,
                "id_conta": id_conta if not id_cartao else None,
                "id_fatura": id_fatura,
                "id_categoria": cat_id,
                "id_parcelamento": None,
                "parcela_atual": None,
                "descricao": descricao,
                "valor": valor_ajustado,
                "data_competencia": data_atual.isoformat()
            })
            
        supabase.table("transacoes").insert(registros_a_inserir).execute()
        
        tipo_emoji = "💵" if tipo == "receita" else "🛒"
        status_msg = (
            f"✅ **Áudio Registrado com Sucesso!**\n\n"
            f"{tipo_emoji} **Tipo:** {tipo.capitalize()}\n"
            f"📝 **Descrição:** {descricao}\n"
            f"💰 **Valor:** R$ {valor:,.2f}\n"
            f"📂 **Categoria:** {categoria}"
        )
        if parcelado and total_parcelas:
            status_msg += f" (em {total_parcelas}x no cartão)"
            
        enviar_mensagem_telegram(chat_id, status_msg)
        
    except Exception as e:
        logger.error(f"Erro crítico no processador de áudio: {str(e)}")
        enviar_mensagem_telegram(chat_id, f"❌ Erro ao registrar áudio: {str(e)}")


@app.task(name="tasks.processar_fatura_pdf")
def processar_fatura_pdf(chat_id: int, user_name: str, pdf_hex: str):
    """
    Tarefa Celery que lê o PDF enviado pelo usuário,
    chama a API do Gemini 1.5 Flash para processar o PDF (OCR),
    extrai os gastos e salva-os em lote vinculados ao Cartão do usuário no Supabase.
    """
    logger.info(f"Iniciando processamento assíncrono de fatura PDF para {user_name} ({chat_id})")
    
    try:
        pdf_bytes = bytes.fromhex(pdf_hex)
    except Exception as e:
        logger.error(f"Erro ao converter PDF Hex: {str(e)}")
        enviar_mensagem_telegram(chat_id, "❌ Erro técnico ao processar arquivo.")
        return
        
    try:
        # Envia PDF diretamente para o Gemini 1.5 Flash
        conteudo_ia = [
            {
                "mime_type": "application/pdf",
                "data": pdf_bytes
            },
            SYSTEM_PROMPT_PDF
        ]
        
        logger.info("Chamando Gemini API com PDF...")
        resposta = model.generate_content(conteudo_ia)
        logger.info(f"Resposta Gemini PDF: {resposta.text}")
        
        dados = limpar_e_carregar_json(resposta.text)
        lista_transacoes = dados.get("transacoes", [])
        
        if not lista_transacoes:
            enviar_mensagem_telegram(chat_id, "⚠️ Nenhuma transação encontrada ou falha ao ler o PDF.")
            return
            
        # Conecta ao Supabase
        from supabase import create_client
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        supabase = create_client(supabase_url, supabase_key)
        
        # Obtém ID do usuário
        user_res = supabase.table("usuarios").select("*").eq("id_telegram", chat_id).execute()
        if not user_res.data:
            user_insert = supabase.table("usuarios").insert({"id_telegram": chat_id, "nome": user_name}).execute()
            user_id = user_insert.data[0]["id"]
        else:
            user_id = user_res.data[0]["id"]
            
        # Busca ou cria cartão de crédito para associar
        cartoes = supabase.table("cartoes").select("*").eq("id_usuario", user_id).execute().data
        if cartoes:
            id_cartao = cartoes[0]["id"]
            dia_fechamento = int(cartoes[0]["dia_fechamento"])
        else:
            # Cria cartão padrão
            novo_cartao = {
                "id_usuario": user_id,
                "nome": "Cartão Padrão",
                "limite": 5000.00,
                "dia_fechamento": 5,
                "dia_vencimento": 12
            }
            res_card = supabase.table("cartoes").insert(novo_cartao).execute()
            id_cartao = res_card.data[0]["id"]
            dia_fechamento = 5
            
        cats = supabase.table("categorias").select("*").execute().data
        registros_a_inserir = []
        valor_total_fatura = 0.0
        
        for tx in lista_transacoes:
            desc = tx.get("descricao", "Compra Cartão")
            valor_abs = abs(tx.get("valor", 0.0))
            cat_nome = tx.get("categoria", "Outros")
            data_str = tx.get("data")
            
            if not valor_abs:
                continue
                
            valor_total_fatura += valor_abs
            
            # Tenta converter data, senão usa hoje
            try:
                data_comp = datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
            except:
                data_comp = datetime.date.today()
                
            # Determina UUID da categoria
            cat_id = None
            for c in cats:
                if c["nome"].lower().strip() == cat_nome.lower().strip():
                    cat_id = c["id"]
                    break
            if not cat_id:
                for c in cats:
                    if c["nome"].lower().strip() == "outros":
                        cat_id = c["id"]
                        break
                        
            # Calcula mês de competência da fatura
            if data_comp.day <= dia_fechamento:
                mes_ref = data_comp.replace(day=1)
            else:
                # Adiciona 1 mês
                m = data_comp.month - 1 + 1
                y = data_comp.year + m // 12
                m = m % 12 + 1
                mes_ref = datetime.date(y, m, 1)
                
            # Busca ou cria fatura correspondente
            fats = supabase.table("faturas").select("*").eq("id_cartao", id_cartao).eq("mes_referencia", mes_ref.isoformat()).execute().data
            if fats:
                id_fatura = fats[0]["id"]
            else:
                new_fat = supabase.table("faturas").insert({
                    "id_cartao": id_cartao,
                    "mes_referencia": mes_ref.isoformat(),
                    "valor_total": 0.0,
                    "status": "aberta"
                }).execute()
                id_fatura = new_fat.data[0]["id"]
                
            registros_a_inserir.append({
                "id_usuario": user_id,
                "id_fatura": id_fatura,
                "id_categoria": cat_id,
                "descricao": desc,
                "valor": -valor_abs,  -- Gastos no cartão são saídas (negativos)
                "data_competencia": data_comp.isoformat()
            })
            
        # Executa insert em lote (Batch Insert)
        supabase.table("transacoes").insert(registros_a_inserir).execute()
        
        # Atualiza o total acumulado das faturas correspondentes
        # (Para simplicidade, atualiza após os inserts)
        # Busca todas as faturas alteradas
        faturas_alteradas = set(r["id_fatura"] for r in registros_a_inserir)
        for fat_id in faturas_alteradas:
            # Re-calcula soma total
            soma = abs(sum(r["valor"] for r in registros_a_inserir if r["id_fatura"] == fat_id))
            # Busca total existente e soma
            fat_data = supabase.table("faturas").select("valor_total").eq("id", fat_id).execute().data[0]
            novo_total = float(fat_data["valor_total"]) + soma
            supabase.table("faturas").update({"valor_total": novo_total}).eq("id", fat_id).execute()
            
        enviar_mensagem_telegram(
            chat_id,
            f"✅ **Fatura Importada com Sucesso!**\n\n"
            f"📂 Registrados **{len(registros_a_inserir)}** lançamentos da fatura.\n"
            f"💰 Valor total processado: **R$ {valor_total_fatura:,.2f}**."
        )
        
    except Exception as e:
        logger.error(f"Erro ao processar fatura PDF: {str(e)}")
        enviar_mensagem_telegram(chat_id, f"❌ Falha ao processar fatura PDF: {str(e)}")
