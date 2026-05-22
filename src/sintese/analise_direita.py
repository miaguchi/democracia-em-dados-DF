"""TESTE E — Análise simétrica da DIREITA, DF 1998-2022.

Replica os Testes A (regressão crescimento × índice institucional) e
C (HHI/Gini) usando partidos de direita, para comparação com a esquerda.

Partidos de direita (Bolognesi, Ribeiro & Codato 2023; mesma lista do
projeto SP, D6 confirmado pelo usuário):
  22 (PL), 11 (PP), 10 (REPUBLICANOS), 44 (UNIÃO), 25 (DEM),
  28 (PRTB), 14 (PTB), 55 (PSD), 20 (PODE)

Hipóteses:
  * Se a tese institucional é específica à esquerda, o R² para a
    direita deve ser baixo ou o β invertido.
  * HHI/Gini da direita pode ter trajetória diferente da esquerda
    (concentração em RAs específicas, ou homogeneidade).

Janela: 2010 → 2022 (regressão); 1998-2022 anos federais (HHI/Gini).
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
from scipy import stats

from src.ingestao.carregar_mysql import DATABASE, MYSQL_CONFIG
from src.sintese.concentracao_territorial import hhi, gini

CD_MUNICIPIO_BRASILIA = 97012
CARGO_DS = "Deputado Distrital"
PARTIDOS_DIREITA = (22, 11, 10, 44, 25, 28, 14, 55, 20)
ANOS = [1998, 2002, 2006, 2010, 2014, 2018, 2022]
ANO_BASE = 2010
ANO_FINAL = 2022

CSV_INDICE = _ROOT / "outputs/indice_institucional_por_zona.csv"
SAIDA_FIG = _ROOT / "outputs/figures/concentracao_territorial_direita.png"
SAIDA_CSV_HHI = _ROOT / "outputs/tables/concentracao_territorial_direita.csv"
SAIDA_CSV_REG = _ROOT / "outputs/tables/regressao_crescimento_direita.csv"
SAIDA_FIG_REG = _ROOT / "outputs/figures/regressao_crescimento_direita.png"


def votos_direita_por_zona(ano: int) -> pd.Series:
    sql_dir = (
        "SELECT v.nr_zona, "
        "       SUM(v.qt_votos_nominais + v.qt_votos_legenda) "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s "
        f"  AND v.nr_partido IN {PARTIDOS_DIREITA} "
        "GROUP BY v.nr_zona"
    )
    conn = mysql.connector.connect(database=DATABASE, **MYSQL_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql_dir, (ano, CARGO_DS, CD_MUNICIPIO_BRASILIA))
        rows = cur.fetchall()
    finally:
        conn.close()
    return pd.Series({z: float(v) for z, v in rows}, name=str(ano)).sort_index()


def votos_totais_por_zona(ano: int) -> pd.Series:
    sql_tot = (
        "SELECT v.nr_zona, "
        "       SUM(v.qt_votos_nominais + v.qt_votos_legenda) "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s "
        "GROUP BY v.nr_zona"
    )
    conn = mysql.connector.connect(database=DATABASE, **MYSQL_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql_tot, (ano, CARGO_DS, CD_MUNICIPIO_BRASILIA))
        rows = cur.fetchall()
    finally:
        conn.close()
    return pd.Series({z: float(v) for z, v in rows}, name=str(ano)).sort_index()


def main() -> None:
    # =================== Concentração HHI/Gini ====================
    registros = []
    for ano in ANOS:
        v = votos_direita_por_zona(ano)
        if v.empty:
            continue
        registros.append(
            {"ano": ano, "n_zonas": len(v),
             "total_votos_dir": int(v.sum()),
             "HHI": hhi(v), "Gini": gini(v)}
        )
    df_hhi = pd.DataFrame(registros)
    print("\n=== Concentração territorial da DIREITA — Dep. Distrital DF ===")
    print(df_hhi.round(4).to_string(index=False))
    SAIDA_CSV_HHI.parent.mkdir(parents=True, exist_ok=True)
    df_hhi.to_csv(SAIDA_CSV_HHI, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(df_hhi["ano"], df_hhi["HHI"], "o-", color="darkred")
    axes[0].set_title("HHI direita por zona")
    axes[0].set_xlabel("Ano"); axes[0].set_ylabel("HHI"); axes[0].grid(alpha=0.3)
    axes[1].plot(df_hhi["ano"], df_hhi["Gini"], "o-", color="darkred")
    axes[1].set_title("Gini direita por zona")
    axes[1].set_xlabel("Ano"); axes[1].set_ylabel("Gini"); axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(SAIDA_FIG, dpi=300)
    print(f"Fig: {SAIDA_FIG}")

    # =================== Regressão Δ direita × índice ====================
    dir_base = votos_direita_por_zona(ANO_BASE)
    tot_base = votos_totais_por_zona(ANO_BASE)
    dir_fim = votos_direita_por_zona(ANO_FINAL)
    tot_fim = votos_totais_por_zona(ANO_FINAL)
    pct_base = (dir_base / tot_base * 100).rename("pct_base")
    pct_fim = (dir_fim / tot_fim * 100).rename("pct_fim")
    delta = (pct_fim - pct_base).rename("delta_pct_direita")

    idx = pd.read_csv(CSV_INDICE).set_index("NR_ZONA")
    merge = pd.concat([idx[["indice_cultural"]], delta], axis=1).dropna()
    print(f"\n=== Regressão Δdireita 2010→2022 × índice institucional ===")
    print(f"Zonas: {len(merge)}")
    print(merge.round(2).to_string())

    x = merge["indice_cultural"].values.astype(float)
    y = merge["delta_pct_direita"].values.astype(float)
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    ss_res = float(((y - y_hat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot
    # erro-padrão e t-stat
    n = len(x); k = 2
    sigma2 = ss_res / (n - k)
    cov = sigma2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t_stat = beta / se
    p_val = 2 * (1 - stats.t.cdf(np.abs(t_stat), n - k))

    print(
        f"\nOLS: Δdireita = {beta[0]:+.3f} + {beta[1]:+.4f} × índice"
    )
    print(
        f"     se=({se[0]:.3f}, {se[1]:.4f}) | t=({t_stat[0]:+.2f}, {t_stat[1]:+.2f}) | "
        f"p=({p_val[0]:.4f}, {p_val[1]:.4f})"
    )
    print(f"     R² = {r2:.3f}, N = {n}")

    SAIDA_CSV_REG.parent.mkdir(parents=True, exist_ok=True)
    merge.to_csv(SAIDA_CSV_REG)

    fig2, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(x, y, s=40)
    xs = np.linspace(x.min(), x.max(), 100)
    ax.plot(xs, beta[0] + beta[1] * xs, "r-")
    ax.axhline(0, color="grey", lw=0.5)
    ax.set_xlabel("Índice institucional (% locais culturais-progressistas)")
    ax.set_ylabel("Δ% direita 2010→2022 (pontos percentuais)")
    ax.set_title(f"Δdireita × índice institucional — DF (β={beta[1]:+.3f}, R²={r2:.2f})")
    ax.grid(alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(SAIDA_FIG_REG, dpi=300)
    print(f"Fig: {SAIDA_FIG_REG}\nCSV: {SAIDA_CSV_REG}")


if __name__ == "__main__":
    main()
