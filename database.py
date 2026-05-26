import os
import uuid
import datetime
import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger("FinBotDatabase")

# Inicializa o cliente do Supabase
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Conexão com o Supabase estabelecida com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao conectar com o Supabase: {str(e)}")
else:
    logger.error("Credenciais do Supabase não fornecidas!")

# ==================== HELPERS DE DATA ====================
def add_months(sourcedate, months):
    """Adiciona meses a uma data, lidando com finais de mês (ex: 31 de Janeiro + 1 mês = 28 de Fevereiro)."""
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    # Dias em cada mês (simplificado para bissextos rápidos)
    is_leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days_in_months = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(sourcedate.day, days_in_months[month-1])
    return datetime.date(year, month, day)


# ==================== OPERAÇÕES DE USUÁRIO ====================
def obter_ou_criar_usuario(id_telegram: int, nome: str) -> dict:
    """Verifica se o usuário já existe na base. Se não, cria-o e retorna seus dados."""
    if not supabase:
        return {"id_telegram": id_telegram, "nome": nome}
    
    try:
        # Busca o usuário pelo ID do Telegram
        resposta = supabase.table("usuarios").select("*").eq("id_telegram", id_telegram).execute()
        if resposta.data:
            logger.info(f"Usuário {nome} ({id_telegram}) encontrado no banco.")
            return resposta.data[0]
        
        # Se não existir, insere
        novo_usuario = {"id_telegram": id_telegram, "nome": nome}
        resposta_insert = supabase.table("usuarios").insert(novo_usuario).execute()
        logger.info(f"Novo usuário {nome} ({id_telegram}) cadastrado com sucesso!")
        return resposta_insert.data[0] if resposta_insert.data else novo_usuario
    except Exception as e:
        logger.error(f"Erro ao obter ou criar usuário {nome}: {str(e)}")
        # Fallback para prosseguir mesmo em caso de erro temporário na base
        return {"id_telegram": id_telegram, "nome": nome}


# ==================== OPERAÇÕES DE CATEGORIA ====================
def obter_mapa_categorias() -> dict:
    """Retorna um dicionário mapeando nome da categoria em minúsculas para seu ID."""
    if not supabase:
        return {}
    
    try:
        resposta = supabase.table("categorias").select("id, nome").execute()
        # Mapeia nome da categoria (lowercase e normalizado para busca fácil) -> ID
        return {cat["nome"].lower().strip(): cat["id"] for cat in resposta.data}
    except Exception as e:
        logger.error(f"Erro ao obter mapa de categorias: {str(e)}")
        return {}

def obter_todas_categorias() -> list:
    """Retorna a lista crua de categorias cadastradas."""
    if not supabase:
        return []
    try:
        resposta = supabase.table("categorias").select("*").execute()
        return resposta.data
    except Exception as e:
        logger.error(f"Erro ao buscar categorias: {str(e)}")
        return []


# ==================== OPERAÇÕES DE TRANSAÇÕES ====================
def salvar_transacao(id_usuario: int, categoria_nome: str, descricao: str, valor: float, tipo: str, parcelado: bool = False, total_parcelas: int = None) -> list:
    """
    Insere uma transação ou gera parcelamentos mensais automáticos no Supabase.
    Retorna a lista de registros inseridos.
    """
    if not supabase:
        logger.warning("Supabase não disponível. Simulação de salvamento concluída.")
        return []
    
    # 1. Obtém o mapa de categorias
    categorias = obter_mapa_categorias()
    cat_id = categorias.get(categoria_nome.lower().strip())
    
    # Se a categoria enviada pelo LLM não bater, tenta um fallback ('Outros')
    if not cat_id:
        cat_id = categorias.get("outros")
        if not cat_id:
            # Caso não tenha outros na base, pega o primeiro disponível
            cat_id = list(categorias.values())[0] if categorias else 1
            
    # 2. Ajusta o sinal do valor de acordo com o tipo (Despesas e cartões são negativos)
    valor_ajustado = abs(valor)
    if tipo.lower() in ["despesa", "cartão", "cartão parcelado", "divida"]:
        valor_ajustado = -valor_ajustado
    elif tipo.lower() in ["receita"]:
        valor_ajustado = valor_ajustado
        
    registros_a_inserir = []
    data_atual = datetime.date.today()
    
    # 3. Lógica de parcelamento
    if parcelado and total_parcelas and total_parcelas > 1:
        id_agrupador = str(uuid.uuid4())
        # Divide o valor total da compra pelas parcelas
        valor_parcela = round(valor_ajustado / total_parcelas, 2)
        # Ajusta diferença de arredondamento na última parcela (se houver)
        valor_acumulado = valor_parcela * total_parcelas
        diferenca_arredondamento = round(valor_ajustado - valor_acumulado, 2)
        
        for i in range(1, total_parcelas + 1):
            competencia = add_months(data_atual, i - 1)
            valor_final_parcela = valor_parcela
            if i == total_parcelas:
                # Soma o arredondamento na última parcela
                valor_final_parcela = round(valor_parcela + diferenca_arredondamento, 2)
                
            desc_parcela = f"{descricao} ({i}/{total_parcelas})"
            
            registro = {
                "id_usuario": id_usuario,
                "id_categoria": cat_id,
                "descricao": desc_parcela,
                "valor": valor_final_parcela,
                "data_competencia": competencia.isoformat(),
                "parcelado": True,
                "parcela_atual": i,
                "total_parcelas": total_parcelas,
                "id_agrupador_parcela": id_agrupador
            }
            registros_a_inserir.append(registro)
    else:
        # Transação simples
        registro = {
            "id_usuario": id_usuario,
            "id_categoria": cat_id,
            "descricao": descricao,
            "valor": valor_ajustado,
            "data_competencia": data_atual.isoformat(),
            "parcelado": False,
            "parcela_atual": None,
            "total_parcelas": None,
            "id_agrupador_parcela": None
        }
        registros_a_inserir.append(registro)
        
    try:
        # Executa a inserção em lote no Supabase
        resposta = supabase.table("transacoes").insert(registros_a_inserir).execute()
        logger.info(f"Sucesso: {len(registros_a_inserir)} transações inseridas no banco.")
        return resposta.data
    except Exception as e:
        logger.error(f"Erro ao salvar transações: {str(e)}")
        raise e


# ==================== OPERAÇÕES DE DÍVIDAS ====================
def salvar_divida(id_usuario: int, credor: str, valor_total: float, valor_pago: float = 0.0, status: str = "pendente") -> dict:
    """Insere um novo saldo devedor na tabela de dívidas."""
    if not supabase:
        logger.warning("Supabase não disponível. Simulação de dívida concluída.")
        return {}
        
    registro = {
        "id_usuario": id_usuario,
        "credor": credor,
        "valor_total": valor_total,
        "valor_pago": valor_pago,
        "status": status
    }
    
    try:
        resposta = supabase.table("dividas").insert(registro).execute()
        logger.info(f"Dívida com {credor} no valor de R$ {valor_total} salva com sucesso.")
        return resposta.data[0] if resposta.data else registro
    except Exception as e:
        logger.error(f"Erro ao salvar dívida: {str(e)}")
        raise e

def atualizar_pagamento_divida(id_divida: str, valor_adicional: float) -> dict:
    """Atualiza o valor pago de uma dívida e muda o status se quitada."""
    if not supabase:
        return {}
        
    try:
        # Busca dívida atual
        divida = supabase.table("dividas").select("*").eq("id", id_divida).execute().data[0]
        novo_pago = float(divida["valor_pago"]) + valor_adicional
        novo_status = "pago" if novo_pago >= float(divida["valor_total"]) else "pendente"
        
        atualizacao = {
            "valor_pago": novo_pago,
            "status": novo_status
        }
        
        resposta = supabase.table("dividas").update(atualizacao).eq("id", id_divida).execute()
        return resposta.data[0]
    except Exception as e:
        logger.error(f"Erro ao atualizar dívida: {str(e)}")
        raise e


# ==================== CONSULTAS DO DASHBOARD (STREAMLIT) ====================
def buscar_todos_usuarios() -> list:
    """Retorna todos os usuários cadastrados."""
    if not supabase:
        return []
    try:
        resposta = supabase.table("usuarios").select("*").execute()
        return resposta.data
    except Exception as e:
        logger.error(f"Erro ao buscar usuários para dashboard: {str(e)}")
        return []

def buscar_transacoes_completas() -> list:
    """Retorna todas as transações com dados populados de categorias e usuários."""
    if not supabase:
        return []
    try:
        # Faz join de tabelas no Supabase (utilizando a estrutura de chaves estrangeiras)
        resposta = supabase.table("transacoes").select("*, categorias(nome, meta_mensal), usuarios(nome)").execute()
        return resposta.data
    except Exception as e:
        logger.error(f"Erro ao buscar transações completas: {str(e)}")
        return []

def buscar_dividas_completas() -> list:
    """Retorna todas as dívidas com dados dos usuários."""
    if not supabase:
        return []
    try:
        resposta = supabase.table("dividas").select("*, usuarios(nome)").execute()
        return resposta.data
    except Exception as e:
        logger.error(f"Erro ao buscar dívidas completas: {str(e)}")
        return []
