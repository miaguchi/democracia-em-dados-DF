"""Votos × financiamento dos eleitos — DF, todos os cargos disponíveis.

Adaptado de `sintese/votos_vs_financiamento_todos_cargos.py` do SP.
Diferenças:
  * Cargos: Governador, Senador, Dep. Federal, Dep. Distrital (não há
    Vereador nem Prefeito no DF).
  * Anos: 2018 e 2022 (prestacao_contas DF disponível só nesses anos).
  * Escopo: sempre DF (`cd_municipio=97012` ou `SG_UF=='DF'`).
  * Presidente fica de fora (cargo nacional, sem filtro de UF nas
    receitas).

Pipeline:
  1. Lê parquet `votacao_candidato_munzona_{ano}_DF.parquet` e identifica
     candidatos eleitos por cargo.
  2. Lê `receitas_candidatos_{ano}_DF.csv` e soma VR_RECEITA por
     candidato (SQ_CANDIDATO).
  3. Junta votos × receitas e calcula eficiência (votos/R$ mil).
  4. Reporta percentis e ranking por cargo/ano.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.partidario.ideologia import ESCORE_BOLOGNESI, bloco_tripartite

warnings.filterwarnings("ignore")

SAIDA_CSV = _ROOT / "outputs/tables/votos_vs_financiamento_todos_cargos.csv"
SAIDA_FIG = _ROOT / "outputs/figures/votos_vs_financiamento_todos_cargos.png"

# Fatores de inflação para R$ de 2024 (IPCA nacional, mesmos do SP)
INFLACAO = {2018: 1.42, 2022: 1.13, 2024: 1.00}

ANALISES = [
    ("Governador", 2018),
    ("Governador", 2022),
    ("Senador", 2018),
    ("Senador", 2022),
    ("Deputado Federal", 2018),
    ("Deputado Federal", 2022),
    ("Deputado Distrital", 2018),
    ("Deputado Distrital", 2022),
]


def carregar_votos_eleitos(cargo: str, ano: int) -> pd.DataFrame:
    f = _ROOT / f"data/processed/votacao_candidato_munzona_{ano}_DF.parquet"
    df = pd.read_parquet(f)
    sub_all = df[df["DS_CARGO"] == cargo].copy()

    # Eleitos (no DF, segundo turno em 2018 sim p/ Gov; 2022 Ibaneis venceu 1T)
    eleitos_2t = sub_all[
        (sub_all["NR_TURNO"] == 2) & (sub_all["DS_SIT_TOT_TURNO"] == "ELEITO")
    ]
    eleitos_1t = sub_all[
        (sub_all["NR_TURNO"] == 1)
        & (
            sub_all["DS_SIT_TOT_TURNO"].isin(
                ["ELEITO POR QP", "ELEITO POR MÉDIA", "ELEITO"]
            )
        )
    ]
    sqs_2t = set(eleitos_2t["SQ_CANDIDATO"].unique())
    sqs_1t = set(eleitos_1t["SQ_CANDIDATO"].unique())
    todos_eleitos = sqs_2t | sqs_1t

    # Somar votos de 1º + 2º turno por candidato eleito
    sub_eleitos = sub_all[sub_all["SQ_CANDIDATO"].isin(todos_eleitos)].copy()
    agg = (
        sub_eleitos.groupby(["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "NR_PARTIDO"])
        .agg(votos=("QT_VOTOS_NOMINAIS", "sum"))
        .reset_index()
    )
    agg["cargo"] = cargo
    agg["ano"] = ano
    return agg


def carregar_receitas(ano: int) -> pd.DataFrame:
    f = _ROOT / f"data/raw/prestacao_contas/{ano}_DF/receitas_candidatos_{ano}_DF.csv"
    df = pd.read_csv(f, sep=";", encoding="latin-1", low_memory=False, dtype=str)
    df["VR_RECEITA"] = pd.to_numeric(
        df["VR_RECEITA"].astype(str).str.replace(",", "."),
        errors="coerce",
    ).fillna(0)
    by_cand = df.groupby("SQ_CANDIDATO")["VR_RECEITA"].sum().reset_index()
    by_cand.columns = ["SQ_CANDIDATO", "receita_total"]
    return by_cand


def cruzar(cargo: str, ano: int) -> pd.DataFrame:
    votos = carregar_votos_eleitos(cargo, ano)
    receitas = carregar_receitas(ano)
    votos["SQ_CANDIDATO"] = votos["SQ_CANDIDATO"].astype(str)
    df = votos.merge(receitas, on="SQ_CANDIDATO", how="left")
    df["receita_total"] = df["receita_total"].fillna(0)
    df["receita_real_2024"] = df["receita_total"] * INFLACAO[ano]
    df["votos_por_mil_real"] = np.where(
        df["receita_real_2024"] > 0,
        df["votos"] / (df["receita_real_2024"] / 1000),
        np.nan,
    )
    # Bloco ideológico via Bolognesi
    df["escore"] = df["SG_PARTIDO"].map(ESCORE_BOLOGNESI)
    df["bloco"] = df["escore"].map(
        lambda e: bloco_tripartite(e) if pd.notna(e) else "DESCONHECIDO"
    )
    return df


def main() -> None:
    todos = []
    for cargo, ano in ANALISES:
        try:
            d = cruzar(cargo, ano)
            print(
                f"  {cargo:>20} {ano}: {len(d)} eleitos | "
                f"votos médios={d['votos'].mean():.0f} | "
                f"receita R$ média={d['receita_total'].mean():.0f}"
            )
            todos.append(d)
        except Exception as e:
            print(f"  ERRO {cargo} {ano}: {e}")
    base = pd.concat(todos, ignore_index=True)

    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(SAIDA_CSV, index=False)
    print(f"\nCSV: {SAIDA_CSV}")

    print("\n=== Eficiência (votos/R$ mil 2024) — média por cargo/ano/bloco ===")
    print(
        base.groupby(["cargo", "ano", "bloco"])["votos_por_mil_real"]
        .mean()
        .round(2)
        .to_string()
    )

    # Figura: dispersão votos × receita por cargo
    cargos_unicos = base["cargo"].unique()
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharey=False)
    for ax, cargo in zip(axes.flat, cargos_unicos):
        sub = base[base["cargo"] == cargo]
        cores = {"ESQUERDA": "tab:red", "CENTRO": "tab:gray",
                 "DIREITA": "tab:blue", "DESCONHECIDO": "tab:olive"}
        for bloco, sub_b in sub.groupby("bloco"):
            ax.scatter(
                sub_b["receita_real_2024"] / 1000,
                sub_b["votos"],
                c=cores.get(bloco, "k"),
                label=bloco,
                alpha=0.7, s=40,
            )
        ax.set_title(cargo)
        ax.set_xlabel("Receita (R$ mil, 2024)")
        ax.set_ylabel("Votos do eleito")
        ax.grid(alpha=0.3)
        if cargo == cargos_unicos[0]:
            ax.legend(fontsize=8)
    fig.suptitle("Votos × financiamento dos eleitos — DF 2018-2022")
    fig.tight_layout()
    SAIDA_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA_FIG, dpi=300)
    print(f"Fig: {SAIDA_FIG}")


if __name__ == "__main__":
    main()
