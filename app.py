import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from database import buscar_transacoes_completas, buscar_dividas_completas, buscar_todos_usuarios, obter_todas_categorias
import config

# Configurações de layout do Streamlit
st.set_page_config(
    page_title="FinBot Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS customizada para visual premium
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

/* Sobrescreve fonte padrão */
html, body, [class*="css"], .stText, .stMarkdown {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Estilização dos blocos de métricas */
.metric-container {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    color: white;
    padding: 24px;
    border-radius: 16px;
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1);
    border: 1px solid #334155;
    text-align: center;
    transition: transform 0.2s ease-in-out;
}
.metric-container:hover {
    transform: translateY(-4px);
}
.metric-title {
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #f8fafc;
}
.text-positive { color: #10b981 !important; }
.text-negative { color: #f43f5e !important; }
.text-warning { color: #f59e0b !important; }

/* Estilização geral dos containers */
.stCard {
    background-color: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    border: 1px solid #f1f5f9;
}
</style>
""", unsafe_allow_html=True)


# ==================== DATA MOCK GENERATOR ====================
def gerar_dados_simulados():
    """Gera dados de teste caso o banco esteja vazio ou não configurado."""
    hoje = datetime.date.today()
    mes_atual = hoje.replace(day=1)
    
    # 1. Usuários simulados
    usuarios = [
        {"id_telegram": 111, "nome": "Vitor (Você)"},
        {"id_telegram": 222, "nome": "Mariana (Compartilhado)"}
    ]
    
    # 2. Categorias simuladas
    categorias = [
        {"id": 1, "nome": "Alimentação", "meta_mensal": 450.00},
        {"id": 2, "nome": "Transporte", "meta_mensal": 200.00},
        {"id": 3, "nome": "Lazer", "meta_mensal": 300.00},
        {"id": 4, "nome": "Cartão", "meta_mensal": None},
        {"id": 5, "nome": "Fixas", "meta_mensal": 1800.00},
        {"id": 6, "nome": "Renda", "meta_mensal": None},
        {"id": 7, "nome": "Outros", "meta_mensal": None}
    ]
    
    # 3. Transações simuladas
    transacoes = [
        # Renda Vitor
        {"id_usuario": 111, "usuarios": {"nome": "Vitor (Você)"}, "id_categoria": 6, "categorias": {"nome": "Renda", "meta_mensal": None}, "descricao": "Salário Principal", "valor": 5500.00, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        # Renda Mariana
        {"id_usuario": 222, "usuarios": {"nome": "Mariana (Compartilhado)"}, "id_categoria": 6, "categorias": {"nome": "Renda", "meta_mensal": None}, "descricao": "Freelance Design", "valor": 2200.00, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        
        # Aluguel (Fixas)
        {"id_usuario": 111, "usuarios": {"nome": "Vitor (Você)"}, "id_categoria": 5, "categorias": {"nome": "Fixas", "meta_mensal": 1800.00}, "descricao": "Aluguel & Condomínio", "valor": -1500.00, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        # Energia (Fixas)
        {"id_usuario": 222, "usuarios": {"nome": "Mariana (Compartilhado)"}, "id_categoria": 5, "categorias": {"nome": "Fixas", "meta_mensal": 1800.00}, "descricao": "Conta de Energia", "valor": -180.00, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        
        # Alimentação Vitor
        {"id_usuario": 111, "usuarios": {"nome": "Vitor (Você)"}, "id_categoria": 1, "categorias": {"nome": "Alimentação", "meta_mensal": 450.00}, "descricao": "Supermercado Carrefour", "valor": -320.50, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        {"id_usuario": 111, "usuarios": {"nome": "Vitor (Você)"}, "id_categoria": 1, "categorias": {"nome": "Alimentação", "meta_mensal": 450.00}, "descricao": "Jantar Outback", "valor": -145.00, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        
        # Alimentação Mariana
        {"id_usuario": 222, "usuarios": {"nome": "Mariana (Compartilhado)"}, "id_categoria": 1, "categorias": {"nome": "Alimentação", "meta_mensal": 450.00}, "descricao": "Ifood Pizza", "valor": -78.90, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        
        # Transporte (Uber/Combustível)
        {"id_usuario": 111, "usuarios": {"nome": "Vitor (Você)"}, "id_categoria": 2, "categorias": {"nome": "Transporte", "meta_mensal": 200.00}, "descricao": "Posto Shell Gasolina", "valor": -120.00, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        {"id_usuario": 222, "usuarios": {"nome": "Mariana (Compartilhado)"}, "id_categoria": 2, "categorias": {"nome": "Transporte", "meta_mensal": 200.00}, "descricao": "Uber Centro", "valor": -35.20, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        
        # Lazer
        {"id_usuario": 111, "usuarios": {"nome": "Vitor (Você)"}, "id_categoria": 3, "categorias": {"nome": "Lazer", "meta_mensal": 300.00}, "descricao": "Ingressos Cinema", "valor": -60.00, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
        {"id_usuario": 222, "usuarios": {"nome": "Mariana (Compartilhado)"}, "id_categoria": 3, "categorias": {"nome": "Lazer", "meta_mensal": 300.00}, "descricao": "Churrasco com Amigos", "valor": -110.00, "data_competencia": mes_atual.isoformat(), "parcelado": False, "parcela_atual": None, "total_parcelas": None},
    ]
    
    # Parcelamento da TV (1200 / 4x = 300 por mês)
    for i in range(1, 5):
        comp = mes_atual
        # Adiciona meses
        month = comp.month - 1 + (i - 1)
        year = comp.year + month // 12
        month = month % 12 + 1
        comp_date = datetime.date(year, month, 10)
        
        transacoes.append({
            "id_usuario": 111,
            "usuarios": {"nome": "Vitor (Você)"},
            "id_categoria": 4,
            "categorias": {"nome": "Cartão", "meta_mensal": None},
            "descricao": f"Smart TV ({i}/4)",
            "valor": -300.00,
            "data_competencia": comp_date.isoformat(),
            "parcelado": True,
            "parcela_atual": i,
            "total_parcelas": 4
        })

    # Parcelamento do Notebook Mariana (1800 / 3x = 600 por mês)
    for i in range(1, 4):
        comp = mes_atual
        # Adiciona meses
        month = comp.month - 1 + (i - 1)
        year = comp.year + month // 12
        month = month % 12 + 1
        comp_date = datetime.date(year, month, 15)
        
        transacoes.append({
            "id_usuario": 222,
            "usuarios": {"nome": "Mariana (Compartilhado)"},
            "id_categoria": 4,
            "categorias": {"nome": "Cartão", "meta_mensal": None},
            "descricao": f"Notebook Trabalho ({i}/3)",
            "valor": -600.00,
            "data_competencia": comp_date.isoformat(),
            "parcelado": True,
            "parcela_atual": i,
            "total_parcelas": 3
        })

    # 4. Dívidas simuladas
    dividas = [
        {"id": "div-1", "id_usuario": 111, "usuarios": {"nome": "Vitor (Você)"}, "credor": "Banco Itaú (Empréstimo)", "valor_total": 5000.00, "valor_pago": 1500.00, "status": "pendente"},
        {"id": "div-2", "id_usuario": 222, "usuarios": {"nome": "Mariana (Compartilhado)"}, "credor": "Carlos (Academia)", "valor_total": 120.00, "valor_pago": 120.00, "status": "pago"},
        {"id": "div-3", "id_usuario": 111, "usuarios": {"nome": "Vitor (Você)"}, "credor": "Mãe (Conserto Carro)", "valor_total": 800.00, "valor_pago": 0.00, "status": "pendente"}
    ]
    
    return usuarios, categorias, transacoes, dividas


# ==================== CARREGAMENTO DE DADOS ====================
# Verifica se o Supabase está configurado corretamente
supabase_configurado = config.TELEGRAM_TOKEN and config.SUPABASE_URL and config.SUPABASE_KEY and config.GEMINI_API_KEY

if not supabase_configurado:
    st.sidebar.warning("⚠️ Chaves de API não configuradas no `.env`. Usando dados simulados.")
    modo_simulado = True
else:
    modo_simulado = st.sidebar.checkbox("Visualizar dados simulados (Test Drive)", value=False)

# Carrega os dados reais do Supabase ou mock
if modo_simulado:
    usuarios_raw, categorias_raw, transacoes_raw, dividas_raw = gerar_dados_simulados()
else:
    try:
        usuarios_raw = buscar_todos_usuarios()
        transacoes_raw = buscar_transacoes_completas()
        dividas_raw = buscar_dividas_completas()
        categorias_raw = obter_todas_categorias()
        
        # Se a base de dados estiver vazia, ativa dados simulados para não ficar em branco
        if not transacoes_raw:
            st.warning("📊 O banco de dados do Supabase está conectado, mas vazio! Exibindo dados de simulação.")
            usuarios_raw, categorias_raw, transacoes_raw, dividas_raw = gerar_dados_simulados()
            modo_simulado = True
    except Exception as e:
        st.error(f"Erro ao buscar dados do Supabase: {str(e)}. Carregando dados de simulação.")
        usuarios_raw, categorias_raw, transacoes_raw, dividas_raw = gerar_dados_simulados()
        modo_simulado = True

# Convertendo para DataFrames para manipulação com Pandas
df_transacoes = pd.DataFrame()
df_dividas = pd.DataFrame()

if transacoes_raw:
    # Trata dados para normalizar o JSON aninhado retornado do Supabase
    df_transacoes = pd.json_normalize(transacoes_raw)
    # Renomeia colunas do normalizamento para ficar limpo
    df_transacoes.rename(columns={
        "categorias.nome": "categoria_nome",
        "categorias.meta_mensal": "categoria_meta",
        "usuarios.nome": "usuario_nome"
    }, inplace=True)
    df_transacoes["data_competencia"] = pd.to_datetime(df_transacoes["data_competencia"]).dt.date
    df_transacoes["valor"] = df_transacoes["valor"].astype(float)

if dividas_raw:
    df_dividas = pd.json_normalize(dividas_raw)
    df_dividas.rename(columns={
        "usuarios.nome": "usuario_nome"
    }, inplace=True)
    df_dividas["valor_total"] = df_dividas["valor_total"].astype(float)
    df_dividas["valor_pago"] = df_dividas["valor_pago"].astype(float)


# ==================== FILTROS E SIDEBAR ====================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4341/4341764.png", width=80)
st.sidebar.title("FinBot Control")

# Filtro de Usuário (Multi-usuário)
lista_usuarios = ["Todos os Usuários"]
if usuarios_raw:
    lista_usuarios.extend([u["nome"] for u in usuarios_raw])
    
usuario_selecionado = st.sidebar.selectbox("Filtrar por Usuário", lista_usuarios)

# Filtro de Mês/Ano Competência
if not df_transacoes.empty:
    df_transacoes["ano_mes"] = pd.to_datetime(df_transacoes["data_competencia"]).dt.to_period('M')
    lista_meses = sorted(df_transacoes["ano_mes"].unique().astype(str), reverse=True)
    mes_selecionado = st.sidebar.selectbox("Mês de Competência", lista_meses)
else:
    mes_selecionado = datetime.date.today().strftime("%Y-%m")

# Aplica o filtro de Usuário
if usuario_selecionado != "Todos os Usuários":
    if not df_transacoes.empty:
        df_transacoes = df_transacoes[df_transacoes["usuario_nome"] == usuario_selecionado]
    if not df_dividas.empty:
        df_dividas = df_dividas[df_dividas["usuario_nome"] == usuario_selecionado]

# Filtra dados para o mês selecionado (para KPIs e gráficos mensais)
df_mes_atual = pd.DataFrame()
if not df_transacoes.empty:
    df_mes_atual = df_transacoes[df_transacoes["ano_mes"].astype(str) == mes_selecionado]


# ==================== CÁLCULO DE KPIs (MÊS SELECIONADO) ====================
renda_mes = 0.0
gastos_mes = 0.0
fatura_proximo_mes = 0.0

if not df_mes_atual.empty:
    renda_mes = df_mes_atual[df_mes_atual["valor"] > 0]["valor"].sum()
    gastos_mes = df_mes_atual[df_mes_atual["valor"] < 0]["valor"].sum()

saldo_atual = renda_mes + gastos_mes # gastos_mes já é negativo

# Calcula projeção da fatura do cartão para o próximo mês
# Filtra transações onde parcelado = True e a competência é o próximo mês do selecionado
if not df_transacoes.empty:
    mes_datetime = datetime.datetime.strptime(mes_selecionado, "%Y-%m")
    # Adiciona 1 mês
    if mes_datetime.month == 12:
        prox_mes = datetime.datetime(mes_datetime.year + 1, 1, 1)
    else:
        prox_mes = datetime.datetime(mes_datetime.year, mes_datetime.month + 1, 1)
        
    fatura_proximo_mes = abs(df_transacoes[
        (df_transacoes["data_competencia"].apply(lambda d: d.year == prox_mes.year and d.month == prox_mes.month)) &
        (df_transacoes["valor"] < 0) & 
        (df_transacoes["parcelado"] == True)
    ]["valor"].sum())


# ==================== MAIN DASHBOARD LAYOUT ====================
st.title("📊 FinBot — Dashboard Financeiro Inteligente")
st.markdown(f"Visualizando dados de competência: **{mes_selecionado}** | Filtro: **{usuario_selecionado}**")

# Grid de KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    saldo_class = "text-positive" if saldo_atual >= 0 else "text-negative"
    st.markdown(
        f'<div class="metric-container">'
        f'  <div class="metric-title">Saldo Competência</div>'
        f'  <div class="metric-value {saldo_class}">R$ {saldo_atual:,.2f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f'<div class="metric-container">'
        f'  <div class="metric-title">Renda do Mês</div>'
        f'  <div class="metric-value text-positive">R$ {renda_mes:,.2f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f'<div class="metric-container">'
        f'  <div class="metric-title">Gastos do Mês</div>'
        f'  <div class="metric-value text-negative">R$ {abs(gastos_mes):,.2f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f'<div class="metric-container">'
        f'  <div class="metric-title">Fatura Cartão Projetada (Prox. Mês)</div>'
        f'  <div class="metric-value text-warning">R$ {fatura_proximo_mes:,.2f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# Linha 2: Cashflow e Categorias vs Metas
col_esquerda, col_direita = st.columns(2)

with col_esquerda:
    st.subheader("📈 Linha do Tempo: Entradas vs Saídas")
    if not df_transacoes.empty:
        # Agrupa por dia para montar o fluxo de caixa
        df_fluxo = df_transacoes[df_transacoes["ano_mes"].astype(str) == mes_selecionado].copy()
        
        if not df_fluxo.empty:
            df_fluxo["tipo_label"] = df_fluxo["valor"].apply(lambda v: "Entrada" if v > 0 else "Saída")
            df_fluxo["valor_absoluto"] = df_fluxo["valor"].abs()
            df_grouped = df_fluxo.groupby(["data_competencia", "tipo_label"])["valor_absoluto"].sum().reset_index()
            
            fig_cashflow = px.line(
                df_grouped,
                x="data_competencia",
                y="valor_absoluto",
                color="tipo_label",
                color_discrete_map={"Entrada": "#10b981", "Saída": "#f43f5e"},
                labels={"valor_absoluto": "Valor (R$)", "data_competencia": "Data", "tipo_label": "Tipo"},
                markers=True,
                template="plotly_white"
            )
            fig_cashflow.update_layout(
                margin=dict(l=20, r=20, t=10, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_cashflow, use_container_width=True)
        else:
            st.info("Sem transações registradas no mês selecionado.")
    else:
        st.info("Sem dados de transações disponíveis.")

with col_direita:
    st.subheader("🎯 Gastos por Categoria vs Metas")
    if not df_mes_atual.empty:
        # Despesas do mês
        df_despesas = df_mes_atual[df_mes_atual["valor"] < 0].copy()
        df_despesas["valor_absoluto"] = df_despesas["valor"].abs()
        
        if not df_despesas.empty:
            # Agrupa por categoria
            df_cat = df_despesas.groupby("categoria_nome").agg(
                gasto_real=("valor_absoluto", "sum"),
                meta=("categoria_meta", "first")
            ).reset_index()
            
            # Gráfico de barras comparando real vs meta
            fig_categoria = go.Figure()
            
            # Barras do Gasto Real
            fig_categoria.add_trace(go.Bar(
                x=df_cat["categoria_nome"],
                y=df_cat["gasto_real"],
                name="Gasto Real",
                marker_color="#3b82f6"
            ))
            
            # Adiciona indicadores de metas (se houver meta cadastrada)
            # Para ficar limpo, vamos adicionar marcadores lineares de meta
            metas_validas = df_cat.dropna(subset=["meta"])
            if not metas_validas.empty:
                fig_categoria.add_trace(go.Scatter(
                    x=metas_validas["categoria_nome"],
                    y=metas_validas["meta"],
                    name="Meta Mensal",
                    mode="markers",
                    marker=dict(symbol="line-ew-open", size=30, line=dict(width=4, color="#f43f5e"))
                ))
            
            fig_categoria.update_layout(
                barmode='group',
                template="plotly_white",
                margin=dict(l=20, r=20, t=10, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_categoria, use_container_width=True)
            
            # Alertas de metas ultrapassadas
            for idx, row in df_cat.iterrows():
                if row["meta"] and row["gasto_real"] > row["meta"]:
                    st.warning(
                        f"🚨 Limite Ultrapassado! Categoria **{row['categoria_nome']}** gastou "
                        f"**R$ {row['gasto_real']:,.2f}** (Meta: R$ {row['meta']:,.2f})"
                    )
        else:
            st.info("Nenhuma despesa lançada nesta competência.")
    else:
        st.info("Sem dados cadastrados.")

st.markdown("---")

# Linha 3: Projeção de Parcelas e Dívidas Ativas
col_parc, col_div = st.columns(2)

with col_parc:
    st.subheader("💳 Comprometimento Futuro (Parcelamentos)")
    if not df_transacoes.empty:
        # Filtra transações parceladas a partir do mês atual
        df_futuro = df_transacoes[
            (df_transacoes["parcelado"] == True) & 
            (df_transacoes["valor"] < 0)
        ].copy()
        
        if not df_futuro.empty:
            df_futuro["valor_absoluto"] = df_futuro["valor"].abs()
            # Ordena e agrupa por mês de competência futuro
            df_futuro["ano_mes_str"] = df_futuro["data_competencia"].apply(lambda d: d.strftime("%Y-%m"))
            df_grouped_futuro = df_futuro.groupby(["ano_mes_str", "descricao"])["valor_absoluto"].sum().reset_index()
            
            fig_parcelas = px.bar(
                df_grouped_futuro,
                x="ano_mes_str",
                y="valor_absoluto",
                color="descricao",
                title="Parcelas a Vencer por Mês",
                labels={"valor_absoluto": "Valor (R$)", "ano_mes_str": "Mês de Competência", "descricao": "Item"},
                template="plotly_white"
            )
            fig_parcelas.update_layout(
                barmode='stack',
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.3)
            )
            st.plotly_chart(fig_parcelas, use_container_width=True)
        else:
            st.info("Nenhuma compra parcelada em andamento.")
    else:
        st.info("Sem dados de transações.")

with col_div:
    st.subheader("🤝 Controle de Dívidas Ativas")
    if not df_dividas.empty:
        # Exibe uma tabela com o status das dívidas
        df_div_exibicao = df_dividas[[
            "usuario_nome", "credor", "valor_total", "valor_pago", "status"
        ]].copy()
        
        # Formata valores para R$
        df_div_exibicao["valor_total"] = df_div_exibicao["valor_total"].apply(lambda v: f"R$ {v:,.2f}")
        df_div_exibicao["valor_pago"] = df_div_exibicao["valor_pago"].apply(lambda v: f"R$ {v:,.2f}")
        
        # Mapeia status com cores/emojis
        df_div_exibicao["status"] = df_div_exibicao["status"].apply(lambda s: "🟢 Quitado" if s == "pago" else "🔴 Pendente")
        
        # Renomeia colunas para cabeçalho bonito
        df_div_exibicao.columns = ["Quem Deve", "Credor/Item", "Valor Total", "Valor Pago", "Situação"]
        
        st.dataframe(df_div_exibicao, use_container_width=True, hide_index=True)
        
        # Gráfico rápido de dividas pendentes vs pagas
        total_devedor = df_dividas[df_dividas["status"] == "pendente"]["valor_total"].sum() - df_dividas[df_dividas["status"] == "pendente"]["valor_pago"].sum()
        if total_devedor > 0:
            st.metric(label="Saldo devedor total acumulado", value=f"R$ {total_devedor:,.2f}")
    else:
        st.info("Parabéns! Nenhuma dívida ativa registrada.")
