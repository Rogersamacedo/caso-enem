
# 🎓 Caso ENEM 2025 — Plataforma de Análise Socioeconômica e Agente Consultor Estratégico

> Projeto de análise de dados educacionais que combina tratamento estatístico dos microdados do ENEM, dashboards interativos e um Agente Consultor Estratégico baseado em IA.

---

## 🎯 Visão geral

O projeto utiliza os microdados do **ENEM 2025** como fonte para construir uma camada de dados municipal tratada e agregada.

A solução transforma um conjunto de dados de grande volume em uma base consolidada por município, permitindo realizar:

- análise de desempenho educacional;
- análise de indicadores socioeconômicos;
- análise estatística;
- visualização interativa;
- interpretação dos indicadores por meio de um Agente Consultor baseado em IA.

A proposta é apoiar gestores na análise do contexto educacional e socioeconômico de municípios que possam receber uma nova instituição de ensino.

---

## 💼 Pergunta de negócio

> **Onde o gestor deve priorizar investimento: em Professores ou em Tutores?**

O projeto utiliza o perfil socioeconômico e educacional observado no município como contexto para uma regra de decisão definida pelo projeto.

### Perfis considerados

**Professor**

Profissional especializado no conteúdo acadêmico e no aprofundamento curricular.

**Tutor**

Profissional voltado ao acompanhamento, orientação metodológica, apoio à aprendizagem e suporte mais próximo ao aluno.

> **Importante:** a recomendação produzida pelo agente é uma regra de negócio do projeto. Ela não representa evidência científica de causalidade nem afirma que determinado profissional produzirá, por si só, melhoria no desempenho dos alunos.

---

# 🏗️ Arquitetura da solução

```text
                 MICRODADOS ENEM 2025
                  ~4,8 milhões de
                     registros
                         │
                         ▼
              Tratamento e agregação
                   estatística
                         │
                         ▼
              BASE MUNICIPAL TRATADA
                 1.805 municípios
                    25 variáveis
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         Dashboard   Estatística  Agente IA
              │          │          │
              ▼          ▼          ▼
        Visualização   Análise   Diagnóstico
                                  e recomendação
