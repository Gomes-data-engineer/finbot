-- Habilita a extensão UUID para geração automática de identificadores
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. TABELA DE USUÁRIOS
-- Armazena as informações dos usuários cadastrados via Telegram
CREATE TABLE IF NOT EXISTS usuarios (
    id_telegram BIGINT PRIMARY KEY,
    nome TEXT NOT NULL,
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. TABELA DE CATEGORIAS
-- Permite categorizar as transações e opcionalmente definir metas mensais de gastos
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    meta_mensal NUMERIC(10, 2)
);

-- 3. TABELA DE TRANSAÇÕES
-- Armazena os lançamentos de receitas, despesas simples e parceladas
CREATE TABLE IF NOT EXISTS transacoes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario BIGINT NOT NULL REFERENCES usuarios(id_telegram) ON DELETE CASCADE,
    id_categoria INTEGER NOT NULL REFERENCES categorias(id) ON DELETE RESTRICT,
    descricao TEXT NOT NULL,
    valor NUMERIC(10, 2) NOT NULL, -- Valor positivo para receitas, negativo para despesas
    data_competencia DATE NOT NULL, -- O mês/ano em que o gasto conta de fato
    data_registro TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    parcelado BOOLEAN DEFAULT FALSE NOT NULL,
    parcela_atual INTEGER,
    total_parcelas INTEGER,
    id_agrupador_parcela UUID, -- Agrupa parcelas de uma mesma compra parcelada
    
    -- Restrições para consistência de dados de parcelamento
    CONSTRAINT chk_parcelamento CHECK (
        (parcelado = FALSE AND parcela_atual IS NULL AND total_parcelas IS NULL AND id_agrupador_parcela IS NULL) OR
        (parcelado = TRUE AND parcela_atual IS NOT NULL AND total_parcelas IS NOT NULL AND id_agrupador_parcela IS NOT NULL)
    )
);

-- 4. TABELA DE DÍVIDAS
-- Controla saldos devedores de contas a pagar/receber de terceiros
CREATE TABLE IF NOT EXISTS dividas (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    id_usuario BIGINT NOT NULL REFERENCES usuarios(id_telegram) ON DELETE CASCADE,
    credor TEXT NOT NULL,
    valor_total NUMERIC(10, 2) NOT NULL,
    valor_pago NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
    status TEXT DEFAULT 'pendente' NOT NULL CONSTRAINT chk_status CHECK (status IN ('pago', 'pendente')),
    data_registro TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- ÍNDICES PARA OTIMIZAÇÃO DE BUSCA E PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_transacoes_usuario ON transacoes(id_usuario);
CREATE INDEX IF NOT EXISTS idx_transacoes_data_competencia ON transacoes(data_competencia);
CREATE INDEX IF NOT EXISTS idx_transacoes_categoria ON transacoes(id_categoria);
CREATE INDEX IF NOT EXISTS idx_dividas_usuario ON dividas(id_usuario);

-- INSERÇÃO DE CATEGORIAS PADRÃO
INSERT INTO categorias (nome, meta_mensal) VALUES
('Alimentação', 400.00), -- Exemplo de meta de R$ 400
('Transporte', null),
('Lazer', null),
('Cartão', null),
('Fixas', null),
('Renda', null),
('Outros', null)
ON CONFLICT (nome) DO NOTHING;
