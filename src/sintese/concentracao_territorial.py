"""TESTE C — Concentração territorial da esquerda, DF 1998-2022.

Adaptado de `sintese/concentracao_territorial.py` do SP. Aqui o cargo
de referência é **Deputado Distrital** (análogo a Vereador em SP) e a
janela é 1998-2022 (anos federais; sem ciclo municipal no DF).

Para cada ano, calcula:
  * HHI = Σ s_i² (s_i = share da zona i no voto-esquerda total)
  * Gini da distribuição de votos da esquerda por zona

Hipótese: se a esquerda concentrou-se territorialmente (Asa Norte,
Asa Sul, Lago Sul, Sudoeste), HHI e Gini sobem com o tempo.
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
CARGO_DS = "Deputado Distrital"
PARTIDOS_ESQUERDA = (13, 50, 65, 12, 40, 43, 18, 16, 29, 80)
ANOS = [1998, 2002, 2006, 2010, 2014, 2018, 2022]

SAIDA_FIG = _ROOT / "outputs/figures/concentracao_territorial.png"
SAIDA_CSV = _ROOT / "outputs/tables/concentracao_territorial.csv"


def votos_esquerda_por_zona(ano: int) -> pd.Series:
    sql = (
        "SELECT v.nr_zona, "
        "       SUM(v.qt_votos_nominais + v.qt_votos_legenda) AS votos "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s "
        f"  AND v.nr_partido IN {PARTIDOS_ESQUERDA} "
        "GROUP BY v.nr_zona"
    )
    conn = mysql.connector.connect(database=DATABASE, **MYSQL_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql, (ano, CARGO_DS, CD_MUNICIPIO_BRASILIA))
        rows = cur.fetchall()
    finally:
        conn.close()
    s = pd.Series(
        {z: float(v) for z, v in rows}, name=str(ano)
    ).sort_index()
    return s


def hhi(votos: pd.Series) -> float:
    total = votos.sum()
    if total <= 0:
        return float("nan")
    s = votos / total
    return float((s ** 2).sum())


def gini(votos: pd.Series) -> float:
    """Gini sobre valores não-negativos (Σ|x_i − x_j| / (2 n μ))."""
    x = votos.dropna().values.astype(float)
    if len(x) == 0 or x.sum() == 0:
        return float("nan")
    x = np.sort(x)
    n = len(x)
    cum = np.cumsum(x)
    return (2 * np.sum((np.arange(1, n + 1)) * x) - (n + 1) * cum[-1]) / (n * cum[-1])


def main() -> None:
    registros = []
    for ano in ANOS:
        v = votos_esquerda_por_zona(ano)
        if v.empty:
            continue
        registros.append(
            {
                "ano": ano,
                "n_zonas": len(v),
                "total_votos_esq": int(v.sum()),
                "HHI": hhi(v),
                "Gini": gini(v),
            }
        )
    df = pd.DataFrame(registros)
    print(f"\n=== Concentração territorial da esquerda — Dep. Distrital DF ===")
    print(df.round(4).to_string(index=False))

    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA_CSV, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(df["ano"], df["HHI"], "o-")
    axes[0].set_title("HHI da distribuição de votos-esquerda por zona")
    axes[0].set_ylabel("HHI")
    axes[0].set_xlabel("Ano")
    axes[0].grid(alpha=0.3)
    axes[1].plot(df["ano"], df["Gini"], "o-", color="firebrick")
    axes[1].set_title("Gini da distribuição de votos-esquerda por zona")
    axes[1].set_ylabel("Gini")
    axes[1].set_xlabel("Ano")
    axes[1].grid(alpha=0.3)
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(SAIDA_FIG, dpi=300)
    print(f"\nFig: {SAIDA_FIG}\nCSV: {SAIDA_CSV}")


if __name__ == "__main__":
    main()
