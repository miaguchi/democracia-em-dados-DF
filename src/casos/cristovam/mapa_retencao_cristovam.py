"""Mapa de retenção de Cristovam Buarque — DF, 1998-2018.

Replica o Tipo 4 do Diagnóstico Estratégico DF (decay de incumbência)
para o caso Cristovam Buarque, com a granularidade disponível.

Candidaturas:
  1998 Governador (PT) — perdeu (2T)        — incluída para histórico
  2002 Senador (PT)    — eleito, 680.715 votos
  2010 Senador (PDT)   — eleito, 833.480 votos (PICO)
  2018 Senador (PPS)   — não eleito, 317.778 votos (-62%)

Análise em dois níveis:
1) Por zona eleitoral (19 zonas DF), 4 ciclos: trajetória nominal +
   normalização por votos válidos da zona + matriz de correlação
   2002-2010-2018 (mesma cargo).
2) Por seção eleitoral, 2018 apenas (granularidade que existe):
   onde estava a base na última candidatura, identificando núcleos
   de retenção residual e zonas de erosão.

Entregável: tabela de zonas em 3 tiers (defender/disputar/abandonar)
+ mapa por zona da variação 2010→2018 + mapa por seção 2018.
"""

from pathlib import Path
import sys
import warnings

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA = _ROOT / "data" / "processed"
SAIDA_FIG = _ROOT / "outputs" / "figures" / "mapa_retencao_cristovam.png"
SAIDA_CSV = _ROOT / "outputs" / "tables" / "mapa_retencao_cristovam_zonas.csv"
SAIDA_TIERS = _ROOT / "outputs" / "tables" / "mapa_retencao_cristovam_tiers.csv"

CARGO_GOV = "Governador"
CARGO_SEN = "Senador"


def votos_cristovam_por_zona(ano: int, cargo: str) -> pd.Series:
    """Votos do Cristovam por zona eleitoral em um ano/cargo."""
    f = DATA / f"votacao_candidato_munzona_{ano}_DF.parquet"
    df = pd.read_parquet(f)
    sub = df[
        (df["NM_CANDIDATO"].astype(str).str.contains("CRISTOVAM", case=False, na=False))
        & (df["DS_CARGO"] == cargo)
        & (df["NR_TURNO"] == 1)
    ]
    if len(sub) == 0:
        return pd.Series(dtype=float, name=f"cristovam_{ano}")
    g = sub.groupby("NR_ZONA")["QT_VOTOS_NOMINAIS"].sum()
    g.name = f"cristovam_{ano}"
    return g


def total_votos_por_zona(ano: int, cargo: str) -> pd.Series:
    """Total de votos nominais válidos por zona, para normalizar share."""
    f = DATA / f"votacao_candidato_munzona_{ano}_DF.parquet"
    df = pd.read_parquet(f)
    sub = df[(df["DS_CARGO"] == cargo) & (df["NR_TURNO"] == 1)]
    g = sub.groupby("NR_ZONA")["QT_VOTOS_NOMINAIS"].sum()
    g.name = f"total_{ano}"
    return g


def votos_secao_cristovam_2018() -> pd.DataFrame:
    """Votos por seção do Cristovam em 2018 (Senador, 1T)."""
    f = DATA / "votacao_secao_2018_DF.parquet"
    df = pd.read_parquet(f)
    sub = df[
        (df["NM_VOTAVEL"].astype(str).str.contains("CRISTOVAM", case=False, na=False))
        & (df["DS_CARGO"] == "Senador")
        & (df["NR_TURNO"] == 1)
    ]
    return sub[["NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO",
                "NM_LOCAL_VOTACAO", "QT_VOTOS"]].copy()


def main() -> None:
    print("=" * 75)
    print("MAPA DE RETENÇÃO — CRISTOVAM BUARQUE (DF, 1998-2018)")
    print("=" * 75)

    # ===== 1) Trajetória por zona, cargo Senador (2002, 2010, 2018) =====
    print("\n1) Trajetória por zona — cargo Senador (3 ciclos comparáveis):")
    s02 = votos_cristovam_por_zona(2002, CARGO_SEN)
    s10 = votos_cristovam_por_zona(2010, CARGO_SEN)
    s18 = votos_cristovam_por_zona(2018, CARGO_SEN)

    tot02 = total_votos_por_zona(2002, CARGO_SEN)
    tot10 = total_votos_por_zona(2010, CARGO_SEN)
    tot18 = total_votos_por_zona(2018, CARGO_SEN)

    df = pd.concat(
        {"crist_2002": s02, "crist_2010": s10, "crist_2018": s18,
         "total_2002": tot02, "total_2010": tot10, "total_2018": tot18},
        axis=1,
    ).fillna(0).astype(int)

    df["share_2002"] = df["crist_2002"] / df["total_2002"].replace(0, np.nan) * 100
    df["share_2010"] = df["crist_2010"] / df["total_2010"].replace(0, np.nan) * 100
    df["share_2018"] = df["crist_2018"] / df["total_2018"].replace(0, np.nan) * 100

    df["var_abs_10_18"] = df["crist_2018"] - df["crist_2010"]
    df["var_pct_10_18"] = (
        (df["crist_2018"] - df["crist_2010"]) /
        df["crist_2010"].replace(0, np.nan) * 100
    )
    df["var_share_10_18"] = df["share_2018"] - df["share_2010"]
    df["var_share_02_18"] = df["share_2018"] - df["share_2002"]

    df = df.sort_values("crist_2010", ascending=False)
    df.index.name = "NR_ZONA"

    print(df[["crist_2002", "crist_2010", "crist_2018",
              "share_2002", "share_2010", "share_2018",
              "var_pct_10_18", "var_share_10_18"]].round(2).to_string())

    # Totais
    print(f"\nTotais por ciclo:")
    print(f"  2002: {df['crist_2002'].sum():>8,}  share médio {df['share_2002'].mean():5.1f}%")
    print(f"  2010: {df['crist_2010'].sum():>8,}  share médio {df['share_2010'].mean():5.1f}%  (PICO)")
    print(f"  2018: {df['crist_2018'].sum():>8,}  share médio {df['share_2018'].mean():5.1f}%")
    print(f"  Variação 2010→2018: {df['crist_2018'].sum() - df['crist_2010'].sum():+,} "
          f"({(df['crist_2018'].sum()/df['crist_2010'].sum() - 1) * 100:+.1f}%)")

    # Matriz de correlação seção... aqui por zona (3 ciclos)
    print(f"\n2) Correlação inter-ciclo das shares (zonas):")
    print(df[["share_2002", "share_2010", "share_2018"]].corr().round(3).to_string())

    # ===== 3) Tiers — defender / disputar / abandonar =====
    # Critério:
    # - DEFENDER:  alta share_2018 + retenção alta (var_pct > -50%) — base que aguenta
    # - DISPUTAR:  share_2018 médio + retenção parcial — recuperável
    # - ABANDONAR: share_2018 baixo + queda profunda (var_pct < -65%) — perdido
    def tier(r):
        s = r["share_2018"] if pd.notna(r["share_2018"]) else 0
        v = r["var_pct_10_18"] if pd.notna(r["var_pct_10_18"]) else -100
        if s >= 5 and v > -50:
            return "DEFENDER"
        if s >= 3 and v > -65:
            return "DISPUTAR"
        return "ABANDONAR"

    df["tier"] = df.apply(tier, axis=1)

    print(f"\n3) Classificação por tier (N={len(df)} zonas):")
    print(df["tier"].value_counts().to_string())
    print(f"\nDETALHE POR TIER:")
    for t in ["DEFENDER", "DISPUTAR", "ABANDONAR"]:
        sub = df[df["tier"] == t]
        if sub.empty:
            continue
        print(f"\n  {t} ({len(sub)} zonas, "
              f"{sub['crist_2018'].sum():,} votos em 2018):")
        for nz, r in sub.iterrows():
            print(f"    Z{int(nz):>2}  votos 2010={int(r['crist_2010']):>6,} "
                  f"→ 2018={int(r['crist_2018']):>6,}  "
                  f"({r['var_pct_10_18']:+6.1f}%)  share 2018={r['share_2018']:5.1f}%")

    # Salvar tabelas
    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA_CSV)
    print(f"\nCSV salvo: {SAIDA_CSV}")

    tiers_resumo = df.groupby("tier").agg(
        n_zonas=("crist_2010", "count"),
        votos_2010=("crist_2010", "sum"),
        votos_2018=("crist_2018", "sum"),
        share_2018_med=("share_2018", "mean"),
        var_pct_med=("var_pct_10_18", "mean"),
    ).round(2)
    tiers_resumo.to_csv(SAIDA_TIERS)
    print(f"CSV tiers: {SAIDA_TIERS}")

    # ===== 4) Granular por seção 2018 =====
    print(f"\n4) Granular por seção — 2018:")
    secoes = votos_secao_cristovam_2018()
    print(f"  Seções com voto Cristovam: {len(secoes)}")
    print(f"  Locais de votação distintos: {secoes['NR_LOCAL_VOTACAO'].nunique()}")
    print(f"  Total votos seção: {secoes['QT_VOTOS'].sum():,}")
    print(f"\n  TOP 10 locais de votação (votos absolutos):")
    top_loc = secoes.groupby(
        ["NR_ZONA", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO"]
    )["QT_VOTOS"].sum().sort_values(ascending=False).head(10)
    for (nz, nlv, nm), v in top_loc.items():
        print(f"    Z{int(nz):>2} L{int(nlv):>5}  {v:>4,} votos  {nm[:60]}")

    # ===== 5) Plot — 4 painéis =====
    fig, axes = plt.subplots(2, 2, figsize=(15, 11), dpi=120)
    cores_tier = {"DEFENDER": "#2ca02c", "DISPUTAR": "#ff7f0e", "ABANDONAR": "#d62728"}

    # Painel 1: trajetória dos votos absolutos por zona
    ax = axes[0, 0]
    df_plot = df.sort_values("crist_2010", ascending=True)
    y = np.arange(len(df_plot))
    ax.plot(df_plot["crist_2002"], y, "o-", color="#1f77b4", label="2002 (PT)",
             markersize=6, linewidth=1.5, alpha=0.8)
    ax.plot(df_plot["crist_2010"], y, "s-", color="#2ca02c", label="2010 (PDT, PICO)",
             markersize=6, linewidth=1.5, alpha=0.8)
    ax.plot(df_plot["crist_2018"], y, "^-", color="#d62728", label="2018 (PPS)",
             markersize=6, linewidth=1.5, alpha=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([f"Z{int(z)}" for z in df_plot.index], fontsize=8)
    ax.set_xlabel("Votos absolutos do Cristovam")
    ax.set_title("Trajetória nominal por zona — 3 ciclos comparáveis (Senador)",
                  fontsize=11, fontweight="bold")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(axis="x", alpha=0.3)

    # Painel 2: variação % 2010→2018 por zona, colorida por tier
    ax = axes[0, 1]
    df_plot2 = df.sort_values("var_pct_10_18")
    cores = [cores_tier[t] for t in df_plot2["tier"]]
    ax.barh([f"Z{int(z)}" for z in df_plot2.index],
            df_plot2["var_pct_10_18"], color=cores, alpha=0.85,
            edgecolor="black", linewidth=0.4)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Variação % 2010 → 2018")
    ax.set_title("Decay de incumbência por zona (com tier)",
                  fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)
    # legenda de tiers
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=c, alpha=0.85, label=t) for t, c in cores_tier.items()]
    ax.legend(handles=handles, loc="lower left", fontsize=9)

    # Painel 3: share 2010 vs share 2018 — scatter (retenção relativa)
    ax = axes[1, 0]
    for t, c in cores_tier.items():
        sub = df[df["tier"] == t]
        if sub.empty: continue
        ax.scatter(sub["share_2010"], sub["share_2018"], c=c, s=80, alpha=0.8,
                   edgecolor="black", linewidth=0.4, label=t)
    lim = max(df["share_2010"].max(), df["share_2018"].max()) * 1.05
    ax.plot([0, lim], [0, lim], "k--", alpha=0.4, label="share igual")
    ax.set_xlabel("Share da zona em 2010 (PICO) %")
    ax.set_ylabel("Share da zona em 2018 %")
    for nz, r in df.iterrows():
        ax.annotate(f"Z{int(nz)}",
                    xy=(r["share_2010"], r["share_2018"]),
                    xytext=(3, 3), textcoords="offset points",
                    fontsize=7, alpha=0.8)
    ax.set_title("Retenção relativa — share da zona 2010 vs 2018",
                  fontsize=11, fontweight="bold")
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(alpha=0.3)

    # Painel 4: top locais 2018
    ax = axes[1, 1]
    top15 = top_loc.head(15)
    labels = [f"Z{int(z)} • {nm[:30]}" for (z, _, nm), _ in top15.items()]
    ax.barh(range(len(top15))[::-1], top15.values,
             color="#9467bd", alpha=0.85, edgecolor="black", linewidth=0.4)
    ax.set_yticks(range(len(top15))[::-1])
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Votos em 2018")
    ax.set_title("Top 15 locais de votação — Cristovam 2018",
                  fontsize=11, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)

    fig.suptitle(
        "MAPA DE RETENÇÃO — Cristovam Buarque (DF)\n"
        "Trajetória 2002→2010→2018 + granular por seção 2018",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout()
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_FIG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\nFigura salva: {SAIDA_FIG}")


if __name__ == "__main__":
    main()
