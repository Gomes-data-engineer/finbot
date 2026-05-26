-- Extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. TABELA DE USUÁRIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_telegram BIGINT UNIQUE,
    email TEXT UNIQUE,
    nome TEXT NOT NULL,
    avatar_url TEXT,
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. TABELA DE CONTAS (Bancárias, Dinheiro em Espécie, etc.)
CREATE TABLE IF NOT EXISTS contas (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nome TEXT NOT NULL, -- ex: "Conta Corrente Itaú", "Carteira Físico"
    tipo TEXT NOT NULL CHECK (tipo IN ('corrente', 'poupanca', 'carteira', 'investimento')),
    saldo NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    moeda TEXT DEFAULT 'BRL' NOT NULL
);

-- 3. TABELA DE CARTÕES DE CRÉDITO
CREATE TABLE IF NOT EXISTS cartoes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    id_conta_vinculada UUID REFERENCES contas(id) ON DELETE SET NULL,
    nome TEXT NOT NULL, -- ex: "Nubank Ultravioleta", "C6 Carbon"
    limite NUMERIC(12, 2) not null,
    dia_fechamento INTEGER NOT NULL CHECK (dia_fechamento BETWEEN 1 AND 31),
    dia_vencimento INTEGER NOT NULL CHECK (dia_vencimento BETWEEN 1 AND 31),
    bandeira TEXT DEFAULT 'Mastercard' NOT NULL
);

-- 4. TABELA DE FATURAS DO CARTÃO
CREATE TABLE IF NOT EXISTS faturas (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_cartao UUID NOT NULL REFERENCES cartoes(id) ON DELETE CASCADE,
    mes_referencia DATE NOT NULL, -- Ex: 2026-05-01 representa fatura de Maio de 2026
    valor_total NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    valor_pago NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    status TEXT DEFAULT 'aberta' NOT NULL CHECK (status IN ('aberta', 'fechada', 'paga', 'atrasada'))
);

-- 5. TABELA DE CATEGORIAS
CREATE TABLE IF NOT EXISTS categorias (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    icone TEXT, -- emoji ou nome de ícone (lucide-react)
    cor TEXT -- código hex ex: "#8B5CF6"
);

-- 6. TABELA DE PARCELAMENTOS
CREATE TABLE IF NOT EXISTS parcelamentos (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    total_parcelas INTEGER NOT NULL CHECK (total_parcelas > 1),
    valor_total NUMERIC(12, 2) NOT NULL,
    descricao TEXT NOT NULL
);

-- 7. TABELA DE TRANSAÇÕES
CREATE TABLE IF NOT EXISTS transacoes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    id_conta UUID REFERENCES contas(id) ON DELETE SET NULL, -- Null se for transação de cartão de crédito pendente de fatura
    id_fatura UUID REFERENCES faturas(id) ON DELETE SET NULL, -- Vinculada se for transação no crédito
    id_categoria UUID REFERENCES categorias(id) ON DELETE RESTRICT,
    id_parcelamento UUID REFERENCES parcelamentos(id) ON DELETE SET NULL,
    parcela_atual INTEGER,
    descricao TEXT NOT NULL,
    valor NUMERIC(12, 2) NOT NULL, -- Negativo para saídas, positivo para entradas
    data_competencia DATE NOT NULL,
    data_registro TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    tag TEXT[],
    confirmado BOOLEAN DEFAULT TRUE NOT NULL
);

-- 8. TABELA DE DÍVIDAS E CRÉDITOS
CREATE TABLE IF NOT EXISTS dividas (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    credor_devedor TEXT NOT NULL, -- Nome da pessoa ou banco
    tipo TEXT NOT NULL CHECK (tipo IN ('pagar', 'receber')),
    valor_total NUMERIC(12, 2) NOT NULL,
    valor_pago NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    vencimento DATE,
    status TEXT DEFAULT 'pendente' NOT NULL CHECK (status IN ('pendente', 'pago'))
);

-- 9. TABELA DE METAS FINANCEIRAS
CREATE TABLE IF NOT EXISTS metas (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    id_categoria UUID REFERENCES categorias(id) ON DELETE SET NULL, -- Opcional: meta de categoria específica ou geral
    titulo TEXT NOT NULL,
    valor_alvo NUMERIC(12, 2) NOT NULL,
    valor_atual NUMERIC(12, 2) DEFAULT 0.00 NOT NULL,
    data_limite DATE,
    tipo TEXT DEFAULT 'gasto' NOT NULL CHECK (tipo IN ('gasto', 'economia'))
);

-- 10. TABELA DE INSIGHTS COM IA
CREATE TABLE IF NOT EXISTS insights_ia (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('alerta', 'dica', 'recorrencia', 'oportunidade')),
    titulo TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    score_impacto INTEGER CHECK (score_impacto BETWEEN 1 AND 5),
    lido BOOLEAN DEFAULT FALSE NOT NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 11. TABELA DE NOTIFICAÇÕES
CREATE TABLE IF NOT EXISTS notificacoes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    mensagem TEXT NOT NULL,
    canal TEXT NOT NULL CHECK (canal IN ('push', 'telegram', 'app')),
    enviada BOOLEAN DEFAULT FALSE NOT NULL,
    data_envio TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) not null
);

-- Índices de Otimização
CREATE INDEX IF NOT EXISTS idx_transacoes_competencia ON transacoes(id_usuario, data_competencia);
CREATE INDEX IF NOT EXISTS idx_faturas_referencia ON faturas(id_cartao, mes_referencia);
CREATE INDEX IF NOT EXISTS idx_transacoes_fatura ON transacoes(id_fatura);
CREATE INDEX IF NOT EXISTS idx_insights_usuario ON insights_ia(id_usuario, lido);

-- INSERÇÃO DE CATEGORIAS PADRÃO
INSERT INTO categorias (nome, icone, cor) VALUES
('Alimentação', 'utensils', '#EF4444'),
('Transporte', 'car', '#3B82F6'),
('Lazer', 'party-popper', '#F59E0B'),
('Cartão', 'credit-card', '#8B5CF6'),
('Fixas', 'home', '#10B981'),
('Renda', 'wallet', '#22C55E'),
('Outros', 'circle-ellipsis', '#64748B')
ON CONFLICT (nome) DO NOTHING;
