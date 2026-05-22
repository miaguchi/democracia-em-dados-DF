"""Mapeamento zona eleitoral → Região Administrativa (RA) do DF.

O DF não tem uma base CEM/USP com geocoding dos locais de votação. Para
chegar à RA dominante de cada zona, esta implementação extrai tokens
do endereço (`DS_LOCAL_VOTACAO_ENDERECO`) e do nome do local
(`NM_LOCAL_VOTACAO`) de cada local de votação, e atribui a cada zona
a RA com maior frequência de matches.

A lista RAS_DF reflete a delimitação oficial de 35 RAs do DF (2020),
com palavras-chave que costumam aparecer no endereço/sigla:
  * SGAS/SQS/CLN → Asa Sul
  * SGAN/SQN/EQN → Asa Norte
  * SHCES/CRUZEIRO/OCTOGONAL → Cruzeiro
  * etc.

Saída: CSV `outputs/zona_to_ra.csv` com colunas [NR_ZONA, RA_DOMINANTE,
n_locais, n_match].

Limitação: alguns endereços são genéricos ("AREA ESPECIAL") sem token
discriminante; zonas que cobrem múltiplas RAs (raro em Brasília) ficam
classificadas pela RA majoritária.
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
SAIDA = _ROOT / "outputs/zona_to_ra.csv"


def normalizar(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode()
    return s.upper().strip()


# Padrões de RA. Cada item é (nome_RA, lista de regex). Ordem importa
# (mais específico antes do mais genérico).
RAS_DF: list[tuple[str, list[str]]] = [
    ("Lago Sul", [r"\bLAGO SUL\b", r"\bSHIS\b", r"\bQI\b", r"\bQL\b", r"PAINEIRAS"]),
    ("Lago Norte", [r"\bLAGO NORTE\b", r"\bSHIN\b", r"\bSHCIN\b"]),
    ("Sudoeste", [r"\bSUDOESTE\b", r"\bSHCSW\b", r"\bSQSW\b", r"\bCCSW\b"]),
    ("Octogonal", [r"\bOCTOGONAL\b", r"\bAOS\b", r"\bSHCES\b"]),
    ("Cruzeiro", [r"\bCRUZEIRO\b", r"\bSRES\b"]),
    ("Aguas Claras", [r"\bAGUAS CLARAS\b", r"AGUAS  CLARAS"]),
    ("Vicente Pires", [r"\bVICENTE PIRES\b"]),
    ("Park Way", [r"\bPARK WAY\b"]),
    ("Nucleo Bandeirante", [r"\bNUCLEO BANDEIRANTE\b", r"\bN BANDEIRANTE\b"]),
    ("Candangolandia", [r"\bCANDANGOLANDIA\b"]),
    ("Riacho Fundo I", [r"\bRIACHO FUNDO I\b", r"\bRIACHO FUNDO 1\b", r"\bRIACHO FUNDO\b"]),
    ("Riacho Fundo II", [r"\bRIACHO FUNDO II\b", r"\bRIACHO FUNDO 2\b"]),
    ("Guara I", [r"\bGUARA I\b", r"\bGUARA 1\b"]),
    ("Guara II", [r"\bGUARA II\b", r"\bGUARA 2\b", r"\bGUARA\b"]),
    ("Taguatinga", [r"\bTAGUATINGA\b"]),
    ("Ceilandia", [r"\bCEILANDIA\b", r"\bEQNM\b", r"\bEQNL\b", r"\bEQNJ\b",
                    r"\bEQNN\b", r"\bEQNP\b", r"\bQNM\b", r"\bQNL\b",
                    r"\bQNJ\b", r"\bQNN\b", r"\bQNP\b", r"\bQNO\b",
                    r"\bQNQ\b", r"\bSETOR M NORTE\b", r"\bSETOR N NORTE\b",
                    r"\bSETOR O NORTE\b", r"\bSETOR P NORTE\b",
                    r"\bSETOR Q NORTE\b"]),
    ("Samambaia", [r"\bSAMAMBAIA\b"]),
    ("Recanto das Emas", [r"\bRECANTO DAS EMAS\b"]),
    ("Riacho Verde", [r"\bRIACHO VERDE\b"]),
    ("Brazlandia", [r"\bBRAZLANDIA\b"]),
    ("Planaltina", [r"\bPLANALTINA\b"]),
    ("Sobradinho I", [r"\bSOBRADINHO\b"]),
    ("Sobradinho II", [r"\bSOBRADINHO II\b"]),
    ("Paranoa", [r"\bPARANOA\b"]),
    ("Itapoa", [r"\bITAPOA\b"]),
    ("Sao Sebastiao", [r"\bSAO SEBASTIAO\b"]),
    ("Jardim Botanico", [r"\bJARDIM BOTANICO\b"]),
    ("Gama", [r"\bGAMA\b"]),
    ("Santa Maria", [r"\bSANTA MARIA\b"]),
    ("Fercal", [r"\bFERCAL\b"]),
    ("Estrutural", [r"\bESTRUTURAL\b", r"\bSCIA\b"]),
    ("Varjao", [r"\bVARJAO\b"]),
    ("SIA", [r"\bSIA\b"]),
    # Plano Piloto vem por último porque é genérico
    ("Asa Sul", [r"\bSGAS\b", r"\bSQS\b", r"\bCLS\b", r"\bSCS\b",
                  r"\bSCRS\b", r"\bSHCS\b", r"\bSHIS\b"]),
    ("Asa Norte", [r"\bSGAN\b", r"\bSQN\b", r"\bCLN\b", r"\bEQN\b",
                    r"\bSCN\b", r"\bSCRN\b", r"\bSHCNO\b"]),
    ("Plano Piloto", [r"\bPLANO PILOTO\b", r"\bBRASILIA\b"]),
]


def classificar_endereco(endereco: str, nome: str) -> set[str]:
    texto = f"{normalizar(endereco)} {normalizar(nome)}"
    matches: set[str] = set()
    for ra, padroes in RAS_DF:
        for pat in padroes:
            if re.search(pat, texto):
                matches.add(ra)
                break
    return matches


def mapear() -> pd.DataFrame:
    df = pd.read_parquet(PARQUET_SECAO)
    locais = df[
        ["NR_ZONA", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO",
         "DS_LOCAL_VOTACAO_ENDERECO"]
    ].drop_duplicates().reset_index(drop=True)

    # Expandir: cada (zona, local) → lista de RAs candidatas
    registros = []
    for _, row in locais.iterrows():
        ras = classificar_endereco(
            row["DS_LOCAL_VOTACAO_ENDERECO"], row["NM_LOCAL_VOTACAO"]
        )
        if not ras:
            registros.append({"NR_ZONA": row["NR_ZONA"], "RA": "DESCONHECIDA"})
        else:
            for ra in ras:
                registros.append({"NR_ZONA": row["NR_ZONA"], "RA": ra})
    long = pd.DataFrame(registros)

    contagem = (
        long.groupby(["NR_ZONA", "RA"]).size().rename("n").reset_index()
    )
    # RA dominante por zona (maior contagem; descarta DESCONHECIDA se houver
    # outras opções)
    def dominante(grupo: pd.DataFrame) -> pd.Series:
        sem_desc = grupo[grupo["RA"] != "DESCONHECIDA"]
        base = sem_desc if len(sem_desc) > 0 else grupo
        top = base.sort_values("n", ascending=False).iloc[0]
        total = grupo["n"].sum()
        return pd.Series({
            "RA_DOMINANTE": top["RA"],
            "n_match_dominante": int(top["n"]),
            "n_locais_total": int(total),
            "pct_dominante": round(top["n"] / total * 100, 1),
        })

    zona_ra = contagem.groupby("NR_ZONA").apply(dominante).reset_index()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    zona_ra.to_csv(SAIDA, index=False)
    return zona_ra


if __name__ == "__main__":
    z = mapear()
    print("\n=== Mapeamento zona → RA dominante (DF) ===")
    print(z.to_string(index=False))
    print(f"\nCSV: {SAIDA}")
