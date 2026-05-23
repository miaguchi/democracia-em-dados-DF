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
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1 import make_axes_locatable

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
    # Layout: 1 mapa grande (choropleth share por RA + bolhas de votos)
    # + ranking top 30 à direita. Sem painéis duplicados, sem colorbars
    # do geopandas (uso cax fixado via make_axes_locatable).
    fig = plt.figure(figsize=(22, 15), dpi=120)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.4, 1.0], wspace=0.22)
    ax_map = fig.add_subplot(gs[0, 0])
    ax_rank = fig.add_subplot(gs[0, 1])

    # ----- MAPA: choropleth share por RA (Blues) + bolhas vermelhas -----
    com_dado_df = ras_plot[ras_plot["share"].notna()].copy()
    vmin = float(com_dado_df["share"].min())
    vmax = float(com_dado_df["share"].max())
    cmap = plt.get_cmap("Blues")
    norm = Normalize(vmin=vmin, vmax=vmax)

    sem_dado = ras_plot[ras_plot["share"].isna()]
    if not sem_dado.empty:
        sem_dado.plot(ax=ax_map, color="#f0f0f0",
                      edgecolor="#888", linewidth=0.5)
    com_dado_df.plot(ax=ax_map, column="share", cmap=cmap,
                     vmin=vmin, vmax=vmax,
                     edgecolor="black", linewidth=0.5, alpha=0.92)

    # Anotações curtas das RAs (somente as grandes, sem caixa branca)
    grandes = ["Plano Piloto", "Ceilândia", "Taguatinga", "Samambaia",
               "Lago Sul", "Lago Norte", "Águas Claras", "Gama",
               "Planaltina", "Sobradinho", "Recanto das Emas", "Paranoá",
               "Cruzeiro", "Sudoeste/Octogonal", "Guará", "Brazlândia",
               "Núcleo Bandeirante", "Riacho Fundo", "Santa Maria",
               "São Sebastião", "Vicente Pires"]
    for _, r in com_dado_df.iterrows():
        if r["name_subdistrict"] in grandes:
            cx, cy = r.geometry.centroid.x, r.geometry.centroid.y
            ax_map.annotate(
                f"{r['name_subdistrict']}\n{r['share']:.1f}%",
                xy=(cx, cy), ha="center", va="center", fontsize=6.5,
                color="#222", fontweight="bold", alpha=0.85,
            )

    # Bolhas (locais) em vermelho — tamanho = votos absolutos
    gdf["_size"] = np.clip(gdf["votos_cristovam"] / 8, 5, 280)
    ax_map.scatter(
        gdf["lon"], gdf["lat"], s=gdf["_size"],
        facecolor="#d62728", edgecolor="white", linewidth=0.4, alpha=0.75,
    )

    ax_map.set_title(
        f"Cristovam Buarque 2018 — locais de votação sobre share por RA\n"
        f"Choropleth (RA) = share agregado | Bolhas (local) = votos absolutos",
        fontsize=12, fontweight="bold", pad=10,
    )
    ax_map.set_axis_off()

    # Colorbar do choropleth pinada à direita do mapa
    divider = make_axes_locatable(ax_map)
    cax = divider.append_axes("right", size="2.5%", pad=0.1,
                              axes_class=plt.Axes)
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax)
    cb.set_label("Share Cristovam por RA (%)", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    # Legenda de tamanhos das bolhas — caixa flutuante no canto inferior
    # esquerdo do mapa, sem cobrir o Plano Piloto (centro-leste)
    sizes_demo = [100, 500, 1500, 2500]
    handles_size = [
        Line2D([], [], marker="o", linestyle="",
               markerfacecolor="#d62728", markeredgecolor="white",
               markersize=np.sqrt(np.clip(v / 8, 5, 280)),
               alpha=0.75, label=f"{v:,} votos".replace(",", "."))
        for v in sizes_demo
    ]
    ax_map.legend(
        handles=handles_size, loc="lower left", fontsize=8,
        title="Votos Cristovam por local", title_fontsize=8.5,
        framealpha=0.95, labelspacing=1.2, borderpad=0.9,
    )

    # ----- RANKING top 30 -----
    top30 = df.dropna(subset=["lat"]).nlargest(30, "votos_cristovam").iloc[::-1]

    # Cor da barra = densidade de votos absolutos (Reds gradient)
    cmap_bar = plt.get_cmap("Reds")
    vmin_bar = float(top30["votos_cristovam"].min())
    vmax_bar = float(top30["votos_cristovam"].max())
    norm_bar = Normalize(vmin=vmin_bar, vmax=vmax_bar)
    cores_bar = [cmap_bar(norm_bar(v)) for v in top30["votos_cristovam"]]

    # Labels curtos: "Z15 • UNIEURO" (truncado a 24 chars no nome do local)
    labels = [
        f"Z{int(r.NR_ZONA):>2} • {str(r.nome)[:24]}"
        for _, r in top30.iterrows()
    ]
    ax_rank.barh(range(len(top30)), top30["votos_cristovam"],
                 color=cores_bar, edgecolor="black", linewidth=0.4, alpha=0.95)
    ax_rank.set_yticks(range(len(top30)))
    ax_rank.set_yticklabels(labels, fontsize=8.5)
    ax_rank.tick_params(axis="y", which="major", pad=4)
    ax_rank.set_ylim(-0.6, len(top30) - 0.4)

    # Rótulos numéricos no fim de cada barra: total e share local
    xmax = top30["votos_cristovam"].max()
    for i, (_, r) in enumerate(top30.iterrows()):
        ax_rank.text(
            r.votos_cristovam + xmax * 0.012, i,
            f"{int(r.votos_cristovam):,}".replace(",", ".") + f"  ({r.share:.1f}%)",
            va="center", fontsize=7.5,
        )
    ax_rank.set_xlim(0, xmax * 1.28)
    ax_rank.set_xlabel("Votos Cristovam 2018  (rótulo final: total e share local %)",
                       fontsize=9.5)
    ax_rank.set_title("Top 30 locais — base residual 2018",
                      fontsize=12, fontweight="bold", pad=10)
    ax_rank.grid(axis="x", alpha=0.3, linestyle=":")
    ax_rank.spines[["top", "right"]].set_visible(False)

    # Colorbar à direita do ranking — densidade de votos
    divider_rank = make_axes_locatable(ax_rank)
    cax_rank = divider_rank.append_axes("right", size="2.5%", pad=0.1,
                                        axes_class=plt.Axes)
    sm_bar = ScalarMappable(cmap=cmap_bar, norm=norm_bar)
    sm_bar.set_array([])
    cb_bar = fig.colorbar(sm_bar, cax=cax_rank)
    cb_bar.set_label("Votos Cristovam (densidade)", fontsize=9)
    cb_bar.ax.tick_params(labelsize=8)

    fig.suptitle(
        "CRISTOVAM BUARQUE — MAPA POR LOCAL DE VOTAÇÃO (Senador, DF, 2018)\n"
        f"{len(gdf):,} locais geocodificados  |  "
        f"{int(df['votos_cristovam'].sum()):,} votos totais  |  "
        f"share médio {df['share'].mean():.1f}%  |  "
        f"mediana {df['share'].median():.1f}%".replace(",", "."),
        fontsize=13, fontweight="bold", y=0.995,
    )
    fig.subplots_adjust(top=0.93, bottom=0.04, left=0.02, right=0.99)
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_FIG, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"\nFigura salva: {SAIDA_FIG}")


if __name__ == "__main__":
    main()
