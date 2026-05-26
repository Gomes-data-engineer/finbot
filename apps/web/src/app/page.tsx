"use client";

import { useState, useEffect } from "react";
import { 
  Eye, 
  EyeOff, 
  TrendingUp, 
  TrendingDown, 
  CreditCard, 
  Sparkles, 
  Send, 
  Bot, 
  ArrowRight,
  Utensils,
  Car,
  Tv,
  Film,
  ShoppingBag,
  User,
  Users,
  CircleEllipsis,
  Home as HomeIcon
} from "lucide-react";

// Dados simulados de finanças compartilhadas do casal (Vitor + Mariana)
const MOCK_SHARED_DATA = {
  usuarios: [
    { nome: "Consolidado (Casal)", id: "all" },
    { nome: "Vitor", id: "vitor" },
    { nome: "Mariana", id: "mariana" }
  ],
  saldos: {
    all: 5350.22,
    vitor: 3493.82,
    mariana: 1856.40
  },
  renda: {
    all: 7700.00,
    vitor: 5500.00,
    mariana: 2200.00
  },
  gastos: {
    all: 2349.78,
    vitor: 2006.18,
    mariana: 343.60
  },
  faturaNubank: {
    all: 1840.50,
    vitor: 1240.50,
    mariana: 600.00
  },
  metas: [
    { titulo: "Reserva de Emergência", categoria: "Geral", alvo: 10000.00, atual: 5500.00, progressoPct: 55, icone: "🛡️" },
    { titulo: "Limite de Alimentação", categoria: "Mensal", alvo: 450.00, atual: 399.40, progressoPct: 88, icone: "🍔" }
  ],
  transacoes: [
    { id: "1", descricao: "McDonalds", categoria: "Alimentação", valor: -45.90, data: "Hoje", usuario: "Vitor", icone: Utensils, corBg: "bg-rose-500/10 text-rose-400" },
    { id: "2", descricao: "Uber Viagem", categoria: "Transporte", valor: -18.20, data: "Hoje", usuario: "Vitor", icone: Car, corBg: "bg-blue-500/10 text-blue-400" },
    { id: "3", descricao: "Freelance Design", categoria: "Renda", valor: 2200.00, data: "Ontem", usuario: "Mariana", icone: TrendingUp, corBg: "bg-emerald-500/10 text-emerald-400" },
    { id: "4", descricao: "Salário Principal", categoria: "Renda", valor: 5500.00, data: "Ontem", usuario: "Vitor", icone: TrendingUp, corBg: "bg-emerald-500/10 text-emerald-400" },
    { id: "5", descricao: "Netflix Mensal", categoria: "Fixas", valor: -55.90, data: "24 Mai", usuario: "Mariana", icone: Film, corBg: "bg-purple-500/10 text-purple-400" },
    { id: "6", descricao: "Supermercado Pão de Açúcar", categoria: "Alimentação", valor: -320.40, data: "22 Mai", usuario: "Vitor", icone: ShoppingBag, corBg: "bg-rose-500/10 text-rose-400" }
  ]
};

export default function Home() {
  const [showBalance, setShowBalance] = useState(true);
  const [selectedUser, setSelectedUser] = useState("all"); // 'all' | UUID
  const [users, setUsers] = useState<any[]>([]);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);

  // Salva estado de usuário e API no localStorage para compartilhamento entre páginas Next.js
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("selectedUser", selectedUser);
      localStorage.setItem("apiOnline", String(apiOnline));
      if (users.length > 0) {
        localStorage.setItem("users", JSON.stringify(users));
      }
    }
  }, [selectedUser, apiOnline, users]);

  // Estados para o Chat com a IA Financeira
  const [chatMessage, setChatMessage] = useState("");
  const [chatHistory, setChatHistory] = useState([
    { role: "assistant", content: "Olá! Sou o FinBot IA. Consigo ler as contas tanto do Vitor quanto da Mariana no banco de dados. Pergunte-me sobre salários recebidos, faturas ou o progresso das suas metas de gastos!" }
  ]);
  const [isTyping, setIsTyping] = useState(false);

  // 1. Busca usuários da API Gateway
  useEffect(() => {
    async function loadUsers() {
      try {
        const res = await fetch("http://localhost:8000/api/v1/usuarios");
        if (res.ok) {
          const data = await res.json();
          setUsers(data);
          setApiOnline(true);
        } else {
          setApiOnline(false);
        }
      } catch (err) {
        console.warn("API Gateway offline. Usando dados fictícios.", err);
        setApiOnline(false);
      }
    }
    loadUsers();
  }, []);

  // 2. Busca dados consolidados do usuário selecionado (ou junta todos se 'all')
  useEffect(() => {
    if (!apiOnline) return;

    async function loadDashboardData() {
      setLoading(true);
      try {
        if (selectedUser === "all") {
          if (users.length === 0) {
            setDashboardData({ contas: [], cartoes: [], transacoes: [], dividas: [] });
            return;
          }
          const promises = users.map(u => 
            fetch(`http://localhost:8000/api/v1/dashboard/consolidado/${u.id}`)
              .then(r => r.ok ? r.json() : { contas: [], cartoes: [], transacoes: [], dividas: [] })
          );
          const results = await Promise.all(promises);
          
          const combined = {
            contas: results.flatMap(r => r.contas || []),
            cartoes: results.flatMap(r => r.cartoes || []),
            transacoes: results.flatMap(r => r.transacoes || []),
            dividas: results.flatMap(r => r.dividas || [])
          };
          setDashboardData(combined);
        } else {
          const res = await fetch(`http://localhost:8000/api/v1/dashboard/consolidado/${selectedUser}`);
          if (res.ok) {
            const data = await res.json();
            setDashboardData(data);
          }
        }
      } catch (err) {
        console.error("Erro ao carregar dados consolidados:", err);
      } finally {
        setLoading(false);
      }
    }

    loadDashboardData();
  }, [selectedUser, users, apiOnline]);

  // Seletor de usuários dinâmico
  const displayUsers = apiOnline
    ? [{ nome: "Consolidado (Todos)", id: "all" }, ...users.map(u => ({ nome: u.nome, id: u.id }))]
    : MOCK_SHARED_DATA.usuarios;

  // Cálculos de saldo, receita e fatura reais vs mockados
  const currentSaldo = apiOnline && dashboardData
    ? (dashboardData.contas?.reduce((acc: number, c: any) => acc + parseFloat(c.saldo), 0) || 0)
    : MOCK_SHARED_DATA.saldos[selectedUser as keyof typeof MOCK_SHARED_DATA.saldos] || 0;

  const currentRenda = apiOnline && dashboardData
    ? (dashboardData.transacoes?.filter((t: any) => parseFloat(t.valor) > 0).reduce((acc: number, t: any) => acc + parseFloat(t.valor), 0) || 0)
    : MOCK_SHARED_DATA.renda[selectedUser as keyof typeof MOCK_SHARED_DATA.renda] || 0;

  const currentFatura = apiOnline && dashboardData
    ? (dashboardData.transacoes?.filter((t: any) => t.id_fatura !== null && parseFloat(t.valor) < 0).reduce((acc: number, t: any) => acc + Math.abs(parseFloat(t.valor)), 0) || 0)
    : MOCK_SHARED_DATA.faturaNubank[selectedUser as keyof typeof MOCK_SHARED_DATA.faturaNubank] || 0;

  // Mapeamento e formatação de transações para o extrato recente
  const displayTransacoes = apiOnline && dashboardData
    ? dashboardData.transacoes.map((t: any) => {
        const categoryName = t.categorias?.nome || "Outros";
        const isIncome = parseFloat(t.valor) > 0;
        
        let icon = CircleEllipsis;
        let corBg = "bg-slate-500/10 text-slate-400";
        
        if (categoryName === "Alimentação") {
          icon = Utensils;
          corBg = "bg-rose-500/10 text-rose-400";
        } else if (categoryName === "Transporte") {
          icon = Car;
          corBg = "bg-blue-500/10 text-blue-400";
        } else if (categoryName === "Lazer") {
          icon = Film;
          corBg = "bg-amber-500/10 text-amber-400";
        } else if (categoryName === "Renda") {
          icon = TrendingUp;
          corBg = "bg-emerald-500/10 text-emerald-400";
        } else if (categoryName === "Fixas") {
          icon = HomeIcon;
          corBg = "bg-purple-500/10 text-purple-400";
        } else if (categoryName === "Cartão") {
          icon = CreditCard;
          corBg = "bg-violet-500/10 text-violet-400";
        }
        
        return {
          id: t.id,
          descricao: t.descricao,
          categoria: categoryName,
          valor: parseFloat(t.valor),
          data: new Date(t.data_competencia).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
          usuario: users.find(u => u.id === t.id_usuario)?.nome || "Usuário",
          icone: icon,
          corBg: corBg
        };
      })
    : MOCK_SHARED_DATA.transacoes.map(t => {
        // Resolve a string de ícones do mockup antigo para o componente real
        let icon = CircleEllipsis;
        if (t.descricao.toLowerCase().includes("mcdonalds") || t.descricao.toLowerCase().includes("mercado")) icon = Utensils;
        else if (t.descricao.toLowerCase().includes("uber")) icon = Car;
        else if (t.descricao.toLowerCase().includes("freelance") || t.descricao.toLowerCase().includes("salário")) icon = TrendingUp;
        else if (t.descricao.toLowerCase().includes("netflix")) icon = Film;
        return { ...t, icone: icon };
      });

  // Mapeamento e formatação de metas
  const displayMetas = apiOnline && dashboardData
    ? (dashboardData.metas || []).map((m: any) => {
        const alvo = parseFloat(m.valor_alvo) || 1;
        const atual = parseFloat(m.valor_atual) || 0;
        const progressoPct = Math.min(Math.round((atual / alvo) * 100), 100);
        const icone = m.tipo === "gasto" ? "🍔" : "🛡️";
        const categoria = m.tipo === "gasto" ? "Gasto Máximo" : "Economia/Reserva";
        return {
          titulo: m.titulo,
          categoria,
          alvo,
          atual,
          progressoPct,
          icone
        };
      })
    : MOCK_SHARED_DATA.metas;

  // Filtra transações pelo usuário selecionado se estiver usando dados simulados
  const transacoesExibidas = apiOnline
    ? displayTransacoes
    : displayTransacoes.filter((tx: any) => {
        if (selectedUser === "all") return true;
        return tx.usuario.toLowerCase() === selectedUser;
      });

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatMessage.trim()) return;

    const userMsg = { role: "user", content: chatMessage };
    setChatHistory((prev) => [...prev, userMsg]);
    const currentMsg = chatMessage;
    setChatMessage("");
    setIsTyping(true);

    if (apiOnline && users.length > 0) {
      try {
        const chatUserId = selectedUser === "all" ? users[0].id : selectedUser;
        const res = await fetch("http://localhost:8000/api/v1/ai/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            id_usuario: chatUserId,
            mensagem: currentMsg
          })
        });
        if (res.ok) {
          const data = await res.json();
          setChatHistory((prev) => [...prev, { role: "assistant", content: data.resposta }]);
        } else {
          setChatHistory((prev) => [...prev, { role: "assistant", content: "Erro ao processar consulta com o assistente do Gateway." }]);
        }
      } catch (err) {
        console.error(err);
        setChatHistory((prev) => [...prev, { role: "assistant", content: "Erro de conexão com o Gateway de IA." }]);
      } finally {
        setIsTyping(false);
      }
    } else {
      // Chat simulado local
      setTimeout(() => {
        let responseContent = "";
        const lower = currentMsg.toLowerCase();
        
        const vRenda = MOCK_SHARED_DATA.renda.vitor;
        const mRenda = MOCK_SHARED_DATA.renda.mariana;
        const totalRenda = MOCK_SHARED_DATA.renda.all;
        const metaAlimentacao = MOCK_SHARED_DATA.metas[1];

        if (lower.includes("salário") || lower.includes("renda") || lower.includes("quanto entrou")) {
          responseContent = `Neste mês, registramos um total de **R$ ${totalRenda.toLocaleString("pt-BR")}** em rendas:\n- **Vitor (Salário)**: R$ ${vRenda.toLocaleString("pt-BR")}\n- **Mariana (Freelance)**: R$ ${mRenda.toLocaleString("pt-BR")}\n\nAmbos os valores já estão refletidos no saldo da conta compartilhada.`;
        } else if (lower.includes("meta") || lower.includes("alimentação") || lower.includes("gasto")) {
          responseContent = `Vocês estão com a meta **${metaAlimentacao.titulo}** ativa. \n- **Valor Limite**: R$ ${metaAlimentacao.alvo.toFixed(2)}\n- **Gasto Atual**: R$ ${metaAlimentacao.atual.toFixed(2)} (**${metaAlimentacao.progressoPct}%** consumido).\n\n⚠️ **Aviso**: Restam apenas **R$ ${(metaAlimentacao.alvo - metaAlimentacao.atual).toFixed(2)}** de margem para compras de mercado/restaurantes este mês!`;
        } else if (lower.includes("reserva") || lower.includes("emergência")) {
          const reserva = MOCK_SHARED_DATA.metas[0];
          responseContent = `A **${reserva.titulo}** está atualmente em **R$ ${reserva.atual.toLocaleString("pt-BR")}** (Meta de R$ ${reserva.alvo.toLocaleString("pt-BR")}). \n\nVocê já alcançou **{55%}** do objetivo! Mantendo o ritmo médio de economias, restam aproximadamente **9 meses** para a conclusão total.`;
        } else if (lower.includes("vitor")) {
          responseContent = `Filtrando apenas o **Vitor**: \n- Receita: R$ ${vRenda.toLocaleString("pt-BR")}\n- Gastos individuais: R$ ${MOCK_SHARED_DATA.gastos.vitor.toLocaleString("pt-BR")}\n- Fatura no cartão: R$ ${MOCK_SHARED_DATA.faturaNubank.vitor.toLocaleString("pt-BR")}.`;
        } else if (lower.includes("mariana")) {
          responseContent = `Filtrando apenas a **Mariana**: \n- Receita: R$ ${mRenda.toLocaleString("pt-BR")}\n- Gastos individuais: R$ ${MOCK_SHARED_DATA.gastos.mariana.toLocaleString("pt-BR")}\n- Fatura no cartão: R$ ${MOCK_SHARED_DATA.faturaNubank.mariana.toLocaleString("pt-BR")}.`;
        } else {
          responseContent = `Consolidado atual do casal:\n- **Saldo Combinado**: R$ ${MOCK_SHARED_DATA.saldos.all.toLocaleString("pt-BR")}\n- **Renda total**: R$ ${totalRenda.toLocaleString("pt-BR")}\n- **Fatura do cartão**: R$ ${MOCK_SHARED_DATA.faturaNubank.all.toLocaleString("pt-BR")}.\n\nSe precisar que eu liste o extrato de um usuário específico, basta pedir.`;
        }

        setChatHistory((prev) => [...prev, { role: "assistant", content: responseContent }]);
        setIsTyping(false);
      }, 1000);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5 animate-in fade-in duration-300 relative">
      
      {/* Luzes difusas de fundo (Fintech Ambient) */}
      <div className="absolute top-[-100px] left-[10%] w-[300px] h-[300px] rounded-full radial-glow-1 pointer-events-none -z-10"></div>

      {/* BARRA DE FILTRO DE USUÁRIO (MOBILE-FIRST SELETOR DE CASAL) */}
      <div className="flex justify-between items-center bg-[#0A0D18] border border-white/5 p-3 rounded-2xl">
        <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5 text-violet-400" /> Perfil de Visualização
        </span>
        <div className="flex gap-1">
          {displayUsers.map(u => (
            <button
              key={u.id}
              onClick={() => setSelectedUser(u.id)}
              className={`px-3 py-1.5 rounded-xl text-[10px] font-bold transition-all ${
                selectedUser === u.id
                  ? "bg-violet-600 text-white shadow-md shadow-violet-600/20"
                  : "bg-slate-800/40 text-slate-400 hover:text-slate-200 border border-white/5"
              }`}
            >
              {u.nome}
            </button>
          ))}
        </div>
      </div>

      {/* HEADER DE SALDO PRINCIPAL (ESTILO NUBANK ULTRAVIOLETA) */}
      <section className="glass-card rounded-2xl p-5 relative overflow-hidden border border-white/5">
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Saldo disponível {selectedUser === "all" ? "(Todos)" : `(${displayUsers.find(u => u.id === selectedUser)?.nome})`}
              </span>
              <button 
                onClick={() => setShowBalance(!showBalance)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                {showBalance ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
              {showBalance ? `R$ ${currentSaldo.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : "••••••"}
            </h1>
          </div>
          
          <div className="flex gap-6 border-t sm:border-t-0 sm:border-l border-white/5 pt-4 sm:pt-0 sm:pl-6">
            <div>
              <span className="text-[10px] text-slate-400 block uppercase tracking-wider mb-0.5">Renda Recebida</span>
              <span className="text-emerald-400 text-sm font-extrabold flex items-center gap-1">
                <TrendingUp className="w-3.5 h-3.5" /> R$ {currentRenda.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 block uppercase tracking-wider mb-0.5">Gastos no Crédito</span>
              <span className="text-rose-400 text-sm font-extrabold flex items-center gap-1">
                <TrendingDown className="w-3.5 h-3.5" /> R$ {currentFatura.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* CORE GRID: CHAT COM IA & DETALHES DE CARTÃO */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        
        {/* LADO ESQUERDO: CHAT IA (2 COLS) */}
        <div className="lg:col-span-2 space-y-5">
          
          {/* CHAT IA CONECTADO AO POSTGRES */}
          <div className="glass-card rounded-2xl border border-white/5 flex flex-col h-[350px] overflow-hidden">
            <div className="p-4 border-b border-white/5 bg-[#0A0D18] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="w-4.5 h-4.5 text-violet-400" />
                <span className="font-bold text-xs text-slate-100">Assistente IA Financeiro</span>
              </div>
              <span className="text-[9px] bg-violet-950/50 text-violet-300 px-2 py-0.5 rounded-full border border-violet-800/30 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" /> {apiOnline ? "Conexão de Banco Real" : "Modo Simulação"}
              </span>
            </div>

            {/* Histórico do Chat */}
            <div className="flex-grow p-4 overflow-y-auto space-y-3 scrollbar-none text-xs">
              {chatHistory.map((msg, idx) => (
                <div 
                  key={idx} 
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 leading-relaxed ${
                    msg.role === "user" 
                      ? "bg-violet-600 text-white rounded-tr-none" 
                      : "bg-[#1E293B]/70 border border-white/5 text-slate-200 rounded-tl-none"
                  }`}>
                    {msg.content}
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-[#1E293B]/70 border border-white/5 text-slate-400 rounded-2xl rounded-tl-none px-3.5 py-2.5 text-[11px] animate-pulse">
                    FinBot está analisando a fatura e o banco de dados...
                  </div>
                </div>
              )}
            </div>

            {/* Input Form */}
            <form onSubmit={handleSendMessage} className="p-3 bg-[#0A0D18] border-t border-white/5 flex gap-2">
              <input 
                type="text" 
                placeholder="Pergunte sobre salários, quem gastou mais, faturas ou limites de metas..." 
                value={chatMessage}
                onChange={(e) => setChatMessage(e.target.value)}
                className="flex-grow bg-[#1E293B]/60 border border-white/5 rounded-xl px-3.5 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 text-slate-100 placeholder-slate-500"
              />
              <button 
                type="submit" 
                className="bg-violet-600 hover:bg-violet-500 text-white p-2.5 rounded-xl transition-colors shrink-0"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          </div>

        </div>

        {/* LADO DIREITO: ÚLTIMAS TRANSAÇÕES DA CONTA (1 COL) */}
        <div className="space-y-4">
          <h3 className="font-bold text-xs uppercase tracking-widest text-slate-400">Extrato Recente</h3>
          
          <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
            {transacoesExibidas.length === 0 ? (
              <p className="text-[10px] text-slate-500 text-center py-6">Nenhum lançamento encontrado para este perfil.</p>
            ) : (
              transacoesExibidas.slice(0, 6).map((tx: any) => {
                const IconComponent = tx.icone;
                const isIncome = tx.valor > 0;
                return (
                  <div 
                    key={tx.id} 
                    className="flex items-center justify-between p-3.5 bg-[#1E293B]/25 border border-white/5 rounded-2xl hover:bg-[#1E293B]/50 transition-all duration-300"
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-8.5 h-8.5 rounded-lg flex items-center justify-center ${tx.corBg}`}>
                        <IconComponent className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <p className="font-bold text-xs text-slate-100">{tx.descricao}</p>
                          <span className="text-[8px] bg-slate-800 text-slate-400 px-1.5 py-0.2 rounded border border-slate-700">
                            {tx.usuario}
                          </span>
                        </div>
                        <span className="text-[9px] text-slate-500">{tx.categoria} • {tx.data}</span>
                      </div>
                    </div>
                    
                    <span className={`font-bold text-xs ${isIncome ? "text-emerald-400" : "text-slate-200"}`}>
                      {isIncome ? "+" : "-"} R$ {Math.abs(tx.valor).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>

      </div>

      {/* METAS INTEGRADAS COM INSIGHTS */}
      <section className="space-y-3">
        <h3 className="font-bold text-xs uppercase tracking-widest text-slate-400">Objetivos Financeiros</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayMetas.length > 0 ? (
            displayMetas.map((meta, idx) => (
              <div key={idx} className="glass-card rounded-2xl p-4 border border-white/5 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-lg">{meta.icone}</span>
                  <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">{meta.categoria}</span>
                </div>
                <div>
                  <h4 className="font-bold text-xs text-slate-100">{meta.titulo}</h4>
                  <div className="flex justify-between text-[9px] text-slate-400 mt-1">
                    <span>Progresso: {meta.progressoPct}%</span>
                    <span>R$ {meta.atual.toLocaleString("pt-BR", { minimumFractionDigits: 2 })} / R$ {meta.alvo.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-1">
                  <div 
                    className={`h-1 rounded-full ${meta.titulo.toLowerCase().includes("limite") || meta.categoria.toLowerCase().includes("gasto") ? "bg-rose-500" : "bg-emerald-500"}`} 
                    style={{ width: `${meta.progressoPct}%` }}
                  ></div>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full text-center py-8 text-slate-500 text-xs border border-dashed border-white/5 rounded-2xl">
              Nenhum objetivo financeiro cadastrado para este usuário.
            </div>
          )}
        </div>
      </section>

    </div>
  );
}
