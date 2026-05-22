"""Carrega dados de votação para Presidente (1998-2022, DF) no MySQL.

Replica de `carregar_presidente.py` do projeto SP, com filtro SG_UF='DF'.
Lê os CSVs nacionais (BR.csv / BRASIL.csv) e filtra DF + Presidente + 1º
turno (vide nota: o 2º turno não tem desagregação Zona × Município
relevante para a análise de zonas).
"""

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd

from src.ingestao.carregar_mysql import (
    DATABASE,
    UF,
    conectar,
    inserir_dimensoes,
    inserir_fato,
)

ANOS = [1998, 2002, 2006, 2010, 2014, 2018, 2022]
RAW_DIR = _ROOT / "data/raw"


def localizar_csv_nacional(ano: int) -> Path:
    """Encontra o CSV nacional que tem os dados de Presidente."""
    pasta = RAW_DIR / f"votacao_partido_munzona_{ano}"
    for nome in [
        f"votacao_partido_munzona_{ano}_BR.csv",
        f"votacao_partido_munzona_{ano}_BRASIL.csv",
    ]:
        f = pasta / nome
        if f.exists():
            return f
    raise FileNotFoundError(f"Nenhum CSV nacional para {ano} em {pasta}")


def carregar_presidente_df(ano: int) -> pd.DataFrame:
    """Lê o CSV nacional, filtra DF/Presidente/1º turno."""
    f = localizar_csv_nacional(ano)
    df = pd.read_csv(f, sep=";", encoding="latin-1", low_memory=False)
    sub = df[
        (df["SG_UF"] == UF)
        & (df["DS_CARGO"].str.upper() == "PRESIDENTE")
        & (df["NR_TURNO"] == 1)
    ].copy()

    if "QT_VOTOS_NOMINAIS" not in sub.columns and "QT_VOTOS_NOMINAIS_VALIDOS" in sub.columns:
        sub["QT_VOTOS_NOMINAIS"] = sub["QT_VOTOS_NOMINAIS_VALIDOS"]
        sub["QT_VOTOS_LEGENDA"] = sub["QT_VOTOS_LEGENDA_VALIDOS"]
    if "QT_VOTOS_NOMINAIS" not in sub.columns:
        raise ValueError(
            f"Colunas de votos não reconhecidas em {f.name}: "
            f"{list(sub.columns)[:25]}"
        )

    print(f"  {ano}: {len(sub)} linhas (Pres {UF} 1T)")
    return sub


def main() -> None:
    print("=" * 60)
    print(f"CARGA DE PRESIDENTE — {UF}, 1998-2022, 1º turno")
    print("=" * 60)

    print("\nLendo CSVs nacionais...")
    dfs = [carregar_presidente_df(ano) for ano in ANOS]
    df = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal: {len(df)} linhas")

    conn = conectar(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM votacao_partido_munzona WHERE cd_cargo = 1"
    )
    pres_antes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM votacao_partido_munzona")
    fato_antes = cursor.fetchone()[0]
    print(f"\nLinhas de Presidente já no banco: {pres_antes}")

    if pres_antes > 0:
        print("Já existem dados de Presidente — abortando para evitar duplicação.")
        cursor.close()
        conn.close()
        return

    print("\nInserindo dimensões (INSERT IGNORE — não duplica)...")
    inserir_dimensoes(df, conn)

    print("\nInserindo fato...")
    inserir_fato(df, conn)

    print("\n" + "=" * 60)
    print("VERIFICAÇÃO")
    print("=" * 60)
    cursor.execute("SELECT COUNT(*) FROM votacao_partido_munzona")
    fato_depois = cursor.fetchone()[0]
    print(
        f"  votacao_partido_munzona: {fato_antes} -> {fato_depois} "
        f"(+{fato_depois - fato_antes})"
    )

    cursor.execute(
        "SELECT e.ano_eleicao, COUNT(*) FROM votacao_partido_munzona v "
        "JOIN eleicao e ON v.cd_eleicao = e.cd_eleicao AND v.nr_turno = e.nr_turno "
        "WHERE v.cd_cargo = 1 GROUP BY e.ano_eleicao ORDER BY e.ano_eleicao"
    )
    print("\nPresidente por ano:")
    for ano, n in cursor.fetchall():
        print(f"  {ano}: {n} linhas")

    cursor.close()
    conn.close()
    print("\nCarga concluída.")


if __name__ == "__main__":
    main()
