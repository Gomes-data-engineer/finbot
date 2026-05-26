"use client";

import { useState, useEffect } from "react";
import { 
  Search, 
  Utensils, 
  Car, 
  Gamepad2, 
  CreditCard, 
  Home, 
  TrendingUp, 
  CircleEllipsis, 
  Film, 
  ShoppingBag,
  Sparkles
} from "lucide-react";

// Mapeamento dinâmico de categorias para componentes de ícones Lucide
const CATEGORY_ICONS: Record<string, any> = {
  "Alimentação": { icon: Utensils, bg: "bg-rose-500/10 text-rose-400" },
  "Transporte": { icon: Car, bg: "bg-blue-500/10 text-blue-400" },
  "Lazer": { icon: Gamepad2, bg: "bg-amber-500/10 text-amber-400" },
  "Cartão": { icon: CreditCard, bg: "bg-purple-500/10 text-purple-400" },
  "Fixas": { icon: Home, bg: "bg-teal-500/10 text-teal-400" },
  "Renda": { icon: TrendingUp, bg: "bg-emerald-500/10 text-emerald-400" },
  "Outros": { icon: CircleEllipsis, bg: "bg-slate-500/10 text-slate-400" }
};

const MOCK_TRANSACTIONS = [
  { id: "1", descricao: "McDonalds", categoria: "Alimentação", valor: -45.90, data: "Hoje", parcelado: false },
  { id: "2", descricao: "Uber Viagem", categoria: "Transporte", valor: -18.20, data: "Hoje", parcelado: false },
  { id: "3", descricao: "Supermercado Carrefour", categoria: "Alimentação", valor: -320.50, data: "Ontem", parcelado: false },
  { id: "4", descricao: "Pix Recebido (Salário)", categoria: "Renda", valor: 5500.00, data: "Ontem", parcelado: false },
  { id: "5", descricao: "Netflix Mensal", categoria: "Fixas", valor: -55.90, data: "24 Mai", parcelado: false },
  { id: "6", descricao: "Churrascaria Gauchão", categoria: "Alimentação", valor: -180.00, data: "24 Mai", parcelado: false },
  { id: "7", descricao: "Gasolina Shell", categoria: "Transporte", valor: -150.00, data: "22 Mai", parcelado: false },
  { id: "8", descricao: "Smart TV (1/4)", categoria: "Cartão", valor: -300.00, data: "22 Mai", parcelado: true }
];

function formatCompetenciaDate(dateStr: string) {
  const date = new Date(dateStr + "T00:00:00"); // Evita timezone shifts locais no parsed string
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  
  if (date.toDateString() === today.toDateString()) {
    return "Hoje";
  } else if (date.toDateString() === yesterday.toDateString()) {
    return "Ontem";
  } else {
    const label = date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
    return label.charAt(0).toUpperCase() + label.slice(1).replace(".", "");
  }
}

export default function Timeline() {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("Todas");
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);

  const categorias = ["Todas", "Alimentação", "Transporte", "Lazer", "Cartão", "Fixas", "Renda"];

  useEffect(() => {
    if (typeof window === "undefined") return;

    const isApiOnline = localStorage.getItem("apiOnline") === "true";
    const selectedUser = localStorage.getItem("selectedUser") || "all";
    const usersRaw = localStorage.getItem("users");
    const users = usersRaw ? JSON.parse(usersRaw) : [];

    setApiOnline(isApiOnline);

    if (!isApiOnline) {
      // Mapeia ícones mockados
      const mappedMocks = MOCK_TRANSACTIONS.map(tx => {
        let icon = CircleEllipsis;
        if (tx.categoria === "Alimentação") icon = Utensils;
        else if (tx.categoria === "Transporte") icon = Car;
        else if (tx.categoria === "Lazer") icon = Gamepad2;
        else if (tx.categoria === "Renda") icon = TrendingUp;
        else if (tx.categoria === "Fixas") icon = Home;
        else if (tx.categoria === "Cartão") icon = CreditCard;

        return {
          ...tx,
          icone: icon,
          corBg: CATEGORY_ICONS[tx.categoria]?.bg || CATEGORY_ICONS["Outros"].bg
        };
      });
      setTransactions(mappedMocks);
      return;
    }

    async function loadTimelineData() {
      setLoading(true);
      try {
        let results = [];
        if (selectedUser === "all") {
          if (users.length === 0) return;
          const promises = users.map((u: any) => 
            fetch(`http://localhost:8000/api/v1/dashboard/consolidado/${u.id}`)
              .then(r => r.ok ? r.json() : null)
          );
          results = (await Promise.all(promises)).filter(r => r !== null);
        } else {
          const res = await fetch(`http://localhost:8000/api/v1/dashboard/consolidado/${selectedUser}`);
          if (res.ok) {
            results = [await res.json()];
          }
        }

        const fetchedTransactions = results.flatMap(r => r.transacoes || []);

        const formatted = fetchedTransactions.map((t: any) => {
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
            icon = Gamepad2;
            corBg = "bg-amber-500/10 text-amber-400";
          } else if (categoryName === "Renda") {
            icon = TrendingUp;
            corBg = "bg-emerald-500/10 text-emerald-400";
          } else if (categoryName === "Fixas") {
            icon = Home;
            corBg = "bg-teal-500/10 text-teal-400";
          } else if (categoryName === "Cartão") {
            icon = CreditCard;
            corBg = "bg-purple-500/10 text-purple-400";
          }
          
          return {
            id: t.id,
            descricao: t.descricao,
            categoria: categoryName,
            valor: parseFloat(t.valor),
            data: formatCompetenciaDate(t.data_competencia),
            parcelado: t.id_parcelamento !== null,
            icone: icon,
            corBg
          };
        });

        setTransactions(formatted);

      } catch (err) {
        console.error("Erro ao carregar extrato:", err);
      } finally {
        setLoading(false);
      }
    }

    loadTimelineData();
  }, []);

  const filteredTransactions = transactions.filter(tx => {
    const matchesSearch = tx.descricao.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = selectedCategory === "Todas" || tx.categoria === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const datasUnicas = Array.from(new Set(filteredTransactions.map(tx => tx.data)));

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-in fade-in duration-500 relative">
      
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-extrabold tracking-tight">Extrato Conversacional</h1>
          <p className="text-[11px] text-slate-400">
            {apiOnline ? "Puxando extrato em tempo real do banco PostgreSQL" : "Histórico de lançamentos inseridos via texto, voz ou OCR de faturas PDF (Simulado)"}
          </p>
        </div>
        {loading && <span className="text-[10px] bg-slate-800 text-slate-400 px-3 py-1 rounded-full border border-slate-700">Buscando extrato...</span>}
      </div>

      {/* BARRA DE BUSCA E FILTROS */}
      <div className="space-y-3">
        <div className="relative">
          <input 
            type="text" 
            placeholder="Buscar lançamentos por descrição..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#1E293B]/60 border border-white/5 rounded-xl pl-10 pr-4 py-2.5 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 placeholder-slate-500 text-slate-100"
          />
          <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-500" />
        </div>

        {/* Categoria Pills */}
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          {categorias.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3.5 py-1.5 rounded-full text-[10px] font-semibold whitespace-nowrap transition-all border ${
                selectedCategory === cat 
                  ? "bg-violet-600 border-violet-500 text-white shadow-lg shadow-violet-600/20" 
                  : "bg-[#1E293B]/60 text-slate-400 hover:text-white border-white/5"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* EXTRATO AGRUPADO POR DIAS */}
      <div className="space-y-4">
        {datasUnicas.length > 0 ? (
          datasUnicas.map(data => (
            <div key={data} className="space-y-2">
              {/* Separador do Dia Sticky */}
              <div className="sticky top-[64px] bg-[#05070F]/90 py-1.5 z-10 border-b border-white/5">
                <span className="text-[10px] font-bold text-violet-400 tracking-widest uppercase">{data}</span>
              </div>

              {/* Lançamentos do Dia */}
              <div className="space-y-2">
                {filteredTransactions
                  .filter(tx => tx.data === data)
                  .map(tx => {
                    const IconComponent = tx.icone;
                    
                    return (
                      <div 
                        key={tx.id} 
                        className="flex items-center justify-between p-3 bg-[#1E293B]/20 border border-white/5 rounded-2xl hover:bg-[#1E293B]/50 transition-all"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`w-8.5 h-8.5 rounded-xl flex items-center justify-center ${tx.corBg}`}>
                            <IconComponent className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="font-bold text-xs text-slate-100">{tx.descricao}</p>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[8px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full border border-slate-700/50">
                                {tx.categoria}
                              </span>
                              {tx.parcelado && (
                                <span className="text-[8px] bg-violet-950/40 text-violet-300 px-2 py-0.5 rounded-full border border-violet-800/30 flex items-center gap-0.5">
                                  <Sparkles className="w-2.5 h-2.5" /> Fatura
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <span className={`font-bold text-xs ${tx.valor > 0 ? "text-emerald-400" : "text-rose-500"}`}>
                          {tx.valor > 0 ? "+" : "-"} R$ {Math.abs(tx.valor).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-12 text-slate-500 text-xs">
            <span className="text-2xl block mb-2">🔍</span>
            Nenhuma transação encontrada para os filtros ativos.
          </div>
        )}
      </div>
    </div>
  );
}
