"""Classificação ideológica dos partidos e decomposição de volatilidade.

Escores de Bolognesi, Ribeiro & Codato (2023), "Uma Nova Classificação
Ideológica dos Partidos Políticos Brasileiros", Dados 66(2). Survey com
especialistas da ABCP em 2018, escala 0 (extrema-esquerda) a 10 (extrema-
direita). Usamos as médias publicadas na Tabela 1.

A decomposição de volatilidade é a de Bartolini & Mair (1990):
    V_total  = 0.5 * sum_i |p_i,t+1 - p_i,t|        (partido a partido)
    V_entre  = 0.5 * sum_b |P_b,t+1 - P_b,t|        (bloco a bloco)
    V_dentro = V_total - V_entre

V_entre mede realinhamento ideológico genuíno; V_dentro mede rotação de
votos entre partidos da mesma família.
"""

from typing import Dict, Tuple

import pandas as pd

# Escores Bolognesi et al. (2023) — Tabela 1, coluna Média.
ESCORE_BOLOGNESI: Dict[str, float] = {
    "PSTU": 0.51,
    "PCO": 0.61,
    "PCB": 0.91,
    "PSOL": 1.28,
    "PC do B": 1.92,
    "PT": 2.97,
    "PDT": 3.92,
    "PSB": 4.05,
    "REDE": 4.77,
    "CIDADANIA": 4.92,   # ex-PPS
    "PV": 5.29,
    "PTB": 6.10,
    "AVANTE": 6.32,
    "SOLIDARIEDADE": 6.50,
    "PMN": 6.88,
    "PMB": 6.90,
    "MDB": 7.01,
    "PSD": 7.09,
    "PSDB": 7.11,
    "PODE": 7.24,
    "PRTB": 7.45,
    "PROS": 7.47,
    "REPUBLICANOS": 7.78,  # ex-PRB
    "PL": 7.78,            # ex-PR
    "AGIR": 7.86,          # ex-PTC
    "DC": 8.11,
    "PSL": 8.11,
    "NOVO": 8.13,
    "PP": 8.20,            # Progressistas
    "PSC": 8.33,
    "PATRIOTA": 8.55,
    "DEM": 8.57,
}

# Partidos fundidos/renomeados recebem escore herdado da média dos membros.
ESCORE_BOLOGNESI["UNIÃO"] = (
    ESCORE_BOLOGNESI["DEM"] + ESCORE_BOLOGNESI["PSL"]
) / 2  # 8.34
ESCORE_BOLOGNESI["PRD"] = (
    ESCORE_BOLOGNESI["PTB"] + ESCORE_BOLOGNESI["PATRIOTA"]
) / 2  # 7.325

# Federações usadas em analise_volatilidade.normalizar_partido
ESCORE_BOLOGNESI["FED_PT_PCDOB_PV"] = (
    ESCORE_BOLOGNESI["PT"] + ESCORE_BOLOGNESI["PC do B"] + ESCORE_BOLOGNESI["PV"]
) / 3  # 3.39
ESCORE_BOLOGNESI["FED_PSOL_REDE"] = (
    ESCORE_BOLOGNESI["PSOL"] + ESCORE_BOLOGNESI["REDE"]
) / 2  # 3.03
ESCORE_BOLOGNESI["FED_PSDB_CIDADANIA"] = (
    ESCORE_BOLOGNESI["PSDB"] + ESCORE_BOLOGNESI["CIDADANIA"]
) / 2  # 6.02


def bloco_tripartite(escore: float) -> str:
    """Divide em 3 blocos usando os limiares de Bolognesi et al. (2023)."""
    if escore <= 4.49:
        return "ESQUERDA"
    if escore <= 5.50:
        return "CENTRO"
    return "DIREITA"


def bloco_quintipartite(escore: float) -> str:
    """Divide em 5 blocos: extremas colapsam em ESQ/DIR, meio refinado."""
    if escore <= 3.00:
        return "ESQUERDA"
    if escore <= 4.49:
        return "CENTRO-ESQUERDA"
    if escore <= 5.50:
        return "CENTRO"
    if escore <= 7.00:
        return "CENTRO-DIREITA"
    return "DIREITA"


_MODO_CLASSIFICACAO = bloco_tripartite


def usar_tripartite() -> None:
    global _MODO_CLASSIFICACAO
    _MODO_CLASSIFICACAO = bloco_tripartite


def usar_quintipartite() -> None:
    global _MODO_CLASSIFICACAO
    _MODO_CLASSIFICACAO = bloco_quintipartite


def classificar(sigla: str) -> str:
    """Retorna bloco ideológico usando o esquema ativo (tripartite por padrão)."""
    if sigla not in ESCORE_BOLOGNESI:
        return "DESCONHECIDO"
    return _MODO_CLASSIFICACAO(ESCORE_BOLOGNESI[sigla])


def votos_por_bloco(votos_partido: pd.Series) -> pd.Series:
    """Agrega votos por bloco ideológico a partir de votos por partido."""
    blocos = votos_partido.index.map(classificar)
    return votos_partido.groupby(blocos).sum()


def _pedersen(ant: pd.Series, atu: pd.Series) -> float:
    p_ant = ant / ant.sum()
    p_atu = atu / atu.sum()
    chaves = p_ant.index.union(p_atu.index)
    return 0.5 * (
        p_ant.reindex(chaves, fill_value=0) - p_atu.reindex(chaves, fill_value=0)
    ).abs().sum()


def volatilidade_decomposta(
    votos_ant: pd.Series, votos_atu: pd.Series
) -> Tuple[float, float, float]:
    """Retorna (V_total, V_entre_blocos, V_dentro_blocos).

    V_dentro = V_total - V_entre (decomposição de Bartolini & Mair).
    """
    v_total = _pedersen(votos_ant, votos_atu)
    v_entre = _pedersen(votos_por_bloco(votos_ant), votos_por_bloco(votos_atu))
    return v_total, v_entre, v_total - v_entre


def proporcao_desconhecida(votos_partido: pd.Series) -> float:
    """Fração dos votos em partidos sem escore ideológico mapeado."""
    total = votos_partido.sum()
    if total == 0:
        return 0.0
    blocos = votos_partido.index.map(classificar)
    desconhecidos = votos_partido[blocos == "DESCONHECIDO"].sum()
    return desconhecidos / total
