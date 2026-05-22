# Projeto: Democracia em Dados — Distrito Federal

## Contexto
Replicação do projeto Democracia em Dados (SP) para o Distrito Federal.
Análise de comportamento eleitoral em zonas eleitorais e regiões
administrativas do DF (1998-2022). Serve como replicação empírica
da metodologia desenvolvida em São Paulo, testando se os achados
sobre índice institucional cultural-progressista, voto diferenciado
por nível e dinâmicas de financiamento se sustentam num contexto
federativo diferente (DF = UF e município simultaneamente).

**Projeto irmão (somente leitura, referência):** `~/democracia-em-dados`

## Diferenças DF vs SP

| Aspecto | SP | DF |
|---|---|---|
| Prefeito | cd_cargo=11 | **não existe** |
| Vereador | cd_cargo=13 | **não existe** |
| Dep. Estadual | cd_cargo=7 | **Distrital** (cd_cargo=8), 24 cadeiras |
| Governador | sim | sim, acumula função executiva municipal |
| Senador, Dep. Federal, Pres | iguais | iguais |
| Município TSE | 71072 | 97012 (BRASÍLIA) |
| Município IBGE | 3550308 | 5300108 |
| Subdivisões | zonas eleitorais (~58 cap) | 31 RAs + ~13 zonas eleitorais |
| Universidade pública | USP, Unicamp | UnB |
| Anos disponíveis | municipal (par) + federal | só federal (2002, 2006, 2010, 2014, 2018, 2022) |

## Stack
- Python 3.11+ via conda-forge (env: radiografia)
- pandas, geopandas, statsmodels, linearmodels, libpysal/esda
- matplotlib, seaborn
- MySQL Workbench (banco `democracia_em_dados_df`)
- pytest

## Convenções de código
- Type hints obrigatórios em funções públicas
- Docstrings no estilo NumPy
- snake_case para funções/variáveis, PascalCase para classes
- Toda função estatística precisa de teste pytest correspondente
- Reusar código do SP sempre que possível (`~/democracia-em-dados`)

## Estrutura de diretórios
- data/raw/ — TSE, IBGE, CEM, no .gitignore
- data/processed/ — output dos pipelines, regenerável
- src/ — módulos Python organizados por eixo
- src/sintese/ — análises transversais
- src/casos/ — replicações de cidade-caso
- src/ingestao/, src/dominio/ — infraestrutura compartilhada
- scripts/ — utilitários
- notebooks/ — exploração apenas
- reports/ — markdown e PDFs versionados
- outputs/figures, outputs/tables, outputs/logs
- tests/

## Decisões metodológicas (herdadas do SP)
- Escala ideológica: Bolognesi, Ribeiro & Codato (2023)
- Limiar centro-direita/direita: 7,00
- Volatilidade: Pedersen (1979) decomposta por Bartolini & Mair (1990)
- Vizinhança espacial: k=6 nearest neighbors para LISA
- Geometrias: pacote geobr
- Locais de votação: base CEM/USP (verificar disponibilidade DF)

## Regras importantes para o agente
1. NUNCA simular dados. Se não existir localmente, parar e avisar.
2. Sempre validar Content-Length de downloads do TSE.
3. Resultados estatísticos precisam de IC ou erro-padrão.
4. Antes de implementar nova análise, escrever teste pytest primeiro.
5. Toda figura final precisa de versão PNG (300 dpi) e código que regenera.
6. Não decidir econometria sozinho — propor opções e esperar confirmação.
7. Commits seguem Conventional Commits (feat:, fix:, docs:, test:, refactor:).
8. **Achados negativos contam.** Se o índice institucional não prediz
   no DF como prevê em SP, isso é resultado — não fracasso.

## Hipóteses pré-formuladas para testar
1. Índice institucional: UnB cria "ilha de esquerda" análoga ao
   corredor universitário SP? (Asa Norte/Sul como locus)
2. Voto diferenciado por nível: o eleitorado do DF é conservador
   no executivo (Bolsonaro/Ibaneis 2022) mas vota mais à esquerda
   para Câmara Federal?
3. Eficiência eleitoral: servidores públicos federais (perfil
   majoritário do DF) reagem diferente ao financiamento tradicional?
4. Heterogeneidade interna: Lago Sul/Park Way × Ceilândia/Samambaia
   /Estrutural. Análise por RA pode ser mais informativa que por
   zona eleitoral.

## Comandos comuns
- `pytest tests/ -q` — roda pytest
- `python -m src.<modulo>` — executa script

## Como começar
Há um prompt completo de orientação em
`~/democracia-em-dados/PROMPT_REPLICAR_DF.md`. Leia-o no início
da sessão para entender o plano de 9 tarefas em ordem.
