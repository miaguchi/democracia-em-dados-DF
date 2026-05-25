# Análise eleitoral Cristovam Buarque (DF, 2002–2018)
## Limitações metodológicas

Documento de apoio para a reunião — checklist do que está sólido, do
que tem ressalvas, e de como apresentar os achados sem expor
fragilidades não-comunicadas.

---

## 1. O que é incontestável

- **Votos absolutos por ciclo** (680.715 em 2002, 833.480 em 2010,
  317.778 em 2018): vêm dos boletins agregados oficiais do TSE.
  Replicáveis a partir do parquet
  `data/processed/votacao_candidato_munzona_<ano>_DF.parquet`.
- **Queda de −61,9 %** entre o pico (2010) e a última candidatura
  (2018): aritmética sobre dados oficiais.
- **Identidade dos 597 locais de votação** onde houve voto Cristovam
  em 2018 e seus respectivos endereços/CNPJs: cadastro TSE.
- **Padrão territorial** (concentração no eixo Plano Piloto / Asa
  Sul / Asa Norte / Águas Claras / Lago Sul / Cruzeiro): visível
  tanto no mapa coroplético quanto na tabela de zonas.

---

## 2. Caveats que precisam ser ditos em voz alta

### 2.1 Voto em um LOCAL ≠ voto de morador do bairro

O top 10 é composto por colégios privados de elite e universidades
particulares (UniEuro, La Salle, UniPlan, UniCEUB, Colégio Ciman).
Estes locais recebem eleitores de várias RAs simultaneamente —
alunos, funcionários, professores que moram em bairros distintos
escolhem votar no campus.

- Forma correta de enunciar: *"no UniEuro, 11 % dos votos para
  Senador foram em Cristovam"*.
- Forma incorreta: *"Cristovam venceu em Águas Claras"*.

Para um juízo territorial mais robusto seria preciso pareamento
com o domicílio eleitoral (não disponível publicamente sem quebra
de sigilo).

### 2.2 Tiers DEFENDER / DISPUTAR / ABANDONAR são *judgment*

Os limiares (`DEFENDER = votos ≥ 15 k AND share ≥ 12 %`;
`DISPUTAR = votos ≥ 12 k AND share ≥ 9 %`) foram escolhidos
pragmaticamente para uma narrativa de campanha. Não são derivados
de um modelo estatístico nem de literatura específica. Qualquer
revisor crítico vai questionar.

- Apresentar como: *"ferramenta de priorização tática"*.
- Não apresentar como: *"classificação metodológica"*.

### 2.3 Correlações inter-ciclo de share são afetadas por mudança da geografia eleitoral

Pearson(2002, 2010) = 0,84; (2010, 2018) = 0,71; (2002, 2018) = 0,45.

A erosão aparente da identidade no horizonte 16 anos sofre dois
problemas:

1. **Redivisão de zonas**: Z18, Z19, Z20, Z21 não existiam em 2002
   — para essas zonas o share_2002 é NaN e a Pearson é pairwise
   (exclui o par). N efetivo cai.
2. **N pequeno** (21 zonas no DF): com 21 observações, o intervalo
   de confiança da Pearson é largo. Não estão calculados intervalos
   nem testes de significância.

- Como dizer: *"a correlação permanece alta entre as duas últimas
  eleições (r = 0,71); dilui no horizonte de 16 anos, em parte por
  mudança da própria geografia eleitoral"*.

### 2.4 Cristovam mudou de partido três vezes

PT (2002) → PDT (2010) → PPS (2018). A variação do voto absoluto
mistura efeito de identidade pessoal com efeito de coligação,
de marca partidária e de onda nacional (Lula 2002, anti-Dilma 2014,
Bolsonaro 2018). Não é possível atribuir a queda exclusivamente ao
candidato sem um modelo contrafactual.

### 2.5 Trajetória inclui um cargo diferente (Governador 1998)

A candidatura de 1998 foi para governador, não para senador. Cargo,
regra eleitoral, número de vagas, dinâmica de coalizão — tudo difere.
Mantida como referência biográfica, não como ponto comparável da
série temporal.

### 2.6 Cadastro de coordenadas dos locais é de 2022

Usadas para análise de 2018 (única base geocodificada disponível
para o DF — CEM/USP não cobre a UF). 597 dos 609 locais (98 %) com
voto Cristovam em 2018 foram pareados. 12 locais ficaram sem
coordenadas, possivelmente extintos ou renumerados.

---

## 3. O que esta análise **não** explica

- **Por quê** Cristovam caiu (a análise descreve onde, não causa).
- **Para onde** o voto perdido migrou (precisa de cruzamento com
  Izalci/Leila no mesmo nível).
- **Quem** é o eleitor que ficou (precisa de cruzamento com dados
  censitários — escolaridade, renda — por área de ponderação).

Estes três pontos são os próximos passos analíticos sugeridos.

---

## 4. Como apresentar com integridade

Sugestão de fala de abertura para a reunião:

> "O que tenho são três coisas. Primeiro, a trajetória oficial dos
> votos absolutos — isso é incontestável. Segundo, a geografia do
> voto remanescente em 2018 — isso é descritivo, mas robusto.
> Terceiro, uma classificação operacional em três tiers — isso é
> uma proposta tática, não uma medida científica, e os limiares
> podem ser ajustados. Não vou dizer a causa nem prever a próxima
> eleição."
