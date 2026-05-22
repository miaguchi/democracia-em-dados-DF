"""Volatilidade eleitoral (Pedersen) — Distrito Federal, 1998-2022.

Adaptado de `src/partidario/analise_volatilidade.py` do projeto SP. Aqui:
  * Leitura do MySQL (`democracia_em_dados_df`) em vez de parquet — DF tem
    o banco completo e isso mantém uma única fonte da verdade.
  * Parametrizado por cargo e par de anos: como o DF não tem ciclo
    municipal, a granularidade interessante é Governador, Dep. Distrital,
    Dep. Federal, Senador, Presidente — 1998 → 2002 → ... → 2022.
  * Federações e fusões 2020-2024 reaproveitadas; ajustes adicionais
    para a janela 1998-2022 ficam para validação caso a caso.

Pedersen por zona retorna apenas as zonas presentes nas duas eleições
do par (zonas extintas/novas excluídas) — comportamento idêntico ao SP.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from typing import Dict

import mysql.connector
import pandas as pd

from src.ingestao.carregar_mysql import DATABASE, MYSQL_CONFIG

CD_MUNICIPIO_BRASILIA = 97012

# Mesmas federações usadas em SP (válidas para 2022).
FEDERACOES = {
    "PT": "FED_PT_PCDOB_PV",
    "PC do B": "FED_PT_PCDOB_PV",
    "PV": "FED_PT_PCDOB_PV",
    "PSDB": "FED_PSDB_CIDADANIA",
    "CIDADANIA": "FED_PSDB_CIDADANIA",
    "PSOL": "FED_PSOL_REDE",
    "REDE": "FED_PSOL_REDE",
}

# Fusões e renomeações usadas pelo projeto SP — válidas para o DF na
# mesma janela. Para a janela longa 1998-2022 outras transições podem
# importar (PFL→DEM, PMDB→MDB, PPB→PP) — adicionar conforme detectadas.
FUSOES: Dict[str, str] = {
    "DEM": "UNIÃO",
    "PSL": "UNIÃO",
    "PROS": "SOLIDARIEDADE",
    "PATRIOTA": "PRD",
    "PTB": "PRD",
    "PTC": "AGIR",
    "PSC": "PODE",
    # Janela longa:
    "PFL": "DEM",
    "PMDB": "MDB",
    "PPB": "PP",
    "PPR": "PP",
    "PRB": "REPUBLICANOS",
    "PR": "PL",
}


def normalizar_partido(sigla: str) -> str:
    """Aplica fusões e federações, em cascata, até estabilizar."""
    if sigla is None:
        return sigla
    s = sigla
    for _ in range(3):  # 2 cascatas costumam bastar (PFL→DEM→UNIÃO etc.)
        novo = FUSOES.get(s, s)
        if novo == s:
            break
        s = novo
    return FEDERACOES.get(s, s)


def _fetch(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = mysql.connector.connect(database=DATABASE, **MYSQL_CONFIG)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return pd.DataFrame(rows, columns=cols)
    finally:
        conn.close()


def carregar_df(ano: int, cargo: str) -> pd.DataFrame:
    """Carrega votos por zona × partido para o cargo dado, 1º turno, DF.

    Parameters
    ----------
    ano : int
    cargo : str
        Texto livre, casado contra ds_cargo (case-insensitive). Ex.:
        "Governador", "Senador", "Deputado Federal", "Deputado Distrital",
        "Presidente".
    """
    sql = (
        "SELECT v.nr_zona AS NR_ZONA, p.sg_partido AS SG_PARTIDO, "
        "       v.qt_votos_nominais AS QT_VOTOS_NOMINAIS, "
        "       v.qt_votos_legenda  AS QT_VOTOS_LEGENDA "
        "FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao=e.cd_eleicao AND v.nr_turno=e.nr_turno "
        "JOIN partido p ON v.nr_partido=p.nr_partido "
        "JOIN cargo c ON v.cd_cargo=c.cd_cargo "
        "WHERE e.ano_eleicao=%s AND UPPER(c.ds_cargo)=UPPER(%s) "
        "  AND v.nr_turno=1 AND v.cd_municipio=%s"
    )
    sub = _fetch(sql, (ano, cargo, CD_MUNICIPIO_BRASILIA))
    sub["VOTOS"] = sub["QT_VOTOS_NOMINAIS"] + sub["QT_VOTOS_LEGENDA"]
    sub["PARTIDO"] = sub["SG_PARTIDO"].map(normalizar_partido)
    return sub


def votos_por_partido(df: pd.DataFrame) -> pd.Series:
    return df.groupby("PARTIDO")["VOTOS"].sum().sort_values(ascending=False)


def votos_por_zona_partido(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(["NR_ZONA", "PARTIDO"])["VOTOS"].sum().unstack(fill_value=0)


def pedersen(anterior: pd.Series, atual: pd.Series) -> float:
    """Índice de Pedersen (1979) — 0.5 × Σ|p_i,t+1 − p_i,t|."""
    p_ant = anterior / anterior.sum()
    p_atu = atual / atual.sum()
    partidos = p_ant.index.union(p_atu.index)
    return 0.5 * (
        p_ant.reindex(partidos, fill_value=0) - p_atu.reindex(partidos, fill_value=0)
    ).abs().sum()


def pedersen_por_zona(
    matriz_ant: pd.DataFrame, matriz_atu: pd.DataFrame
) -> pd.Series:
    """Pedersen por zona. Mantém só zonas presentes nas duas eleições."""
    partidos = matriz_ant.columns.union(matriz_atu.columns)
    m_ant = matriz_ant.reindex(columns=partidos, fill_value=0)
    m_atu = matriz_atu.reindex(columns=partidos, fill_value=0)
    zonas = m_ant.index.intersection(m_atu.index)
    m_ant = m_ant.loc[zonas]
    m_atu = m_atu.loc[zonas]
    p_ant = m_ant.div(m_ant.sum(axis=1), axis=0).fillna(0)
    p_atu = m_atu.div(m_atu.sum(axis=1), axis=0).fillna(0)
    return 0.5 * (p_ant - p_atu).abs().sum(axis=1)


def resumo_volatilidade(ano_ant: int, ano_atu: int, cargo: str) -> pd.Series:
    """Pipeline completo para um par de eleições. Imprime e retorna a série
    por zona ordenada decrescente."""
    df_ant = carregar_df(ano_ant, cargo)
    df_atu = carregar_df(ano_atu, cargo)

    v_total = pedersen(votos_por_partido(df_ant), votos_por_partido(df_atu))
    print(
        f"\n=== Volatilidade Pedersen — {cargo}, {ano_ant} → {ano_atu} (DF) ==="
    )
    print(f"DF (cidade-toda): {v_total:.4f}")

    vol_zona = pedersen_por_zona(
        votos_por_zona_partido(df_ant), votos_por_zona_partido(df_atu)
    ).sort_values(ascending=False)
    print(
        f"Zonas: {len(vol_zona)} | média {vol_zona.mean():.4f} | "
        f"mediana {vol_zona.median():.4f} | dp {vol_zona.std():.4f}"
    )
    print(
        f"Mín {vol_zona.min():.4f} (zona {vol_zona.idxmin()}) | "
        f"Máx {vol_zona.max():.4f} (zona {vol_zona.idxmax()})"
    )
    return vol_zona


def main() -> None:
    """Imprime a volatilidade para cada cargo entre eleições adjacentes."""
    pares = [
        (1998, 2002), (2002, 2006), (2006, 2010),
        (2010, 2014), (2014, 2018), (2018, 2022),
    ]
    cargos = ["Governador", "Senador", "Deputado Federal",
              "Deputado Distrital", "Presidente"]
    for cargo in cargos:
        for ano_ant, ano_atu in pares:
            try:
                resumo_volatilidade(ano_ant, ano_atu, cargo)
            except Exception as e:
                print(f"  pulado {cargo} {ano_ant}→{ano_atu}: {e}")


if __name__ == "__main__":
    main()
