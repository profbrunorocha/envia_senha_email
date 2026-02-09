-- Script SQL para criar o banco de dados no Neon
-- Execute este script diretamente no console SQL do Neon

-- Criação da tabela de usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha VARCHAR(100) NOT NULL,
    data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Criação de índice para melhorar performance nas buscas por email
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);

-- Comentários nas colunas para documentação
COMMENT ON TABLE usuarios IS 'Tabela para armazenar usuários cadastrados no sistema';
COMMENT ON COLUMN usuarios.id IS 'Identificador único do usuário';
COMMENT ON COLUMN usuarios.email IS 'Email do usuário (único)';
COMMENT ON COLUMN usuarios.senha IS 'Senha gerada automaticamente';
COMMENT ON COLUMN usuarios.data_cadastro IS 'Data e hora do cadastro';

-- Verificar a criação
SELECT 
    table_name, 
    column_name, 
    data_type, 
    is_nullable
FROM 
    information_schema.columns
WHERE 
    table_name = 'usuarios'
ORDER BY 
    ordinal_position;
