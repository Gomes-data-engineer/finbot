import os
import uuid
import datetime
import logging
from supabase import create_client, Client

logger = logging.getLogger("FinBotGatewayDB")

# Inicializa cliente do Supabase
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

supabase: Client = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Gateway conectado ao Supabase com sucesso.")
    except Exception as e:
        logger.error(f"Erro de conexão no Gateway: {str(e)}")
else:
    logger.error("Credenciais do Supabase ausentes no Gateway.")


# ==================== HELPERS DE DATAS E FATURAS ====================
def add_months(sourcedate, months):
    """Adiciona meses a uma data considerando finais de meses."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    is_leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days_in_months = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(sourcedate.day, days_in_months[month-1])
    return datetime.date(year, month, day)

def obter_ou_criar_fatura(id_cartao: str, data_transacao: datetime.date) -> str:
    """
    Calcula a fatura correspondente de um cartão com base na data da compra e no dia de fechamento.
    Retorna o ID da fatura (aberta ou criada).
    """
    if not supabase:
        return None
        
    try:
        cartao = supabase.table("cartoes").select("*").eq("id", id_cartao).execute().data[0]
        dia_fechamento = int(cartao["dia_fechamento"])
        
        if data_transacao.day <= dia_fechamento:
            mes_referencia = data_transacao.replace(day=1)
        else:
            mes_referencia = add_months(data_transacao, 1).replace(day=1)
            
        ref_str = mes_referencia.isoformat()
        resposta = supabase.table("faturas").select("*").eq("id_cartao", id_cartao).eq("mes_referencia", ref_str).execute()
        
        if resposta.data:
            return resposta.data[0]["id"]
            
        nova_fatura = {
            "id_cartao": id_cartao,
            "mes_referencia": ref_str,
            "valor_total": 0.00,
            "status": "aberta"
        }
        res_insert = supabase.table("faturas").insert(nova_fatura).execute()
        return res_insert.data[0]["id"] if res_insert.data else None
    except Exception as e:
        logger.error(f"Erro ao calcular ou criar fatura: {str(e)}")
        raise e


# ==================== USUÁRIOS E CONTAS ====================
def obter_ou_criar_usuario(id_telegram: int, nome: str, email: str = None) -> dict:
    """Obtém ou cria o usuário na base relacional."""
    if not supabase:
        return {}
    try:
        res = supabase.table("usuarios").select("*").eq("id_telegram", id_telegram).execute()
        if res.data:
            return res.data[0]
            
        novo = {
            "id_telegram": id_telegram,
            "nome": nome,
            "email": email
        }
        res_insert = supabase.table("usuarios").insert(novo).execute()
        
        user_uuid = res_insert.data[0]["id"]
        criar_conta_padrao(user_uuid)
        
        return res_insert.data[0]
    except Exception as e:
        logger.error(f"Erro ao gerenciar usuário: {str(e)}")
        raise e

def criar_conta_padrao(id_usuario: str):
    """Cria uma conta corrente/carteira default para controle de transações físicas."""
    if not supabase:
        return
    conta = {
        "id_usuario": id_usuario,
        "nome": "Dinheiro em Espécie (Carteira)",
        "tipo": "carteira",
        "saldo": 0.00
    }
    supabase.table("contas").insert(conta).execute()


# ==================== CARTÕES E METAS ====================
def salvar_cartao(id_usuario: str, nome: str, limite: float, dia_fechamento: int, dia_vencimento: int, bandeira: str) -> dict:
    """Cadastra um novo cartão de crédito no Supabase."""
    if not supabase:
        return {}
    registro = {
        "id_usuario": id_usuario,
        "nome": nome,
        "limite": limite,
        "dia_fechamento": dia_fechamento,
        "dia_vencimento": dia_vencimento,
        "bandeira": bandeira
    }
    try:
        res = supabase.table("cartoes").insert(registro).execute()
        return res.data[0] if res.data else registro
    except Exception as e:
        logger.error(f"Erro ao salvar cartão: {str(e)}")
        raise e

def salvar_meta(id_usuario: str, categoria_nome: str, titulo: str, valor_alvo: float, tipo: str, data_limite: str) -> dict:
    """Cadastra uma nova meta financeira no Supabase."""
    if not supabase:
        return {}
        
    cat_id = None
    if categoria_nome and categoria_nome.lower() != "geral":
        try:
            cats = supabase.table("categorias").select("*").execute().data
            for c in cats:
                if c["nome"].lower().strip() == categoria_nome.lower().strip():
                    cat_id = c["id"]
                    break
        except Exception as e:
            logger.error(f"Erro ao buscar categorias para meta: {str(e)}")

    registro = {
        "id_usuario": id_usuario,
        "id_categoria": cat_id,
        "titulo": titulo,
        "valor_alvo": valor_alvo,
        "valor_atual": 0.00,
        "tipo": tipo,
        "data_limite": None if data_limite.lower() == "mensal" else data_limite
    }
    try:
        res = supabase.table("metas").insert(registro).execute()
        return res.data[0] if res.data else registro
    except Exception as e:
        logger.error(f"Erro ao salvar meta: {str(e)}")
        raise e


# ==================== TRANSAÇÕES & PARCELAMENTOS V2 ====================
def salvar_transacao_v2(id_usuario: str, id_categoria: str, descricao: str, valor: float, tipo: str,
                        id_conta: str = None, id_cartao: str = None, parcelado: bool = False, total_parcelas: int = None) -> list:
    """
    Insere transações na modelagem V2.
    Se for cartão de crédito, calcula a fatura e insere nela.
    Se for parcelado, gera faturas futuras correspondentes e divide os valores.
    """
    if not supabase:
        return []
        
    data_atual = datetime.date.today()
    registros_a_inserir = []
    
    valor_ajustado = abs(valor)
    if tipo in ["despesa", "cartão parcelado", "cartão"]:
        valor_ajustado = -valor_ajustado
        
    id_parcelamento = None
    if parcelado and total_parcelas and total_parcelas > 1:
        parc = {
            "total_parcelas": total_parcelas,
            "valor_total": abs(valor),
            "descricao": descricao
        }
        res_parc = supabase.table("parcelamentos").insert(parc).execute()
        id_parcelamento = res_parc.data[0]["id"]
        
        valor_parcela = round(valor_ajustado / total_parcelas, 2)
        valor_acumulado = valor_parcela * total_parcelas
        diferenca = round(valor_ajustado - valor_acumulado, 2)
        
        for i in range(1, total_parcelas + 1):
            comp_date = add_months(data_atual, i - 1)
            valor_final_parcela = valor_parcela
            if i == total_parcelas:
                valor_final_parcela = round(valor_parcela + diferenca, 2)
                
            id_fatura = None
            if id_cartao:
                id_fatura = obter_ou_criar_fatura(id_cartao, comp_date)
                
            registro = {
                "id_usuario": id_usuario,
                "id_conta": id_conta if not id_cartao else None,
                "id_fatura": id_fatura,
                "id_categoria": id_categoria,
                "id_parcelamento": id_parcelamento,
                "parcela_atual": i,
                "descricao": f"{descricao} ({i}/{total_parcelas})",
                "valor": valor_final_parcela,
                "data_competencia": comp_date.isoformat(),
                "confirmado": True
            }
            registros_a_inserir.append(registro)
    else:
        id_fatura = None
        if id_cartao:
            id_fatura = obter_ou_criar_fatura(id_cartao, data_atual)
            
        registro = {
            "id_usuario": id_usuario,
            "id_conta": id_conta if not id_cartao else None,
            "id_fatura": id_fatura,
            "id_categoria": id_categoria,
            "id_parcelamento": None,
            "parcela_atual": None,
            "descricao": descricao,
            "valor": valor_ajustado,
            "data_competencia": data_atual.isoformat(),
            "confirmado": True
        }
        registros_a_inserir.append(registro)
        
    try:
        resposta = supabase.table("transacoes").insert(registros_a_inserir).execute()
        
        if id_conta and not id_cartao:
            atualizar_saldo_conta(id_conta, valor_ajustado)
            
        for reg in registros_a_inserir:
            if reg["id_fatura"]:
                atualizar_valor_fatura(reg["id_fatura"], reg["valor"])
                
        return resposta.data
    except Exception as e:
        logger.error(f"Erro ao inserir transações no banco V2: {str(e)}")
        raise e

def atualizar_saldo_conta(id_conta: str, delta: float):
    if not supabase:
        return
    try:
        conta = supabase.table("contas").select("*").eq("id", id_conta).execute().data[0]
        novo_saldo = float(conta["saldo"]) + delta
        supabase.table("contas").update({"saldo": novo_saldo}).eq("id", id_conta).execute()
    except Exception as e:
        logger.error(f"Erro ao atualizar saldo de conta: {str(e)}")

def atualizar_valor_fatura(id_fatura: str, delta_gasto: float):
    if not supabase:
        return
    try:
        fat = supabase.table("faturas").select("*").eq("id", id_fatura).execute().data[0]
        novo_valor = float(fat["valor_total"]) + abs(delta_gasto)
        supabase.table("faturas").update({"valor_total": novo_valor}).eq("id", id_fatura).execute()
    except Exception as e:
        logger.error(f"Erro ao atualizar total de fatura: {str(e)}")
