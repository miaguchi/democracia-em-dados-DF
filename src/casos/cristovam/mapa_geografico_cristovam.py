"""Mapa GEOGRÁFICO de retenção do Cristovam Buarque (DF).

Complementa `mapa_retencao_cristovam.py` plotando o resultado dos
tiers (DEFENDER/DISPUTAR/ABANDONAR) sobre a geometria das RAs.

Pipeline:
1. Lê resultado de tiers por zona (CSV gerado).
2. Mapeia NR_ZONA → RA_DOMINANTE via outputs/zona_to_ra.csv.
3. Carrega geometria das RAs via geobr (dissolve setores por subdistrito).
4. Plota 2 painéis:
   - Mapa por tier (3 cores)
   - Mapa coroplético da variação % 2010→2018
"""

from pathlib import Path
import sys
import warnings

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import geobr
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CSV_ZONAS = _ROOT / "outputs/tables/mapa_retencao_cristovam_zonas.csv"
CSV_ZONA_RA = _ROOT / "outputs/zona_to_ra.csv"
CACHE_GEO = _ROOT / "data/raw/shapes/ras_df.gpkg"
SAIDA_FIG = _ROOT / "outputs/figures/mapa_geografico_cristovam.png"

# Aliases mesmo do mapa_volatilidade.py
RA_ALIAS = {
    "Asa Sul": "Plano Piloto", "Asa Norte": "Plano Piloto",
    "Cruzeiro": "Cruzeiro", "Octogonal": "Sudoeste/Octogonal",
    "Sudoeste": "Sudoeste/Octogonal",
    "Riacho Fundo I": "Riacho Fundo", "Riacho Fundo II": "Riacho Fundo II",
    "Guara I": "Guará", "Guara II": "Guará",
    "Ceilandia": "Ceilândia", "Aguas Claras": "Águas Claras",
    "Sao Sebastiao": "São Sebastião",
    "Recanto das Emas": "Recanto das Emas",
    "Santa Maria": "Santa Maria", "Sobradinho": "Sobradinho",
    "Sobradinho II": "Sobradinho II", "Planaltina": "Planaltina",
    "Brazlandia": "Brazlândia", "Paranoa": "Paranoá",
    "Gama": "Gama", "Taguatinga": "Taguatinga", "Samambaia": "Samambaia",
    "Lago Sul": "Lago Sul", "Lago Norte": "Lago Norte",
    "Park Way": "Park Way", "Núcleo Bandeirante": "Núcleo Bandeirante",
    "Candangolândia": "Candangolândia", "SIA": "SIA",
    "SCIA": "SCIA", "Estrutural": "SCIA",
    "Itapoa": "Itapoã", "Varjao": "Varjão", "Vicente Pires": "Vicente Pires",
    "Fercal": "Fercal", "Jardim Botanico": "Jardim Botânico",
}


def carregar_ras_geo() -> gpd.GeoDataFrame:
    """Geometria das RAs do DF (dissolve setores 2022 por subdistrito)."""
    if CACHE_GEO.exists():
        print(f"Lendo cache: {CACHE_GEO.name}")
        return gpd.read_file(CACHE_GEO)
    print("Baixando setores DF via geobr...")
    setores = geobr.read_census_tract(code_tract=5300108, year=2022)
    ras = setores.dissolve(by="name_subdistrict", as_index=False)[
        ["name_subdistrict", "geometry"]
    ]
    CACHE_GEO.parent.mkdir(parents=True, exist_ok=True)
    ras.to_file(CACHE_GEO, driver="GPKG")
    print(f"Cache salvo: {CACHE_GEO}")
    return ras


def main() -> None:
    print("=" * 75)
    print("MAPA GEOGRÁFICO — Retenção Cristovam por RA")
    print("=" * 75)

    zonas = pd.read_csv(CSV_ZONAS)
    zona_ra = pd.read_csv(CSV_ZONA_RA)
    print(f"  Zonas com tier: {len(zonas)}")
    print(f"  Mapeamento zona→RA: {len(zona_ra)}")

    df = zonas.merge(zona_ra, on="NR_ZONA", how="left")
    df["RA_geo"] = df["RA_DOMINANTE"].map(RA_ALIAS).fillna(df["RA_DOMINANTE"])

    # Agregar por RA (uma RA pode ter várias zonas)
    by_ra = df.groupby("RA_geo").agg(
        var_pct=("var_pct_10_18", "mean"),
        votos_2018=("crist_2018", "sum"),
        votos_2010=("crist_2010", "sum"),
        share_2018=("share_2018", "mean"),
        n_zonas=("NR_ZONA", "count"),
        tier=("tier", lambda s: s.mode().iloc[0] if len(s.mode()) > 0 else "—"),
    ).reset_index()

    ras = carregar_ras_geo()
    print(f"  RAs com geometria: {len(ras)}")
    gdf = ras.merge(by_ra, left_on="name_subdistrict",
                     right_on="RA_geo", how="left")
    com_dado = gdf["tier"].notna().sum()
    print(f"  RAs com dado de Cristovam: {com_dado}")

    # ===== Plot — 2 painéis =====
    fig, axes = plt.subplots(1, 2, figsize=(20, 10), dpi=120)
    cores_tier = {"DEFENDER": "#2ca02c", "DISPUTAR": "#ff7f0e",
                   "ABANDONAR": "#d62728"}

    # PAINEL 1: tier por RA
    ax = axes[0]
    gdf.boundary.plot(ax=ax, color="#888", linewidth=0.5)
    gdf[gdf["tier"].isna()].plot(ax=ax, color="#f0f0f0",
                                   edgecolor="#888", linewidth=0.5)
    for t, c in cores_tier.items():
        sub = gdf[gdf["tier"] == t]
        if sub.empty: continue
        sub.plot(ax=ax, color=c, alpha=0.85, edgecolor="black",
                 linewidth=0.5)

    # Rótulos com nome RA + votos 2018
    for _, r in gdf.iterrows():
        if pd.notna(r["tier"]):
            cx, cy = r.geometry.centroid.x, r.geometry.centroid.y
            ax.annotate(
                f"{r['RA_geo'][:12]}\n{int(r['votos_2018']):,}".replace(",", "."),
                xy=(cx, cy), ha="center", va="center", fontsize=7,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                          edgecolor="gray", alpha=0.9),
            )

    from matplotlib.patches import Patch
    handles = [Patch(facecolor=c, alpha=0.85, edgecolor="black",
                      label=f"{t} ({(gdf['tier']==t).sum()} RAs)")
               for t, c in cores_tier.items()]
    handles.append(Patch(facecolor="#f0f0f0", edgecolor="#888",
                          label="sem dado"))
    ax.legend(handles=handles, loc="lower left", fontsize=10,
               framealpha=0.95)
    ax.set_title("Tiers de campanha por RA\n"
                  "(DEFENDER / DISPUTAR / ABANDONAR)",
                  fontsize=13, fontweight="bold")
    ax.set_axis_off()

    # PAINEL 2: choropleth da variação % 2010→2018
    ax = axes[1]
    gdf.boundary.plot(ax=ax, color="#888", linewidth=0.5)
    gdf[gdf["var_pct"].isna()].plot(ax=ax, color="#f0f0f0",
                                      edgecolor="#888", linewidth=0.5)
    with_data = gdf[gdf["var_pct"].notna()].copy()
    if not with_data.empty:
        vmin, vmax = -100, 0
        with_data.plot(ax=ax, column="var_pct", cmap="RdYlGn",
                       vmin=vmin, vmax=vmax, edgecolor="black",
                       linewidth=0.5, alpha=0.9,
                       legend=True,
                       legend_kwds={"label": "Variação % 2010 → 2018",
                                    "shrink": 0.6, "orientation": "vertical"})

    for _, r in with_data.iterrows():
        cx, cy = r.geometry.centroid.x, r.geometry.centroid.y
        ax.annotate(
            f"{r['RA_geo'][:10]}\n{r['var_pct']:+.0f}%",
            xy=(cx, cy), ha="center", va="center", fontsize=7,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.18", facecolor="white",
                      edgecolor="gray", alpha=0.9),
        )
    ax.set_title("Decay de incumbência por RA\n"
                  "Variação % do voto Cristovam (Senador, 2010 → 2018)",
                  fontsize=13, fontweight="bold")
    ax.set_axis_off()

    fig.suptitle(
        "MAPA DE RETENÇÃO GEOGRÁFICO — Cristovam Buarque (DF)\n"
        f"Total 2010: 833k | Total 2018: 318k (−62%)",
        fontsize=15, fontweight="bold",
    )
    fig.tight_layout()
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_FIG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\nFigura geográfica salva: {SAIDA_FIG}")


if __name__ == "__main__":
    main()
