"""Mapas de volatilidade eleitoral por Região Administrativa — DF.

Como o DF não tem shapefile próprio de zonas eleitorais, esta
implementação:

  1. Carrega setores censitários do DF via geobr (5418 setores
     com `name_subdistrict` = RA).
  2. Dissolve setores por `name_subdistrict` → polígonos das 33 RAs.
  3. Lê o CSV `outputs/zona_to_ra.csv` para mapear cada zona
     eleitoral à sua RA dominante.
  4. Para cada par de eleições (cargo, ano_ant → ano_atu), calcula
     volatilidade Pedersen por zona via
     `src.partidario.analise_volatilidade.pedersen_por_zona`, e
     atribui o valor à RA dominante da zona (média se múltiplas
     zonas caem na mesma RA).
  5. Plota o mapa colorido pela volatilidade.

Saída: `outputs/figures/mapa_volatilidade_{cargo}_{anos}.png` para
os pares relevantes da janela 2014-2022 + Presidente 2018-2022.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import warnings

import geobr
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.partidario.analise_volatilidade import (
    carregar_df,
    pedersen_por_zona,
    votos_por_zona_partido,
)

warnings.filterwarnings("ignore")

CSV_ZONA_RA = _ROOT / "outputs/zona_to_ra.csv"
DIR_FIG = _ROOT / "outputs/figures"

# Alias zona_para_ra.RAS → geobr name_subdistrict (mesmo dict que usei
# em socioeconomia_zonas_2022.py).
RA_ALIAS = {
    "Asa Sul": "Plano Piloto",
    "Asa Norte": "Plano Piloto",
    "Cruzeiro": "Cruzeiro",
    "Octogonal": "Sudoeste/Octogonal",
    "Sudoeste": "Sudoeste/Octogonal",
    "Riacho Fundo I": "Riacho Fundo",
    "Riacho Fundo II": "Riacho Fundo II",
    "Guara I": "Guará",
    "Guara II": "Guará",
    "Sobradinho I": "Sobradinho",
    "Sobradinho II": "Sobradinho II",
    "Nucleo Bandeirante": "Núcleo Bandeirante",
    "Candangolandia": "Candangolândia",
    "Aguas Claras": "Águas Claras",
    "Brazlandia": "Brazlândia",
    "Sao Sebastiao": "São Sebastião",
    "Jardim Botanico": "Jardim Botânico",
    "Itapoa": "Itapoã",
    "Paranoa": "Paranoá",
    "Estrutural": "SCIA",
    "Varjao": "Varjão",
    "Fercal": "Fercal",
    "Ceilandia": "Ceilândia",
    "Lago Sul": "Lago Sul",
    "Lago Norte": "Lago Norte",
    "Vicente Pires": "Vicente Pires",
    "Park Way": "Park Way",
    "Taguatinga": "Taguatinga",
    "Samambaia": "Samambaia",
    "Recanto das Emas": "Recanto das Emas",
    "Planaltina": "Planaltina",
    "Gama": "Gama",
    "Santa Maria": "Santa Maria",
    "Plano Piloto": "Plano Piloto",
}


def carregar_geometria_ras() -> gpd.GeoDataFrame:
    """Polígonos das RAs do DF (dissolve de setores 2022 por subdistrict)."""
    print("Baixando setores DF via geobr (Censo 2022)...")
    setores = geobr.read_census_tract(code_tract=5300108, year=2022)
    print(f"  setores: {len(setores)}")
    ras = setores.dissolve(by="name_subdistrict", as_index=False)
    ras = ras[["name_subdistrict", "geometry"]].rename(
        columns={"name_subdistrict": "RA"}
    )
    print(f"  RAs (dissolvidas): {len(ras)}")
    return ras


def mapa_zona_ra() -> pd.DataFrame:
    """Lê outputs/zona_to_ra.csv e adiciona coluna `RA_geobr`."""
    df = pd.read_csv(CSV_ZONA_RA)
    df["RA_geobr"] = df["RA_DOMINANTE"].map(lambda x: RA_ALIAS.get(x, x))
    return df[["NR_ZONA", "RA_DOMINANTE", "RA_geobr", "pct_dominante"]]


def vol_por_ra(cargo: str, ano_ant: int, ano_atu: int,
               zona_ra: pd.DataFrame) -> pd.DataFrame:
    """Volatilidade Pedersen por zona, agregada por RA (média se múltiplas)."""
    df_ant = carregar_df(ano_ant, cargo)
    df_atu = carregar_df(ano_atu, cargo)
    vol = pedersen_por_zona(
        votos_por_zona_partido(df_ant), votos_por_zona_partido(df_atu)
    ).rename("volatilidade").reset_index().rename(columns={"NR_ZONA": "NR_ZONA"})
    merge = vol.merge(zona_ra, on="NR_ZONA", how="left")
    por_ra = (
        merge.groupby("RA_geobr")["volatilidade"].mean().reset_index()
    )
    return por_ra, merge


def plotar(ras_geo: gpd.GeoDataFrame, por_ra: pd.DataFrame,
           cargo: str, ano_ant: int, ano_atu: int,
           detalhes: pd.DataFrame) -> Path:
    gdf = ras_geo.merge(por_ra, left_on="RA", right_on="RA_geobr", how="left")
    fig, ax = plt.subplots(figsize=(11, 9))
    gdf.plot(
        column="volatilidade",
        cmap="viridis",
        legend=True,
        ax=ax,
        edgecolor="white",
        linewidth=0.5,
        missing_kwds={"color": "lightgrey", "label": "sem zona mapeada"},
    )
    # Anotar nome de RA + zonas
    for _, row in gdf.iterrows():
        if row["geometry"] is None or pd.isna(row.get("volatilidade")):
            continue
        cent = row["geometry"].representative_point()
        zonas_aqui = detalhes[detalhes["RA_geobr"] == row["RA"]]["NR_ZONA"].tolist()
        rotulo = f"{row['RA']}\nZ{'/'.join(map(str, zonas_aqui))}"
        ax.annotate(
            rotulo, (cent.x, cent.y), ha="center", va="center",
            fontsize=7, color="white",
            bbox=dict(boxstyle="round,pad=0.1", facecolor="black", alpha=0.4, lw=0),
        )
    ax.set_title(
        f"Volatilidade Pedersen — {cargo}, {ano_ant} → {ano_atu} (DF, por RA)",
        fontsize=13,
    )
    ax.set_axis_off()
    fig.tight_layout()
    DIR_FIG.mkdir(parents=True, exist_ok=True)
    cargo_slug = cargo.lower().replace(" ", "_")
    out = DIR_FIG / f"mapa_volatilidade_{cargo_slug}_{ano_ant}_{ano_atu}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    zona_ra = mapa_zona_ra()
    ras_geo = carregar_geometria_ras()

    pares = [
        ("Governador", 2014, 2018),
        ("Governador", 2018, 2022),
        ("Presidente", 2018, 2022),
        ("Deputado Distrital", 2018, 2022),
        ("Deputado Federal", 2018, 2022),
    ]
    for cargo, ano_ant, ano_atu in pares:
        try:
            por_ra, det = vol_por_ra(cargo, ano_ant, ano_atu, zona_ra)
        except Exception as e:
            print(f"  pulado {cargo} {ano_ant}->{ano_atu}: {e}")
            continue
        out = plotar(ras_geo, por_ra, cargo, ano_ant, ano_atu, det)
        print(
            f"  {cargo:>18} {ano_ant}->{ano_atu}: "
            f"vol média = {por_ra['volatilidade'].mean():.3f} | "
            f"min {por_ra['volatilidade'].min():.3f} | "
            f"max {por_ra['volatilidade'].max():.3f}"
        )
        print(f"    {out}")


if __name__ == "__main__":
    main()
