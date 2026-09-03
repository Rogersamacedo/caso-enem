# =============================================================
# main.py — Orquestrador do pipeline Caso ENEM
#
# Ranking geral (sem agente):
#   python main.py --amostra 100000
#
# Recomendação única para um município:
#   python main.py --amostra 100000 --municipio "Salvador"
#
# Modo interativo — conversa livre com o agente no terminal:
#   python main.py --amostra 100000 --municipio "Salvador" --interativo
# =============================================================

import argparse
import sys
import textwrap

import config
from analise import (
    calcular_score_vulnerabilidade,
    carregar_microdados,
    obter_perfil_municipio,
)
from agente import AgenteConsultor

# Largura da linha para formatação do terminal
_LARGURA = 65


def _separador(char: str = "=") -> str:
    return char * _LARGURA


def _imprimir_ranking(df_agg) -> None:
    """Imprime os rankings dos 10 municípios mais e menos vulneráveis."""
    colunas = ["municipio", "uf", "score_vulnerabilidade", "perfil", "n_alunos"]

    print()
    print(_separador())
    print("  TOP 10 — MAIOR VULNERABILIDADE  →  PRIORIDADE: TUTORES")
    print(_separador())
    print(df_agg.head(10)[colunas].to_string(index=False))

    print()
    print(_separador())
    print("  TOP 10 — MENOR VULNERABILIDADE  →  PRIORIDADE: PROFESSORES")
    print(_separador())
    print(df_agg.tail(10)[colunas].to_string(index=False))
    print()


def _imprimir_perfil(perfil: dict) -> None:
    """Imprime os indicadores do município de forma legível."""
    print()
    print(_separador("-"))
    print(f"  PERFIL SOCIOECONÔMICO — {perfil['municipio']} ({perfil['uf']})")
    print(_separador("-"))
    print(f"  Score de vulnerabilidade : {perfil['score_vulnerabilidade']}/100")
    print(f"  Classificação            : {perfil['perfil']}")
    print(f"  % sem internet em casa   : {perfil['pct_sem_internet']}%")
    print(f"  % renda ≤ 1 salário mín. : {perfil['pct_renda_baixa']}%")
    print(f"  % pais sem Ensino Médio  : {perfil['pct_pais_baixa_escolaridade']}%")
    print(f"  Alunos analisados        : {perfil['n_alunos']:,}")
    print(_separador("-"))


def _imprimir_recomendacao(municipio: str, uf: str, texto: str) -> None:
    """Imprime a recomendação do agente com formatação limpa."""
    print()
    print(_separador())
    print(f"  RECOMENDAÇÃO ESTRATÉGICA — {municipio} ({uf})")
    print(_separador())
    # Quebra de linha automática para respeitar a largura do terminal
    for linha in texto.split("\n"):
        if linha.strip():
            print(textwrap.fill(linha, width=_LARGURA, subsequent_indent="  "))
        else:
            print()
    print(_separador())
    print()


def _modo_interativo(agente, perfil: dict) -> None:
    """Loop de conversa interativa no terminal.

    O agente mantém o histórico completo da sessão — cada pergunta
    digitada recebe uma resposta que considera tudo que foi dito antes.

    Comandos especiais:
      sair   → encerra a sessão
      perfil → exibe novamente os indicadores do município
      limpar → apaga o histórico e recomeça a conversa
    """
    print()
    print(_separador())
    print("  MODO INTERATIVO — AGENTE CONSULTOR ENEM")
    print(_separador())
    print(f"  Município: {perfil['municipio']} ({perfil['uf']}) | "
          f"Score: {perfil['score_vulnerabilidade']} | Perfil: {perfil['perfil']}")
    print(_separador())
    print("  Comandos: 'sair' | 'perfil' | 'limpar'")
    print(_separador())
    print()

    # Passo 1: gera a análise inicial usando consultar() — modo estático limpo
    print("[agente] Gerando análise inicial... aguarde.", flush=True)
    print("[agente] (Pode demorar até 2 min se houver fila no servidor)\n", flush=True)
    try:
        resposta_inicial = agente.consultar(perfil)
    except Exception as e:
        print(f"\n[ERRO] {e}\n")
        return

    _imprimir_recomendacao(perfil["municipio"], perfil["uf"], resposta_inicial)

    # Passo 2: prepara o histórico com a troca inicial para manter contexto
    agente.iniciar_sessao(perfil)
    agente._historico.append({"role": "assistant", "content": resposta_inicial})

    # Passo 3: loop de conversa livre
    print("  Digite sua pergunta ou um dos comandos abaixo:")
    print("  'sair' → encerra | 'perfil' → mostra indicadores | 'limpar' → reseta")
    print()

    while True:
        try:
            entrada = input(">>> Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[agente] Sessão encerrada.")
            break

        if not entrada:
            continue

        if entrada.lower() == "sair":
            print("\n[agente] Sessão encerrada. Até logo!")
            break

        if entrada.lower() == "perfil":
            _imprimir_perfil(perfil)
            continue

        if entrada.lower() == "limpar":
            agente.limpar_historico()
            agente.iniciar_sessao(perfil)
            agente._historico.append({"role": "assistant", "content": resposta_inicial})
            print("\n[agente] Histórico limpo. Pode perguntar algo novo.\n")
            continue

        print("\n[agente] Consultando... aguarde.\n")
        try:
            resposta = agente.chat(entrada)
        except Exception as e:
            print(f"\n[ERRO] {e}\n")
            continue

        print()
        print(_separador("-"))
        for linha in resposta.split("\n"):
            if linha.strip():
                print(textwrap.fill(linha, width=_LARGURA, subsequent_indent="  "))
            else:
                print()
        print(_separador("-"))
        print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Caso ENEM — Agente Consultor Estratégico\n"
            "Analisa os microdados do ENEM e recomenda onde investir\n"
            "em Professores (conteúdo) ou Tutores (suporte integral)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Exemplos:
              # Ranking sem agente (rápido)
              python main.py --amostra 100000

              # Recomendação única para um município
              python main.py --amostra 100000 --municipio "Salvador"

              # Modo interativo — conversa livre no terminal
              python main.py --amostra 100000 --municipio "Salvador" --interativo
              python main.py --amostra 100000 --municipio "Recife"   --interativo
            """
        ),
    )
    parser.add_argument(
        "--dados",
        default=config.CAMINHO_DADOS_PADRAO,
        metavar="CAMINHO",
        help=(
            f"Caminho para o arquivo PARTICIPANTES_XXXX.csv "
            f"(padrão: {config.CAMINHO_DADOS_PADRAO})"
        ),
    )
    parser.add_argument(
        "--municipio",
        default=None,
        metavar="NOME",
        help=(
            "Nome (ou parte do nome) do município a consultar. "
            "Se omitido, exibe o ranking dos 10 mais e 10 menos vulneráveis."
        ),
    )
    parser.add_argument(
        "--amostra",
        default=None,
        type=int,
        metavar="N",
        help=(
            "Carrega apenas as primeiras N linhas do CSV. "
            "Recomendado para máquinas com pouca RAM. "
            "Ex: --amostra 100000 (rápido) ou --amostra 500000 (representativo). "
            "Omitir carrega o dataset completo (~4,8 milhões de linhas)."
        ),
    )
    parser.add_argument(
        "--interativo",
        action="store_true",
        default=False,
        help=(
            "Abre o modo de conversa interativa após a análise inicial. "
            "Requer --municipio. Ideal para apresentações e perguntas livres."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    # --- 1. Carregar e processar os microdados ---
    try:
        df_bruto = carregar_microdados(args.dados, amostra=args.amostra)
    except FileNotFoundError:
        print(
            f"\n[ERRO] Arquivo não encontrado: {args.dados}\n"
            "Verifique o caminho ou use --dados para informar o local correto.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    df_agg = calcular_score_vulnerabilidade(df_bruto)

    # --- 2. Modo ranking (sem município informado) ---
    if args.municipio is None:
        _imprimir_ranking(df_agg)
        print(
            "Dica: use --municipio \"<nome>\" para obter a recomendação "
            "estratégica detalhada de um município específico."
        )
        return

    # --- 3. Modo consulta (com município informado) ---
    perfil = obter_perfil_municipio(df_agg, args.municipio)

    if perfil is None:
        print(
            f"\n[ERRO] Município \"{args.municipio}\" não encontrado nos dados.\n"
            "Verifique a grafia ou tente uma parte do nome (ex: \"Paulo\" para \"São Paulo\").\n",
            file=sys.stderr,
        )
        sys.exit(1)

    _imprimir_perfil(perfil)

    try:
        agente = AgenteConsultor()
    except EnvironmentError as e:
        print(f"\n[ERRO] {e}\n", file=sys.stderr)
        sys.exit(1)

    # --- 4. Modo interativo ou estático ---
    if args.interativo:
        _modo_interativo(agente, perfil)
    else:
        print("\n[agente] Consultando IBM watsonx.ai... aguarde.\n")
        recomendacao = agente.consultar(perfil)
        _imprimir_recomendacao(perfil["municipio"], perfil["uf"], recomendacao)


if __name__ == "__main__":
    main()
