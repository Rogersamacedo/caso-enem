# =============================================================
# analise.py — Pipeline de ETL e cálculo do score de
#              vulnerabilidade socioeconômica por município.
#
# Fonte dos dados: microdados ENEM 2025 — INEP
# Arquivo: PARTICIPANTES_2025.csv
# =============================================================

import pandas as pd

import config


# ------------------------------------------------------------------
# 1. Carregamento
# ------------------------------------------------------------------

def carregar_microdados(caminho: str, amostra: int = None) -> pd.DataFrame:
    """Lê o CSV de participantes do ENEM e retorna apenas as colunas
    relevantes para a análise socioeconômica.

    Parâmetros
    ----------
    caminho : str
        Caminho completo para o arquivo PARTICIPANTES_XXXX.csv.
    amostra : int, opcional
        Se informado, carrega apenas as primeiras N linhas do CSV.
        Útil para testes rápidos em máquinas com pouca RAM.
        Valores sugeridos: 100_000 (rápido) a 500_000 (representativo).

    Retorna
    -------
    pd.DataFrame
        DataFrame com somente as colunas definidas em config.COLUNAS,
        sem linhas onde todos os campos socioeconômicos sejam nulos.
    """
    if amostra:
        print(f"[analise] Carregando amostra de {amostra:,} linhas de: {caminho}")
    else:
        print(f"[analise] Carregando microdados completos de: {caminho}")

    df = pd.read_csv(
        caminho,
        sep=config.SEPARADOR_CSV,
        encoding=config.ENCODING_CSV,
        usecols=config.COLUNAS,
        dtype=str,          # Todas as colunas como string para preservar os códigos (A, B, C...)
        low_memory=False,
        nrows=amostra,      # None = carrega tudo; int = limita linhas
    )

    print(f"[analise] {len(df):,} registros carregados.")

    # Elimina linhas em que TODAS as variáveis socioeconômicas são nulas
    cols_socioec = ["Q001", "Q002", "Q007", "Q020"]
    df.dropna(subset=cols_socioec, how="all", inplace=True)

    # Normaliza os valores: remove espaços e converte para maiúsculas
    for col in cols_socioec + ["Q023"]:
        df[col] = df[col].str.strip().str.upper()

    print(f"[analise] {len(df):,} registros após limpeza de nulos.")
    return df


# ------------------------------------------------------------------
# 2. Pontuação individual
# ------------------------------------------------------------------

def _pontuar_aluno(row: pd.Series) -> float:
    """Calcula o score de vulnerabilidade de um único aluno (0 a 100).

    Componentes:
      - Renda baixa    → peso 40%  (Q007 nas faixas A ou B)
      - Sem internet   → peso 30%  (Q020 == 'A', ou seja, Não)
      - Pais sem EM    → peso 30%  (média de Q001 e Q002 nas faixas A-E)

    Retorna um valor entre 0 (sem vulnerabilidade) e 100 (máxima).
    """
    # --- Renda ---
    renda_baixa = 1.0 if row.get("Q007", "") in config.FAIXAS_RENDA_BAIXA else 0.0

    # --- Internet ---
    sem_internet = 1.0 if row.get("Q020", "") == config.SEM_INTERNET else 0.0

    # --- Escolaridade dos pais: média dos dois indicadores ---
    pai_baixo = 1.0 if row.get("Q001", "") in config.FAIXAS_ESCOLARIDADE_BAIXA else 0.0
    mae_baixa = 1.0 if row.get("Q002", "") in config.FAIXAS_ESCOLARIDADE_BAIXA else 0.0
    escol_baixa = (pai_baixo + mae_baixa) / 2.0

    score = (
        config.PESO_RENDA * renda_baixa
        + config.PESO_INTERNET * sem_internet
        + config.PESO_ESCOLARIDADE_PAIS * escol_baixa
    ) * 100.0

    return round(score, 2)


def _classificar_perfil(score: float) -> str:
    """Classifica o score em perfil Alto / Médio / Baixo."""
    if score >= config.LIMIAR_VULNERABILIDADE_ALTA:
        return "Alto"
    if score <= config.LIMIAR_VULNERABILIDADE_BAIXA:
        return "Baixo"
    return "Médio"


# ------------------------------------------------------------------
# 3. Agregação por município
# ------------------------------------------------------------------

def calcular_score_vulnerabilidade(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula o score de vulnerabilidade médio por município.

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame retornado por `carregar_microdados()`.

    Retorna
    -------
    pd.DataFrame
        Uma linha por município com colunas:
        municipio | uf | score_vulnerabilidade | perfil | n_alunos |
        pct_renda_baixa | pct_sem_internet | pct_pais_baixa_escolaridade
    """
    print("[analise] Calculando scores individuais...")

    # Score de cada aluno
    df = df.copy()
    df["score_aluno"] = df.apply(_pontuar_aluno, axis=1)

    # Flags individuais para cálculo de percentuais
    df["flag_renda_baixa"] = df["Q007"].isin(config.FAIXAS_RENDA_BAIXA).astype(int)
    df["flag_sem_internet"] = (df["Q020"] == config.SEM_INTERNET).astype(int)
    df["flag_pai_baixo"] = df["Q001"].isin(config.FAIXAS_ESCOLARIDADE_BAIXA).astype(int)
    df["flag_mae_baixa"] = df["Q002"].isin(config.FAIXAS_ESCOLARIDADE_BAIXA).astype(int)
    df["flag_escol_baixa"] = ((df["flag_pai_baixo"] + df["flag_mae_baixa"]) / 2).round(0).astype(int)

    print("[analise] Agregando por município...")

    agg = (
        df.groupby(["NO_MUNICIPIO_PROVA", "SG_UF_PROVA"], dropna=True)
        .agg(
            n_alunos=("score_aluno", "count"),
            score_vulnerabilidade=("score_aluno", "mean"),
            pct_renda_baixa=("flag_renda_baixa", "mean"),
            pct_sem_internet=("flag_sem_internet", "mean"),
            pct_pais_baixa_escolaridade=("flag_escol_baixa", "mean"),
        )
        .reset_index()
    )

    agg.rename(
        columns={
            "NO_MUNICIPIO_PROVA": "municipio",
            "SG_UF_PROVA": "uf",
        },
        inplace=True,
    )

    # Arredonda scores e converte percentuais para 0–100
    agg["score_vulnerabilidade"] = agg["score_vulnerabilidade"].round(1)
    agg["pct_renda_baixa"] = (agg["pct_renda_baixa"] * 100).round(1)
    agg["pct_sem_internet"] = (agg["pct_sem_internet"] * 100).round(1)
    agg["pct_pais_baixa_escolaridade"] = (agg["pct_pais_baixa_escolaridade"] * 100).round(1)

    # Classificação do perfil
    agg["perfil"] = agg["score_vulnerabilidade"].apply(_classificar_perfil)

    # Ordena por score decrescente (mais vulnerável primeiro)
    agg.sort_values("score_vulnerabilidade", ascending=False, inplace=True)
    agg.reset_index(drop=True, inplace=True)

    print(f"[analise] {len(agg):,} municípios processados.")
    return agg


# ------------------------------------------------------------------
# 4. Lookup por município
# ------------------------------------------------------------------

def obter_perfil_municipio(df_agg: pd.DataFrame, municipio: str) -> dict:
    """Retorna o perfil socioeconômico de um município específico.

    A busca é case-insensitive e aceita correspondência parcial.

    Parâmetros
    ----------
    df_agg : pd.DataFrame
        DataFrame retornado por `calcular_score_vulnerabilidade()`.
    municipio : str
        Nome (ou parte do nome) do município desejado.

    Retorna
    -------
    dict
        Dicionário com os dados do município, ou None se não encontrado.
    """
    termo = municipio.strip().upper()
    resultado = df_agg[df_agg["municipio"].str.upper().str.contains(termo, na=False)]

    if resultado.empty:
        return None

    # Se mais de um match, retorna o de maior score (mais relevante)
    linha = resultado.iloc[0]

    return {
        "municipio": linha["municipio"],
        "uf": linha["uf"],
        "score_vulnerabilidade": linha["score_vulnerabilidade"],
        "perfil": linha["perfil"],
        "n_alunos": int(linha["n_alunos"]),
        "pct_renda_baixa": linha["pct_renda_baixa"],
        "pct_sem_internet": linha["pct_sem_internet"],
        "pct_pais_baixa_escolaridade": linha["pct_pais_baixa_escolaridade"],
    }


# ------------------------------------------------------------------
# 5. Teste rápido (execução direta)
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    caminho = sys.argv[1] if len(sys.argv) > 1 else config.CAMINHO_DADOS_PADRAO

    df_bruto = carregar_microdados(caminho)
    df_agg = calcular_score_vulnerabilidade(df_bruto)

    print("\n" + "=" * 65)
    print("TOP 10 MUNICÍPIOS COM MAIOR VULNERABILIDADE SOCIOECONÔMICA")
    print("=" * 65)
    print(
        df_agg.head(10)[
            ["municipio", "uf", "score_vulnerabilidade", "perfil", "n_alunos"]
        ].to_string(index=False)
    )

    print("\n" + "=" * 65)
    print("TOP 10 MUNICÍPIOS COM MENOR VULNERABILIDADE SOCIOECONÔMICA")
    print("=" * 65)
    print(
        df_agg.tail(10)[
            ["municipio", "uf", "score_vulnerabilidade", "perfil", "n_alunos"]
        ].to_string(index=False)
    )

    # Exemplo de lookup
    perfil = obter_perfil_municipio(df_agg, "São Paulo")
    if perfil:
        print(f"\n--- Perfil: {perfil['municipio']} ({perfil['uf']}) ---")
        for k, v in perfil.items():
            print(f"  {k}: {v}")
