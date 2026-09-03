# =============================================================
# agente.py — Agente Consultor Estratégico Educacional
#
# Recebe o perfil socioeconômico de um município (gerado por
# analise.py) e consulta o IBM watsonx.ai para gerar uma
# recomendação estratégica: investir em Professores ou Tutores.
#
# Suporta dois modos:
#   - consultar(perfil)      → recomendação única (modo estático)
#   - chat(pergunta)         → conversa livre com histórico (modo interativo)
#
# Modelo configurável em config.py (WATSONX_MODEL_ID)
# Autenticação: WATSONX_API_KEY + WATSONX_PROJECT_ID + WATSONX_URL
#               definidos em .env (ver env.example)
# =============================================================

import os
import time
import warnings

# Suprime warnings informativos do watsonx (licença de terceiros, etc.)
warnings.filterwarnings("ignore", category=UserWarning, module="ibm_watsonx_ai")

from dotenv import load_dotenv
from ibm_watsonx_ai.credentials import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.wml_client_error import ApiRequestFailure

import config

# Número máximo de tentativas e espera inicial (s) para erro 429
# Backoff com teto de 60s: 15 → 30 → 60 → 60 → 60 → 60 → 60
_MAX_TENTATIVAS = 10
_ESPERA_INICIAL = 15
_ESPERA_MAXIMA  = 60

# ------------------------------------------------------------------
# Guardrail Nível 1 — validação local (sem custo de API)
# ------------------------------------------------------------------

# Palavras-chave que indicam perguntas DENTRO do escopo permitido
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

# Tamanho mínimo de pergunta para aplicar o guardrail (perguntas curtas são liberadas)
_GUARDRAIL_MIN_CHARS = 10

# Mensagem padrão de resposta fora de escopo
_MSG_FORA_DE_ESCOPO = (
    "⚠️  Essa pergunta está fora do escopo desta consultoria educacional.\n\n"
    "Estou aqui para ajudar com:\n"
    "  • Estratégias de contratação (Professor vs. Tutor)\n"
    "  • Análise do perfil socioeconômico do município\n"
    "  • Interpretação dos indicadores do ENEM\n"
    "  • Ações para abertura de nova instituição de ensino\n\n"
    "Como posso te ajudar nesse contexto?"
)


def _esta_no_escopo(pergunta: str) -> bool:
    """Verifica se a pergunta está dentro do contexto educacional/ENEM.

    Lógica: retorna True se qualquer palavra-chave do escopo for encontrada
    na pergunta (case-insensitive). Perguntas muito curtas são sempre liberadas.

    Parâmetros
    ----------
    pergunta : str
        Texto digitado pelo usuário.

    Retorna
    -------
    bool
        True = dentro do escopo → enviar ao modelo.
        False = fora do escopo → retornar mensagem padrão.
    """
    if len(pergunta.strip()) < _GUARDRAIL_MIN_CHARS:
        return True  # Perguntas curtas (ex: "ok", "sim") são sempre liberadas

    pergunta_lower = pergunta.lower()
    return any(palavra in pergunta_lower for palavra in _PALAVRAS_ESCOPO)

# Prompt do sistema: define o papel e as regras de decisão do agente
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
    """Formata os dados do município como texto para injetar no contexto."""
    return (
        f"Município: {perfil['municipio']} ({perfil['uf']})\n"
        f"Score de vulnerabilidade: {perfil['score_vulnerabilidade']}/100 — Perfil: {perfil['perfil']}\n"
        f"% alunos sem internet em casa: {perfil['pct_sem_internet']}%\n"
        f"% renda familiar até 1 salário mínimo: {perfil['pct_renda_baixa']}%\n"
        f"% pais sem Ensino Médio completo: {perfil['pct_pais_baixa_escolaridade']}%\n"
        f"Total de alunos analisados: {perfil['n_alunos']}"
    )


class AgenteConsultor:
    """Agente Consultor Estratégico via IBM watsonx.ai.

    Modos de uso
    ------------
    # Recomendação única (modo estático):
    agente = AgenteConsultor()
    print(agente.consultar(perfil))

    # Conversa livre com histórico (modo interativo):
    agente = AgenteConsultor()
    agente.iniciar_sessao(perfil)
    print(agente.chat("Qual a diferença entre tutor e professor aqui?"))
    print(agente.chat("E para o ensino médio especificamente?"))
    agente.limpar_historico()
    """

    def __init__(self):
        """Carrega credenciais e prepara o agente. A conexão com o
        modelo é feita de forma lazy — só na primeira chamada real."""
        load_dotenv()

        self._api_key    = os.getenv("WATSONX_API_KEY")
        self._project_id = os.getenv("WATSONX_PROJECT_ID")
        self._url        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

        if not self._api_key or not self._project_id:
            raise EnvironmentError(
                "Credenciais não encontradas. Verifique se o arquivo .env existe e "
                "contém WATSONX_API_KEY e WATSONX_PROJECT_ID. "
                "Use env.example como referência."
            )

        # Parâmetros para a API chat
        self._chat_params = {
            "max_tokens":         config.WATSONX_MAX_NEW_TOKENS,
            "temperature":        config.WATSONX_TEMPERATURE,
            "repetition_penalty": 1.1,
            "time_limit":         60000,  # 60s timeout por chamada
        }

        # Modelo instanciado de forma lazy em _get_model()
        self._model = None

        # Histórico de mensagens para o modo interativo
        self._historico: list[dict] = []
        self._perfil_ativo: dict | None = None

    def _get_model(self) -> ModelInference:
        """Instancia o modelo na primeira chamada (lazy loading).
        Evita conexão desnecessária durante a carga dos dados."""
        if self._model is None:
            print("[agente] Conectando ao IBM watsonx.ai...", flush=True)
            credentials = Credentials(url=self._url, api_key=self._api_key)
            self._model = ModelInference(
                model_id=config.WATSONX_MODEL_ID,
                credentials=credentials,
                project_id=self._project_id,
                validate=False,   # evita chamada de validação extra na inicialização
            )
            print("[agente] Conectado.", flush=True)
        return self._model

    # ------------------------------------------------------------------
    # Modo estático — recomendação única
    # ------------------------------------------------------------------

    def consultar(self, perfil: dict) -> str:
        """Gera a recomendação estratégica completa para um município.

        Usa a API chat com uma única rodada — não mantém histórico.

        Parâmetros
        ----------
        perfil : dict
            Dicionário retornado por `analise.obter_perfil_municipio()`.

        Retorna
        -------
        str
            Texto completo da recomendação gerada pelo modelo.
        """
        mensagens = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Analise o perfil socioeconômico abaixo e gere a "
                    f"recomendação estratégica completa nos 4 blocos solicitados:\n\n"
                    f"{_resumo_perfil(perfil)}"
                ),
            },
        ]
        return self._enviar(mensagens)

    # ------------------------------------------------------------------
    # Modo interativo — conversa com histórico
    # ------------------------------------------------------------------

    def iniciar_sessao(self, perfil: dict) -> None:
        """Prepara o agente para uma sessão de conversa interativa.

        Injeta os dados do município no contexto inicial e limpa
        qualquer histórico anterior.

        Parâmetros
        ----------
        perfil : dict
            Dicionário retornado por `analise.obter_perfil_municipio()`.
        """
        self._perfil_ativo = perfil
        self._historico = []

        # Primeira mensagem do usuário já traz os dados do município
        contexto_inicial = (
            f"Vou te consultar sobre a estratégia de contratação para uma nova "
            f"instituição de ensino. Aqui estão os dados do município:\n\n"
            f"{_resumo_perfil(perfil)}\n\n"
            f"Com base nesses dados, gere a recomendação estratégica completa "
            f"nos 4 blocos solicitados (Diagnóstico, Recomendação, Justificativa "
            f"e Ações Estratégicas)."
        )
        self._historico.append({"role": "user", "content": contexto_inicial})

    def chat(self, pergunta: str) -> str:
        """Envia uma pergunta livre e retorna a resposta do agente.

        Mantém o histórico completo da conversa para que o modelo
        lembre do contexto do município e das respostas anteriores.

        Parâmetros
        ----------
        pergunta : str
            Texto digitado pelo usuário no console.

        Retorna
        -------
        str
            Resposta do modelo com o contexto acumulado.
        """
        if not self._historico:
            raise RuntimeError(
                "Sessão não iniciada. Chame iniciar_sessao(perfil) antes de chat()."
            )

        # --- Guardrail Nível 1: validação local antes de chamar a API ---
        if not _esta_no_escopo(pergunta):
            return _MSG_FORA_DE_ESCOPO

        # Adiciona a nova pergunta ao histórico
        self._historico.append({"role": "user", "content": pergunta})

        # Monta mensagens completas: system + histórico acumulado
        mensagens = [{"role": "system", "content": _SYSTEM_PROMPT}] + self._historico

        resposta = self._enviar(mensagens)

        # Registra a resposta no histórico para a próxima rodada
        self._historico.append({"role": "assistant", "content": resposta})

        return resposta

    def limpar_historico(self) -> None:
        """Reseta o histórico e o perfil ativo da sessão."""
        self._historico = []
        self._perfil_ativo = None

    # ------------------------------------------------------------------
    # Envio com retry automático (429 backoff exponencial)
    # ------------------------------------------------------------------

    def _enviar(self, mensagens: list[dict]) -> str:
        """Envia mensagens para a API chat com retry em caso de 429.

        Parâmetros
        ----------
        mensagens : list[dict]
            Lista de dicts no formato {"role": ..., "content": ...}.

        Retorna
        -------
        str
            Texto da resposta gerada pelo modelo.
        """
        espera = _ESPERA_INICIAL

        for tentativa in range(1, _MAX_TENTATIVAS + 1):
            try:
                print(f"[agente] Tentativa {tentativa}/{_MAX_TENTATIVAS}...", flush=True)
                resposta = self._get_model().chat(
                    messages=mensagens,
                    params=self._chat_params,
                )
                # A API chat retorna um dict com choices[0].message.content
                return resposta["choices"][0]["message"]["content"].strip()

            except ApiRequestFailure as e:
                msg = str(e)
                is_rate_limit = "429" in msg or "consumption_limit_reached" in msg

                if is_rate_limit and tentativa < _MAX_TENTATIVAS:
                    print(
                        f"\n[agente] Limite de requisições atingido (429). "
                        f"Aguardando {espera}s antes da tentativa "
                        f"{tentativa + 1}/{_MAX_TENTATIVAS}..."
                    )
                    time.sleep(espera)
                    espera = min(espera * 2, _ESPERA_MAXIMA)  # teto de 60s
                else:
                    raise

        raise RuntimeError("Número máximo de tentativas esgotado.")


# ------------------------------------------------------------------
# Teste isolado (execução direta)
# ------------------------------------------------------------------

if __name__ == "__main__":
    perfis_exemplo = [
        {
            "municipio": "Alto Santo", "uf": "CE",
            "score_vulnerabilidade": 91.0, "perfil": "Alto",
            "n_alunos": 42, "pct_renda_baixa": 87.0,
            "pct_sem_internet": 74.0, "pct_pais_baixa_escolaridade": 92.0,
        },
        {
            "municipio": "Salvador", "uf": "BA",
            "score_vulnerabilidade": 41.4, "perfil": "Médio",
            "n_alunos": 760, "pct_renda_baixa": 43.0,
            "pct_sem_internet": 12.1, "pct_pais_baixa_escolaridade": 57.4,
        },
    ]

    agente = AgenteConsultor()

    for perfil in perfis_exemplo:
        sep = "=" * 65
        print(f"\n{sep}")
        print(f"  MUNICÍPIO: {perfil['municipio']} ({perfil['uf']}) — Perfil {perfil['perfil'].upper()}")
        print(sep)
        print(agente.consultar(perfil))
        print()
