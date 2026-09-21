# =============================================================
# agente.py — Agente Consultor Estratégico Educacional (UNIFICADO)
#
# Recebe o perfil socioeconômico de um município diretamente de um 
# arquivo .parquet (tabela_municipio_final.parquet) gerado pelo grupo,
# e consulta o IBM watsonx.ai para gerar recomendações estratégicas.
#
# Suporta dois modos:
#   - consultar(perfil)      → recomendação única (modo estático)
#   - chat(pergunta)         → conversa livre com histórico (modo interativo)
#
# Modelo configurável em config.py (WATSONX_MODEL_ID)
# =============================================================

import os
import time
import warnings
import pandas as pd

# Suprime warnings informativos do watsonx
warnings.filterwarnings("ignore", category=UserWarning, module="ibm_watsonx_ai")

from dotenv import load_dotenv
from ibm_watsonx_ai.credentials import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.wml_client_error import ApiRequestFailure

import config

# Configurações de Retentativa da API
_MAX_TENTATIVAS = 10
_ESPERA_INICIAL = 15
_ESPERA_MAXIMA  = 60

# ------------------------------------------------------------------
# Guardrail Nível 1 — Validação Local de Escopo
# ------------------------------------------------------------------
_PALAVRAS_ESCOPO = {
    "professor", "tutor", "escola", "ensino", "educação", "educacional",
    "aluno", "município", "municipio", "vulnerabilidade", "score", "perfil",
    "renda", "internet", "investimento", "contrat", "gestor", "instituição",
    "instituicao", "enem", "socioeconômico", "socioeconomico", "aprendizagem",
    "estratégia", "estrategia", "recomend", "indicador", "dados", "análise",
    "analise", "regional", "nordeste", "sudeste", "brasil", "público", "privado",
    "infraestrutura", "metodolog", "emocional", "suporte", "conteúdo", "conteudo",
    "capital cultural", "capital humano", "cultural", "familiar", "escolaridade", "pai", "mãe", "mae",
    "salário", "salario", "estrutura", "diferencial", "competitiv", "currículo",
    "curriculo", "resultado", "desempenho", "formação", "formacao", "recife",
    "salvador", "fortaleza", "são paulo", "sao paulo", "rio", "minas", "bahia",
    "ceará", "ceara", "pernambuco", "nordeste", "norte", "sul", "centro",
}

_GUARDRAIL_MIN_CHARS = 10

_MSG_FORA_DE_ESCOPO = (
    "⚠️  Essa pergunta está fora do escopo desta consultoria educacional.\n\n"
    "Estou aqui para ajudar com:\n"
    "  • Estratégias de contratação (Professor vs. Tutor)\n"
    "  • Análise do perfil socioeconômico do município baseado no ENEM\n"
    "  • Interpretação dos indicadores estruturais locais\n"
    "  • Ações para alocação de recursos em novas instituições de ensino\n\n"
    "Como posso te ajudar nesse contexto?"
)

def _esta_no_escopo(pergunta: str) -> bool:
    if len(pergunta.strip()) < _GUARDRAIL_MIN_CHARS:
        return True  
    pergunta_lower = pergunta.lower()
    return any(palavra in pergunta_lower for palavra in _PALAVRAS_ESCOPO)

# ------------------------------------------------------------------
# Mecanismo de Leitura Local do Parquet (Unificação)
# ------------------------------------------------------------------
def buscar_perfil_no_parquet(nome_municipio: str, caminho_parquet: str = "tabela_municipio_final.parquet") -> dict:
    """Busca o município no Parquet e extrai os indicadores estatísticos."""
    if not os.path.exists(caminho_parquet):
        raise FileNotFoundError(f"Erro: O arquivo '{caminho_parquet}' precisa estar nesta pasta.")
    
    # Prevenção de travamento de CPU: prioriza fastparquet se instalado
    try:
        df = pd.read_parquet(caminho_parquet, engine='fastparquet')
    except ImportError:
        df = pd.read_parquet(caminho_parquet)
        
    resultado = df[df['nome_municipio'].str.strip().str.lower() == nome_municipio.strip().lower()]
    
    if resultado.empty:
        raise ValueError(f"Município '{nome_municipio}' não foi encontrado na base de dados do ENEM.")
    
    # Extrai dados da primeira linha encontrada
    linha = resultado.iloc[0]
    idx_vulnerabilidade = float(linha.get('indice_vulnerabilidade_medio', 0))
    
    # Escala de 0 a 100 baseada na métrica original do colega
    score = int(idx_vulnerabilidade * 100)
    perfil_tipo = "Alto" if idx_vulnerabilidade >= 0.65 else ("Baixo" if idx_vulnerabilidade <= 0.35 else "Médio")
    
    return {
        'municipio':                     str(linha['nome_municipio']),
        'uf':                            str(linha.get('uf', 'UF')), 
        'score_vulnerabilidade':         score,
        'perfil':                        perfil_tipo,
        'pct_sem_internet':              round(float(linha.get('pct_sem_internet', 0)) * 100, 2),
        'pct_renda_baixa':               round(float(linha.get('pct_sem_renda_familiar', 0)) * 100, 2),
        'pct_pais_baixa_escolaridade':   round(float(linha.get('pct_pais_baixa_escolaridade', 0)) * 100, 2),
        'n_alunos':                      int(linha.get('qtd_inscritos', 0)),
        'nota_enem_geral':             round(float(linha.get('nota_media_geral', 0)), 1),
        'nota_redacao':                round(float(linha.get('nota_media_redacao', 0)), 1)
    }

# ------------------------------------------------------------------
# Prompts do Sistema e Formatação de Resumos
# ------------------------------------------------------------------
_SYSTEM_PROMPT = """Você é um Consultor Estratégico Educacional especialista em dados do ENEM e em gestão escolar.
Seu papel é ajudar gestores que desejam abrir uma nova instituição de ensino a decidir onde alocar seus recursos humanos.

Você deve recomendar entre dois perfis de profissional:
- PROFESSOR: especialista em conteúdo acadêmico. Indicado onde os alunos já têm estrutura (internet, renda adequada, apoio familiar com escolaridade) e o diferencial competitivo é o aprofundamento curricular.
- TUTOR: profissional de suporte integral. Indicado onde os alunos enfrentam vulnerabilidade socioeconômica — precisam de acolhimento emocional, orientação metodológica e compensação pela falta de estrutura em casa.

Regras de decisão baseadas no score de vulnerabilidade socioeconômica (0 a 100):
- Score ALTO (>= 65): priorize TUTORES. Esses alunos precisam de presença humana, vínculo e suporte antes do conteúdo.
- Score BAIXO (<= 35): priorize PROFESSORES. Esses alunos têm base e estrutura; o diferencial é o conhecimento aprofundado.
- Score MÉDIO (36 a 64): recomende COMBINAÇÃO, explicando qual perfil deve ser contratado primeiro e por quê, com base nos indicadores específicos do município.

Formato da sua resposta (sempre em português):
1. DIAGNÓSTICO DO PERFIL: resumo do que os dados revelam sobre o município.
2. RECOMENDAÇÃO PRINCIPAL: qual perfil contratar prioritariamente e por quê.
3. JUSTIFICATIVA POR INDICADOR: explique como cada indicador (renda, internet, escolaridade dos pais) influencia a decisão.
4. AÇÕES ESTRATÉGICAS SUGERIDAS: 3 ações concretas que o gestor deve tomar ao abrir a instituição nesse município."""

def _resumo_perfil(perfil: dict) -> str:
    """Formata os dados estruturados obtidos do Parquet para a LLM."""
    return (
        f"Município: {perfil['municipio']} ({perfil['uf']})\n"
        f"Score de vulnerabilidade: {perfil['score_vulnerabilidade']}/100 — Perfil: {perfil['perfil']}\n"
        f"% alunos sem internet em casa: {perfil['pct_sem_internet']}%\n"
        f"% renda familiar vulnerável: {perfil['pct_renda_baixa']}%\n"
        f"% pais sem Ensino Médio completo: {perfil['pct_pais_baixa_escolaridade']}%\n"
        f"Nota Média Geral do Município no ENEM: {perfil.get('nota_enem_geral', 'N/A')} pts\n"
        f"Nota Média da Redação: {perfil.get('nota_redacao', 'N/A')} pts\n"
        f"Total de alunos analisados: {perfil['n_alunos']}"
    )

# ------------------------------------------------------------------
# Classe Principal do Agente
# ------------------------------------------------------------------
class AgenteConsultor:
    def __init__(self):
        load_dotenv()
        self._api_key    = os.getenv("WATSONX_API_KEY")
        self._project_id = os.getenv("WATSONX_PROJECT_ID")
        self._url        = os.getenv("WATSONX_URL", "https://ibm.com")

        if not self._api_key or not self._project_id:
            raise EnvironmentError("Credenciais não encontradas no arquivo .env.")

        self._chat_params = {
            "max_tokens":         config.WATSONX_MAX_NEW_TOKENS,
            "temperature":        config.WATSONX_TEMPERATURE,
            "repetition_penalty": 1.1,
            "time_limit":         60000,
        }

        self._model = None
        self._historico: list[dict] = []
        self._perfil_ativo: dict | None = None

    def _get_model(self) -> ModelInference:
        if self._model is None:
            credentials = Credentials(url=self._url, api_key=self._api_key)
            self._model = ModelInference(
                model_id=config.WATSONX_MODEL_ID,
                credentials=credentials,
                project_id=self._project_id,
                params=self._chat_params
            )
        return self._get_model

    def iniciar_sessao(self, nome_municipio: str):
        """Nova função para iniciar o agente puxando os dados do Parquet."""
        perfil_mapeado = buscar_perfil_no_parquet(nome_municipio)
        self._perfil_ativo = perfil_mapeado
        
        resumo = _resumo_perfil(perfil_mapeado)
        self._historico = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "system", "content": f"Contexto Atual do Município Selecionado:\n{resumo}"}
        ]
        return resumo

    def chat(self, pergunta: str) -> str:
        """Modo interativo com tratamento de escopo local."""
        if not self._perfil_ativo:
            return "⚠️ Nenhuma sessão ativa. Inicie a sessão informando o município primeiro."
            
