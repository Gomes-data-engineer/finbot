import os
import logging
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import google.generativeai as genai
import database_v2

# Configuração do Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FinBotGateway")

app = FastAPI(
    title="FinBot API Gateway",
    description="API Gateway de Alta Performance para a plataforma FinBot 2.0",
    version="2.0.0"
)

# Configura Gemini para chat cognitivo síncrono
gemini_key = os.environ.get("GEMINI_API_KEY")
if gemini_key:
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    logger.info("Gemini configurado no Gateway para Chat.")
else:
    logger.error("Gemini Key ausente no Gateway!")


# ==================== PYDANTIC SCHEMAS ====================
class TransacaoCreate(BaseModel):
    id_usuario: str = Field(..., description="UUID do usuário cadastrado")
    categoria_nome: str = Field("Outros", description="Nome da categoria")
    descricao: str = Field(..., description="Descrição da transação")
    valor: float = Field(..., description="Valor numérico absoluto da transação")
    tipo: str = Field(..., description="'receita', 'despesa', 'cartão' ou 'cartão parcelado'")
    id_conta: Optional[str] = Field(None, description="UUID da conta bancária de débito")
    id_cartao: Optional[str] = Field(None, description="UUID do cartão de crédito se pago com crédito")
    parcelado: Optional[bool] = False
    total_parcelas: Optional[int] = Field(None, ge=2, description="Número total de parcelas")

class UsuarioRegistro(BaseModel):
    id_telegram: int
    nome: str
    email: Optional[str] = None

class CartaoCreate(BaseModel):
    id_usuario: str
    nome: str
    limite: float
    dia_fechamento: int
    dia_vencimento: int
    bandeira: str

class MetaCreate(BaseModel):
    id_usuario: str
    categoria_nome: Optional[str] = "Geral"
    titulo: str
    valor_alvo: float
    tipo: str = "gasto" # gasto ou economia
    data_limite: Optional[str] = "Mensal"

class ChatRequest(BaseModel):
    id_usuario: str
    mensagem: str


# ==================== ENDPOINTS ====================

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    status_db = "offline"
    if database_v2.supabase:
        status_db = "online"
    return {
        "status": "healthy",
        "version": "2.0.0",
        "database_connection": status_db
    }

@app.get("/api/v1/usuarios")
async def listar_usuarios():
    """Retorna todos os usuários cadastrados."""
    if not database_v2.supabase:
        return []
    try:
        res = database_v2.supabase.table("usuarios").select("*").execute()
        return res.data
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar usuários: {str(e)}"
        )

@app.post("/api/v1/usuarios", status_code=status.HTTP_201_CREATED)
async def registrar_usuario(dados: UsuarioRegistro):
    try:
        usuario = database_v2.obter_ou_criar_usuario(dados.id_telegram, dados.nome, dados.email)
        return usuario
    except Exception as e:
        logger.error(f"Erro ao registrar usuário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao registrar usuário: {str(e)}"
        )

@app.post("/api/v1/cartoes", status_code=status.HTTP_201_CREATED)
async def criar_cartao(dados: CartaoCreate):
    """Cadastra um novo cartão de crédito para o usuário."""
    try:
        cartao = database_v2.salvar_cartao(
            dados.id_usuario, dados.nome, dados.limite,
            dados.dia_fechamento, dados.dia_vencimento, dados.bandeira
        )
        return cartao
    except Exception as e:
        logger.error(f"Erro ao cadastrar cartão: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar cartão: {str(e)}"
        )

@app.post("/api/v1/metas", status_code=status.HTTP_201_CREATED)
async def criar_meta(dados: MetaCreate):
    """Cadastra uma nova meta financeira (limite de gasto ou economia)."""
    try:
        meta = database_v2.salvar_meta(
            dados.id_usuario, dados.categoria_nome, dados.titulo,
            dados.valor_alvo, dados.tipo, dados.data_limite
        )
        return meta
    except Exception as e:
        logger.error(f"Erro ao cadastrar meta: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar meta: {str(e)}"
        )

@app.post("/api/v1/transacoes", status_code=status.HTTP_201_CREATED)
async def criar_transacao(dados: TransacaoCreate):
    try:
        cats = database_v2.supabase.table("categorias").select("*").execute().data
        cat_id = None
        for c in cats:
            if c["nome"].lower().strip() == dados.categoria_nome.lower().strip():
                cat_id = c["id"]
                break
                
        if not cat_id:
            for c in cats:
                if c["nome"].lower().strip() == "outros":
                    cat_id = c["id"]
                    break
            if not cat_id and cats:
                cat_id = cats[0]["id"]
                
        if not cat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhuma categoria encontrada no banco de dados."
            )
            
        inseridos = database_v2.salvar_transacao_v2(
            id_usuario=dados.id_usuario,
            id_categoria=cat_id,
            descricao=dados.descricao,
            valor=dados.valor,
            tipo=dados.tipo,
            id_conta=dados.id_conta,
            id_cartao=dados.id_cartao,
            parcelado=dados.parcelado,
            total_parcelas=dados.total_parcelas
        )
        return {"status": "success", "transactions_created": len(inseridos), "data": inseridos}
    except Exception as e:
        logger.error(f"Erro ao criar transação: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/v1/dashboard/consolidado/{id_usuario}")
async def obter_dados_consolidado(id_usuario: str):
    if not database_v2.supabase:
        raise HTTPException(status_code=503, detail="Supabase indisponível.")
    try:
        contas = database_v2.supabase.table("contas").select("*").eq("id_usuario", id_usuario).execute().data
        transacoes = database_v2.supabase.table("transacoes").select("*, categorias(nome)").eq("id_usuario", id_usuario).order("data_competencia", desc=True).execute().data
        cartoes = database_v2.supabase.table("cartoes").select("*").eq("id_usuario", id_usuario).execute().data
        dividas = database_v2.supabase.table("dividas").select("*").eq("id_usuario", id_usuario).execute().data
        metas = database_v2.supabase.table("metas").select("*, categorias(nome)").eq("id_usuario", id_usuario).execute().data
        
        return {
            "contas": contas,
            "cartoes": cartoes,
            "transacoes": transacoes,
            "dividas": dividas,
            "metas": metas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ai/chat")
async def chat_ia_financeira(dados: ChatRequest):
    if not database_v2.supabase:
        raise HTTPException(status_code=53, detail="Banco de dados Supabase indisponível.")
    if not gemini_key:
        raise HTTPException(status_code=53, detail="Serviço cognitivo Gemini indisponível.")
        
    try:
        tx_data = database_v2.supabase.table("transacoes").select("*, categorias(nome)").eq("id_usuario", dados.id_usuario).order("data_competencia", desc=True).limit(50).execute().data
        contas = database_v2.supabase.table("contas").select("*").eq("id_usuario", dados.id_usuario).execute().data
        cartoes = database_v2.supabase.table("cartoes").select("*").eq("id_usuario", dados.id_usuario).execute().data
        
        contexto_contas = "\n".join([f"- {c['nome']} ({c['tipo'].capitalize()}): Saldo R$ {float(c['saldo']):,.2f}" for c in contas])
        contexto_cartoes = "\n".join([f"- {c['nome']}: Limite R$ {float(c['limite']):,.2f}" for c in cartoes])
        
        contexto_transacoes = []
        for t in tx_data:
            cat_nome = t["categorias"]["nome"] if t.get("categorias") else "Outros"
            sinal = "+" if float(t["valor"]) > 0 else "-"
            contexto_transacoes.append(
                f"- {t['data_competencia']}: {t['descricao']} ({cat_nome}) | {sinal}R$ {abs(float(t['valor'])):,.2f}"
            )
        tx_str = "\n".join(contexto_transacoes)
        
        prompt_ia = (
            f"Você é a IA Cognitiva do FinBot 2.0, um assistente especializado em finanças pessoais.\n"
            f"Abaixo está o panorama financeiro do usuário em tempo real carregado diretamente do banco PostgreSQL:\n\n"
            f"💵 CONTAS BANCÁRIAS:\n{contexto_contas}\n\n"
            f"💳 CARTÕES DE CRÉDITO:\n{contexto_cartoes}\n\n"
            f"📜 ÚLTIMAS TRANSAÇÕES REGISTRADAS:\n{tx_str}\n\n"
            f"Instruções:\n"
            f"- Responda a pergunta do usuário baseando-se estritamente neste contexto.\n"
            f"- Caso ele queira saber sobre gastos específicos (ex: quanto gastou com comida), faça as contas mentalmente com base nas transações fornecidas e informe o total correto.\n"
            f"- Responda de forma clara, amigável, objetiva e no formato Markdown (português do Brasil).\n\n"
            f"Pergunta do Usuário: \"{dados.mensagem}\"\n"
            f"Resposta do FinBot IA:"
        )
        
        logger.info(f"Chamando Gemini para chat cognitivo... Usuário: {dados.id_usuario}")
        resposta = model.generate_content(prompt_ia)
        
        return {
            "status": "success",
            "resposta": resposta.text
        }
    except Exception as e:
        logger.error(f"Erro ao executar chat de IA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar consulta com a IA: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
