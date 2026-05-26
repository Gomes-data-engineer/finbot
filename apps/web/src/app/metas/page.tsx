"use client";

import { useState, useEffect } from "react";
import { 
  Shield, 
  Plane, 
  Utensils, 
  Target, 
  TrendingUp, 
  AlertCircle 
} from "lucide-react";

const MOCK_GOALS = [
  {
    id: "goal-1",
    titulo: "Reserva de Emergência",
    categoria: "Economia",
    alvo: 10000.00,
    atual: 5500.00,
    dataLimite: "31 Dez 2026",
    icone: Shield,
    cor: "bg-emerald-500",
    corBorda: "border-emerald-500/20",
    corFundo: "bg-emerald-950/20",
    corIcon: "text-emerald-400 bg-emerald-500/10"
  },
  {
    id: "goal-2",
    titulo: "Viagem de Fim de Ano",
    categoria: "Sonho/Lazer",
    alvo: 5000.00,
    atual: 1500.00,
    dataLimite: "30 Nov 2026",
    icone: Plane,
    cor: "bg-violet-500",
    corBorda: "border-violet-500/20",
    corFundo: "bg-violet-950/20",
    corIcon: "text-violet-400 bg-violet-500/10"
  },
  {
    id: "goal-3",
    titulo: "Limite de Alimentação (Mensal)",
    categoria: "Gasto Máximo",
    alvo: 450.00,
    atual: 399.40,
    dataLimite: "Mensal",
    icone: Utensils,
    cor: "bg-rose-500",
    corBorda: "border-rose-500/20",
    corFundo: "bg-rose-950/20",
    corIcon: "text-rose-400 bg-rose-500/10"
  }
];

export default function Metas() {
  const [metas, setMetas] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const isApiOnline = localStorage.getItem("apiOnline") === "true";
    const selectedUser = localStorage.getItem("selectedUser") || "all";
    const usersRaw = localStorage.getItem("users");
    const users = usersRaw ? JSON.parse(usersRaw) : [];

    setApiOnline(isApiOnline);

    if (!isApiOnline) {
      setMetas(MOCK_GOALS);
      return;
    }

    async function loadMetasData() {
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

        const fetchedMetas = results.flatMap(r => r.metas || []);

        if (fetchedMetas.length === 0) {
          setMetas([]);
          return;
        }

        const formattedMetas = fetchedMetas.map((m: any) => {
          let icon = Target;
          let cor = "bg-violet-500";
          let corBorda = "border-violet-500/20";
          let corFundo = "bg-violet-950/20";
          let corIcon = "text-violet-400 bg-violet-500/10";

          if (m.tipo === "gasto") {
            icon = Utensils;
            cor = "bg-rose-500";
            corBorda = "border-rose-500/20";
            corFundo = "bg-rose-950/20";
            corIcon = "text-rose-400 bg-rose-500/10";
          } else if (m.tipo === "economia") {
            icon = Shield;
            cor = "bg-emerald-500";
            corBorda = "border-emerald-500/20";
            corFundo = "bg-emerald-950/20";
            corIcon = "text-emerald-400 bg-emerald-500/10";
          }

          return {
            id: m.id,
            titulo: m.titulo,
            categoria: m.tipo === "gasto" ? "Gasto Máximo" : "Economia/Reserva",
            alvo: parseFloat(m.valor_alvo),
            atual: parseFloat(m.valor_atual),
            dataLimite: m.data_limite ? new Date(m.data_limite).toLocaleDateString("pt-BR") : "Sem prazo",
            icone: icon,
            cor,
            corBorda,
            corFundo,
            corIcon
          };
        });

        setMetas(formattedMetas);

      } catch (err) {
        console.error("Erro ao buscar metas:", err);
        setMetas([]);
      } finally {
        setLoading(false);
      }
    }

    loadMetasData();
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-in fade-in duration-500 relative">
      
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-extrabold tracking-tight">Metas e Objetivos</h1>
          <p className="text-[11px] text-slate-400">
            {apiOnline ? "Acompanhamento real de metas financeiras do banco PostgreSQL" : "Acompanhamento visual de reservas financeiras e limites de gastos (Simulado)"}
          </p>
        </div>
        {loading && <span className="text-[10px] bg-slate-800 text-slate-400 px-3 py-1 rounded-full border border-slate-700">Atualizando metas...</span>}
      </div>

      {/* LISTA DE METAS */}
      <div className="space-y-4">
        {metas.length > 0 ? (
          metas.map((meta) => {
            const pct = Math.min(Math.round((meta.atual / meta.alvo) * 100), 100);
            const IconComponent = meta.icone;
            
            return (
              <div 
                key={meta.id} 
                className={`glass-card rounded-2xl p-5 border ${meta.corBorda} relative overflow-hidden`}
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${meta.corIcon}`}>
                      <IconComponent className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-extrabold text-sm text-slate-100">{meta.titulo}</h3>
                      <span className="text-[10px] text-slate-400">{meta.categoria}</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-semibold text-slate-400">Prazo: {meta.dataLimite}</span>
                </div>

                {/* BARRA DE PROGRESSO */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[10px] text-slate-400">
                    <span>Progresso: {pct}%</span>
                    <span>R$ {meta.atual.toLocaleString("pt-BR", { minimumFractionDigits: 2 })} de R$ {meta.alvo.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</span>
                  </div>
                  
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-1000 ${meta.cor}`} 
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>
                </div>

                {/* INSIGHT DE VELOCIDADE DA META */}
                <div className={`mt-3 p-3 rounded-xl text-[10px] text-slate-300 ${meta.corFundo}`}>
                  {meta.categoria === "Gasto Máximo" ? (
                    meta.atual > meta.alvo * 0.9 ? (
                      <span className="text-rose-400 font-bold flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5" /> Atenção: Você já ultrapassou ou está muito próximo do limite mensal!
                      </span>
                    ) : (
                      <span>🟢 Gastos dentro do limite estipulado. Margem de R$ {(meta.alvo - meta.atual).toLocaleString("pt-BR", { minimumFractionDigits: 2 })} restantes.</span>
                    )
                  ) : (
                    <span className="flex items-center gap-1.5">
                      <TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> **Projeção IA**: Mantendo economias regulares, você está se aproximando do objetivo!
                    </span>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <div className="glass-card rounded-2xl p-8 border border-white/5 text-center space-y-2">
            <span className="text-3xl block">🎯</span>
            <h3 className="font-extrabold text-sm text-slate-100">Nenhum objetivo cadastrado</h3>
            <p className="text-[10px] text-slate-400 max-w-sm mx-auto">
              Você ainda não tem metas ou limites configurados. Use o bot do Telegram para cadastrar uma meta ou insira diretamente no banco de dados Supabase!
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
