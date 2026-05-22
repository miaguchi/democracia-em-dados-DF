"""Comparação de blocos ideológicos por cargo, na mesma zona — DF.

Achado 2 do PROMPT_REPLICAR_DF: inversão de regimes entre níveis no DF
(majoritário vs proporcional). No SP a comparação clássica era Vereador
× Prefeito. Aqui o análogo natural é **Deputado Distrital × Governador**
— mesma cédula, mesmo eleitor, decisão simultânea: as zonas votam
ideologicamente diferente para o legislativo distrital e para o
executivo distrital?

Pipeline:
1. Lê do MySQL DF as votações por zona × partido em cada cargo (ano).
2. Aplica escores Bolognesi e agrupa em blocos (tripartite por padrão).
3. Calcula, por zona, o % de votos em cada bloco (esquerda/centro/direita).
4. Retorna a diferença bloco × cargo, e a correlação intra-zona.

Uso: `python -m src.partidario.comparacao_blocos_cargos`
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
from src.partidario.ideologia import classificar


def percentuais_por_bloco(matriz: pd.DataFrame) -> pd.DataFrame:
    """Recebe matriz zona × partido (votos absolutos), retorna zona × bloco
    em percentual (excluindo DESCONHECIDO do denominador)."""
    blocos = pd.Index([classificar(p) for p in matriz.columns], name="BLOCO")
    matriz_bloco = matriz.copy()
    matriz_bloco.columns = blocos
    agregado = matriz_bloco.groupby(level=0, axis=1).sum()
    # Remove DESCONHECIDO da soma percentual — só os blocos mapeados.
    se_conhecido = [c for c in agregado.columns if c != "DESCONHECIDO"]
    total_conhecido = agregado[se_conhecido].sum(axis=1)
    pct = agregado[se_conhecido].div(total_conhecido, axis=0) * 100
    pct = pct.fillna(0)
    return pct


def perfil_bloco_por_cargo(ano: int, cargos: Iterable[str]) -> pd.DataFrame:
    """Empilha o % de cada bloco por zona em cada cargo do ano."""
    frames = []
    for cargo in cargos:
        df = carregar_df(ano, cargo)
        matriz = votos_por_zona_partido(df)
        pct = percentuais_por_bloco(matriz)
        pct.columns = [f"{cargo[:3].upper()}_{b}" for b in pct.columns]
        frames.append(pct)
    return pd.concat(frames, axis=1).dropna()


def main() -> None:
    """Comparação Distrital × Governador em 2022 (eleição mais recente)."""
    ano = 2022
    cargos = ["Deputado Distrital", "Governador"]
    perfil = perfil_bloco_por_cargo(ano, cargos)

    print(f"\n=== Bloco × cargo por zona — DF {ano} ===")
    print(f"Zonas: {len(perfil)}")
    print("\nPerfil médio (% de votos por bloco e cargo):")
    print(perfil.mean().round(1))

    # Diferença bloco a bloco entre Distrital e Governador
    print("\nDiferença média (Distrital − Governador) por bloco:")
    for bloco in ["ESQUERDA", "CENTRO", "DIREITA"]:
        col_dis = f"DEP_{bloco}"
        col_gov = f"GOV_{bloco}"
        if col_dis in perfil.columns and col_gov in perfil.columns:
            diff = (perfil[col_dis] - perfil[col_gov]).mean()
            print(f"  {bloco:<10}: {diff:+.2f} pp")

    # Correlação intra-zona (cargos votam alinhado ou divergente?)
    print("\nCorrelação Distrital × Governador por bloco (Pearson):")
    for bloco in ["ESQUERDA", "CENTRO", "DIREITA"]:
        col_dis = f"DEP_{bloco}"
        col_gov = f"GOV_{bloco}"
        if col_dis in perfil.columns and col_gov in perfil.columns:
            r = perfil[col_dis].corr(perfil[col_gov])
            print(f"  {bloco:<10}: r = {r:+.3f}")


if __name__ == "__main__":
    main()
