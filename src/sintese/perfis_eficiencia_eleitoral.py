"""Perfis de eficiência eleitoral por arquétipo — DF.

Adaptação de `sintese/perfis_eficiencia_eleitoral.py` do SP. Lê
`outputs/tables/votos_vs_financiamento_todos_cargos.csv` (base
gerada pelo script homônimo no DF) e classifica cada candidato por
arquétipo identificado no nome de urna.

Arquétipos (mesma taxonomia do SP):
  * Religioso
  * Segurança
  * Profissional
  * Familiar/Dinastia
  * Coletivo/Mandata
  * Outros (sem arquétipo claro)

Compara eficiência (votos/R$ mil) por arquétipo × cargo × bloco
ideológico.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import re
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

CSV_BASE = _ROOT / "outputs/tables/votos_vs_financiamento_todos_cargos.csv"
SAIDA_CSV = _ROOT / "outputs/tables/perfis_eficiencia_eleitoral.csv"
SAIDA_FIG = _ROOT / "outputs/figures/perfis_eficiencia_eleitoral.png"

ARQUETIPOS = [
    ("Religioso", [
        r"\bPASTOR\b", r"\bPASTORA\b", r"\bBISPO\b", r"\bBISPA\b",
        r"\bMISSION", r"\bIRM[ÃA]O\b", r"\bIRM[ÃA]\b", r"\bDI[ÁA]CONO\b",
        r"\bAP[ÓO]STOLO\b", r"\bPADRE\b", r"\bFREI\b", r"\bREVERENDO\b",
        r"\bPRESB[ÍI]TERO\b", r"\bRABINO\b",
    ]),
    ("Segurança", [
        r"\bSARGENTO\b", r"\bMAJOR\b", r"\bCABO\b", r"\bCAPIT[ÃA]O\b",
        r"\bTENENTE\b", r"\bDELEGADO\b", r"\bDELEGADA\b", r"\bCORONEL\b",
        r"\bINSPETOR\b", r"\bCOMANDANTE\b", r"\bPM\b", r"\bGCM\b",
        r"\bGUARDA\b", r"\bBOMBEIRO\b", r"\bBRIGADIER\b", r"\bSOLDADO\b",
        r"\bPOLICIAL\b", r"\bAGENTE\b",
    ]),
    ("Profissional", [
        r"\bDR\b\.?", r"\bDR[A]?\b\.?", r"\bDOUTOR\b", r"\bDOUTORA\b",
        r"\bPROFESSOR\b", r"\bPROFESSORA\b", r"\bPROF\b\.?",
        r"\bENG\b\.?", r"\bENGENHEIRO\b", r"\bENGENHEIRA\b",
        r"\bADVOGAD[OA]\b", r"\bM[ÉE]DIC[OA]\b", r"\bDENTISTA\b",
    ]),
    ("Familiar/Dinastia", [
        r"\bNETO\b$", r"\bFILHO\b$", r"\bFILHA\b$", r"\bJR\b\.?$",
        r"\bJ[UÚ]NIOR\b$", r"\bSOBRINHO\b$",
    ]),
    ("Coletivo/Mandata", [
        r"\bMANDATA\b", r"\bMANDATO COLETIVO\b", r"\bBANCADA\b",
        r"\bJUNTAS\b", r"\bCOLETIV[OA]\b",
    ]),
]


def classificar(nome: str) -> str:
    if not isinstance(nome, str):
        return "Outros"
    n = nome.upper()
    for arq, padroes in ARQUETIPOS:
        for pat in padroes:
            if re.search(pat, n):
                return arq
    return "Outros"


def main() -> None:
    base = pd.read_csv(CSV_BASE)
    base["arquetipo"] = base["NM_URNA_CANDIDATO"].map(classificar)

    print("\n=== Distribuição de arquétipos por cargo/ano ===")
    print(
        base.groupby(["cargo", "ano", "arquetipo"]).size().to_string()
    )

    print("\n=== Eficiência média (votos/R$ mil) por arquétipo ===")
    geral = (
        base.dropna(subset=["votos_por_mil_real"])
        .groupby("arquetipo")["votos_por_mil_real"]
        .agg(["count", "mean", "median"])
        .round(2)
    )
    print(geral.to_string())

    print("\n=== Eficiência por arquétipo × bloco ideológico ===")
    cruz = (
        base.dropna(subset=["votos_por_mil_real"])
        .groupby(["arquetipo", "bloco"])["votos_por_mil_real"]
        .agg(["count", "mean"])
        .round(2)
    )
    print(cruz.to_string())

    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(SAIDA_CSV, index=False)

    fig, ax = plt.subplots(figsize=(9, 5))
    medias = (
        base.dropna(subset=["votos_por_mil_real"])
        .groupby("arquetipo")["votos_por_mil_real"]
        .mean()
        .sort_values(ascending=False)
    )
    ax.bar(medias.index, medias.values, color="steelblue")
    ax.set_ylabel("Eficiência (votos / R$ mil de 2024)")
    ax.set_title("Eficiência eleitoral por arquétipo — eleitos DF 2018-2022")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_FIG, dpi=300)
    print(f"\nCSV: {SAIDA_CSV}\nFig: {SAIDA_FIG}")


if __name__ == "__main__":
    main()
