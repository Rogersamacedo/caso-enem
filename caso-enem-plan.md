# Plano: Caso ENEM — Agente Consultor Estratégico (Trilha 4)

## Visão Geral

**Objetivo:** Construir uma solução Python que processa os microdados socioeconômicos do ENEM, calcula um perfil de vulnerabilidade por município e alimenta um Agente Consultor estratégico (via IBM watsonx.ai / llama-3-3-70b-instruct) que responde à pergunta de negócio:

> _"Onde o gestor escolar deve investir em **Professores** (foco em conteúdo) e onde deve investir em **Tutores** (suporte emocional, metodológico e contorno da falta de estrutura física)?"_

**Escopo:**
- Leitura e filtragem dos microdados do ENEM (CSV, separador `;`, encoding `latin-1`)
- Seleção e cruzamento de variáveis socioeconômicas relevantes
- Cálculo de score de vulnerabilidade por município/UF
- Classificação dos municípios em perfis de investimento
- Agente conversacional via IBM watsonx.ai que interpreta o perfil e gera recomendação textual

**Fora de escopo:**
- Interface gráfica ou dashboard
- Análise de desempenho nas provas (notas)
- Deploy em produção

---

## Variáveis Socioeconômicas Selecionadas

As variáveis abaixo estão disponíveis no dicionário oficial dos microdados ENEM (INEP) e são os pilares do score de vulnerabilidade:

| Código ENEM        | Descrição                              | Papel no modelo                          |
|--------------------|----------------------------------------|------------------------------------------|
| `Q001`             | Escolaridade do pai                    | Proxy de capital cultural familiar       |
| `Q002`             | Escolaridade da mãe                    | Proxy de capital cultural familiar       |
| `Q006`             | Renda familiar mensal                  | Capacidade econômica da família          |
| `Q025`             | Acesso à internet em casa              | Proxy de acesso a recursos digitais      |
| `TP_ESCOLA`        | Tipo de escola (pública/privada)       | Contexto institucional do aluno          |
| `NO_MUNICIPIO_ESC` | Município da escola                    | Granularidade geográfica                 |
| `SG_UF_ESC`        | UF da escola                           | Agrupamento regional                     |

**Lógica de cruzamento:**
- Renda baixa (`Q006` <= faixa 4: até R$ 1.212) + sem internet (`Q025 = B`) + pais sem ensino médio (`Q001/Q002` <= C) → **Alta Vulnerabilidade** → recomendação de **Tutor**
- Renda média/alta + com internet + pais com ensino superior → **Baixa Vulnerabilidade** → recomendação de **Professor**
- Casos intermediários → score ponderado decide

---

## Estrutura de Arquivos

```
caso_enem/
├── .env                  # Credenciais IBM watsonx.ai (não versionado)
├── .gitignore            # Exclui .env e dados brutos
├── requirements.txt      # Dependências Python
├── config.py             # Constantes: colunas, pesos, limiares
├── analise.py            # ETL + cálculo do score de vulnerabilidade
├── agente.py             # Agente IBM watsonx.ai + lógica de prompt
└── main.py               # Ponto de entrada: orquestra analise.py e agente.py
```

---

## Sub-Tarefas

---

### Sub-Tarefa 1 — Configuração do Ambiente e Estrutura Base

**Intent:** Preparar o ambiente Python com todas as dependências e criar os arquivos de scaffolding do projeto antes de qualquer lógica de negócio.

**Expected Outcomes:**
- `requirements.txt` com pandas, python-dotenv e ibm-watsonx-ai
- `.gitignore` protegendo `.env` e arquivos de dados brutos
- `.env` com placeholders documentados para `WATSONX_API_KEY`, `WATSONX_PROJECT_ID` e `WATSONX_URL`
- `config.py` com as constantes do projeto (nomes de colunas, faixas de renda, pesos do score)

**Todo List:**
1. Criar `requirements.txt` com: `pandas`, `python-dotenv`, `ibm-watsonx-ai`
2. Criar `.gitignore` excluindo `.env`, `*.csv`, `__pycache__/`
3. Criar `.env` com as três variáveis de ambiente documentadas como placeholders
4. Criar `config.py` definindo: lista de colunas a importar, mapeamento das faixas de renda do ENEM, pesos do score de vulnerabilidade, limiar de corte Alto/Médio/Baixo

**Relevant Context:**
- Autenticação watsonx.ai: `WATSONX_API_KEY` + `WATSONX_PROJECT_ID` + `WATSONX_URL`
- Modelo alvo: `meta-llama/llama-3-3-70b-instruct`
- Encoding dos microdados: `latin-1`, separador: `;`

**Status:** `[x] done`

---

### Sub-Tarefa 2 — Módulo de Análise (`analise.py`)

**Intent:** Implementar o pipeline de ETL e o cálculo do score de vulnerabilidade socioeconômica por município, que é a matéria-prima para o agente.

**Expected Outcomes:**
- Função `carregar_microdados(caminho: str) -> pd.DataFrame` que lê o CSV com as colunas corretas
- Função `calcular_score_vulnerabilidade(df: pd.DataFrame) -> pd.DataFrame` que retorna um DataFrame agregado por município com colunas: `municipio`, `uf`, `score_vulnerabilidade` (0–100), `perfil` (Alto/Médio/Baixo), `n_alunos`
- Função `obter_perfil_municipio(df_agg: pd.DataFrame, municipio: str) -> dict` que retorna o perfil de um município específico como dicionário

**Lógica do Score (ponderação sugerida em config.py):**
- Renda baixa contribui com peso 40%
- Sem acesso à internet contribui com peso 30%
- Pais sem ensino médio contribui com peso 30%
- Score final normalizado de 0 (baixa vulnerabilidade) a 100 (alta vulnerabilidade)

**Todo List:**
1. Implementar `carregar_microdados()`: leitura com `usecols` para economizar memória, tratamento de valores ausentes nas colunas socioeconômicas
2. Implementar a lógica de pontuação individual por aluno usando as faixas definidas em `config.py`
3. Implementar agregação por `NO_MUNICIPIO_ESC` + `SG_UF_ESC`: média do score, classificação em perfil
4. Implementar `obter_perfil_municipio()` para lookup por nome
5. Adicionar bloco `if __name__ == "__main__"` para teste rápido com print do top-10 municípios mais vulneráveis

**Relevant Context:**
- Colunas a usar: definidas na Sub-Tarefa 1 em `config.py`
- Arquivo de dados em: `~/Downloads/` (gestor deve copiar para o projeto ou passar o caminho via argumento)
- Filtrar apenas `TP_PRESENCA_CH == 1` e `TP_PRESENCA_CN == 1` (presentes na prova) para evitar distorções
- **Nota pós-implementação:** O arquivo PARTICIPANTES_2025.csv não possui TP_PRESENCA — essa coluna está apenas em RESULTADOS_2025.csv. O filtro foi removido sem impacto, pois participantes sem presença simplesmente não respondem ao questionário socioeconômico.
- **Nota pós-implementação:** Q025 (internet) e Q006 (renda) foram renomeados em 2025 para Q020 e Q007 respectivamente. config.py foi atualizado.

**Status:** `[x] done`

---

### Sub-Tarefa 3 — Módulo do Agente (`agente.py`)

**Intent:** Implementar o Agente Consultor Estratégico que recebe o perfil socioeconômico de um município e retorna uma recomendação fundamentada sobre onde investir em Professores vs. Tutores.

**Expected Outcomes:**
- Classe `AgenteConsultor` com método `consultar(perfil: dict) -> str`
- O método constrói um prompt estruturado com os dados do perfil e envia ao modelo `meta-llama/llama-3-3-70b-instruct` via `ibm-watsonx-ai`
- A resposta inclui: diagnóstico do perfil, recomendação principal (Professor ou Tutor), justificativa baseada nos dados, e ações concretas sugeridas

**Modelo Lógico do Prompt:**

```
[SISTEMA] Você é um Consultor Estratégico Educacional especialista em dados do ENEM.
Seu papel é ajudar gestores escolares a decidir onde alocar recursos humanos.

Regras de decisão:
- Score de vulnerabilidade ALTO (>= 65): recomendar TUTOR como prioridade
- Score de vulnerabilidade BAIXO (<= 35): recomendar PROFESSOR como prioridade
- Score MÉDIO (36-64): recomendar COMBINAÇÃO com ênfase explicada pelos dados

[USUÁRIO] Perfil do município {municipio} - {uf}:
- Score de vulnerabilidade: {score}/100
- Perfil: {perfil}
- % alunos sem internet: {pct_sem_internet}%
- % alunos com renda familiar até R$1.212: {pct_renda_baixa}%
- % alunos com pais sem ensino médio: {pct_pais_baixa_escolaridade}%
- Total de alunos analisados: {n_alunos}
```

**Todo List:**
1. Implementar classe `AgenteConsultor.__init__()`: carrega `.env`, instancia cliente `ibm_watsonx_ai.foundation_models.ModelInference`
2. Implementar método `_construir_prompt(perfil: dict) -> str` usando o template acima
3. Implementar método `consultar(perfil: dict) -> str`: chama o modelo e retorna o texto da resposta
4. Adicionar parâmetros de inferência: `max_new_tokens=500`, `temperature=0.3`
5. Adicionar bloco `if __name__ == "__main__"` com perfil de exemplo hardcoded para teste isolado

**Relevant Context:**
- Autenticação watsonx.ai: usar `Credentials(url=..., api_key=...)` + `project_id`
- Sub-Tarefa 2 deve estar concluída pois `perfil` é o dict retornado por `obter_perfil_municipio()`
- Temperatura baixa (0.3) para garantir consistência nas recomendações estratégicas
- **Nota pós-implementação:** Prompt usa formato nativo Llama 3 (`<|begin_of_text|>`, `<|start_header_id|>`) para melhor aproveitamento do modelo.
- **Nota pós-implementação:** Adicionado `REPETITION_PENALTY=1.1` para evitar loops de texto na geração.

**Status:** `[x] done`

---

### Sub-Tarefa 4 — Ponto de Entrada (`main.py`)

**Intent:** Criar o script principal que orquestra a análise e o agente, tornando o sistema utilizável com um único comando e parâmetros de linha de comando.

**Expected Outcomes:**
- `main.py` que aceita argumentos: `--dados` (caminho do CSV), `--municipio` (nome do município a consultar)
- Executa o pipeline completo: carrega → calcula score → consulta agente → imprime recomendação formatada
- Se `--municipio` não for informado, imprime o ranking dos 10 municípios mais vulneráveis e os 10 menos vulneráveis

**Todo List:**
1. Implementar parsing de argumentos com `argparse`: `--dados` (obrigatório), `--municipio` (opcional)
2. Chamar `carregar_microdados()` e `calcular_score_vulnerabilidade()` de `analise.py`
3. Se `--municipio` fornecido: chamar `obter_perfil_municipio()` → `AgenteConsultor().consultar()` → imprimir resultado
4. Se `--municipio` não fornecido: imprimir tabela formatada com top-10 vulneráveis e top-10 seguros
5. Adicionar tratamento de erro claro se o município não for encontrado nos dados

**Relevant Context:**
- Exemplo de uso: `python main.py --municipio "Salvador"`
- Sub-Tarefas 1, 2 e 3 devem estar concluídas

**Status:** `[x] done`

---

## Sequência de Implementação

```
Sub-Tarefa 1 (ambiente) → Sub-Tarefa 2 (analise.py) → Sub-Tarefa 3 (agente.py) → Sub-Tarefa 4 (main.py)
```

Cada sub-tarefa é independente da próxima e pode ser revisada antes de avançar.
