"""Carrega dados eleitorais do TSE (votacao_partido_munzona) no MySQL — DF.

Replica do carregar_mysql.py do projeto SP, com três adaptações:
  * DATABASE = 'democracia_em_dados_df'
  * UF alvo = 'DF' (filtro aplicado na leitura quando o CSV é nacional)
  * Anos cobertos = federais (1998, 2002, 2006, 2010, 2014, 2018, 2022)

Para cada ano, lê o CSV `votacao_partido_munzona_{ano}_DF.csv` quando
existe (todos os anos exceto 1998) ou cai no nacional
`votacao_partido_munzona_{ano}_BRASIL.csv` filtrando SG_UF='DF'. Cobre
Governador, Senador, Deputado Federal, Deputado Distrital. Presidente
fica para `carregar_presidente.py`.
"""

from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import mysql.connector
import pandas as pd

SCHEMA_SQL = _ROOT / "scripts/sql/schema_tse.sql"
RAW_DIR = _ROOT / "data/raw"
DATA_DIR = _ROOT / "data/processed"

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Miaguchi123!",
}

DATABASE = "democracia_em_dados_df"
UF = "DF"
ANOS_FEDERAIS = [1998, 2002, 2006, 2010, 2014, 2018, 2022]


def conectar(database: str | None = None) -> mysql.connector.MySQLConnection:
    """Conecta ao MySQL, opcionalmente a um banco específico."""
    config = dict(MYSQL_CONFIG)
    if database:
        config["database"] = database
    return mysql.connector.connect(**config)


def criar_banco() -> None:
    """Cria o banco de dados se não existir."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS {DATABASE} "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    conn.commit()
    print(f"Banco '{DATABASE}' criado/verificado.")
    cursor.close()
    conn.close()


def executar_schema() -> None:
    """Executa o schema SQL (CREATE TABLEs)."""
    conn = conectar(DATABASE)
    cursor = conn.cursor()
    sql = SCHEMA_SQL.read_text()
    sql_clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    for statement in sql_clean.split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        try:
            cursor.execute(stmt)
        except mysql.connector.Error as e:
            if e.errno not in (1061, 1050):  # duplicate key/table
                print(f"  AVISO: {e.msg}")
    conn.commit()
    print("Schema executado.")
    cursor.close()
    conn.close()


def localizar_csv(ano: int) -> tuple[Path, bool]:
    """Retorna (path, precisa_filtrar_uf) para o CSV do ano dado.

    Prefere DF.csv; se ausente, cai em BRASIL.csv (precisa filtrar SG_UF).
    """
    pasta = RAW_DIR / f"votacao_partido_munzona_{ano}"
    df_csv = pasta / f"votacao_partido_munzona_{ano}_{UF}.csv"
    if df_csv.exists():
        return df_csv, False
    for nome in [
        f"votacao_partido_munzona_{ano}_BRASIL.csv",
        f"votacao_partido_munzona_{ano}_BR.csv",
    ]:
        f = pasta / nome
        if f.exists():
            return f, True
    raise FileNotFoundError(f"CSV de partido_munzona não encontrado para {ano} em {pasta}")


def carregar_ano(ano: int) -> pd.DataFrame:
    """Lê o CSV do ano, filtra UF se necessário, harmoniza colunas.

    Exclui Presidente — esse cargo é tratado por carregar_presidente.py.
    """
    f, precisa_filtrar = localizar_csv(ano)
    df = pd.read_csv(f, sep=";", encoding="latin-1", low_memory=False)
    if precisa_filtrar:
        df = df[df["SG_UF"] == UF].copy()
    # Excluir Presidente (vai em carregar_presidente.py — evita duplicação)
    df = df[df["DS_CARGO"].str.upper() != "PRESIDENTE"].copy()

    # Harmonizar colunas de votos (2012-2016 vs 2018+)
    if "QT_VOTOS_NOMINAIS" not in df.columns and "QT_VOTOS_NOMINAIS_VALIDOS" in df.columns:
        df["QT_VOTOS_NOMINAIS"] = df["QT_VOTOS_NOMINAIS_VALIDOS"]
        df["QT_VOTOS_LEGENDA"] = df["QT_VOTOS_LEGENDA_VALIDOS"]
    # 1998-2010: campos podem se chamar outra coisa — checar dinamicamente
    if "QT_VOTOS_NOMINAIS" not in df.columns:
        # 1998 BRASIL.csv tem QTDE_VOTOS por candidato; para partido_munzona,
        # as colunas-padrão devem existir. Se não existirem, é um sinal claro
        # de incompatibilidade — interrompe.
        raise ValueError(
            f"Colunas de votos não reconhecidas no CSV {f.name}: "
            f"{list(df.columns)[:25]}"
        )

    print(f"  {ano}: {len(df)} linhas (UF={UF}, excl. Presidente)")
    return df


def carregar_anos(anos: list[int]) -> pd.DataFrame:
    """Concatena os DataFrames dos anos solicitados."""
    return pd.concat([carregar_ano(a) for a in anos], ignore_index=True)


def inserir_dimensoes(df: pd.DataFrame, conn: mysql.connector.MySQLConnection) -> None:
    """Popula tabelas de dimensão."""
    cursor = conn.cursor()

    munis = df[["CD_MUNICIPIO", "NM_MUNICIPIO", "SG_UF"]].drop_duplicates()
    cursor.executemany(
        "INSERT IGNORE INTO municipio (cd_municipio, nm_municipio, sg_uf) VALUES (%s, %s, %s)",
        munis.values.tolist(),
    )
    print(f"  municipio: {cursor.rowcount} inseridos (de {len(munis)} únicos)")

    zonas = df[["NR_ZONA", "CD_MUNICIPIO"]].drop_duplicates()
    cursor.executemany(
        "INSERT IGNORE INTO zona_eleitoral (nr_zona, cd_municipio) VALUES (%s, %s)",
        zonas.values.tolist(),
    )
    print(f"  zona_eleitoral: {cursor.rowcount} inseridos (de {len(zonas)} únicos)")

    partidos = (
        df.sort_values("ANO_ELEICAO", ascending=False)
        .drop_duplicates(subset=["NR_PARTIDO"])[["NR_PARTIDO", "SG_PARTIDO", "NM_PARTIDO"]]
    )
    cursor.executemany(
        "INSERT IGNORE INTO partido (nr_partido, sg_partido, nm_partido) VALUES (%s, %s, %s)",
        partidos.values.tolist(),
    )
    print(f"  partido: {cursor.rowcount} inseridos (de {len(partidos)} únicos)")

    cargos = df[["CD_CARGO", "DS_CARGO"]].drop_duplicates()
    cursor.executemany(
        "INSERT IGNORE INTO cargo (cd_cargo, ds_cargo) VALUES (%s, %s)",
        cargos.values.tolist(),
    )
    print(f"  cargo: {cursor.rowcount} inseridos (de {len(cargos)} únicos)")

    eleicoes = df[
        [
            "CD_ELEICAO",
            "ANO_ELEICAO",
            "NR_TURNO",
            "CD_TIPO_ELEICAO",
            "NM_TIPO_ELEICAO",
            "DS_ELEICAO",
            "DT_ELEICAO",
            "TP_ABRANGENCIA",
        ]
    ].drop_duplicates(subset=["CD_ELEICAO", "NR_TURNO"])
    eleicoes = eleicoes.copy()
    eleicoes["DT_ELEICAO"] = pd.to_datetime(
        eleicoes["DT_ELEICAO"], format="%d/%m/%Y"
    ).dt.strftime("%Y-%m-%d")
    cursor.executemany(
        "INSERT IGNORE INTO eleicao (cd_eleicao, ano_eleicao, nr_turno, "
        "cd_tipo_eleicao, nm_tipo_eleicao, ds_eleicao, dt_eleicao, tp_abrangencia) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        eleicoes.values.tolist(),
    )
    print(f"  eleicao: {cursor.rowcount} inseridos (de {len(eleicoes)} únicos)")

    conn.commit()
    cursor.close()


def inserir_fato(df: pd.DataFrame, conn: mysql.connector.MySQLConnection) -> None:
    """Popula tabela fato votacao_partido_munzona."""
    cursor = conn.cursor()
    fato = df[
        [
            "CD_ELEICAO",
            "NR_TURNO",
            "CD_MUNICIPIO",
            "NR_ZONA",
            "CD_CARGO",
            "NR_PARTIDO",
            "QT_VOTOS_NOMINAIS",
            "QT_VOTOS_LEGENDA",
            "ST_VOTO_EM_TRANSITO",
            "SQ_COLIGACAO",
            "NM_COLIGACAO",
            "DS_COMPOSICAO_COLIGACAO",
            "TP_AGREMIACAO",
        ]
    ].copy()
    fato = fato.where(fato.notna(), None)

    sql = (
        "INSERT INTO votacao_partido_munzona "
        "(cd_eleicao, nr_turno, cd_municipio, nr_zona, cd_cargo, nr_partido, "
        "qt_votos_nominais, qt_votos_legenda, st_voto_em_transito, "
        "sq_coligacao, nm_coligacao, ds_composicao_coligacao, tp_agremiacao) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )

    batch_size = 5000
    total = len(fato)
    inserted = 0
    for i in range(0, total, batch_size):
        batch = fato.iloc[i : i + batch_size]
        rows = [
            tuple(None if pd.isna(v) else v for v in row)
            for row in batch.itertuples(index=False)
        ]
        cursor.executemany(sql, rows)
        conn.commit()
        inserted += len(rows)
        if (i // batch_size) % 10 == 0:
            print(f"  votacao_partido_munzona: {inserted}/{total}...")
    print(f"  votacao_partido_munzona: {inserted} inseridos")
    cursor.close()


def main(anos: list[int] | None = None) -> None:
    """Pipeline completo de carga DF."""
    if anos is None:
        anos = ANOS_FEDERAIS
    print("=" * 60)
    print(f"CARGA TSE NO MYSQL — DF, anos {anos}")
    print("=" * 60)

    criar_banco()
    executar_schema()

    print("\nCarregando CSVs...")
    df = carregar_anos(anos)
    print(f"Total: {len(df)} linhas")

    print("\nInserindo dimensões...")
    conn = conectar(DATABASE)
    inserir_dimensoes(df, conn)

    print("\nInserindo fato...")
    inserir_fato(df, conn)

    print("\n" + "=" * 60)
    print("VERIFICAÇÃO")
    print("=" * 60)
    cursor = conn.cursor()
    for tabela in [
        "municipio",
        "zona_eleitoral",
        "partido",
        "cargo",
        "eleicao",
        "votacao_partido_munzona",
    ]:
        cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
        count = cursor.fetchone()[0]
        print(f"  {tabela:<30} {count:>10} linhas")
    cursor.close()
    conn.close()
    print("\nCarga concluída.")


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else None
    main(args)
