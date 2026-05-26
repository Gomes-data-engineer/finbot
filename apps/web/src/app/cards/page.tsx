"use client";

import { useState, useEffect } from "react";

const MOCK_CARDS = [
  {
    id: "card-1",
    nome: "Nubank Ultravioleta",
    limite: 10000.00,
    utilizado: 1840.50,
    diaFechamento: 5,
    diaVencimento: 12,
    bandeira: "Mastercard Black",
    cor: "from-[#1b102f] via-[#0b0c15] to-[#12071d]"
  },
  {
    id: "card-2",
    nome: "C6 Carbon Premium",
    limite: 15000.00,
    utilizado: 4200.00,
    diaFechamento: 15,
    diaVencimento: 22,
    bandeira: "Visa Infinite",
    cor: "from-[#22252A] via-[#111315] to-[#1A1C1F]"
  }
];

const MOCK_FUTURE_INSTALLMENTS = [
  { id: "1", descricao: "Smart TV (2/4)", valor: 300.00, vencimento: "12 Jun", cartao: "Nubank Ultravioleta" },
  { id: "2", descricao: "Notebook Trabalho (2/3)", valor: 600.00, vencimento: "22 Jun", cartao: "C6 Carbon Premium" },
  { id: "3", descricao: "Smart TV (3/4)", valor: 300.00, vencimento: "12 Jul", cartao: "Nubank Ultravioleta" },
  { id: "4", descricao: "Notebook Trabalho (3/3)", valor: 600.00, vencimento: "22 Jul", cartao: "C6 Carbon Premium" }
];

export default function Cards() {
  const [activeCardIndex, setActiveCardIndex] = useState(0);
  const [cards, setCards] = useState<any[]>([]);
  const [futureInstallments, setFutureInstallments] = useState<any[]>([]);
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
      setCards(MOCK_CARDS);
      setFutureInstallments(MOCK_FUTURE_INSTALLMENTS);
      return;
    }

    async function loadCardsData() {
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

        // Agrupa cartões, faturas e transações de todos os resultados
        const fetchedCards = results.flatMap(r => r.cartoes || []);
        const fetchedFaturas = results.flatMap(r => r.faturas || []);
        const fetchedTransactions = results.flatMap(r => r.transacoes || []);

        if (fetchedCards.length === 0) {
          setCards([]);
          setFutureInstallments([]);
          return;
        }

        // Formata os cartões
        const colors = [
          "from-[#1b102f] via-[#0b0c15] to-[#12071d]", // Nubank Purple
          "from-[#22252A] via-[#111315] to-[#1A1C1F]", // C6 Dark
          "from-[#0d1e2e] via-[#08111a] to-[#04090f]"  // Navy Dark
        ];

        const formattedCards = fetchedCards.map((c: any, index: number) => {
          const utilizado = fetchedFaturas
            ?.filter((f: any) => f.id_cartao === c.id && f.status === "aberta")
            ?.reduce((sum: number, f: any) => sum + parseFloat(f.valor_total), 0) || 0;

          return {
            id: c.id,
            nome: c.nome,
            limite: parseFloat(c.limite),
            utilizado: utilizado,
            diaFechamento: c.dia_fechamento,
            diaVencimento: c.dia_vencimento,
            bandeira: c.bandeira || "Mastercard",
            cor: colors[index % colors.length]
          };
        });

        setCards(formattedCards);

        // Formata faturas futuras
        const formattedInstallments = fetchedTransactions
          ?.filter((t: any) => t.id_parcelamento !== null && t.id_fatura !== null && new Date(t.data_competencia) > new Date())
          ?.map((t: any) => {
            const fatura = fetchedFaturas?.find((f: any) => f.id === t.id_fatura);
            const cardName = fetchedCards?.find((c: any) => c.id === fatura?.id_cartao)?.nome || "Cartão";

            return {
              id: t.id,
              descricao: t.descricao,
              valor: Math.abs(parseFloat(t.valor)),
              vencimento: new Date(t.data_competencia).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }),
              cartao: cardName
            };
          }) || [];

        setFutureInstallments(formattedInstallments);

      } catch (err) {
        console.error("Erro ao carregar cartões:", err);
        setCards([]);
        setFutureInstallments([]);
      } finally {
        setLoading(false);
      }
    }

    loadCardsData();
  }, []);

  const card = cards[activeCardIndex] || null;

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-500 relative">
      
      {/* Glow de fundo */}
      <div className="absolute top-[50px] left-[20%] w-[300px] h-[300px] rounded-full radial-glow-1 pointer-events-none -z-10"></div>

      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">Meus Cartões</h1>
          <p className="text-xs text-slate-400">
            {apiOnline ? "Puxando dados reais do banco PostgreSQL no Supabase" : "Gerenciamento de limites, faturas e parcelamentos futuros (Simulado)"}
          </p>
        </div>
        {loading && <span className="text-[10px] bg-slate-800 text-slate-400 px-3 py-1 rounded-full border border-slate-700">Carregando dados...</span>}
      </div>

      {cards.length > 0 && card ? (
        <>
          {/* SELETOR DE CARTÃO */}
          <div className="flex gap-4">
            {cards.map((c, idx) => (
              <button
                key={c.id}
                onClick={() => setActiveCardIndex(idx)}
                className={`px-4 py-3 rounded-2xl text-xs font-bold transition-all border ${
                  activeCardIndex === idx
                    ? "bg-violet-600 border-violet-500 text-white shadow-lg shadow-violet-600/25"
                    : "bg-[#1E293B]/60 border-white/5 text-slate-400 hover:text-white"
                }`}
              >
                {c.nome}
              </button>
            ))}
          </div>

          {/* VISUALIZADOR DE CARTÃO (FINTECH METAL CARD DESIGN) */}
          <div className={`w-full max-w-md mx-auto bg-gradient-to-br ${card.cor} border border-white/10 rounded-3xl p-6 relative overflow-hidden shadow-2xl transition-all duration-500 hover:scale-[1.01]`}>
            {/* Glow holográfico */}
            <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-violet-500/5 to-transparent pointer-events-none"></div>

            <div className="flex justify-between items-start mb-10">
              <div>
                <p className="text-[9px] uppercase tracking-widest text-violet-400 font-extrabold">FinBot Elite</p>
                <h3 className="font-extrabold text-md text-white mt-0.5">{card.nome}</h3>
              </div>
              <span className="text-[10px] font-bold text-slate-400 bg-slate-800/60 px-2.5 py-1 rounded-full border border-slate-700/50">
                {card.bandeira}
              </span>
            </div>

            {/* Chip */}
            <div className="w-10 h-8 bg-gradient-to-br from-amber-400 via-amber-500 to-yellow-600 rounded-md mb-8 relative">
              <div className="absolute inset-1 border border-black/10 rounded"></div>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest block">Fatura Aberta</p>
                  <h2 className="text-2xl font-extrabold text-white">
                    R$ {card.utilizado.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                  </h2>
                </div>
                <span className="text-xs text-slate-400">Vence dia {card.diaVencimento}</span>
              </div>

              <div className="space-y-2">
                <div className="w-full bg-slate-800 rounded-full h-1.5">
                  <div 
                    className="bg-gradient-to-r from-violet-500 to-indigo-500 h-1.5 rounded-full transition-all duration-500" 
                    style={{ width: `${card.limite > 0 ? (card.utilizado / card.limite) * 100 : 0}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[10px] text-slate-400">
                  <span>Limite Disponível: R$ {(card.limite - card.utilizado).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</span>
                  <span>Total R$ {card.limite.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}</span>
                </div>
              </div>
            </div>
          </div>

          {/* METRICAS DE FATURAMENTO */}
          <section className="grid grid-cols-2 gap-4">
            <div className="bg-[#1E293B]/45 border border-white/5 rounded-2xl p-4 text-center">
              <span className="text-xs text-slate-400 uppercase block mb-1">Melhor Dia de Compra</span>
              <span className="text-md font-extrabold text-emerald-400">Dia {card.diaFechamento + 1}</span>
            </div>
            <div className="bg-[#1E293B]/45 border border-white/5 rounded-2xl p-4 text-center">
              <span className="text-xs text-slate-400 uppercase block mb-1">Dia do Vencimento</span>
              <span className="text-md font-extrabold text-rose-500">Dia {card.diaVencimento}</span>
            </div>
          </section>

          {/* DETALHES DE PARCELAS FUTURAS */}
          <section className="space-y-4">
            <h3 className="font-bold text-xs uppercase tracking-widest text-slate-400">Parcelamentos Futuros Vinculados</h3>
            <div className="space-y-2">
              {futureInstallments.filter(inst => inst.cartao === card.nome).length === 0 ? (
                <p className="text-xs text-slate-500 py-4 text-center">Nenhum parcelamento futuro ativo para este cartão.</p>
              ) : (
                futureInstallments
                  .filter(inst => inst.cartao === card.nome)
                  .map((inst) => (
                    <div 
                      key={inst.id} 
                      className="flex items-center justify-between p-4 bg-[#1E293B]/25 border border-white/5 rounded-2xl hover:bg-[#1E293B]/50 transition-colors"
                    >
                      <div>
                        <p className="font-bold text-sm text-slate-100">{inst.descricao}</p>
                        <span className="text-xs text-slate-500">Fatura prevista para {inst.vencimento}</span>
                      </div>
                      <span className="font-bold text-sm text-rose-500">
                        - R$ {inst.valor.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </span>
                    </div>
                  ))
              )}
            </div>
          </section>
        </>
      ) : (
        <div className="glass-card rounded-2xl p-8 border border-white/5 text-center space-y-2">
          <span className="text-3xl block">💳</span>
          <h3 className="font-extrabold text-sm text-slate-100">Nenhum cartão cadastrado</h3>
          <p className="text-[10px] text-slate-400 max-w-sm mx-auto">
            Você não tem cartões de crédito configurados no banco de dados. Cadastre cartões via bot ou insira registros na tabela `cartoes` do Supabase para começar!
          </p>
        </div>
      )}

    </div>
  );
}
