"""Mapas de volatilidade por LOCAL DE VOTAÇÃO — DF.

Versão refinada de `mapa_volatilidade.py`. Em vez de agregar por RA (33
polígonos), calcula a volatilidade Pedersen por local de votação (~617
locais no DF) e plota cada local como ponto colorido na geometria das
RAs.

Granularidade: local de votação tem 700-1500 eleitores tipicamente —
intermediária entre zona (>50k) e seção (~300). É menos ruidosa que
seção e ainda muito mais detalhada que zona ou RA.

Pipeline:
  1. Lê votacao_secao parquet de dois anos (`{ano}_DF.parquet`).
  2. Agrega votos por (local, partido normalizado) — soma de todas as
     seções de cada local.
  3. Aplica federações/fusões consistentes via `normalizar_partido`.
  4. Calcula Pedersen por local entre os dois anos.
  5. Lê lat/lon do `eleitorado_local_votacao_{ano}_DF.csv`.
  6. Plota cada local como bolha sobre o mapa de RAs do DF.

Saída: `outputs/figures/mapa_volatilidade_local_<cargo>_<anos>.png`.
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

from src.partidario.analise_volatilidade import normalizar_partido

warnings.filterwarnings("ignore")

PARQUET_BASE = _ROOT / "data/processed"
CSV_LOCAIS = _ROOT / "data/raw/eleitorado_local_votacao_2022_DF.csv"
DIR_FIG = _ROOT / "outputs/figures"


def carregar_locais_coord() -> pd.DataFrame:
    """Coordenadas (lat/lon) dos locais de votação DF."""
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
    # Descarta sentinela -1.0 (NULL TSE)
    locais = locais[(locais["lat"] < -10) & (locais["lon"] < -40)].copy()
    return locais[
        ["NR_ZONA", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO", "lat", "lon"]
    ].reset_index(drop=True)


def votos_local_partido(ano: int, cargo: str) -> pd.DataFrame:
    """Votos por (NR_ZONA, NR_LOCAL_VOTACAO, partido normalizado).

    Filtra cargo, 1º turno; normaliza SG_PARTIDO via federações/fusões.
    Para Presidente, o cargo é nacional — também presente no parquet.
    """
    f = PARQUET_BASE / f"votacao_secao_{ano}_DF.parquet"
    if not f.exists():
        raise FileNotFoundError(f"parquet ausente: {f}")
    df = pd.read_parquet(f)
    sub = df[
        (df["DS_CARGO"].str.upper() == cargo.upper())
        & (df["NR_TURNO"] == 1)
    ].copy()
    # Partido do candidato — pegar a sigla a partir do NR_VOTAVEL (= número
    # do candidato), unindo com mapping partido pelo SQ_CANDIDATO. Aqui é
    # mais simples: agrupar por NR_VOTAVEL e converter via dicionário no
    # próprio dataset (NM_VOTAVEL tem o nome). Mas para Pedersen partidário
    # preciso de partido. votacao_secao não tem SG_PARTIDO direto — preciso
    # extrair do NR_VOTAVEL via merge.
    return sub


def partidos_por_candidato(ano: int) -> pd.DataFrame:
    """Mapping NR_VOTAVEL -> SG_PARTIDO a partir do parquet votacao_candidato."""
    f = PARQUET_BASE / f"votacao_candidato_munzona_{ano}_DF.parquet"
    if not f.exists():
        raise FileNotFoundError(f"parquet ausente: {f}")
    df = pd.read_parquet(f)
    map_ = (
        df[["NR_CANDIDATO", "SG_PARTIDO", "DS_CARGO", "NR_TURNO"]]
        .drop_duplicates()
        .rename(columns={"NR_CANDIDATO": "NR_VOTAVEL"})
    )
    return map_


def matriz_local_partido(ano: int, cargo: str) -> pd.DataFrame:
    """Matriz (local, partido normalizado) de votos no cargo/ano."""
    votos = votos_local_partido(ano, cargo)
    cand = partidos_por_candidato(ano)
    cand = cand[
        (cand["DS_CARGO"].str.upper() == cargo.upper()) & (cand["NR_TURNO"] == 1)
    ][["NR_VOTAVEL", "SG_PARTIDO"]].drop_duplicates()
    merged = votos.merge(cand, on="NR_VOTAVEL", how="left")
    merged["PARTIDO"] = merged["SG_PARTIDO"].map(normalizar_partido)
    merged = merged.dropna(subset=["PARTIDO"])
    agg = (
        merged.groupby(["NR_LOCAL_VOTACAO", "NR_ZONA", "PARTIDO"])["QT_VOTOS"]
        .sum()
        .reset_index()
    )
    matriz = agg.pivot_table(
        index=["NR_ZONA", "NR_LOCAL_VOTACAO"],
        columns="PARTIDO",
        values="QT_VOTOS",
        fill_value=0,
    )
    return matriz


def pedersen_por_local(
    matriz_ant: pd.DataFrame, matriz_atu: pd.DataFrame, min_votos: int = 50
) -> pd.Series:
    """Pedersen Local-a-local. Filtra locais com poucos votos (ruído)."""
    partidos = matriz_ant.columns.union(matriz_atu.columns)
    m_ant = matriz_ant.reindex(columns=partidos, fill_value=0)
    m_atu = matriz_atu.reindex(columns=partidos, fill_value=0)
    locais = m_ant.index.intersection(m_atu.index)
    m_ant = m_ant.loc[locais]
    m_atu = m_atu.loc[locais]
    soma_ant = m_ant.sum(axis=1)
    soma_atu = m_atu.sum(axis=1)
    valido = (soma_ant >= min_votos) & (soma_atu >= min_votos)
    m_ant = m_ant.loc[valido]
    m_atu = m_atu.loc[valido]
    p_ant = m_ant.div(m_ant.sum(axis=1), axis=0).fillna(0)
    p_atu = m_atu.div(m_atu.sum(axis=1), axis=0).fillna(0)
    return 0.5 * (p_ant - p_atu).abs().sum(axis=1)


def carregar_geometria_ras() -> gpd.GeoDataFrame:
    print("geobr setores 2022 -> dissolve por subdistrict...")
    setores = geobr.read_census_tract(code_tract=5300108, year=2022)
    ras = setores.dissolve(by="name_subdistrict", as_index=False)
    return ras[["name_subdistrict", "geometry"]].rename(
        columns={"name_subdistrict": "RA"}
    )


def plotar(
    ras_geo: gpd.GeoDataFrame,
    locais_vol: gpd.GeoDataFrame,
    cargo: str,
    ano_ant: int,
    ano_atu: int,
) -> Path:
    fig, ax = plt.subplots(figsize=(11, 9))
    ras_geo.plot(
        ax=ax, facecolor="#f5f5f5", edgecolor="white", linewidth=0.6
    )
    # Annotar nomes de RA — só algumas grandes
    grandes = [
        "Plano Piloto", "Ceilândia", "Taguatinga", "Samambaia",
        "Lago Sul", "Lago Norte", "Águas Claras", "Gama",
        "Planaltina", "Sobradinho", "Recanto das Emas", "Paranoá",
        "Cruzeiro", "Sudoeste/Octogonal",
    ]
    for _, row in ras_geo.iterrows():
        if row["RA"] in grandes and row["geometry"] is not None:
            cent = row["geometry"].representative_point()
            ax.annotate(
                row["RA"], (cent.x, cent.y),
                ha="center", va="center", fontsize=7,
                color="#444", alpha=0.6,
            )
    sc = locais_vol.plot(
        ax=ax,
        column="volatilidade",
        cmap="viridis",
        legend=True,
        markersize=25,
        edgecolor="white",
        linewidth=0.4,
        legend_kwds={"label": "Pedersen (local)", "shrink": 0.6},
    )
    ax.set_title(
        f"Volatilidade Pedersen por local de votação — {cargo}, "
        f"{ano_ant} → {ano_atu} (DF, N={len(locais_vol)} locais)",
        fontsize=12,
    )
    ax.set_axis_off()
    fig.tight_layout()
    DIR_FIG.mkdir(parents=True, exist_ok=True)
    cargo_slug = cargo.lower().replace(" ", "_")
    out = DIR_FIG / f"mapa_volatilidade_local_{cargo_slug}_{ano_ant}_{ano_atu}.png"
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    locais = carregar_locais_coord()
    print(f"Locais com lat/lon: {len(locais)}")
    ras_geo = carregar_geometria_ras()

    pares = [
        ("Governador", 2018, 2022),
        ("Presidente", 2018, 2022),
        ("Deputado Distrital", 2018, 2022),
        ("Deputado Federal", 2018, 2022),
        ("Senador", 2018, 2022),
    ]
    for cargo, ano_ant, ano_atu in pares:
        try:
            m_ant = matriz_local_partido(ano_ant, cargo)
            m_atu = matriz_local_partido(ano_atu, cargo)
        except Exception as e:
            print(f"  pulado {cargo}: {e}")
            continue
        vol = pedersen_por_local(m_ant, m_atu).rename("volatilidade")
        vol = vol.reset_index()
        # Juntar coords
        locais_vol = locais.merge(
            vol, on=["NR_ZONA", "NR_LOCAL_VOTACAO"], how="inner"
        )
        if locais_vol.empty:
            print(f"  {cargo}: sem dados após merge")
            continue
        gdf = gpd.GeoDataFrame(
            locais_vol,
            geometry=gpd.points_from_xy(locais_vol["lon"], locais_vol["lat"]),
            crs="EPSG:4674",
        )
        out = plotar(ras_geo, gdf, cargo, ano_ant, ano_atu)
        print(
            f"  {cargo:>20} {ano_ant}->{ano_atu}: N={len(gdf)} locais | "
            f"vol médio={gdf['volatilidade'].mean():.3f} | "
            f"mín={gdf['volatilidade'].min():.3f} | "
            f"máx={gdf['volatilidade'].max():.3f}"
        )
        print(f"    {out}")


if __name__ == "__main__":
    main()
