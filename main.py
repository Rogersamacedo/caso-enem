# =============================================================
# main.py — Interface de Inicialização do Agente Consultor
#
# Permite que o usuário informe o município de interesse, busca os
# dados do ENEM automaticamente no arquivo Parquet unificado e
# abre o modo de chat interativo (conversa livre com histórico).
# =============================================================

import sys
from agente import AgenteConsultor

def main():
    print("=" * 65)
    print("   BEM-VINDO AO AGENTE CONSULTOR ESTRATÉGICO EDUCACIONAL   ")
    print("                Análise Socioeconômica - ENEM              ")
    print("=" * 65)
    
    # 1. Inicializa o agente carregando as configurações da IBM
    try:
        print("🤖 Inicializando inteligência do agente...")
        agente = AgenteConsultor()
    except Exception as e:
        print(f"\n❌ Erro crítico ao carregar o agente: {e}")
        print("Verifique se o seu arquivo .env está configurado corretamente.")
        sys.exit(1)

    # 2. Loop de busca do município com o Parquet unificado
    perfil_resumo = None
    while not perfil_resumo:
        print("\n📍 Digite o nome do município que deseja analisar (ou 'sair'):")
        municipio_input = input("👉 ").strip()
        
        if municipio_input.lower() in ['sair', 'exit', 'q']:
            print("\n👋 Encerrando consultoria. Até logo!")
            sys.exit(0)
            
        if not municipio_input:
            print("⚠️ Por favor, digite um nome válido.")
            continue
            
        try:
            print(f"\n🔍 Buscando '{municipio_input}' na base unificada do grupo...")
            # Chama a função modificada que lê direto do Parquet do seu colega
            perfil_resumo = agente.iniciar_sessao(municipio_input)
            
            print("\n" + "=" * 50)
            print("📊 PERFIL EDUCACIONAL CONTEXTUALIZADO")
            print("=" * 50)
            print(perfil_resumo)
            print("=" * 50)
            
        except FileNotFoundError as e:
            print(f"\n❌ {e}")
            print("Certifique-se de que o arquivo 'tabela_municipio_final.parquet' está nesta pasta.")
            sys.exit(1)
        except ValueError as e:
            print(f"\n⚠️ {e}")
            print("Tente digitar o nome completo com acentos se necessário (Ex: São Paulo, Ribeirão Preto).")
            continue

    # 3. Inicializa o loop de Chat Interativo
    print("\n💬 Sessão de chat iniciada! Você pode fazer perguntas sobre estratégias de")
    print("   investimento, contratação de Professores vs. Tutores ou indicadores locais.")
    print("   Digite 'voltar' para escolher outra cidade ou 'sair' para encerrar.")
    print("-" * 65)

    while True:
        pergunta = input("\n👤 Você: ").strip()
        
        if not pergunta:
            continue
            
        if pergunta.lower() in ['sair', 'exit', 'q']:
            print("\n👋 Encerrando consultoria. Até logo!")
            break
            
        if pergunta.lower() == 'voltar':
            print("\n🔄 Reiniciando o pipeline para nova busca...")
            agente.limpar_historico()
            main() # Recomeça o fluxo
            break

        # Envia a pergunta ao Watsonx através do histórico contextualizado
        resposta = agente.chat(pergunta)
        print(f"\n🤖 Agente:\n{resposta}")
        print("-" * 65)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Operação cancelada pelo usuário. Saindo...")
        sys.exit(0)
