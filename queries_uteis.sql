-- Queries úteis para gerenciamento do banco de dados

-- =============================================
-- CONSULTAS BÁSICAS
-- =============================================

-- Listar todos os usuários
SELECT id, email, data_cadastro 
FROM usuarios 
ORDER BY data_cadastro DESC;

-- Contar total de usuários cadastrados
SELECT COUNT(*) as total_usuarios 
FROM usuarios;

-- Buscar usuário por email
SELECT id, email, data_cadastro 
FROM usuarios 
WHERE email = 'exemplo@email.com';

-- Listar usuários cadastrados hoje
SELECT id, email, data_cadastro 
FROM usuarios 
WHERE DATE(data_cadastro) = CURRENT_DATE
ORDER BY data_cadastro DESC;

-- Listar usuários cadastrados nos últimos 7 dias
SELECT id, email, data_cadastro 
FROM usuarios 
WHERE data_cadastro >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY data_cadastro DESC;

-- =============================================
-- ESTATÍSTICAS
-- =============================================

-- Usuários cadastrados por dia (últimos 30 dias)
SELECT 
    DATE(data_cadastro) as data,
    COUNT(*) as total_cadastros
FROM usuarios
WHERE data_cadastro >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(data_cadastro)
ORDER BY data DESC;

-- Usuários cadastrados por mês
SELECT 
    TO_CHAR(data_cadastro, 'YYYY-MM') as mes,
    COUNT(*) as total_cadastros
FROM usuarios
GROUP BY TO_CHAR(data_cadastro, 'YYYY-MM')
ORDER BY mes DESC;

-- Estatísticas gerais
SELECT 
    COUNT(*) as total_usuarios,
    MIN(data_cadastro) as primeiro_cadastro,
    MAX(data_cadastro) as ultimo_cadastro,
    COUNT(CASE WHEN DATE(data_cadastro) = CURRENT_DATE THEN 1 END) as cadastros_hoje
FROM usuarios;

-- =============================================
-- MANUTENÇÃO E LIMPEZA
-- =============================================

-- Deletar usuário específico por email
-- CUIDADO: Esta ação é irreversível!
-- DELETE FROM usuarios WHERE email = 'exemplo@email.com';

-- Deletar usuários antigos (mais de 1 ano sem uso)
-- CUIDADO: Esta ação é irreversível!
-- DELETE FROM usuarios 
-- WHERE data_cadastro < CURRENT_DATE - INTERVAL '1 year';

-- Limpar toda a tabela (use com EXTREMO cuidado!)
-- TRUNCATE TABLE usuarios RESTART IDENTITY;

-- =============================================
-- BACKUP E EXPORTAÇÃO
-- =============================================

-- Exportar lista de emails (copie o resultado)
SELECT email FROM usuarios ORDER BY email;

-- Exportar dados completos em formato CSV (use ferramentas do Neon)
SELECT 
    id,
    email,
    TO_CHAR(data_cadastro, 'YYYY-MM-DD HH24:MI:SS') as data_cadastro
FROM usuarios
ORDER BY data_cadastro DESC;

-- =============================================
-- VERIFICAÇÕES DE INTEGRIDADE
-- =============================================

-- Verificar duplicatas de email (não deveria haver)
SELECT email, COUNT(*) 
FROM usuarios 
GROUP BY email 
HAVING COUNT(*) > 1;

-- Verificar registros com dados inválidos
SELECT * FROM usuarios 
WHERE email IS NULL 
   OR email = '' 
   OR email NOT LIKE '%@%';

-- Verificar tamanho da tabela
SELECT 
    pg_size_pretty(pg_total_relation_size('usuarios')) as tamanho_total,
    pg_size_pretty(pg_relation_size('usuarios')) as tamanho_tabela,
    pg_size_pretty(pg_indexes_size('usuarios')) as tamanho_indices;

-- =============================================
-- PERFORMANCE
-- =============================================

-- Analisar uso de índices
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as numero_de_scans,
    idx_tup_read as tuplas_lidas,
    idx_tup_fetch as tuplas_buscadas
FROM pg_stat_user_indexes 
WHERE tablename = 'usuarios';

-- Recriar índice se necessário (raramente necessário)
-- REINDEX INDEX idx_usuarios_email;

-- Atualizar estatísticas da tabela
ANALYZE usuarios;
