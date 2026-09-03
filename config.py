# =============================================================
# config.py — Constantes e parâmetros do projeto Caso ENEM
# Atualizado para os microdados ENEM 2025 (INEP)
# =============================================================

# --- Modelo IBM watsonx.ai ---
# Modelos de INSTRUÇÃO disponíveis nesta instância:
#   mistralai/mistral-small-3-1-24b-instruct-2503     → respondeu bem, 24B  ← ATIVO
#   meta-llama/llama-4-maverick-17b-128e-instruct-fp8 → timeout de 5min
#   meta-llama/llama-3-3-70b-instruct                 → 70B, fila maior
# ATENÇÃO: modelos sem "-instruct" são base e NÃO suportam geração livre
WATSONX_MODEL_ID = "mistralai/mistral-small-3-1-24b-instruct-2503"
WATSONX_MAX_NEW_TOKENS = 600
WATSONX_TEMPERATURE = 0.3

# --- Leitura dos microdados ---
# Encoding e separador do CSV oficial do INEP
ENCODING_CSV = "latin-1"
SEPARADOR_CSV = ";"

# Caminho padrão do arquivo de participantes ENEM 2025
CAMINHO_DADOS_PADRAO = (
    "/home/rogerio/Documentos/white_cube/enem/"
    "microdados_enem_2025/DADOS/PARTICIPANTES_2025.csv"
)

# Colunas a importar do CSV (usecols) — minimiza uso de memória RAM
# Fonte: PARTICIPANTES_2025.csv
COLUNAS = [
    "NO_MUNICIPIO_PROVA",  # Município de realização da prova
    "SG_UF_PROVA",         # UF de realização da prova
    "Q001",                # Escolaridade do pai
    "Q002",                # Escolaridade da mãe
    "Q007",                # Renda familiar mensal (Q006 em anos anteriores)
    "Q020",                # Acesso à internet wi-fi em casa (Q025 em anos anteriores)
    "Q023",                # Tipo de escola do Ensino Médio (A=pública, B=privada)
]

# --- Mapeamento das faixas de renda (Q007 no ENEM 2025) ---
# A=Nenhuma renda, B=Até R$1.518, C=R$1.518 a R$3.036...
# Mapeamos para valor numérico central de cada faixa (R$)
MAPA_RENDA = {
    "A": 0,        # Nenhuma renda
    "B": 759,      # Até R$ 1.518 (1 salário mínimo 2025)
    "C": 2277,     # De R$ 1.518,01 a R$ 3.036
    "D": 3795,     # De R$ 3.036,01 a R$ 4.554
    "E": 5313,     # De R$ 4.554,01 a R$ 6.072
    "F": 7590,     # De R$ 6.072,01 a R$ 9.108
    "G": 10887,    # De R$ 9.108,01 a R$ 12.144
    "H": 13662,    # De R$ 12.144,01 a R$ 15.180
    "I": 16959,    # De R$ 15.180,01 a R$ 18.216
    "J": 22770,    # Acima de R$ 18.216
    "K": 22770,
    "L": 22770,
    "M": 22770,
    "N": 22770,
    "O": 22770,
    "P": 22770,
    "Q": 22770,
}

# Limiar de renda baixa: faixas A e B (até ~1 salário mínimo 2025)
FAIXAS_RENDA_BAIXA = {"A", "B"}

# --- Mapeamento de escolaridade dos pais (Q001 / Q002) ---
# A=Nunca estudou, B=1-5 anos Fundamental, C=6-9 anos Fundamental,
# D=Fundamental completo, E=Médio incompleto, F=Médio completo...
# Consideramos "baixa escolaridade" quem não completou o Ensino Médio
FAIXAS_ESCOLARIDADE_BAIXA = {"A", "B", "C", "D", "E"}

# --- Acesso à internet wi-fi em casa (Q020 no ENEM 2025) ---
# A=Não, B=Sim (atenção: invertido em relação ao Q025 histórico)
SEM_INTERNET = "A"

# --- Pesos do score de vulnerabilidade ---
# Os três pesos devem somar 1.0
PESO_RENDA = 0.40
PESO_INTERNET = 0.30
PESO_ESCOLARIDADE_PAIS = 0.30

# --- Limiares de classificação do perfil ---
LIMIAR_VULNERABILIDADE_ALTA = 65   # score >= 65 → Perfil: Alto
LIMIAR_VULNERABILIDADE_BAIXA = 35  # score <= 35 → Perfil: Baixo
                                   # entre 36 e 64  → Perfil: Médio
