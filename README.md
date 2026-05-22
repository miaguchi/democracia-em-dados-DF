# Democracia em Dados — Distrito Federal

Replicação da metodologia desenvolvida em São Paulo
([democracia-em-dados](https://github.com/miaguchi/democracia-em-dados))
para o Distrito Federal, com janela 1998-2022 e foco nos 5 cargos
federais (Presidente, Governador, Senador, Deputado Federal,
Deputado Distrital). Sem prefeito e sem vereador — o DF é UF e
município ao mesmo tempo.

Cobre os 8 achados do projeto SP, com adaptações metodológicas
documentadas; os resultados divergem significativamente em vários
eixos, e essas divergências são em si um achado.

## Stack

Python 3.11 (conda env `radiografia`), pandas, geopandas, statsmodels,
geobr, scipy, mysql-connector-python. Dados eleitorais ficam no MySQL
local (`democracia_em_dados_df`).

## Como rodar

```bash
# 1. Ingestão TSE (1998-2022, anos federais)
python -m src.ingestao.carregar_mysql      # cargos não-presidenciais
python -m src.ingestao.carregar_presidente # Presidente filtrado de BR.csv

# 2. Achados (qualquer ordem)
python -m src.partidario.analise_volatilidade
python -m src.partidario.volatilidade_bartolini_mair
python -m src.partidario.comparacao_blocos_cargos
python -m src.urbano.indice_institucional
python -m src.urbano.socioeconomia_zonas_2022
python -m src.dominio.zona_para_ra
python -m src.sintese.correlacao_entre_cargos
python -m src.sintese.concentracao_territorial
python -m src.sintese.quebra_estrutural_esquerda
python -m src.sintese.analise_direita
python -m src.sintese.regressao_crescimento_indice
python -m src.sintese.comparacao_bolsonaro_ibaneis_2022
python -m src.sintese.votos_vs_financiamento_todos_cargos
python -m src.sintese.perfis_eficiencia_eleitoral
```

## Achados principais

### 1. Volatilidade Pedersen por zona

Mais alta em **Governador 2014→2018** (V_total = 0.79 média por zona)
— ascensão de Ibaneis Rocha consolida realinhamento. Cai em 2018→2022
(0.46) — Ibaneis reeleito, recomposição intra-bloco.

### 2. Voto diferenciado por nível (Distrital × Governador)

A correlação intra-zona é alta (r=+0.93 para o bloco de esquerda
entre Distrital e Gov 2022), mas o **nível é sistematicamente
diferente**: o Distrital recebe em média **+9.13pp a mais para a
direita** que o Governador. O eleitor diferencia ideologicamente o
proporcional (mais à direita) do executivo (menos à direita).

### 3. Decomposição Bartolini & Mair

| Cargo / par | V_total | V_entre | V_dentro | prop_entre |
|---|---|---|---|---|
| Governador 2014→2018 | 0.79 | 0.45 | 0.34 | **57.5%** |
| Governador 2018→2022 | 0.46 | 0.09 | 0.37 | 22.4% |
| Presidente 2018→2022 | 0.81 | 0.10 | 0.71 | **12.1%** |
| Dep. Federal 2018→2022 | 0.42 | 0.06 | 0.36 | 13.4% |
| Dep. Distrital 2018→2022 | 0.31 | 0.08 | 0.23 | 25.5% |

Bolsonaro→Lula em 2022 é alta volatilidade dentro do mesmo polo
(prop_entre 12.1%); a inflexão ideológica de Ibaneis 2014→2018 é o
único caso em que metade da volatilidade vem de migração entre blocos.

### 4. Índice institucional cultural-progressista

PADROES adaptados para Brasília: UnB/IESB/UniCEUB/UDF/UPIS/IFB/UCB
(universidades); Galois/Sigma/Marista/La Salle/Leonardo da
Vinci/Rogacionista/Kairós (escolas progressistas); lista nominal
fechada para prestígio público (Elefante Branco, GISNO, Setor
Leste, Caseb); Maple Bear/Canadense/Goethe/Alliance/Cervantes/Pasteur
(internacional cultural). Validação manual após primeira rodada.

| Zona | RA dominante | Índice | Locais |
|---|---|---|---|
| 1 | Asa Sul / Plano Piloto | 30.8% | 8 / 26 |
| 14 | Asa Norte / Plano Piloto | 25.8% | 8 / 31 |
| 15 | Águas Claras / Sudoeste | 22.9% | 8 / 35 |
| 11 | Cruzeiro / Octogonal | 12.5% | 2 / 16 |
| 9, 19, 10, 5, 8 | RAs intermediárias | 2-9% | 1-3 |
| 10 outras zonas | Periferia | 0% | 0 |

### 5. Cinco testes de robustez (A-E)

**Teste A** (regressão Δesquerda 2010→2022 × índice institucional,
controlando renda): M1 (só índice) β=−0.156 (p=0.06); M2 (com
log-renda) β_índice=−0.08 (p=0.44 ns), β_renda=−1.63 (p=0.25 ns).
ΔR² de adicionar índice depois de renda é de apenas +0.029. **No DF
o índice institucional não sobrevive ao controle por renda — a
relação é largamente espúria.** Sinal NEGATIVO em todos os modelos:
zonas mais ricas/educadas perderam mais esquerda. **Achado oposto
ao SP** (onde índice é robusto ao controle por renda e o sinal é
positivo).

**Teste B** (matriz de correlação 5×5 entre Δesquerda nos cargos):
Pres × Senador r=+0.80 (forte intra-bloco majoritário federal);
Federal × Governador r=+0.59; **Distrital × Presidente r=−0.25**
(anti-correlação fraca — voto diferenciado por nível). Spearman
preserva o padrão.

**Teste C** (HHI e Gini da esquerda por zona, 1998-2022): HHI
1998=0.092 → 2022=0.057, Gini 0.31→0.16. **A esquerda DF
DES-concentrou ao longo do tempo**, oposto do SP. Hipótese: PT
cresceu da fortaleza Asa Sul/Norte para distribuição mais homogênea
entre RAs.

**Teste D** (quebra estrutural na esquerda das top-5 zonas):
Chow test detecta quebra significativa em **t=2002** (F=11.43,
p=0.040), não em 2010 ou 2018. A inflexão na ascensão petista
nacional, não no realinhamento recente. N=7 pontos, poder
estatístico baixo — resultado indicativo.

**Teste E** (análise simétrica da direita, replica A+C com PL/PP/
REPUB/UNIÃO/etc.): β=+0.305 (p=0.064) — **zonas de alto índice
cresceram MAIS para a direita também**. Z11 Lago Sul +23pp, Z1 Asa
Sul +18pp. Confirma que a elite educada do DF se bolsonarizou,
enquanto a elite SP tendeu para a esquerda no mesmo período.

### 6. Controle por renda (Censo 2022)

Mapeamento zona→RA por heurística de endereço (siglas SGAS/SGAN/EQNP/
SHCES etc.), depois renda média do responsável (V06004) por RA via
geobr `name_subdistrict`. 19 zonas cobertas com RA dominante
identificada.

Ranking de renda (R$ médios 2022):

| RA | Renda média |
|---|---|
| Lago Sul | R$ 19.529 |
| Plano Piloto (Asa Sul/Norte) | R$ 13.282 |
| Águas Claras | R$ 11.322 |
| Cruzeiro | R$ 7.727 |
| Gama, Riacho Fundo | R$ 4.000-4.500 |
| Ceilândia, Paranoá, Recanto das Emas | R$ 2.200-2.800 |
| SCIA-Estrutural | R$ 1.628 |

Escolaridade 2010 (Tabela 3.5.4) ficou para iteração futura — a
correlação índice × renda no DF (r=0.65) sugere que renda já capta
a maior parte do sinal socioeconômico.

### 7. Bolsonaro → Ibaneis 2022

Ibaneis (MDB) vence DF 2022 com 832k votos contra 910k de Bolsonaro
(PL) — ratio 0.915 no agregado. Geograficamente:

- **Ibaneis SUPERA Bolsonaro em apenas 2 zonas**: Z21 Recanto das
  Emas (1.07) e Z2 Paranoá (1.02) — periferia popular.
- **Bolsonaro SUPERA Ibaneis em 17 zonas**, com déficit maior nas
  zonas centrais elite: Z14 Asa Norte (0.77), Z1 Asa Sul (0.79),
  Z11 Cruzeiro (0.82), Z15 Águas Claras (0.88).
- **r = −0.481 (p=0.037)** entre `ratio_ibaneis_bolso` e
  `diff_lula_bolso_pp`: o gap Bolsonaro→Ibaneis é explicado pela
  força local do petista. Hipótese do PROMPT confirmada.
- **r = −0.678** com índice institucional: elite educada hesitou
  em Ibaneis.

### 8. Financiamento + eficiência eleitoral

Eficiência (votos por R$ mil em valores de 2024) dos eleitos:

| Cargo | 2018 | 2022 |
|---|---|---|
| Governador | 193 | 104 |
| Senador | 101 | 160 |
| Deputado Federal | ~58 | ~62 |
| Deputado Distrital | ~95 | ~67 |

Cargos majoritários (Gov, Senador) têm eficiência sistematicamente
maior — consistente com a hipótese 3 do PROMPT.

**Arquétipos por nome de urna** (Religioso/Segurança/Profissional/
Familiar/Coletivo/Outros): no DF, **88% dos eleitos caem em "Outros"**,
contra ~50% no SP. Religioso e segurança são marginais (1 eleito
cada em todo o período). Profissional aparece em 6 eleitos
(Distrital/Federal) com a maior eficiência média (127 votos/R$ mil).
Hipótese: o eleitorado de servidor público federal premia nomes
"tradicionais" sem epíteto.

## Diferenças metodológicas SP → DF

| Aspecto | SP | DF |
|---|---|---|
| Locais de votação georreferenciados | base CEM/USP (shapefile) | nenhuma — TSE direto via `votacao_secao` |
| Mapeamento espacial setor→zona | spatial join (lat/lon) | heurística zona→RA por tokens de endereço |
| Cargos analíticos | Vereador + Prefeito + federais | só federais (sem cargo municipal) |
| Janela longa | 2000-2024 | 1998-2022 (anos pares federais) |
| Censo escolaridade 2010 | Tabela 3.5.4 aplicada | deferida (renda 2022 como proxy único) |

## Estrutura

```
src/
  ingestao/          # TSE downloader, carregar MySQL
  dominio/           # zona_para_ra (heurística)
  partidario/        # ideologia Bolognesi, volatilidade, blocos
  urbano/            # índice institucional, socioeconomia
  sintese/           # 5 testes de robustez, Bolso×Ibaneis, financiamento
scripts/sql/         # schema MySQL
outputs/
  figures/           # PNGs 300 dpi
  tables/            # CSVs de resultados
  indice_institucional_por_zona.csv
  socioeconomia_por_zona_2022.csv
  zona_to_ra.csv
data/raw/            # TSE/IBGE — não versionado
data/processed/      # parquets — não versionado
```

## Limitações reconhecidas

- N pequeno (19 zonas) limita poder estatístico em todos os testes.
  Chow test (Teste D) com 7 pontos no tempo é particularmente fraco.
- Mapeamento zona→RA tem `pct_dominante` baixo (< 30%) em 8 das 19
  zonas — renda atribuída por RA dominante é proxy, não medida exata.
- Sem geocoding de locais de votação, todas as análises espaciais
  do SP (LISA, Moran's I, mapas por seção) não foram replicadas.
- Censo 2010 escolaridade não aplicado — controle por instrução
  ficou como dívida técnica.

## Projeto irmão

[github.com/miaguchi/democracia-em-dados](https://github.com/miaguchi/democracia-em-dados)
— São Paulo. Quando os dois estiverem maduros, considerar um terceiro
repositório de comparação cruzada SP × DF.
