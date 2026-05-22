"""TESTE D — Quebra estrutural no crescimento da esquerda nas top zonas — DF.

Adaptado de `sintese/quebra_estrutural_psol.py` do SP. Diferenças:
  * Cargo: Deputado Distrital (análogo a Vereador em SP).
  * Bloco testado: esquerda completa (Bolognesi), não só PSOL — decisão
    do usuário (D4), motivada pelo N pequeno do PSOL no DF.
  * Janela: 1998-2022 (anos federais).
  * Top-N zonas: top-5 por índice institucional (com N=19 zonas total,
    top-5 é ~26% do espaço; top-10 seria mais da metade, perde sinal).

Método (Chow test):
  * Modelo restrito: regressão linear simples y = a + b·t.
  * Modelo não-restrito: duas retas com quebra em t = ano_quebra.
  * F = ((SSR_R − SSR_NR)/k) / (SSR_NR / (n − 2k)), k = 2.
  * Reportar F e p-valor para cada candidato a ano de quebra (interior).

LIMITAÇÃO: N=7 pontos no tempo → poder estatístico muito baixo, tal
como em SP. Resultado é indicativo, não conclusivo.
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
ANOS = [1998, 2002, 2006, 2010, 2014, 2018, 2022]
CSV_INDICE = _ROOT / "outputs/indice_institucional_por_zona.csv"
SAIDA_FIG = _ROOT / "outputs/figures/quebra_estrutural_esquerda.png"
SAIDA_CSV = _ROOT / "outputs/tables/quebra_estrutural_esquerda.csv"
TOP_N = 5


def votos_esquerda_top(zonas: list[int], ano: int) -> float:
    sql = (
        "SELECT SUM(v.qt_votos_nominais + v.qt_votos_legenda) "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s "
        f"  AND v.nr_partido IN {PARTIDOS_ESQUERDA} "
        f"  AND v.nr_zona IN ({','.join(map(str, zonas))})"
    )
    conn = mysql.connector.connect(database=DATABASE, **MYSQL_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql, (ano, CARGO_DS, CD_MUNICIPIO_BRASILIA))
        (v,) = cur.fetchone()
    finally:
        conn.close()
    return float(v or 0)


def chow_F(t: np.ndarray, y: np.ndarray, t_break: float) -> tuple[float, float]:
    """Retorna (F, p) do Chow test em t_break (ponto de quebra)."""
    n = len(y)
    k = 2  # cada regime tem intercepto + slope
    # Modelo restrito (1 reta)
    X = np.column_stack([np.ones(n), t])
    beta_r, *_ = np.linalg.lstsq(X, y, rcond=None)
    res_r = y - X @ beta_r
    ssr_r = float((res_r ** 2).sum())

    # Modelo não-restrito (2 retas)
    mask1 = t <= t_break
    mask2 = ~mask1
    X1 = np.column_stack([np.ones(mask1.sum()), t[mask1]])
    X2 = np.column_stack([np.ones(mask2.sum()), t[mask2]])
    if mask1.sum() < 2 or mask2.sum() < 2:
        return float("nan"), float("nan")
    b1, *_ = np.linalg.lstsq(X1, y[mask1], rcond=None)
    b2, *_ = np.linalg.lstsq(X2, y[mask2], rcond=None)
    ssr_nr = float(((y[mask1] - X1 @ b1) ** 2).sum() + ((y[mask2] - X2 @ b2) ** 2).sum())

    df_n = k
    df_d = n - 2 * k
    if df_d <= 0 or ssr_nr <= 0:
        return float("nan"), float("nan")
    F = ((ssr_r - ssr_nr) / df_n) / (ssr_nr / df_d)
    p = 1 - stats.f.cdf(F, df_n, df_d)
    return F, p


def main() -> None:
    idx = pd.read_csv(CSV_INDICE).set_index("NR_ZONA")
    top_zonas = idx.sort_values("indice_cultural", ascending=False).head(TOP_N).index.tolist()
    print(f"\nTop-{TOP_N} zonas por índice institucional: {top_zonas}")
    print(idx.loc[top_zonas, ["indice_cultural", "n_locais", "n_universidade"]])

    serie = pd.Series(
        {ano: votos_esquerda_top(top_zonas, ano) for ano in ANOS}, name="votos_esq"
    )
    print(f"\nSérie temporal de votos-esquerda nas top-{TOP_N} zonas:")
    print(serie.astype(int))

    t = np.array(serie.index, dtype=float)
    y = serie.values.astype(float)

    print("\n=== Chow test — possíveis pontos de quebra (interior) ===")
    registros = []
    for t_break in ANOS[1:-1]:  # excluir endpoints
        F, p = chow_F(t, y, float(t_break))
        registros.append({"t_break": t_break, "F": F, "p_value": p})
        print(f"  t_break={t_break}: F={F:.3f}, p={p:.4f}")
    df_res = pd.DataFrame(registros)
    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_res.to_csv(SAIDA_CSV, index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t, y, "o-", color="navy")
    ax.set_xlabel("Ano")
    ax.set_ylabel("Votos esquerda (top-5 zonas)")
    ax.set_title(
        f"Trajetória da esquerda nas top-{TOP_N} zonas institucionais — Dep. Distrital DF"
    )
    ax.grid(alpha=0.3)
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(SAIDA_FIG, dpi=300)
    print(f"\nFig: {SAIDA_FIG}\nCSV: {SAIDA_CSV}")


if __name__ == "__main__":
    main()
