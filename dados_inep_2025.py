import os
import zipfile
import sqlite3
import urllib.request
import pandas as pd

# CONFIGURAÇÕES DE DIRETÓRIOS
DIRETORIO_DADOS = "./dados_enem"
URL_MICRODADOS = "https://inep.gov.br"
ARQUIVO_ZIP = os.path.join(DIRETORIO_DADOS, "microdados_enem_2025.zip")
ARQUIVO_CSV_GERAL = os.path.join(DIRETORIO_DADOS, "MICRODADOS_ENEM_2025.csv")
ARQUIVO_BANCO_LOCAL = os.path.join(DIRETORIO_DADOS, "enem_2025_geral.db")

# 🎯 SELEÇÃO CRUCIAL DE COLUNAS PARA REDUÇÃO DE 70% DO TAMANHO
COLUNAS_CALCULO = [
    'CO_MUNICIPIO_RESIDENCIA', 'NO_MUNICIPIO_RESIDENCIA', 'SG_UF_RESIDENCIA',
    'TP_ESCOLA', 'TP_PRESENCA_CN', 'TP_PRESENCA_CH', 'TP_PRESENCA_LC', 'TP_PRESENCA_MT',
    'NU_NOTA_CN', 'NU_NOTA_CH', 'NU_NOTA_LC', 'NU_NOTA_MT', 'NU_NOTA_REDACAO',
    'Q006', 'Q025'  # Variáveis socioeconômicas chaves: Renda e Internet
]

def preparar_ambiente():
    os.makedirs(DIRETORIO_DADOS, exist_ok=True)
    print(f"✅ Pasta '{DIRETORIO_DADOS}' verificada/criada.")

import requests  # Certifique-se de adicionar 'requests' no seu requirements.txt

def baixar_dados_inep():
    """Faz o download do ZIP oficial usando a biblioteca requests (mais robusta)."""
    if os.path.exists(ARQUIVO_CSV_GERAL):
        print("✨ O arquivo CSV descompactado já existe. Pulando download.")
        return

    if not os.path.exists(ARQUIVO_ZIP):
        print("📥 Iniciando download dos microdados oficiais do INEP via Requests (Aguarde)...")

        # Cabeçalhos robustos para simular um navegador real e evitar bloqueios
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }

        try:
            # timeout=30 evita que o script fique travado infinitamente se o INEP cair
            with requests.get(URL_MICRODADOS, headers=headers, stream=True, timeout=30) as response:
                response.raise_for_status() # Dispara erro se a página estiver fora do ar

                with open(ARQUIVO_ZIP, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            print("💾 Download do arquivo ZIP concluído com sucesso!")

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de rede ao acessar o INEP: {e}")
            print("💡 Dica: O site do INEP pode estar temporariamente fora do ar ou sua rede precisa de proxy.")
    else:
        print("📦 Arquivo ZIP já encontrado localmente.")

def extrair_csv_principal():
    """Extrai apenas o arquivo de microdados de dentro do ZIP para poupar espaço."""
    if os.path.exists(ARQUIVO_CSV_GERAL):
        return

    print("🔓 Extraindo o arquivo CSV de microdados do pacote ZIP...")
    with zipfile.ZipFile(ARQUIVO_ZIP, 'r') as zip_ref:
        for arquivo in zip_ref.namelist():
            if "MICRODADOS_ENEM" in arquivo and arquivo.endswith(".csv"):
                # Extrai direto na raiz da pasta de dados mapeada
                nome_base = os.path.basename(arquivo)
                destino_completo = os.path.join(DIRETORIO_DADOS, nome_base)

                with zip_ref.open(arquivo) as z_origem, open(destino_completo, 'wb') as f_destino:
                    f_destino.write(z_origem.read())
                print(f"📦 Extraído com sucesso para: {destino_completo}")
                break

def executar_etl_para_sqlite():
    """Executa o ETL com Column Selection de 70% e salva direto no SQLite local."""
    print("✂️ Iniciando processo de ETL e otimização colunar (Redução de 70%)...")

    conn = sqlite3.connect(ARQUIVO_BANCO_LOCAL)
    tamanho_bloco = 100000  # Mantém o consumo de RAM do seu notebook estável
    primeiro_bloco = True

    try:
        # Lê apenas as colunas selecionadas para cálculo usando chunks
        for num_bloco, chunk in enumerate(pd.read_csv(ARQUIVO_CSV_GERAL, sep=';', encoding='latin-1', chunksize=tamanho_bloco, usecols=COLUNAS_CALCULO)):

            # Padronização e Limpeza de strings para busca rápida do Agente
            chunk['NO_MUNICIPIO_RESIDENCIA'] = chunk['NO_MUNICIPIO_RESIDENCIA'].astype(str).str.upper()
            chunk['CO_MUNICIPIO_RESIDENCIA'] = chunk['CO_MUNICIPIO_RESIDENCIA'].fillna(0).astype(int)

            # Persiste os dados de forma incremental no banco local indexado
            if primeiro_bloco:
                chunk.to_sql('microdados', conn, if_exists='replace', index=False)
                primeiro_bloco = False
            else:
                chunk.to_sql('microdados', conn, if_exists='append', index=False)

            if num_bloco % 10 == 0:
                print(f"🔄 Blocos Processados: {num_bloco} ({num_bloco * tamanho_bloco} linhas limpas inseridas)...")

        # ⚡ CRIAÇÃO DE ÍNDICES: Deixa a busca do Agente instantânea por nome da cidade
        print("🔗 Construindo índices de performance no banco local...")
        cursor = conn.cursor()
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_municipio_nome ON microdados (NO_MUNICIPIO_RESIDENCIA);")
        conn.commit()

        print(f"🎯 ETL Concluído! Sua base compacta e indexada está pronta em: {ARQUIVO_BANCO_LOCAL}")

        # 🔥 LIMPEZA DE DISCO OPCIONAL: Remove o arquivo gigante de múltiplos GBs após carregar o SQLite leve
        if os.path.exists(ARQUIVO_CSV_GERAL):
            os.remove(ARQUIVO_CSV_GERAL)
            print("🧹 Arquivo original CSV (pesado) deletado para liberar espaço no seu HD.")

    except Exception as e:
        print(f"❌ Ocorreu um erro crítico durante o ETL: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    preparar_ambiente()
    baixar_dados_inep()
    extrair_csv_principal()
    executar_etl_para_sqlite()
    print("🏁 Todo o pipeline local foi concluído com sucesso!")
