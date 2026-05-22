"""TESTE A — Regressão: crescimento da esquerda 2010→2022 × índice institucional — DF.

Adaptado de `sintese/regressao_crescimento_indice.py` do SP. Diferenças:
  * Cargo: Deputado Distrital (análogo a Vereador em SP).
  * Janela: 2010 → 2022.
  * Modelo: OLS múltiplo com controle de **renda** (V06004 Censo 2022,
    agregado por RA). Escolaridade 2010 (Tabela 3.5.4) ficou para
    iteração futura — proxy de renda 2022 já é controle robusto para
    a estrutura socioeconômica do DF.

Especificações reportadas:
  1. M1 (referência): Δesquerda ~ índice
  2. M2 (com renda): Δesquerda ~ índice + log(renda_2022)
  3. M3 (renda só, p/ comparação): Δesquerda ~ log(renda_2022)

Hipótese: se o índice institucional adiciona poder preditivo além da
renda (β_índice significativo em M2; ΔR² M2 vs M3 grande), a tese
institucional cultural-progressista se sustenta.
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

CD_MUNICIPIO_BRASILIA = 97012
CARGO_DS = "Deputado Distrital"
PARTIDOS_ESQUERDA = (13, 50, 65, 12, 40, 43, 18, 16, 29, 80)
ANO_BASE = 2010
ANO_FINAL = 2022
CSV_INDICE = _ROOT / "outputs/indice_institucional_por_zona.csv"
CSV_SOCIO = _ROOT / "outputs/socioeconomia_por_zona_2022.csv"
SAIDA_FIG = _ROOT / "outputs/figures/regressao_crescimento_indice.png"
SAIDA_CSV = _ROOT / "outputs/tables/regressao_crescimento_indice.csv"


def pct_esquerda(ano: int) -> pd.Series:
    sql_e = (
        "SELECT v.nr_zona, SUM(v.qt_votos_nominais + v.qt_votos_legenda) "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s "
        f"  AND v.nr_partido IN {PARTIDOS_ESQUERDA} "
        "GROUP BY v.nr_zona"
    )
    sql_t = (
        "SELECT v.nr_zona, SUM(v.qt_votos_nominais + v.qt_votos_legenda) "
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
        cur.execute(sql_e, (ano, CARGO_DS, CD_MUNICIPIO_BRASILIA))
        esq = {z: float(v) for z, v in cur.fetchall()}
        cur.execute(sql_t, (ano, CARGO_DS, CD_MUNICIPIO_BRASILIA))
        tot = {z: float(v) for z, v in cur.fetchall()}
    finally:
        conn.close()
    return pd.Series(
        {z: (esq.get(z, 0) / tot[z] * 100 if tot[z] > 0 else 0) for z in tot},
        name=f"pct_esq_{ano}",
    ).sort_index()


def _ols(X: np.ndarray, y: np.ndarray) -> dict:
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    ss_res = float(((y - y_hat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    r2_adj = 1 - (ss_res / (n - k)) / (ss_tot / (n - 1)) if (n - k) > 0 else float("nan")
    sigma2 = ss_res / (n - k) if (n - k) > 0 else float("nan")
    try:
        cov = sigma2 * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(k, float("nan"))
    t_stat = beta / se
    p_val = 2 * (1 - stats.t.cdf(np.abs(t_stat), df=max(n - k, 1)))
    return {"beta": beta, "se": se, "t": t_stat, "p": p_val,
            "r2": r2, "r2_adj": r2_adj, "n": n, "k": k}


def main() -> None:
    base = pct_esquerda(ANO_BASE)
    fim = pct_esquerda(ANO_FINAL)
    zonas = base.index.intersection(fim.index)
    delta = (fim.loc[zonas] - base.loc[zonas]).rename("delta_esq")

    idx = pd.read_csv(CSV_INDICE).set_index("NR_ZONA")[["indice_cultural"]]
    socio = pd.read_csv(CSV_SOCIO).set_index("NR_ZONA")[["renda_resp_2022"]]
    df = pd.concat([delta, idx, socio], axis=1).dropna()
    df["log_renda"] = np.log(df["renda_resp_2022"])

    print(f"\n=== Δ% esquerda Dep. Distrital DF {ANO_BASE}→{ANO_FINAL} ===")
    print(f"Zonas com todos os dados: {len(df)}")
    print(df.round(2).to_string())

    print("\n=== Correlações brutas ===")
    print(df[["delta_esq", "indice_cultural", "log_renda"]].corr().round(3))

    y = df["delta_esq"].values
    one = np.ones(len(df))

    print("\n=== M1 OLS: Δesq ~ índice ===")
    X1 = np.column_stack([one, df["indice_cultural"].values])
    r1 = _ols(X1, y)
    print(
        f"  intercepto = {r1['beta'][0]:+.3f} (se={r1['se'][0]:.3f}, p={r1['p'][0]:.4f})"
    )
    print(
        f"  índice     = {r1['beta'][1]:+.4f} (se={r1['se'][1]:.4f}, p={r1['p'][1]:.4f})"
    )
    print(f"  R² = {r1['r2']:.3f} | R²adj = {r1['r2_adj']:.3f} | N = {r1['n']}")

    print("\n=== M2 OLS: Δesq ~ índice + log(renda) ===")
    X2 = np.column_stack([one, df["indice_cultural"].values, df["log_renda"].values])
    r2 = _ols(X2, y)
    print(
        f"  intercepto = {r2['beta'][0]:+.3f} (se={r2['se'][0]:.3f}, p={r2['p'][0]:.4f})"
    )
    print(
        f"  índice     = {r2['beta'][1]:+.4f} (se={r2['se'][1]:.4f}, p={r2['p'][1]:.4f})"
    )
    print(
        f"  log_renda  = {r2['beta'][2]:+.3f} (se={r2['se'][2]:.3f}, p={r2['p'][2]:.4f})"
    )
    print(f"  R² = {r2['r2']:.3f} | R²adj = {r2['r2_adj']:.3f} | N = {r2['n']}")

    print("\n=== M3 OLS: Δesq ~ log(renda) ===")
    X3 = np.column_stack([one, df["log_renda"].values])
    r3 = _ols(X3, y)
    print(
        f"  intercepto = {r3['beta'][0]:+.3f} (se={r3['se'][0]:.3f}, p={r3['p'][0]:.4f})"
    )
    print(
        f"  log_renda  = {r3['beta'][1]:+.3f} (se={r3['se'][1]:.3f}, p={r3['p'][1]:.4f})"
    )
    print(f"  R² = {r3['r2']:.3f} | R²adj = {r3['r2_adj']:.3f} | N = {r3['n']}")

    print(f"\nΔR² M2 vs M1 (acrescentar renda) = {r2['r2'] - r1['r2']:+.3f}")
    print(f"ΔR² M2 vs M3 (acrescentar índice) = {r2['r2'] - r3['r2']:+.3f}")

    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA_CSV)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(df["indice_cultural"], df["delta_esq"], s=40)
    xs = np.linspace(df["indice_cultural"].min(), df["indice_cultural"].max(), 100)
    ax.plot(xs, r1["beta"][0] + r1["beta"][1] * xs, "r-",
            label=f"M1: β={r1['beta'][1]:+.3f}, R²={r1['r2']:.2f}")
    ax.axhline(0, color="grey", lw=0.5)
    ax.set_xlabel("Índice institucional (%)")
    ax.set_ylabel("Δ% esquerda 2010→2022 (pp)")
    ax.set_title("Crescimento da esquerda × índice institucional — DF (Dep. Distrital)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_FIG, dpi=300)
    print(f"\nFig: {SAIDA_FIG}\nCSV: {SAIDA_CSV}")


if __name__ == "__main__":
    main()
