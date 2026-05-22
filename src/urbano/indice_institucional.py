"""Índice de densidade institucional cultural-progressista por zona — DF.

Adaptação do `urbano/indice_institucional.py` do SP. As palavras-chave
(PADROES) foram trocadas pelos análogos brasilienses, conforme orientação
do `PROMPT_REPLICAR_DF.md`:

  * UNIVERSIDADE: UnB, IESB, UniCEUB, UDF, UPIS, IFB, UCB, Uniplan,
    Unieuro, faculdade, campus.
  * ESCOLA_PROGRESSISTA: Galois, Sigma, Marista, La Salle.
  * PRESTIGIO_PUBLICO: Elefante Branco, Centro Educacional <nº>, GISNO,
    CEM, CEF (centros típicos das RAs de Brasília).
  * INTERNACIONAL_CULTURAL: Goethe, Alliance, Cervantes, American School,
    Swiss School, Lycée Français.

Locais de votação: extraídos de `votacao_secao_2022_DF.parquet` (NR_ZONA,
NR_LOCAL_VOTACAO, NM_LOCAL_VOTACAO). O DF não tem base CEM/USP de
locais geocodificados — esta é uma análise apenas por nome.

ATENÇÃO: este script é metodologicamente sensível. Após primeira rodada,
inspecionar manualmente os locais classificados em cada categoria e
ajustar os regex se houver falsos positivos/negativos.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import re
import unicodedata

import pandas as pd

PARQUET_SECAO = _ROOT / "data/processed/votacao_secao_2022_DF.parquet"
SAIDA = _ROOT / "outputs/indice_institucional_por_zona.csv"


def normalizar(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode()
    return s.upper().strip()


PADROES = {
    "UNIVERSIDADE": [
        r"\bUNB\b",
        r"\bUNIVERSIDADE DE BRASILIA\b",
        r"\bUNIVERSIDADE\b",
        r"\bIESB\b",
        r"\bUNICEUB\b",
        r"\bUDF\b",
        r"\bUPIS\b",
        r"\bIFB\b",
        r"\bUCB\b",
        r"\bUNIPLAN\b",
        r"\bUNIEURO\b",
        r"\bEURO AMERICANO\b",
        r"\bFACULDADE\b",
        r"\bCAMPUS\b",
        r"\bCATOLICA DE BRASILIA\b",
        r"\bCENTRO UNIVERSITARIO\b",
    ],
    "ESCOLA_PROGRESSISTA": [
        r"\bGALOIS\b",
        r"\bSIGMA\b",
        r"\bMARISTA\b",
        r"\bLA SALLE\b",
        r"\bLEONARDO DA VINCI\b",
        r"\bROGACIONISTA\b",
        r"\bKAIROS\b",  # Colégio Kairós, perfil progressista
    ],
    # Lista nominal fechada (decisão metodológica registrada em
    # reports/decisoes_metodologicas_indice.md): apenas escolas públicas
    # tradicionalmente reconhecidas como de prestígio em Brasília. Regex
    # genérico "CENTRO DE ENSINO MEDIO" foi removido porque pegava CEMs
    # periféricos (Gama, Santa Maria, Recanto das Emas), que não têm o
    # mesmo perfil socioeconômico.
    "PRESTIGIO_PUBLICO": [
        r"\bELEFANTE BRANCO\b",
        r"\bGISNO\b",
        r"\bSETOR LESTE\b",
        r"\bCASEB\b",
    ],
    "INTERNACIONAL_CULTURAL": [
        r"\bGOETHE\b",
        r"\bALLIANCE\b",
        r"\bCERVANTES\b",
        r"\bAMERICAN SCHOOL\b",
        r"\bSWISS SCHOOL\b",
        r"\bLYCEE\b",
        r"\bLYCEUM\b",
        r"\bPASTEUR\b",
        r"\bFRANCO BRASILEIRA\b",
        r"\bBRITANICA\b",
        r"\bDANTE ALIGHIERI\b",
        r"\bMAPLE BEAR\b",
        r"\bESCOLA AMERICANA\b",
        r"\bESCOLA ALEMA\b",
        r"\bESCOLA CANADENSE\b",
        r"\bEAB\b",
    ],
}


def classificar(nome: str) -> set[str]:
    nome_norm = normalizar(nome)
    categorias: set[str] = set()
    for cat, padroes in PADROES.items():
        for padrao in padroes:
            if re.search(padrao, nome_norm):
                categorias.add(cat)
                break
    return categorias


def carregar_locais() -> pd.DataFrame:
    """Lista de locais de votação únicos no DF (parquet votacao_secao 2022)."""
    df = pd.read_parquet(PARQUET_SECAO)
    locais = (
        df[["NR_ZONA", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    return locais


def construir_indice() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (índice por zona, detalhe local-a-local).

    O índice por zona é a fração de locais classificados em qualquer
    categoria cultural-progressista, multiplicada por 100.
    """
    locais = carregar_locais()
    locais["categorias"] = locais["NM_LOCAL_VOTACAO"].map(classificar)
    for cat in PADROES:
        col = f"is_{cat.lower()}"
        locais[col] = locais["categorias"].map(lambda c, k=cat: k in c).astype(int)
    locais["is_cultural_progressista"] = (
        locais[[f"is_{k.lower()}" for k in PADROES]].sum(axis=1) > 0
    ).astype(int)

    agg = locais.groupby("NR_ZONA").agg(
        n_locais=("NM_LOCAL_VOTACAO", "count"),
        n_universidade=("is_universidade", "sum"),
        n_progressista=("is_escola_progressista", "sum"),
        n_prestigio=("is_prestigio_publico", "sum"),
        n_internacional=("is_internacional_cultural", "sum"),
        n_cultural_progressista=("is_cultural_progressista", "sum"),
    )
    agg["indice_cultural"] = (
        agg["n_cultural_progressista"] / agg["n_locais"] * 100
    )
    return agg.sort_values("indice_cultural", ascending=False), locais


def main() -> None:
    idx, det = construir_indice()
    print(f"\nZonas: {len(idx)} | locais analisados: {len(det)}")
    print(
        f"Cultural-progressistas: {det['is_cultural_progressista'].sum()} "
        f"({det['is_cultural_progressista'].mean()*100:.1f}%)"
    )

    print("\n=== ÍNDICE POR ZONA (decrescente) ===")
    cols_int = [
        "n_locais",
        "n_universidade",
        "n_progressista",
        "n_prestigio",
        "n_internacional",
        "n_cultural_progressista",
    ]
    print(
        idx.head(21)[cols_int + ["indice_cultural"]].to_string(
            float_format=lambda x: f"{x:6.1f}"
        )
    )

    print("\n=== AMOSTRA POR CATEGORIA (10 primeiros) ===")
    for cat in PADROES:
        col = f"is_{cat.lower()}"
        sub = det[det[col] == 1][["NR_ZONA", "NM_LOCAL_VOTACAO"]]
        print(f"\n--- {cat} ({len(sub)} locais) ---")
        if len(sub) == 0:
            print("  (nenhum)")
        else:
            for _, row in sub.head(10).iterrows():
                print(f"  zona {row['NR_ZONA']:>3} | {row['NM_LOCAL_VOTACAO']}")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    idx.to_csv(SAIDA)
    print(f"\nCSV: {SAIDA}")


if __name__ == "__main__":
    main()
