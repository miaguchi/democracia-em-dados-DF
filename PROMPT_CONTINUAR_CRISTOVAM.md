# Prompt para continuar — caso Cristovam Buarque (DF)

Copie tudo entre as linhas tracejadas e cole no Claude Code Web (ou em
nova sessão do Claude Code abrindo a pasta `~/democracia-em-dados-DF`).

---

## CONTEXTO

Sou o Thiago. Estou retomando uma sessão sobre análise eleitoral do
Distrito Federal, especificamente o **caso Cristovam Buarque** —
construção de um "mapa de retenção" (decay de incumbência, Tipo 4 do
diagnóstico estratégico) para informar campanha futura.

**Dois projetos relacionados:**

- `~/democracia-em-dados` (GitHub: miaguchi/democracia-em-dados) —
  projeto matriz, SP capital, base metodológica desenvolvida.
- `~/democracia-em-dados-DF` — replicação para DF, em curso.

**Framework conceitual:** está em `reports/diagnostico_estrategico_df.pdf`
(se existir) ou no documento "Diagnóstico Estratégico Eleitoral —
Distrito Federal — Janela 1998-2022". Pontos-chave:

- Escala ideológica Bolognesi-Ribeiro-Codato (Dados, 2023).
- 4 tipos de mapa de volatilidade: variância intertemporal, Pedersen
  por seção, inconsistência cross-cargo, decay de incumbência (Tipo 4).
- 3 níveis territoriais úteis: zona, local de votação, seção (BU
  desde 2014). Microrregião = Voronoi sobre local de votação. NUNCA
  "por quarteirão" (mente; voto é secreto).
- Dois diagnósticos diferenciados: candidata nova de direita
  (oportunidade marginal) vs. candidato veterano PDT/PSB/PT (retenção
  e ativação). **Cristovam é o segundo caso.**

## ESTADO ATUAL DO CASO CRISTOVAM

**Trajetória de candidaturas no DF (já mapeada):**

| Ano | Cargo | Partido | Votos | Status |
|---|---|---|---|---|
| 1998 | Governador | PT | (2T) | perdeu |
| 2002 | Senador | PT | 680.715 | eleito |
| 2010 | Senador | PDT | **833.480** | eleito (pico) |
| 2018 | Senador | PPS | 317.778 | não eleito (**-62%**) |

**Tiers de zona já calculados (21 zonas, mediana de share + variação):**

- **DEFENDER (6 zonas, 119k votos 2018):** Z15, Z18, Z8, Z16, Z2, Z13
  — queda contida entre -38% e -49%
- **DISPUTAR (8 zonas, 135k):** Z14, Z6, Z5, Z17, Z19, Z10, Z11, Z21
  — queda 53-65%, share residual >10%
- **ABANDONAR (7 zonas, 64k):** Z1, Z9, Z4, Z3, Z20, Z12, Z7 — queda
  >67% (Z12 e Z7 com zero em 2018)

**Top 10 locais de votação 2018** (núcleos residuais): UniEuro, La
Salle, UniPlan, UniCEUB, Colégio Ciman, Leonardo da Vinci, CECAP,
ESAF, Escola das Nações. **Padrão:** elite educada cosmopolita do
Plano Piloto / Asa Sul-Norte / Águas Claras.

**Mapa geográfico** mostra gradiente Plano Piloto → periferia: verde
(DEFENDER) concentra em Plano Piloto/Lago Sul/Cruzeiro; vermelho
(ABANDONAR) em Ceilândia/Samambaia/Recanto/Gama/Santa Maria.

## ARTEFATOS JÁ EXISTENTES

- `src/casos/cristovam/mapa_retencao_cristovam.py` — análise zonal
  (trajetória + tiers + top locais)
- `src/casos/cristovam/mapa_geografico_cristovam.py` — mapa
  territorial (tiers + choropleth)
- `outputs/figures/mapa_retencao_cristovam.png` (4 painéis de gráfico)
- `outputs/figures/mapa_geografico_cristovam.png` (mapa territorial)
- `outputs/tables/mapa_retencao_cristovam_zonas.csv`
- `outputs/tables/mapa_retencao_cristovam_tiers.csv`
- `data/raw/shapes/ras_df.gpkg` (cache de geometria 33 RAs)

## DADOS DISPONÍVEIS NO PROJETO DF

- `data/processed/votacao_candidato_munzona_<ano>_DF.parquet` — 1998
  a 2022 (cobertura zona × candidato × cargo)
- `data/processed/votacao_secao_2018_DF.parquet` e
  `votacao_secao_2022_DF.parquet` — granularidade de seção
  (~5.000 seções, ~700-1500 eleitores cada)
- `outputs/zona_to_ra.csv` — mapeamento das 19 zonas → RA dominante
- `outputs/indice_institucional_por_zona.csv` — hipótese institucional
  (testada e refutada no DF — ver README)

**Não tem:** votação por seção pré-2014; cadastro de locais de votação
geocodificado (CEM/USP não cobre DF).

## TAREFAS PENDENTES / CANDIDATAS

Em ordem de impacto vs. esforço:

1. **Tipo 4 verdadeiro por SEÇÃO** — exige boletins de urna por
   seção 2002, 2010, 2018 para mesmo candidato. Só temos seção 2018
   ↓ pré-requisito é ingerir votos por seção dos anos federais
   anteriores (ver implementação fase 1 do diagnóstico estratégico —
   "4-6 semanas"). Maior payoff metodológico mas maior custo.

2. **Cobertura territorial completa** — o mapa atual deixa cinza
   ~19 das 33 RAs (Estrutural, Vicente Pires, Itapoã, Jardim
   Botânico, Fercal, Sobradinho II e várias outras). Refinar o
   mapeamento `zona_to_ra.csv` para usar a 2ª e 3ª RA por zona, não
   só a dominante. **Esforço baixo, ganho informacional alto.**

3. **Cruzamento com renda/escolaridade** — usar `outputs/superior_por_zona_*.csv`
   se existir ou replicar o pipeline do SP (Censo 2010 amostra →
   área de ponderação) para validar a hipótese "base = elite educada".

4. **Inconsistência cross-cargo (Tipo 3) para Cristovam 2018** — em
   quais seções o eleitor votou Cristovam (centro-esquerda) +
   Bolsonaro/Ibaneis (direita)? Identifica voto pessoal puro.

5. **Comparativo com adversários 2018** — outros candidatos a
   Senador DF (Izalci Lucas, Leila do Vôlei) com a mesma análise por
   zona — entender se a perda do Cristovam foi para a direita
   (Izalci) ou para esquerda renovadora (Leila — Pros mas perfil
   social).

6. **Documentação metodológica em `reports/cristovam_metodologia.md`**
   — explicar critérios dos tiers, limitações (faltam ciclos 2006 e
   2014 nas regressões pessoais), versionamento.

## REGRAS

1. **Nunca simular dados.** Se faltar, parar e avisar.
2. **Conventional Commits** (feat:, fix:, docs:, refactor:).
3. **NUNCA prometer mapa "por quarteirão".** Voto é secreto.
   Microrregião eleitoral (Voronoi sobre local de votação) é o limite
   ético do produto.
4. **Citar Bolognesi-Ribeiro-Codato (2023) e Bartolini & Mair (1990)**
   quando usar a classificação ideológica ou decomposição de
   volatilidade.
5. Antes de partir para qualquer tarefa nova, **ler** os scripts
   existentes em `src/casos/cristovam/` e o CSV de tiers para
   entender o estado.
6. **Commitar a cada passo.** Sessão pode ser interrompida.

## PRIMEIRA AÇÃO

Comece pedindo:

> "Leia o estado atual em `src/casos/cristovam/`, o CSV de tiers e a
> figura geográfica. Me diga em 5 linhas o que está pronto e proponha
> a próxima tarefa entre as 6 candidatas listadas no
> PROMPT_CONTINUAR_CRISTOVAM.md, dado meu objetivo agora de
> [PREENCHER: ex. preparar documento para reunião com Cristovam /
> avançar tese sobre desalinhamento DF / refinar metodologia para
> outro candidato]."

---

Boa continuidade.
