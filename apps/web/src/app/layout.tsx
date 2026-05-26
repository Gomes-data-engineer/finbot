import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";
import { Home, History, CreditCard, BarChart3, Target, Bell } from "lucide-react";

export const metadata: Metadata = {
  title: "FinBot — Inteligência Financeira Premium",
  description: "Gerenciador financeiro com IA conversacional e design fintech",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen flex flex-col md:flex-row bg-[#05070F] text-slate-100 antialiased">
        
        {/* SIDEBAR PARA DESKTOP */}
        <aside className="hidden md:flex flex-col w-60 bg-[#0A0D18] border-r border-[#1E293B]/40 p-5 text-white shrink-0">
          <div className="flex items-center gap-2.5 mb-6">
            <span className="text-xl text-violet-500 font-bold">💎</span>
            <h1 className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
              FinBot V2
            </h1>
          </div>
          
          <nav className="flex flex-col gap-1 flex-grow">
            <Link href="/" className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl hover:bg-[#1E293B]/50 transition-all text-sm font-medium text-slate-300 hover:text-white">
              <Home className="w-4.5 h-4.5 text-violet-400" /> Home
            </Link>
            <Link href="/timeline" className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl hover:bg-[#1E293B]/50 transition-all text-sm font-medium text-slate-300 hover:text-white">
              <History className="w-4.5 h-4.5 text-violet-400" /> Extrato
            </Link>
            <Link href="/cards" className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl hover:bg-[#1E293B]/50 transition-all text-sm font-medium text-slate-300 hover:text-white">
              <CreditCard className="w-4.5 h-4.5 text-violet-400" /> Cartões
            </Link>
            <Link href="/analytics" className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl hover:bg-[#1E293B]/50 transition-all text-sm font-medium text-slate-300 hover:text-white">
              <BarChart3 className="w-4.5 h-4.5 text-violet-400" /> Analytics
            </Link>
            <Link href="/metas" className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl hover:bg-[#1E293B]/50 transition-all text-sm font-medium text-slate-300 hover:text-white">
              <Target className="w-4.5 h-4.5 text-violet-400" /> Metas
            </Link>
          </nav>

          <div className="border-t border-[#1E293B]/30 pt-4 mt-auto">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-violet-600 flex items-center justify-center font-bold text-sm">
                V
              </div>
              <div>
                <p className="font-semibold text-xs text-slate-200">Vitor</p>
                <span className="text-[10px] text-slate-500">Premium Account</span>
              </div>
            </div>
          </div>
        </aside>

        {/* ÁREA PRINCIPAL */}
        <main className="flex-grow flex flex-col min-h-screen pb-16 md:pb-0 bg-transparent">
          
          {/* HEADER MOBILE-FIRST */}
          <header className="flex items-center justify-between px-5 py-3.5 border-b border-[#1E293B]/30 bg-[#0A0D18]/80 backdrop-blur-md sticky top-0 z-40">
            <div className="md:hidden flex items-center gap-2">
              <span className="text-lg text-violet-500 font-bold">💎</span>
              <span className="font-extrabold text-md bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">FinBot</span>
            </div>
            
            <div className="hidden md:block">
              <h2 className="font-extrabold text-md text-slate-200">Olá, Vitor! 👋</h2>
            </div>

            <div className="flex items-center gap-3">
              <button className="p-2 hover:bg-[#1E293B]/50 rounded-full transition-colors relative">
                <Bell className="w-4.5 h-4.5 text-slate-400" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-[#0B0F19]"></span>
              </button>
              <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center font-bold text-xs md:hidden">
                V
              </div>
            </div>
          </header>

          {/* CONTEÚDO */}
          <div className="flex-grow p-5 md:p-6 overflow-y-auto">
            {children}
          </div>
        </main>

        {/* BOTTOM NAVIGATION PARA MOBILE */}
        <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-[#0A0D18] border-t border-[#1E293B]/40 flex justify-around py-2.5 z-40 backdrop-blur-md">
          <Link href="/" className="flex flex-col items-center gap-0.5 text-slate-400 hover:text-violet-400 transition-colors">
            <Home className="w-4.5 h-4.5" />
            <span className="text-[9px] font-medium">Home</span>
          </Link>
          <Link href="/timeline" className="flex flex-col items-center gap-0.5 text-slate-400 hover:text-violet-400 transition-colors">
            <History className="w-4.5 h-4.5" />
            <span className="text-[9px] font-medium">Extrato</span>
          </Link>
          <Link href="/cards" className="flex flex-col items-center gap-0.5 text-slate-400 hover:text-violet-400 transition-colors">
            <CreditCard className="w-4.5 h-4.5" />
            <span className="text-[9px] font-medium">Cartões</span>
          </Link>
          <Link href="/analytics" className="flex flex-col items-center gap-0.5 text-slate-400 hover:text-violet-400 transition-colors">
            <BarChart3 className="w-4.5 h-4.5" />
            <span className="text-[9px] font-medium">Analytics</span>
          </Link>
          <Link href="/metas" className="flex flex-col items-center gap-0.5 text-slate-400 hover:text-violet-400 transition-colors">
            <Target className="w-4.5 h-4.5" />
            <span className="text-[9px] font-medium">Metas</span>
          </Link>
        </nav>

      </body>
    </html>
  );
}
