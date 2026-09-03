# 🎓 Caso ENEM — Agente Consultor Estratégico

> **Trilha 4: Agente Especialista** — IBM watsonx.ai

Solução em Python que analisa os microdados socioeconômicos do ENEM 2025 e gera recomendações estratégicas para gestores escolares através de um Agente Consultor powered by IBM watsonx.ai.

## 🎯 Pergunta de Negócio

> *"Onde o gestor deve investir: em **Professores** (conteúdo) ou em **Tutores** (suporte emocional e metodológico)?"*

A resposta depende do perfil socioeconômico de cada município — e este projeto calcula isso automaticamente com base nos dados reais do ENEM.

---

## 🚀 Como Executar

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/caso_enem.git
cd caso_enem
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Configure as credenciais
```bash
cp env.example .env
# Edite o .env com suas credenciais IBM watsonx.ai
```

### 4. Baixe os microdados
Baixe o arquivo `PARTICIPANTES_XXXX.csv` em: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem

### 5. Execute

```bash
# Ranking geral de vulnerabilidade por município
python3 main.py --amostra 100000

# Recomendação estratégica para um município
python3 main.py --amostra 100000 --municipio "Salvador"

# Modo interativo — conversa livre com o agente
python3 main.py --amostra 100000 --municipio "Salvador" --interativo

# Usando outro caminho para os dados
python3 main.py --dados /caminho/para/PARTICIPANTES_2025.csv --municipio "Recife"
```

---

## 📊 Dashboard Visual

Abra `index.html` no navegador para acessar:
- 📊 **Dashboard Estratégico** — gráficos, rankings e tabelas
- 🗺️ **Mapa de Calor** — vulnerabilidade por UF, interativo

---

## 🏗️ Estrutura do Projeto

```
caso_enem/
├── .env               # Credenciais (NÃO versionado)
├── env.example        # Template das credenciais
├── requirements.txt   # Dependências Python
├── config.py          # Constantes e parâmetros
├── analise.py         # ETL + score de vulnerabilidade
├── agente.py          # Agente IBM watsonx.ai
├── main.py            # Ponto de entrada (CLI)
├── index.html         # Menu visual
├── dashboard.html     # Dashboard com gráficos
└── mapa.html          # Mapa interativo do Brasil
```

---

## 📐 Lógica do Score de Vulnerabilidade

| Indicador | Variável ENEM 2025 | Peso |
|---|---|---|
| Renda familiar baixa (≤ 1 salário mínimo) | `Q007` faixas A/B | 40% |
| Sem acesso à internet wi-fi em casa | `Q020` = A (Não) | 30% |
| Pais sem Ensino Médio completo | `Q001`/`Q002` faixas A-E | 30% |

**Classificação:**
- Score ≥ 65 → Perfil **Alto** → Recomendação: **TUTOR**
- Score ≤ 35 → Perfil **Baixo** → Recomendação: **PROFESSOR**
- Score 36–64 → Perfil **Médio** → Recomendação: **COMBINAÇÃO**

---

## 🤖 Modelo de IA

- **Plataforma:** IBM watsonx.ai
- **Modelo:** `mistralai/mistral-small-3-1-24b-instruct-2503`
- **API:** `/ml/v1/text/chat`
- **Retry automático:** até 10 tentativas com backoff exponencial (máx. 60s)
- **Guardrail:** validação local de escopo antes de chamar a API

---

## 📋 Variáveis de Ambiente

```env
WATSONX_API_KEY=sua_api_key_aqui
WATSONX_PROJECT_ID=seu_project_id_aqui
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

---

## 📦 Dependências

```
pandas>=2.2.2
python-dotenv>=1.0.1
ibm-watsonx-ai>=1.1.2
```

---

## 📚 Fonte dos Dados

- **Microdados ENEM 2025** — Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP)
- Dataset: 4,8 milhões de participantes · 27 UFs · 5.570 municípios
