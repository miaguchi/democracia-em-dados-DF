"""Decomposição de Bartolini & Mair (1990) por zona — DF, 1998-2022.

Achado 3 do PROMPT_REPLICAR_DF: decompõe a volatilidade total (Pedersen)
em duas componentes:
  * V_entre  — volatilidade *entre blocos* ideológicos (realinhamento
    genuíno: voto migrando de esquerda → direita ou vice-versa)
  * V_dentro — volatilidade *dentro de blocos* (rotação entre partidos
    do mesmo campo ideológico)

A interpretação substantiva: V_entre alto = mudança ideológica real;
V_dentro alto = recomposição partidária dentro do mesmo campo (sem
movimento ideológico líquido).

Usa os escores Bolognesi et al. (2023) via `src.partidario.ideologia`.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from typing import Iterable

import pandas as pd

from src.partidario.analise_volatilidade import (
    carregar_df,
    votos_por_zona_partido,
)
from src.partidario.ideologia import classificar, volatilidade_decomposta


def _votos_por_bloco_em(matriz: pd.DataFrame) -> pd.DataFrame:
    """Recebe zona × partido (votos), retorna zona × bloco (votos)."""
    blocos = pd.Index([classificar(p) for p in matriz.columns], name="BLOCO")
    mat = matriz.copy()
    mat.columns = blocos
    return mat.groupby(level=0, axis=1).sum()


def decomposicao_zona(
    matriz_ant: pd.DataFrame, matriz_atu: pd.DataFrame
) -> pd.DataFrame:
    """Para cada zona presente nos dois lados, retorna DataFrame com
    colunas V_total, V_entre, V_dentro, prop_entre."""
    partidos = matriz_ant.columns.union(matriz_atu.columns)
    m_ant = matriz_ant.reindex(columns=partidos, fill_value=0)
    m_atu = matriz_atu.reindex(columns=partidos, fill_value=0)
    zonas = m_ant.index.intersection(m_atu.index)

    registros = []
    for zona in zonas:
        ant = m_ant.loc[zona]
        atu = m_atu.loc[zona]
        if ant.sum() == 0 or atu.sum() == 0:
            continue
        v_tot, v_ent, v_dent = volatilidade_decomposta(ant, atu)
        prop = (v_ent / v_tot) if v_tot > 0 else 0.0
        registros.append(
            {
                "NR_ZONA": zona,
                "V_total": v_tot,
                "V_entre": v_ent,
                "V_dentro": v_dent,
                "prop_entre": prop,
            }
        )
    return pd.DataFrame(registros).set_index("NR_ZONA").sort_values(
        "V_total", ascending=False
    )


def decompor_par(ano_ant: int, ano_atu: int, cargo: str) -> pd.DataFrame:
    df_ant = carregar_df(ano_ant, cargo)
    df_atu = carregar_df(ano_atu, cargo)
    m_ant = votos_por_zona_partido(df_ant)
    m_atu = votos_por_zona_partido(df_atu)
    return decomposicao_zona(m_ant, m_atu)


def main(cargos: Iterable[str] | None = None) -> None:
    if cargos is None:
        cargos = [
            "Governador",
            "Senador",
            "Deputado Federal",
            "Deputado Distrital",
            "Presidente",
        ]
    pares = [(2014, 2018), (2018, 2022)]  # foco no realinhamento recente
    for cargo in cargos:
        for ano_ant, ano_atu in pares:
            print(f"\n=== {cargo} {ano_ant} → {ano_atu} (DF) ===")
            try:
                df = decompor_par(ano_ant, ano_atu, cargo)
            except Exception as e:
                print(f"  pulado: {e}")
                continue
            if df.empty:
                print("  (sem zonas comuns)")
                continue
            print(
                f"Zonas: {len(df)} | "
                f"V_total {df['V_total'].mean():.3f} | "
                f"V_entre {df['V_entre'].mean():.3f} | "
                f"V_dentro {df['V_dentro'].mean():.3f} | "
                f"prop_entre {df['prop_entre'].mean():.2%}"
            )


if __name__ == "__main__":
    main()
