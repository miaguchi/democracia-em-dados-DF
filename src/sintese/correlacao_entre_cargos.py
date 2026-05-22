"""TESTE B — Correlação da variação da esquerda entre cargos, por zona — DF.

Adaptado de `sintese/correlacao_entre_cargos.py` do SP. No DF não há
vereador nem prefeito; a matriz é 5×5 cobrindo:

  * Deputado Distrital
  * Deputado Federal
  * Senador
  * Governador
  * Presidente

Janela: 2010 → 2022 (12 anos, equivalente ao 2012→2024 usado em SP).

Hipótese: governador e presidente devem correlacionar alto (executivo
federal/distrital); deputado federal e distrital devem correlacionar
alto entre si (representação proporcional). A pergunta substantiva é
se há "voto diferenciado por nível": correlação alta intra-bloco
(majoritário/proporcional) e mais baixa entre blocos.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import mysql.connector
import numpy as np
import pandas as pd

from src.ingestao.carregar_mysql import DATABASE, MYSQL_CONFIG

CD_MUNICIPIO_BRASILIA = 97012
ANO_BASE = 2010
ANO_FINAL = 2022

CARGOS = {
    "Distrital": "Deputado Distrital",
    "Federal": "Deputado Federal",
    "Senador": "Senador",
    "Governador": "Governador",
    "Presidente": "Presidente",
}

# Mesma lista que SP — D6 confirmado pelo usuário.
PARTIDOS_ESQUERDA = (13, 50, 65, 12, 40, 43, 18, 16, 29, 80)

SAIDA_FIG = _ROOT / "outputs/figures/correlacao_cargos_heatmap.png"
SAIDA_CSV = _ROOT / "outputs/tables/correlacao_cargos.csv"


def _conn() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(database=DATABASE, **MYSQL_CONFIG)


def votos_esquerda_por_zona(ano: int, cargo_ds: str) -> pd.Series:
    """Soma dos votos (nominais+legenda) dos partidos de esquerda no DF,
    para o cargo dado, 1º turno. Indexado por NR_ZONA."""
    sql = (
        "SELECT v.nr_zona AS NR_ZONA, "
        "       SUM(v.qt_votos_nominais + v.qt_votos_legenda) AS VOTOS_ESQ, "
        "       SUM(v.qt_votos_nominais + v.qt_votos_legenda) AS VOTOS_TOT "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s "
        "GROUP BY v.nr_zona"
    )
    sql_esq = (
        "SELECT v.nr_zona AS NR_ZONA, "
        "       SUM(v.qt_votos_nominais + v.qt_votos_legenda) AS VOTOS "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s "
        f"  AND v.nr_partido IN {PARTIDOS_ESQUERDA} "
        "GROUP BY v.nr_zona"
    )
    sql_tot = (
        "SELECT v.nr_zona AS NR_ZONA, "
        "       SUM(v.qt_votos_nominais + v.qt_votos_legenda) AS VOTOS "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s "
        "GROUP BY v.nr_zona"
    )
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute(sql_esq, (ano, cargo_ds, CD_MUNICIPIO_BRASILIA))
        esq = dict(cur.fetchall())
        cur.execute(sql_tot, (ano, cargo_ds, CD_MUNICIPIO_BRASILIA))
        tot = dict(cur.fetchall())
    finally:
        conn.close()
    pct = {
        z: (esq.get(z, 0) / tot[z] * 100 if tot[z] > 0 else 0)
        for z in tot
    }
    return pd.Series(pct, name=f"pct_esq_{ano}").sort_index()


def variacao_esquerda(cargo_label: str) -> pd.Series:
    """Variação (% pontos) do voto da esquerda entre ANO_BASE e ANO_FINAL,
    por zona, para o cargo dado."""
    cargo_ds = CARGOS[cargo_label]
    inicio = votos_esquerda_por_zona(ANO_BASE, cargo_ds)
    fim = votos_esquerda_por_zona(ANO_FINAL, cargo_ds)
    zonas = inicio.index.intersection(fim.index)
    diff = (fim.loc[zonas].astype(float) - inicio.loc[zonas].astype(float))
    return diff.rename(cargo_label)


def main() -> None:
    print(f"\n=== Correlação inter-cargos, esquerda, {ANO_BASE}→{ANO_FINAL} (DF) ===")
    series = {label: variacao_esquerda(label) for label in CARGOS}
    df = pd.concat(series.values(), axis=1).dropna()
    print(f"Zonas com dado válido em todos os cargos: {len(df)}")

    print("\nEstatísticas descritivas da variação (pp):")
    print(df.describe().round(2))

    print("\nMatriz de correlação Pearson:")
    pearson = df.corr(method="pearson").round(3)
    print(pearson)

    print("\nMatriz de correlação Spearman:")
    spearman = df.corr(method="spearman").round(3)
    print(spearman)

    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    pearson.to_csv(SAIDA_CSV.with_name("correlacao_cargos_pearson.csv"))
    spearman.to_csv(SAIDA_CSV.with_name("correlacao_cargos_spearman.csv"))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, mat, titulo in zip(
        axes, [pearson, spearman], ["Pearson", "Spearman"]
    ):
        im = ax.imshow(mat, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(len(mat)))
        ax.set_xticklabels(mat.columns, rotation=30, ha="right")
        ax.set_yticks(range(len(mat)))
        ax.set_yticklabels(mat.index)
        for i in range(len(mat)):
            for j in range(len(mat)):
                ax.text(
                    j, i, f"{mat.iloc[i, j]:.2f}",
                    ha="center", va="center",
                    color="black" if abs(mat.iloc[i, j]) < 0.6 else "white",
                )
        ax.set_title(f"{titulo} — Δ esquerda {ANO_BASE}→{ANO_FINAL}")
        plt.colorbar(im, ax=ax)
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(SAIDA_FIG, dpi=300)
    print(f"\nFig: {SAIDA_FIG}")
    print(f"CSVs: {SAIDA_CSV.parent}")


if __name__ == "__main__":
    main()
