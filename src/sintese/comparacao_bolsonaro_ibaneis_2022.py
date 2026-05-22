"""Comparação espacial Bolsonaro × Ibaneis no DF, 2022 (1º turno).

Adaptado de `sintese/comparacao_bolsonaro_tarcisio_2022.py` do SP.
Bolsonaro disputou Presidente (PL=22), Ibaneis disputou Governador
(MDB=15) — ambos venceram no DF em 2022.

A hipótese análoga é: o gap entre votos majoritários do candidato
de direita federal × candidato de direita local é explicado pela
força do candidato de esquerda concorrente (Lula para Pres × Leandro
Grass / PV para Gov, federação FED_PT_PCdoB_PV).

Pipeline:
  1. Carregar votos por zona em (Pres, PL=22) e (Gov, MDB=15).
  2. Carregar votos de Lula (Pres, PT=13) e Leandro Grass (Gov, PV=43
     pela federação) por zona.
  3. Calcular razão Ibaneis/Bolsonaro por zona e correlacionar com
     razão Lula/Bolsonaro (gap em pres) e com índice institucional.
  4. Reportar zonas em que Ibaneis supera Bolsonaro e vice-versa.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import mysql.connector
import pandas as pd
from scipy import stats

from src.ingestao.carregar_mysql import DATABASE, MYSQL_CONFIG

CD_MUNICIPIO_BRASILIA = 97012
CSV_INDICE = _ROOT / "outputs/indice_institucional_por_zona.csv"
CSV_SOCIO = _ROOT / "outputs/socioeconomia_por_zona_2022.csv"
SAIDA_CSV = _ROOT / "outputs/tables/comparacao_bolsonaro_ibaneis_2022.csv"
SAIDA_FIG = _ROOT / "outputs/figures/scatter_bolsonaro_ibaneis_2022.png"


def carregar_votos() -> pd.DataFrame:
    sql = f"""
    SELECT
        v.nr_zona,
        SUM(CASE WHEN v.cd_cargo = 1 AND v.nr_partido = 22 THEN v.qt_votos_nominais ELSE 0 END) AS votos_bolsonaro,
        SUM(CASE WHEN v.cd_cargo = 3 AND v.nr_partido = 15 THEN v.qt_votos_nominais ELSE 0 END) AS votos_ibaneis,
        SUM(CASE WHEN v.cd_cargo = 1 AND v.nr_partido = 13 THEN v.qt_votos_nominais ELSE 0 END) AS votos_lula,
        SUM(CASE WHEN v.cd_cargo = 3 AND v.nr_partido = 43 THEN v.qt_votos_nominais ELSE 0 END) AS votos_leandro
    FROM votacao_partido_munzona v
    JOIN eleicao e ON v.cd_eleicao = e.cd_eleicao AND v.nr_turno = e.nr_turno
    WHERE v.cd_municipio = {CD_MUNICIPIO_BRASILIA}
      AND e.ano_eleicao = 2022
      AND e.nr_turno = 1
    GROUP BY v.nr_zona
    """
    conn = mysql.connector.connect(database=DATABASE, **MYSQL_CONFIG)
    try:
        df = pd.read_sql(sql, conn)
    finally:
        conn.close()
    for col in ["votos_bolsonaro", "votos_ibaneis", "votos_lula", "votos_leandro"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def main() -> None:
    print("=" * 65)
    print("Bolsonaro (Pres PL) × Ibaneis (Gov MDB) — DF 2022 1T")
    print("=" * 65)
    df = carregar_votos()

    # Trazer índice e renda
    idx = pd.read_csv(CSV_INDICE)[["NR_ZONA", "indice_cultural"]].rename(
        columns={"NR_ZONA": "nr_zona"}
    )
    socio = pd.read_csv(CSV_SOCIO)[
        ["NR_ZONA", "RA_geobr", "renda_resp_2022"]
    ].rename(columns={"NR_ZONA": "nr_zona"})
    df = df.merge(idx, on="nr_zona", how="left").merge(socio, on="nr_zona", how="left")

    total_b = df["votos_bolsonaro"].sum()
    total_i = df["votos_ibaneis"].sum()
    total_l = df["votos_lula"].sum()
    total_lg = df["votos_leandro"].sum()
    print(f"\nTotais (1T): Bolsonaro={total_b:,.0f}, Ibaneis={total_i:,.0f}")
    print(f"             Lula={total_l:,.0f}, Leandro={total_lg:,.0f}")
    print(f"Ratio Ibaneis/Bolsonaro = {total_i / total_b:.3f}")
    print(f"Ratio Lula/Bolsonaro    = {total_l / total_b:.3f}")
    print(f"Ratio Leandro/Lula      = {total_lg / total_l:.3f}")

    df["ratio_ibaneis_bolso"] = df["votos_ibaneis"] / df["votos_bolsonaro"]
    df["ratio_lula_bolso"] = df["votos_lula"] / df["votos_bolsonaro"]
    df["ratio_leandro_ibaneis"] = df["votos_leandro"] / df["votos_ibaneis"]
    df["diff_lula_bolso_pp"] = (
        df["votos_lula"] / (df["votos_lula"] + df["votos_bolsonaro"]) * 100
        - df["votos_bolsonaro"] / (df["votos_lula"] + df["votos_bolsonaro"]) * 100
    )
    df["diff_leandro_ibaneis_pp"] = (
        df["votos_leandro"] / (df["votos_leandro"] + df["votos_ibaneis"]) * 100
        - df["votos_ibaneis"] / (df["votos_leandro"] + df["votos_ibaneis"]) * 100
    )

    print("\n=== Zonas onde Ibaneis SUPERA Bolsonaro (mais votos) ===")
    supera = df[df["ratio_ibaneis_bolso"] > 1].sort_values(
        "ratio_ibaneis_bolso", ascending=False
    )
    print(
        supera[
            ["nr_zona", "RA_geobr", "votos_bolsonaro", "votos_ibaneis",
             "ratio_ibaneis_bolso", "indice_cultural"]
        ].round(3).to_string(index=False)
    )

    print("\n=== Zonas onde Bolsonaro SUPERA Ibaneis ===")
    nsup = df[df["ratio_ibaneis_bolso"] <= 1].sort_values(
        "ratio_ibaneis_bolso"
    )
    print(
        nsup[
            ["nr_zona", "RA_geobr", "votos_bolsonaro", "votos_ibaneis",
             "ratio_ibaneis_bolso", "indice_cultural"]
        ].round(3).to_string(index=False)
    )

    print("\n=== Correlações (Pearson) ===")
    cols = [
        "ratio_ibaneis_bolso", "ratio_lula_bolso", "ratio_leandro_ibaneis",
        "diff_lula_bolso_pp", "diff_leandro_ibaneis_pp",
        "indice_cultural", "renda_resp_2022",
    ]
    print(df[cols].corr(method="pearson").round(3))

    # Teste-chave: a razão Ibaneis/Bolsonaro varia com a força local da esquerda
    # (proxy: diff_lula_bolso_pp). Se r grande, gap é explicado por esquerda
    # local — o "transbordo" do voto presidencial para o local depende do
    # adversário direto.
    r, p = stats.pearsonr(df["ratio_ibaneis_bolso"], df["diff_lula_bolso_pp"])
    print(
        f"\nPearson ratio_ibaneis_bolso × diff_lula_bolso_pp:"
        f" r = {r:+.3f}, p = {p:.4f}"
    )

    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA_CSV, index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(df["diff_lula_bolso_pp"], df["ratio_ibaneis_bolso"], s=40)
    for _, row in df.iterrows():
        ax.annotate(
            str(row["nr_zona"]),
            (row["diff_lula_bolso_pp"], row["ratio_ibaneis_bolso"]),
            fontsize=8, alpha=0.7,
        )
    ax.axhline(1, color="grey", lw=0.5)
    ax.axvline(0, color="grey", lw=0.5)
    ax.set_xlabel("Vantagem Lula − Bolsonaro (pp) — Pres 1T")
    ax.set_ylabel("Razão Ibaneis / Bolsonaro (votos)")
    ax.set_title("Transbordo presidencial → governador no DF, 2022")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_FIG, dpi=300)
    print(f"\nFig: {SAIDA_FIG}\nCSV: {SAIDA_CSV}")


if __name__ == "__main__":
    main()
