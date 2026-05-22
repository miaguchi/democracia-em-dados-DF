# Prompt — Replicar análise Democracia em Dados para o Distrito Federal

Copie tudo entre as três linhas tracejadas abaixo e cole numa nova
sessão do Claude Code aberta em pasta vazia (ex.: `~/democracia-em-dados-DF`).

---

## CONTEXTO

Você vai replicar para o **Distrito Federal** o pipeline analítico
desenvolvido para São Paulo no projeto irmão em
`~/democracia-em-dados`. **Use aquele projeto como referência viva**:
leia os scripts, replique a estrutura e a metodologia, adaptando
apenas o que muda entre SP e DF.

Diretório de referência (somente leitura, não modificar):
`~/democracia-em-dados`

Diretório de trabalho (criar e desenvolver):
`~/democracia-em-dados-DF`

## DIFERENÇAS-CHAVE DF vs SP

| Aspecto | SP | DF |
|---|---|---|
| Estrutura federativa | Município de cidade-capital | DF é UF e município simultâneos |
| Prefeito | Sim (cd_cargo=11) | **Não existe** — Governador acumula |
| Vereador | 55 cadeiras (cd_cargo=13) | **Não existe** — Câmara Legislativa |
| Dep. Estadual | Sim (cd_cargo=7) | **Distrital** (cd_cargo=8), 24 cadeiras |
| Governador | 1 (cd_cargo=3) | 1, mas escolhido pela cidade toda |
| Senador, Dep. Federal, Pres | Iguais | Iguais (cd_cargo 5, 6, 1) |
| Município (código TSE) | 71072 (SP) | 97012 (BRASÍLIA) |
| Município (código IBGE) | 3550308 | 5300108 |
| Subdivisões intramunicipais | Zonas eleitorais (~58 SP cap) | 31 Regiões Administrativas + ~13 zonas eleitorais |
| Universidade pública principal | USP, Unicamp | UnB |

**Implicação: os cargos a analisar no DF são** Presidente, Governador,
Senador, Deputado Federal, Deputado Distrital. **Sem prefeito e sem
vereador.** Os anos relevantes são federais (1998, 2002, 2006, 2010,
2014, 2018, 2022). Não há ciclo municipal separado no DF.

## OBJETIVO

Reproduzir, na medida do possível, os **8 achados** do projeto SP:

1. Volatilidade eleitoral por zona (Pedersen)
2. Inversão de regimes entre níveis (proporcional vs majoritário) —
   no DF, será **Distrital × Governador**
3. Decomposição da volatilidade (Bartolini & Mair) com escores
   Bolognesi
4. Índice institucional cultural-progressista por zona
5. Cinco testes de robustez (regressão variação, correlação entre
   cargos, HHI/Gini, quebra estrutural, análise simétrica direita)
6. Controle por renda + escolaridade (Censo 2010 amostra)
7. Análise espacial de transferência presidencialismo→governador
   (no DF talvez Lula→Ibaneis ou Bolsonaro→Ibaneis)
8. Eficiência eleitoral por arquétipo (votos/R$ por candidato)

## TAREFAS

### 1. Setup inicial (15 min)

- Criar pasta `~/democracia-em-dados-DF` e inicializar git
- Copiar `CLAUDE.md` da pasta SP, adaptando o contexto para DF
- Reaproveitar a stack: pandas, geopandas, statsmodels, libpysal,
  geobr, mysql-connector-python, scipy, scikit-learn

### 2. Ingestão de dados (1-2h)

Replicar `src/ingestao/tse_downloader.py` (cópia direta — TSE não
muda) e adaptar `carregar_mysql.py` + `carregar_anos_adicionais.py`
+ `carregar_presidente.py` para usar `cd_municipio = 97012` e
`SG_UF = DF`.

Baixar:
- `votacao_partido_munzona` 1998-2022 (anos federais) UF=DF
- `votacao_candidato_munzona` 1998-2022 UF=DF
- `prestacao_contas_candidato` 2018, 2022 UF=DF
- CEM/USP local de votação DF (verificar se existe — provavelmente
  não tem; usar geocode TSE direto ou pedir agendamento de download)
- Censo 2022 setores DF: filtrar `CD_SETOR` começando com `530010`
  do mesmo arquivo nacional já baixado pelo SP
- Censo 2010 Tabela 3.5.4 (instrução): filtrar áreas de ponderação
  com código começando em `5300108`

### 3. Esquema MySQL idêntico (30 min)

Schema do SP serve sem modificação. Apenas criar banco
`democracia_em_dados_df` para isolar.

### 4. Índice institucional para DF (2-3h)

**Atenção: este é o passo mais sensível.** O índice de SP usa
palavras-chave específicas para universidades paulistanas (USP,
Mackenzie, PUC-SP etc.). Para o DF, **renomear PADROES** com:

```python
PADROES = {
    "UNIVERSIDADE": [r"\bUNB\b", r"\bUNIVERSIDADE DE BRASILIA\b",
                     r"\bIESB\b", r"\bUNICEUB\b", r"\bUDF\b",
                     r"\bUPIS\b", r"\bIFB\b", r"\bUCB\b",
                     r"\bUNIPLAN\b", r"FACULDADE", "CAMPUS"],
    "ESCOLA_PROGRESSISTA": [r"\bGALOIS\b", r"\bSIGMA\b",
                            r"\bMARISTA\b", ...],
    "PRESTIGIO_PUBLICO": [r"\bELEFANTE BRANCO\b",
                          r"\bCENTRO EDUCACIONAL", ...],
    "INTERNACIONAL_CULTURAL": [r"GOETHE", r"ALLIANCE",
                                r"CERVANTES", r"\bAMERICAN SCHOOL\b",
                                r"\bSWISS SCHOOL\b", ...],
}
```

**Validar manualmente** após primeira rodada: rodar a função em uma
amostra e olhar os locais classificados, ajustar regex.

### 5. Replicar testes A-D + análise simétrica (3-4h)

Copiar os 5 scripts em `src/sintese/`:
- `regressao_crescimento_indice.py`
- `correlacao_entre_cargos.py` (5×5 ou 4×4 sem prefeito)
- `concentracao_territorial.py`
- `quebra_estrutural_psol.py`
- `analise_direita.py`

Adaptar:
- Remover cd_cargo de vereador/prefeito (não existe)
- Adicionar Dep. Distrital (cd_cargo=8)
- Janela temporal: 2010→2022 para tudo (sem ciclo municipal)

### 6. Controle por escolaridade (1-2h)

Replicar `controle_renda_escolaridade_v3.py`:
- Censo 2010 Tabela 3.5.4 já cobre todo o Brasil; filtrar áreas
  começando com `5300108`
- geobr: `read_weighting_area(code_weighting=5300108, year=2010)`
- Censo 2022 setores: filtrar `CD_SETOR` começando `530010` no
  arquivo `Agregados_por_setores_renda_responsavel_BR.csv` já
  baixado pelo projeto SP — **pode ser copiado** para economizar
  download

### 7. Análise de transferência Bolsonaro→Ibaneis (1h)

Replicar `comparacao_bolsonaro_tarcisio_2022.py`. No DF, o par é
**Bolsonaro × Ibaneis Rocha** (2022, MDB). Hipótese análoga: gap
existe e é explicado por força do candidato petista (Lula × Lula
para Governador?) — verificar se o PT lançou alguém competitivo
para Governador do DF em 2022.

### 8. Financiamento + eficiência (1-2h)

Replicar `votos_vs_financiamento_todos_cargos.py` e
`perfis_eficiencia_eleitoral.py`. Sem vereador/prefeito; com
distrital, federal, senador, governador.

### 9. README e documentação (1h)

Replicar estrutura do README do SP, adaptando achados para o que
foi encontrado no DF. Incluir comparação SP × DF onde relevante.

## ENTREGÁVEIS ESPERADOS

- Banco MySQL `democracia_em_dados_df` populado com 1998-2022
- ~15-20 scripts em `src/` adaptados
- Pasta `outputs/figures/` com mapas e regressões equivalentes
- Pasta `outputs/tables/` com CSVs de resultados
- Pasta `reports/` com achados em markdown
- README atualizado com achados DF (incluir comparação SP↔DF)
- Repositório GitHub novo: `democracia-em-dados-DF`

## REGRAS

1. **NUNCA simular dados.** Se não baixar do TSE, parar e avisar.
2. **Reusar código sempre que possível.** A maior parte dos scripts
   do SP funciona com pequenas adaptações.
3. **Validar contagens** depois de cada carga (anos esperados, N de
   eleitos esperado, geometria casa com tabela).
4. **Commitar a cada passo concluído** (Conventional Commits).
5. **Push periódico** para o GitHub (criar repo `democracia-em-dados-DF`
   no perfil miaguchi).
6. **Achados negativos contam.** Se o índice institucional não
   prediz no DF como prevê em SP, isso é resultado — não fracasso.
7. **Tempo estimado total:** 10-15h de trabalho com pausas.
   Distribuir em 3-5 sessões.

## HIPÓTESES PRÉ-FORMULADAS PARA TESTAR NO DF

1. **Índice institucional:** UnB cria uma "ilha de esquerda" análoga
   ao corredor universitário SP? Asa Norte/Sul devem ser as zonas
   de maior densidade institucional.
2. **Voto diferenciado por nível:** o eleitorado do DF é
   notoriamente conservador no executivo (Bolsonaro/Ibaneis venceram
   em 2022) mas vota mais à esquerda para deputado federal? Testar.
3. **Eficiência eleitoral:** servidores públicos federais (perfil
   majoritário no DF) reagem de modo diferente ao financiamento
   tradicional? Esperar que cargos majoritários sejam ainda mais
   baratos por voto que em SP.
4. **Heterogeneidade interna:** ricos de Lago Sul/Park Way votam
   diferente de pobres de Ceilândia/Samambaia/Estrutural? Análise
   por região administrativa pode ser mais informativa que por
   zona eleitoral.

## CONTATO COM O PROJETO PAI

Se precisar de algo específico do SP para comparação, **leia
diretamente** os arquivos em `~/democracia-em-dados/`. Não modifique
nada lá. Quando o DF estiver pronto, considerar criar um terceiro
repo `democracia-em-dados-comparacao` que cruza os dois.

---

Boa replicação. Quando terminar, atualize aqui o que aprendeu sobre
o DF que mudou a metodologia (se algo mudou).
