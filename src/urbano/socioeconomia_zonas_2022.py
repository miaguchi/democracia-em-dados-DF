"""Renda média do responsável por zona eleitoral — DF, Censo 2022.

Adaptação de `urbano/socioeconomia_zonas_2022.py` do SP. Diferença
fundamental: no DF não há base CEM/USP com lat/lon dos locais de
votação. O cruzamento setor censitário → zona eleitoral é feito
**por RA dominante**, não por spatial join:

  1. Carrega setores do DF via geobr (`code_tract=5300108`), que traz
     `name_subdistrict` = nome da RA para cada setor.
  2. Carrega CSV nacional de renda do responsável (Censo 2022,
     `Agregados_por_setores_renda_responsavel_BR.csv`), filtrando
     `CD_SETOR` começando com `530010` (= Brasília-DF).
  3. Junta por `code_tract` ↔ `CD_SETOR` e agrega V06004 (renda média)
     por RA, ponderado por V06001 (n. responsáveis).
  4. Mapeia cada zona eleitoral → RA via heurística de endereço
     (`src.dominio.zona_para_ra`), aplicando consolidação Asa Sul +
     Asa Norte → "Plano Piloto" (granularidade do geobr).
  5. Resultado: CSV `outputs/socioeconomia_por_zona_2022.csv` com
     renda média ponderada por zona.

Limitação: zonas que cobrem múltiplas RAs ficam classificadas pela
RA majoritária — a heurística reporta `pct_dominante` para
quantificar o erro.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import warnings

import geobr
import pandas as pd

warnings.filterwarnings("ignore")

CSV_RENDA_BR = (
    _ROOT / "data/raw/censo2022/extraido_renda"
    / "Agregados_por_setores_renda_responsavel_BR.csv"
)
CSV_ZONA_RA = _ROOT / "outputs/zona_to_ra.csv"
SAIDA = _ROOT / "outputs/socioeconomia_por_zona_2022.csv"

# Consolidações para casar o vocabulário da heurística com `name_subdistrict`
# do geobr (RA oficial do DF).
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


def carregar_renda_setor_df() -> pd.DataFrame:
    """Renda média do responsável (V06004) por setor do DF."""
    print("Carregando CSV nacional de renda 2022...")
    df = pd.read_csv(
        CSV_RENDA_BR, sep=";", encoding="latin-1", dtype={"CD_SETOR": str}
    )
    df_dist = df[df["CD_SETOR"].str.startswith("530010")].copy()
    print(f"  setores no DF: {len(df_dist)}")
    df_dist["renda_resp"] = pd.to_numeric(
        df_dist["V06004"].astype(str).str.replace(",", ".").replace("X", pd.NA),
        errors="coerce",
    )
    df_dist["n_resp"] = pd.to_numeric(
        df_dist["V06001"].astype(str).str.replace(",", ".").replace("X", pd.NA),
        errors="coerce",
    )
    return df_dist[["CD_SETOR", "renda_resp", "n_resp"]]


def carregar_setores_geobr_df() -> pd.DataFrame:
    """Setores do DF via geobr, com `name_subdistrict` (= RA)."""
    print("Baixando setores DF via geobr (Censo 2022)...")
    gdf = geobr.read_census_tract(code_tract=5300108, year=2022)
    gdf["CD_SETOR"] = (
        gdf["code_tract"].astype("int64").astype(str)
    )
    return gdf[["CD_SETOR", "name_subdistrict"]].rename(
        columns={"name_subdistrict": "RA"}
    )


def renda_por_ra() -> pd.DataFrame:
    renda = carregar_renda_setor_df()
    setores = carregar_setores_geobr_df()
    base = renda.merge(setores, on="CD_SETOR", how="inner")
    base = base.dropna(subset=["renda_resp", "n_resp"])
    base = base[base["n_resp"] > 0]
    print(f"  setores com renda+n_resp válidos: {len(base)}")

    grupo = base.groupby("RA")
    pond = (
        grupo.apply(
            lambda g: (g["renda_resp"] * g["n_resp"]).sum() / g["n_resp"].sum()
        ).rename("renda_resp_media_pond")
    )
    n_total = grupo["n_resp"].sum().rename("n_resp_total")
    n_setores = grupo.size().rename("n_setores")
    return pd.concat([pond, n_total, n_setores], axis=1).reset_index()


def main() -> None:
    ra_renda = renda_por_ra()
    print(f"\n=== Renda média responsável por RA (Censo 2022, DF) ===")
    print(
        ra_renda.sort_values("renda_resp_media_pond", ascending=False)
        .round(2)
        .to_string(index=False)
    )

    zona_ra = pd.read_csv(CSV_ZONA_RA)
    zona_ra["RA_geobr"] = zona_ra["RA_DOMINANTE"].map(
        lambda x: RA_ALIAS.get(x, x)
    )
    merge = zona_ra.merge(
        ra_renda, left_on="RA_geobr", right_on="RA", how="left"
    )
    merge = merge[
        [
            "NR_ZONA",
            "RA_DOMINANTE",
            "RA_geobr",
            "pct_dominante",
            "renda_resp_media_pond",
            "n_resp_total",
            "n_setores",
        ]
    ].rename(columns={"renda_resp_media_pond": "renda_resp_2022"})

    print(f"\n=== Renda por zona eleitoral (DF) ===")
    print(merge.sort_values("renda_resp_2022", ascending=False).round(2).to_string(index=False))

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    merge.to_csv(SAIDA, index=False)
    print(f"\nCSV: {SAIDA}")


if __name__ == "__main__":
    main()
