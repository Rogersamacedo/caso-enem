# =============================================================
# gerar_dashboard.py — Relatório Estatístico Nativo (Sem Pandas)
# =============================================================

import os
import csv

def main():
    caminho_csv = "dados/tratado/tabela_municipio_final.csv"

    if not os.path.exists(caminho_csv):
        print(f"❌ Erro: O arquivo '{caminho_csv}' não foi encontrado.")
        return

    print("📊 Carregando dados locais do ENEM via Python Nativo...")

    municipios_dados = []

    # Abre o arquivo usando o leitor nativo de CSV do Python
    with open(caminho_csv, mode='r', encoding='utf-8') as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            try:
                # Transforma os textos em números para os cálculos
                municipios_dados.append({
                    'nome_municipio': linha['nome_municipio'],
                    'uf': linha.get('uf', 'UF'),
                    'qtd_inscritos': int(float(linha['qtd_inscritos'] or 0)),
                    'nota_media_geral': float(linha['nota_media_geral'] or 0),
                    'indice_vulnerabilidade_medio': float(linha['indice_vulnerabilidade_medio'] or 0)
                })
            except (ValueError, KeyError):
                continue

    if not municipios_dados:
        print("⚠️ Nenhum dado pôde ser processado.")
        return

    # 1. Cálculos Estatísticos Gerais
    total_municipios = len(municipios_dados)
    total_alunos = sum(m['qtd_inscritos'] for m in municipios_dados)

    # Ordena por nota para achar máximos, mínimos e top 5
    municipios_ordenados_por_nota = sorted(municipios_dados, key=lambda x: x['nota_media_geral'])
    nota_minima_m = municipios_ordenados_por_nota[0]
    nota_maxima_m = municipios_ordenados_por_nota[-1]

    # 2. Agrupamento por Faixa de Vulnerabilidade (Provando a tese do grupo)
    # Classifica direto pelas faixas do índice (0 a 1)
    grupos_vuln = {'Baixa (0.0 a 0.25)': [], 'Média-Baixa (0.25 a 0.5)': [], 'Média-Alta (0.5 a 0.75)': [], 'Alta (0.75 a 1.0)': []}

    for m in municipios_dados:
        v = m['indice_vulnerabilidade_medio']
        if v <= 0.25:
            grupos_vuln['Baixa (0.0 a 0.25)'].append(m['nota_media_geral'])
        elif v <= 0.50:
            grupos_vuln['Média-Baixa (0.25 a 0.5)'].append(m['nota_media_geral'])
        elif v <= 0.75:
            grupos_vuln['Média-Alta (0.5 a 0.75)'].append(m['nota_media_geral'])
        else:
            grupos_vuln['Alta (0.75 a 1.0)'].append(m['nota_media_geral'])

    # 3. Monta a string do Relatório Markdown
    relatorio = f"""# Relatório Estratégico Educacional - ENEM

## 1. Visão Geral da Base de Dados
- **Total de Municípios Analisados:** {total_municipios}
- **Total de Alunos Mapeados:** {total_alunos:,}
- **Maior Nota Média:** {nota_maxima_m['nota_media_geral']:.2f} pts ({nota_maxima_m['nome_municipio']}-{nota_maxima_m['uf']})
- **Menor Nota Média:** {nota_minima_m['nota_media_geral']:.2f} pts ({nota_minima_m['nome_municipio']}-{nota_minima_m['uf']})

## 2. Cruzamento de Dados (Tese do Grupo)
Análise do impacto da vulnerabilidade socioeconômica no desempenho médio:

| Faixa de Vulnerabilidade Bruta | Nota Média Geral do ENEM | Cidades no Grupo |
|--------------------------------|--------------------------|------------------|
"""
    for faixa, notas in grupos_vuln.items():
        media_grupo = sum(notas) / len(notas) if notas else 0
        relatorio += f"| {faixa:<30} | {media_grupo:.2f} pts               | {len(notas):<16} |\n"

    # 4. Top 5 Cidades de Maior Desempenho
    relatorio += """
## 3. Top 5 Municípios com Maiores Notas Médias
"""
    top_5 = municipios_ordenados_por_nota[-5:]
    top_5.reverse()
    for m in top_5:
        relatorio += f"- **{m['nome_municipio']} ({m['uf']}):** {m['nota_media_geral']:.2f} pts\n"

    # Exibe na tela do terminal na hora
    print("\n" + "="*55)
    print("📈 RELATÓRIO PROCESSADO SEM DEPENDÊNCIAS DE HARDWARE")
    print("="*55)
    print(relatorio)
    print("="*55)

    # Salva o arquivo final Markdown
    with open("relatorio_enem_final.md", "w", encoding="utf-8") as f:
        f.write(relatorio)
    print("✅ Sucesso! O arquivo Markdown foi gerado e salvo como: 'relatorio_enem_final.md'")

if __name__ == "__main__":
    main()
