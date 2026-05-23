"""Mapa por LOCAL DE VOTAÇÃO — Cristovam Buarque, Senador 2018 (DF).

Refinamento de `mapa_geografico_cristovam.py`. Em vez de pintar
as 33 RAs via zona dominante (mapeamento impreciso — várias zonas
têm pct_dominante < 20%), agrega o voto Cristovam 2018 por LOCAL DE
VOTAÇÃO (~600 locais no DF) usando lat/lon do cadastro TSE 2022.

Para cada local:
  votos_cristovam = soma de QT_VOTOS nas seções daquele local
  total_validos   = soma de todos os votos nominais válidos para
                    Senador 1T naquele local
  share           = votos_cristovam / total_validos

Visualização (3 painéis):
  1. Bolhas nos locais sobre o mapa das RAs, tamanho = votos abs,
     cor = share Cristovam (azul → roxo, quartis).
  2. Choropleth das RAs com share médio (ponderado pelos votos
     válidos dos locais que caem dentro de cada polígono).
  3. Ranking top 30 locais.

Limitações: as coordenadas vêm do cadastro 2022; locais que existiam
em 2018 mas mudaram de endereço em 2022 podem ter NR_LOCAL_VOTACAO
preservado ou não — usamos merge por (NR_ZONA, NR_LOCAL_VOTACAO).
"""

from __future__ import annotations

from pathlib import Path
import sys
import warnings

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

warnings.filterwarnings("ignore")

PARQUET_2018 = _ROOT / "data/processed/votacao_secao_2018_DF.parquet"
CSV_LOCAIS = _ROOT / "data/raw/eleitorado_local_votacao_2022_DF.csv"
CACHE_GEO = _ROOT / "data/raw/shapes/ras_df.gpkg"
SAIDA_FIG = _ROOT / "outputs/figures/mapa_locais_cristovam_2018.png"
SAIDA_CSV = _ROOT / "outputs/tables/locais_cristovam_2018.csv"


def carregar_locais_coord() -> pd.DataFrame:
    """Coordenadas (lat/lon) dos locais TSE 2022 (cadastro mais recente)."""
    df = pd.read_csv(CSV_LOCAIS, sep=";", encoding="latin-1", low_memory=False)
    locais = df[
        ["NR_ZONA", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO",
         "NR_LATITUDE", "NR_LONGITUDE"]
    ].drop_duplicates(subset=["NR_ZONA", "NR_LOCAL_VOTACAO"]).copy()
    locais["lat"] = pd.to_numeric(
        locais["NR_LATITUDE"].astype(str).str.replace(",", "."), errors="coerce"
    )
    locais["lon"] = pd.to_numeric(
        locais["NR_LONGITUDE"].astype(str).str.replace(",", "."), errors="coerce"
    )
    locais = locais[(locais["lat"] < -10) & (locais["lon"] < -40)].copy()
    return locais[
        ["NR_ZONA", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO", "lat", "lon"]
    ].reset_index(drop=True)


def votos_cristovam_por_local() -> pd.DataFrame:
    """Soma de QT_VOTOS do Cristovam por (NR_ZONA, NR_LOCAL_VOTACAO) em 2018."""
    df = pd.read_parquet(PARQUET_2018)
    sub = df[
        (df["NM_VOTAVEL"].astype(str).str.contains("CRISTOVAM", case=False, na=False))
        & (df["DS_CARGO"] == "Senador")
        & (df["NR_TURNO"] == 1)
    ]
    agg = sub.groupby(["NR_ZONA", "NR_LOCAL_VOTACAO"]).agg(
        votos_cristovam=("QT_VOTOS", "sum"),
        endereco=("DS_LOCAL_VOTACAO_ENDERECO", "first"),
        nome=("NM_LOCAL_VOTACAO", "first"),
    ).reset_index()
    return agg


def total_validos_por_local() -> pd.DataFrame:
    """Total de votos nominais válidos para Senador 1T por local em 2018."""
    df = pd.read_parquet(PARQUET_2018)
    sub = df[(df["DS_CARGO"] == "Senador") & (df["NR_TURNO"] == 1)]
    agg = sub.groupby(["NR_ZONA", "NR_LOCAL_VOTACAO"])["QT_VOTOS"].sum().reset_index()
    agg = agg.rename(columns={"QT_VOTOS": "total_validos"})
    return agg


def carregar_ras_geo() -> gpd.GeoDataFrame:
    if not CACHE_GEO.exists():
        raise FileNotFoundError(
            f"Cache de RAs não existe ({CACHE_GEO}). Rode "
            "mapa_geografico_cristovam.py primeiro para gerá-lo."
        )
    return gpd.read_file(CACHE_GEO)


def main() -> None:
    print("=" * 75)
    print("MAPA POR LOCAL DE VOTAÇÃO — CRISTOVAM BUARQUE 2018 (Senador)")
    print("=" * 75)

    print("\n1) Agregando votos Cristovam por local...")
    cris = votos_cristovam_por_local()
    print(f"   locais com voto Cristovam: {len(cris)}")
    print(f"   votos totais: {cris['votos_cristovam'].sum():,}")

    print("\n2) Calculando total de válidos por local (Senador 1T)...")
    totais = total_validos_por_local()
    print(f"   locais com qualquer voto: {len(totais)}")

    df = cris.merge(totais, on=["NR_ZONA", "NR_LOCAL_VOTACAO"], how="left")
    df["share"] = df["votos_cristovam"] / df["total_validos"] * 100

    print("\n3) Juntando coordenadas (cadastro 2022)...")
    coord = carregar_locais_coord()
    df = df.merge(coord, on=["NR_ZONA", "NR_LOCAL_VOTACAO"], how="left")
    com_coord = df["lat"].notna().sum()
    print(f"   locais geocodificados: {com_coord}/{len(df)} "
          f"({com_coord/len(df)*100:.1f}%)")

    # Salvar tabela
    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values("votos_cristovam", ascending=False).to_csv(SAIDA_CSV, index=False)
    print(f"\nCSV salvo: {SAIDA_CSV}")

    # Ranking top 30
    print(f"\nTOP 30 locais por voto absoluto Cristovam 2018:")
    top30 = df.nlargest(30, "votos_cristovam")
    for _, r in top30.iterrows():
        print(f"  Z{int(r.NR_ZONA):>2} L{int(r.NR_LOCAL_VOTACAO):>5}  "
              f"{int(r.votos_cristovam):>5} votos  "
              f"share {r.share:>5.1f}%  {str(r.nome)[:50]}")

    # Geo
    df_geo = df.dropna(subset=["lat", "lon"]).copy()
    gdf = gpd.GeoDataFrame(
        df_geo, geometry=gpd.points_from_xy(df_geo["lon"], df_geo["lat"]),
        crs="EPSG:4674",
    )
    ras = carregar_ras_geo()
    if ras.crs is None:
        ras = ras.set_crs("EPSG:4674")
    if ras.crs.to_string() != gdf.crs.to_string():
        ras = ras.to_crs(gdf.crs)

    # ===== Agregar locais -> RA via spatial join =====
    sj = gpd.sjoin(gdf, ras[["name_subdistrict", "geometry"]],
                   how="left", predicate="within")
    sj = sj.dropna(subset=["name_subdistrict"])
    print(f"\n4) Spatial join: {len(sj)}/{len(gdf)} locais dentro de uma RA")

    by_ra = sj.groupby("name_subdistrict").apply(
        lambda g: pd.Series({
            "votos_cristovam": g["votos_cristovam"].sum(),
            "total_validos": g["total_validos"].sum(),
            "n_locais": len(g),
        })
    ).reset_index()
    by_ra["share"] = by_ra["votos_cristovam"] / by_ra["total_validos"] * 100

    ras_plot = ras.merge(by_ra, on="name_subdistrict", how="left")
    com_dado = ras_plot["share"].notna().sum()
    print(f"   RAs com pelo menos 1 local: {com_dado}/{len(ras_plot)}")

    # ===== Plot =====
    fig = plt.figure(figsize=(20, 12), dpi=120)
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 0.9], hspace=0.18, wspace=0.10)

    # PAINEL 1: bolhas nos locais sobre RAs
    ax1 = fig.add_subplot(gs[:, 0])
    ras_plot.plot(ax=ax1, facecolor="#f5f5f5", edgecolor="white", linewidth=0.6)

    # Quartis de share para colorir
    q = np.nanpercentile(gdf["share"], [25, 50, 75])
    cores_q = ["#bdd7e7", "#6baed6", "#3182bd", "#08519c"]
    def quartil(s):
        if s < q[0]: return 0
        if s < q[1]: return 1
        if s < q[2]: return 2
        return 3
    gdf["_qshare"] = gdf["share"].apply(quartil)
    gdf["_cor"] = gdf["_qshare"].map(dict(enumerate(cores_q)))
    gdf["_size"] = np.clip(gdf["votos_cristovam"] / 8, 5, 250)

    ax1.scatter(gdf["lon"], gdf["lat"], s=gdf["_size"], c=gdf["_cor"],
                edgecolor="black", linewidth=0.3, alpha=0.85)

    # Anotar nomes de RA grandes
    grandes = ["Plano Piloto", "Ceilândia", "Taguatinga", "Samambaia",
               "Lago Sul", "Lago Norte", "Águas Claras", "Gama",
               "Planaltina", "Sobradinho", "Recanto das Emas", "Paranoá",
               "Cruzeiro", "Sudoeste/Octogonal", "Guará"]
    for _, row in ras_plot.iterrows():
        if row["name_subdistrict"] in grandes and row.geometry is not None:
            cent = row.geometry.representative_point()
            ax1.annotate(row["name_subdistrict"], (cent.x, cent.y),
                         ha="center", va="center", fontsize=7,
                         color="#444", alpha=0.7)
    ax1.set_title(f"Locais de votação — Cristovam 2018 (N={len(gdf)})\n"
                  f"Tamanho = votos absolutos | Cor = share local (quartis)",
                  fontsize=11, fontweight="bold")
    ax1.set_axis_off()

    # Legenda tamanho
    sizes_demo = [50, 500, 2000]
    handles_size = [
        Line2D([], [], marker="o", linestyle="",
               markerfacecolor="#08519c", markeredgecolor="black",
               markersize=np.sqrt(np.clip(v/8, 5, 250)),
               label=f"{v} votos")
        for v in sizes_demo
    ]
    handles_cor = [
        Line2D([], [], marker="o", linestyle="", markerfacecolor=cores_q[0],
               markeredgecolor="black", markersize=8,
               label=f"share <{q[0]:.1f}% (Q1)"),
        Line2D([], [], marker="o", linestyle="", markerfacecolor=cores_q[1],
               markeredgecolor="black", markersize=8,
               label=f"{q[0]:.1f}–{q[1]:.1f}% (Q2)"),
        Line2D([], [], marker="o", linestyle="", markerfacecolor=cores_q[2],
               markeredgecolor="black", markersize=8,
               label=f"{q[1]:.1f}–{q[2]:.1f}% (Q3)"),
        Line2D([], [], marker="o", linestyle="", markerfacecolor=cores_q[3],
               markeredgecolor="black", markersize=8,
               label=f">{q[2]:.1f}% (Q4)"),
    ]
    leg1 = ax1.legend(handles=handles_size, loc="lower left", fontsize=8,
                      title="Volume", framealpha=0.92)
    ax1.add_artist(leg1)
    ax1.legend(handles=handles_cor, loc="upper right", fontsize=8,
               title="Intensidade", framealpha=0.92)

    # PAINEL 2: choropleth das RAs por share agregado
    ax2 = fig.add_subplot(gs[0, 1])
    ras_plot.boundary.plot(ax=ax2, color="#888", linewidth=0.5)
    sem_dado = ras_plot[ras_plot["share"].isna()]
    if not sem_dado.empty:
        sem_dado.plot(ax=ax2, color="#f0f0f0", edgecolor="#888", linewidth=0.5)
    com_dado_df = ras_plot[ras_plot["share"].notna()].copy()
    com_dado_df.plot(ax=ax2, column="share", cmap="Blues",
                     edgecolor="black", linewidth=0.4, alpha=0.92,
                     legend=True,
                     legend_kwds={"label": "Share Cristovam (%)",
                                  "shrink": 0.7, "orientation": "vertical"})
    for _, r in com_dado_df.iterrows():
        cx, cy = r.geometry.centroid.x, r.geometry.centroid.y
        ax2.annotate(
            f"{r['name_subdistrict'][:12]}\n{r['share']:.1f}%",
            xy=(cx, cy), ha="center", va="center", fontsize=6.5,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                      edgecolor="gray", alpha=0.85),
        )
    ax2.set_title("Share agregado por RA\n(ponderado pelos votos válidos)",
                  fontsize=10, fontweight="bold")
    ax2.set_axis_off()

    # PAINEL 3: votos absolutos agregados por RA
    ax3 = fig.add_subplot(gs[1, 1])
    ras_plot.boundary.plot(ax=ax3, color="#888", linewidth=0.5)
    sem_dado3 = ras_plot[ras_plot["votos_cristovam"].isna()]
    if not sem_dado3.empty:
        sem_dado3.plot(ax=ax3, color="#f0f0f0", edgecolor="#888", linewidth=0.5)
    com_dado_df.plot(ax=ax3, column="votos_cristovam", cmap="Greens",
                     edgecolor="black", linewidth=0.4, alpha=0.92,
                     legend=True,
                     legend_kwds={"label": "Votos absolutos",
                                  "shrink": 0.7, "orientation": "vertical"})
    for _, r in com_dado_df.iterrows():
        cx, cy = r.geometry.centroid.x, r.geometry.centroid.y
        ax3.annotate(
            f"{r['name_subdistrict'][:12]}\n"
            f"{int(r['votos_cristovam']):,}".replace(",", "."),
            xy=(cx, cy), ha="center", va="center", fontsize=6.5,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                      edgecolor="gray", alpha=0.85),
        )
    ax3.set_title("Votos absolutos agregados por RA",
                  fontsize=10, fontweight="bold")
    ax3.set_axis_off()

    # PAINEL 4: top 30 ranking
    ax4 = fig.add_subplot(gs[:, 2])
    top30 = df.dropna(subset=["lat"]).nlargest(30, "votos_cristovam").iloc[::-1]
    cores_bar = top30["share"].apply(quartil).map(dict(enumerate(cores_q)))
    labels = [
        f"Z{int(r.NR_ZONA)} • {str(r.nome)[:32]}"
        for _, r in top30.iterrows()
    ]
    ax4.barh(range(len(top30)), top30["votos_cristovam"],
             color=cores_bar, edgecolor="black", linewidth=0.4, alpha=0.9)
    ax4.set_yticks(range(len(top30)))
    ax4.set_yticklabels(labels, fontsize=7)
    for i, (_, r) in enumerate(top30.iterrows()):
        ax4.text(r.votos_cristovam + 20, i,
                 f"{int(r.votos_cristovam):,} ({r.share:.0f}%)",
                 va="center", fontsize=6.5)
    ax4.set_xlabel("Votos Cristovam 2018", fontsize=9)
    ax4.set_title("Top 30 locais — base residual 2018",
                  fontsize=10, fontweight="bold")
    ax4.grid(axis="x", alpha=0.3)

    fig.suptitle(
        "CRISTOVAM BUARQUE — MAPA POR LOCAL DE VOTAÇÃO (Senador, DF, 2018)\n"
        f"{len(gdf):,} locais geocodificados | "
        f"{int(df['votos_cristovam'].sum()):,} votos totais | "
        f"share médio {df['share'].mean():.1f}% | mediana {df['share'].median():.1f}%",
        fontsize=13, fontweight="bold",
    )
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_FIG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\nFigura salva: {SAIDA_FIG}")


if __name__ == "__main__":
    main()
