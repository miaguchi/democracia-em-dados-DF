"""PDF de diagnóstico estratégico — Distrito Federal.

Integra três blocos:
  Parte I  — Referencial teórico: ideologia (Bobbio, Bolognesi et al.)
             e sociologia política brasileira (Wanderley Guilherme,
             Singer, geografia eleitoral, caso DF).
  Parte II — Desenho do produto: granularidade (zona/seção/microrregião),
             quatro tipos de volatilidade, dois diagnósticos diferenciados.
  Parte III — Implementação: arquitetura de dados, cronograma e
              considerações éticas/legais.

Saída: outputs/diagnostico_estrategico_df.pdf

Notas sobre citações: apenas referências verificáveis são incluídas.
Bolognesi-Ribeiro-Codato (Dados 2023) já é a fonte canônica usada no
projeto. Outros nomes (Bobbio, Singer, Wanderley G. dos Santos,
Pedersen, Bartolini & Mair) entram com obra e ano. Referências que o
diálogo de origem mencionou em forma incerta (placeholder
Zolnerkevic-Guarnieri; Bolognesi 2026 Opinião Pública) ficam de fora
para evitar imprecisão.
"""

from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SAIDA = _ROOT / "outputs/diagnostico_estrategico_df.pdf"

# ---------- estilos ----------
styles = getSampleStyleSheet()
st_titulo = ParagraphStyle(
    "titulo", parent=styles["Title"], fontSize=20, alignment=TA_CENTER,
    spaceAfter=12, textColor=colors.HexColor("#1a1a1a"),
)
st_subt = ParagraphStyle(
    "subt", parent=styles["Normal"], fontSize=12, alignment=TA_CENTER,
    spaceAfter=4, textColor=colors.HexColor("#444"),
)
st_parte = ParagraphStyle(
    "parte", parent=styles["Heading1"], fontSize=18, alignment=TA_CENTER,
    spaceBefore=24, spaceAfter=12, textColor=colors.HexColor("#1a4dd0"),
)
st_h1 = ParagraphStyle(
    "h1", parent=styles["Heading1"], fontSize=13, spaceBefore=16, spaceAfter=6,
    textColor=colors.HexColor("#1a1a1a"),
)
st_h2 = ParagraphStyle(
    "h2", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4,
    textColor=colors.HexColor("#333"),
)
st_body = ParagraphStyle(
    "body", parent=styles["Normal"], fontSize=10, leading=14,
    alignment=TA_JUSTIFY, spaceAfter=6,
)
st_leg = ParagraphStyle(
    "leg", parent=styles["Italic"], fontSize=8, alignment=TA_CENTER,
    textColor=colors.HexColor("#555"), spaceAfter=10,
)
st_box = ParagraphStyle(
    "box", parent=styles["Normal"], fontSize=9.5, leading=13,
    alignment=TA_JUSTIFY, leftIndent=10, rightIndent=10,
    spaceBefore=4, spaceAfter=10, borderColor=colors.HexColor("#1a4dd0"),
    borderWidth=0.5, borderPadding=6, backColor=colors.HexColor("#f0f4ff"),
)
st_cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8.5, leading=11, alignment=TA_LEFT)
st_cell_c = ParagraphStyle("cell_c", parent=styles["Normal"], fontSize=8.5, leading=11, alignment=TA_CENTER)
st_cell_b = ParagraphStyle(
    "cell_b", parent=styles["Normal"], fontSize=8.5, leading=11,
    fontName="Helvetica-Bold", alignment=TA_CENTER,
)


def p(t): return Paragraph(t, st_body)
def h1(t): return Paragraph(t, st_h1)
def h2(t): return Paragraph(t, st_h2)
def parte(t): return Paragraph(t, st_parte)
def caixa(t): return KeepTogether([Paragraph(t, st_box)])
def _c(t): return Paragraph(t, st_cell)
def _cc(t): return Paragraph(t, st_cell_c)
def _cb(t): return Paragraph(t, st_cell_b)


def tabela(dados, col_widths, header=True):
    t = Table(dados, colWidths=col_widths)
    estilo = [
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        estilo.insert(0, ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e0e0e0")))
    t.setStyle(TableStyle(estilo))
    return t


def fig(caminho, w_cm=15, legenda=None):
    out = [Image(str(caminho), width=w_cm * cm, height=w_cm * 0.75 * cm, kind="proportional")]
    if legenda:
        out.append(Paragraph(legenda, st_leg))
    return out


def conteudo() -> list:
    el: list = []

    # ============ CAPA ============
    el.append(Spacer(1, 4 * cm))
    el.append(Paragraph("Diagnóstico Estratégico Eleitoral", st_titulo))
    el.append(Paragraph("Distrito Federal — Janela 1998-2022", st_subt))
    el.append(Spacer(1, 0.4 * cm))
    el.append(Paragraph(
        "Referencial teórico, desenho de produto e implementação",
        st_subt,
    ))
    el.append(Spacer(1, 6 * cm))
    el.append(Paragraph(
        "Base empírica: ingestão TSE 1998-2022, Censo IBGE 2022, "
        "cobertura de cinco cargos federais e 19 zonas eleitorais "
        "(Brasília-DF, código IBGE 5300108). Reproduz a metodologia "
        "desenvolvida em São Paulo "
        "(<i>github.com/miaguchi/democracia-em-dados</i>) e a estende "
        "para o desenho de produto de inteligência eleitoral por "
        "microrregião.",
        st_body,
    ))
    el.append(PageBreak())

    # ============ PARTE I ============
    el.append(parte("Parte I — Referencial teórico"))

    el.append(h1("1. O problema da medida ideológica"))
    el.append(p(
        "A distinção esquerda/direita não é um vestígio do século XX. Bobbio "
        "(1995) sustenta que ela persiste porque traduz um conflito "
        "permanente entre dois eixos morais: o de <b>liberdade</b> "
        "(autonomia vs. autoridade) e o de <b>igualdade</b> "
        "(redistribuição vs. mérito/herança). Toda tentativa de medir "
        "ideologia partidária precisa lidar com três famílias de "
        "abordagem:"
    ))
    el.append(p(
        "<b>(a) Programática</b> — codificação de manifestos partidários "
        "(<i>Comparative Manifesto Project</i>). Robusta historicamente, "
        "mas no Brasil pós-1988 padece da fluidez programática dos "
        "partidos (manifestos genéricos, plataformas oportunistas)."
    ))
    el.append(p(
        "<b>(b) Comportamental</b> — análise de votações nominais "
        "parlamentares (<i>roll-call</i>) e coalizões. Mede o que os "
        "partidos efetivamente fazem, não o que dizem. Excelente em "
        "sistemas estáveis, problemática quando a disciplina partidária "
        "é fraca ou as votações são pactuadas (caso Brasil pré-2018)."
    ))
    el.append(p(
        "<b>(c) Expert survey</b> — agregação de juízos de especialistas "
        "via questionário sistematizado. Captura o consenso intersubjetivo "
        "da comunidade acadêmica em um momento dado. É a base de "
        "instrumentos como o <i>Chapel Hill Expert Survey</i> "
        "internacional e, no Brasil, do estudo de Bolognesi, Ribeiro & "
        "Codato (Dados, 2023)."
    ))

    el.append(h1("2. A escala Bolognesi-Ribeiro-Codato (2023)"))
    el.append(p(
        "Aplicada em 2018 a 174 especialistas da Associação Brasileira "
        "de Ciência Política, a escala mede a posição de cada partido "
        "em um eixo contínuo de 0 (extrema-esquerda) a 10 "
        "(extrema-direita). Combina questões sobre dimensão econômica "
        "(estatização vs. mercado), dimensão moral-cultural (progressismo "
        "vs. conservadorismo) e auto-localização agregada dos "
        "respondentes."
    ))
    el.append(p(
        "Os autores propõem cinco limiares operativos a partir das "
        "médias: extrema-esquerda (≤ 1,49), esquerda (1,50-3,00), "
        "centro-esquerda (3,01-4,49), centro (4,50-5,50), centro-direita "
        "(5,51-7,00), direita (7,01-8,49), extrema-direita (≥ 8,50). "
        "O projeto adota o esquema <i>tripartite</i> (esquerda ≤ 4,49 / "
        "centro 4,50-5,50 / direita ≥ 5,51) como classificação operacional "
        "padrão e o <i>quintipartite</i> (com centros refinados) como "
        "robustez."
    ))
    el.append(caixa(
        "<b>O centro como categoria em erosão.</b> Um achado recorrente "
        "da literatura brasileira é o esvaziamento da posição central. "
        "No survey de 2018 já se observa concentração de partidos "
        "abaixo de 3,00 (campo esquerda) e acima de 7,00 (campo direita), "
        "com a faixa 4,50-5,50 efetivamente vazia. Para a régua aplicada "
        "ao DF em 2022, isso significa que partidos historicamente "
        "considerados centrais — MDB, PSDB — caem no campo da direita "
        "(MDB = 7,01; PSDB = 7,11). A consequência prática é metodológica: "
        "uma trajetória PDT → PSB → PT cruza dois polos do campo "
        "esquerda, mas não passa por nenhum centro consensual no sistema "
        "atual."
    ))

    el.append(h1("3. Quatro chaves da sociologia política brasileira"))
    el.append(p(
        "Quatro tradições teóricas estruturam o entendimento de quem vota "
        "em quem no Brasil contemporâneo e por quê. Nenhuma delas, "
        "isoladamente, dá conta do quadro; em conjunto formam o pano de "
        "fundo conceitual para interpretar achados quantitativos por zona "
        "ou seção."
    ))
    el.append(h2("3.1 Cidadania regulada (Wanderley Guilherme dos Santos, 1979)"))
    el.append(p(
        "A tese central de <i>Cidadania e Justiça</i> é que, no Brasil "
        "pós-1930, o direito à cidadania foi historicamente mediado pela "
        "inserção em ocupações reguladas pelo Estado (sindicatos "
        "reconhecidos, profissões certificadas, vínculo empregatício "
        "formal). Quem está dentro tem acesso a previdência, saúde, "
        "educação, proteção; quem está fora é cidadão de segunda. "
        "Para a sociologia eleitoral, isso explica por que o "
        "funcionalismo público — federal, em especial — vota como "
        "categoria, e por que regiões de alta concentração de servidores "
        "(Plano Piloto, Sudoeste, parte do Lago Norte) têm comportamento "
        "estatisticamente distinto de regiões de informalidade ou "
        "trabalho privado de baixa renda."
    ))
    el.append(h2("3.2 Lulismo (André Singer, 2012)"))
    el.append(p(
        "Em <i>Os Sentidos do Lulismo</i>, Singer descreve a "
        "consolidação, entre 2002 e 2010, de uma nova base eleitoral do "
        "PT: o <i>subproletariado</i>, classes populares historicamente "
        "antipetistas que migraram em massa para Lula após os ganhos "
        "materiais do primeiro mandato (Bolsa Família, formalização do "
        "trabalho, salário mínimo). A tese é que essa adesão é "
        "<i>cautelosa</i>: troca redistribuição por estabilidade, sem "
        "ruptura institucional. Permite explicar por que zonas pobres "
        "viraram bases lulistas estáveis até 2014 e por que parte dessa "
        "base se moveu para Bolsonaro a partir de 2018, quando a oferta "
        "redistributiva petista perdeu credibilidade e o discurso de "
        "ordem ganhou tração."
    ))
    el.append(h2("3.3 Bolsonarismo pós-2013"))
    el.append(p(
        "A literatura sobre o bolsonarismo identifica pelo menos três "
        "componentes não-coextensivos: (i) ressentimento de classe "
        "média educada contra o lulismo redistributivo; (ii) "
        "mobilização evangélica em torno de pauta moral; (iii) bloco de "
        "elite empresarial e de segurança que viu na ruptura de 2018 "
        "uma oportunidade. No DF, o terceiro componente tem peso maior "
        "que a média nacional pela concentração de militares, policiais "
        "federais e operadores do sistema de justiça, particularmente "
        "em regiões como Águas Claras, Sudoeste e partes do Lago Norte."
    ))
    el.append(h2("3.4 Geografia eleitoral"))
    el.append(p(
        "A tradição de geografia eleitoral — de André Siegfried "
        "(1913) a Cem Anos do voto (2018) — sustenta que o voto se "
        "<i>territorializa</i> por estrutura social mais que por "
        "convicção: dois eleitores com renda e escolaridade comparáveis, "
        "morando em bairros distintos, tendem a votar diferente porque "
        "estão imersos em redes sociais e símbolos diferentes. No DF, "
        "isso se traduz na distinção entre o Plano Piloto "
        "cosmopolita-universitário e periferias de funcionalismo "
        "civil-segurança (Ceilândia, Samambaia, Gama, Planaltina), com "
        "Lago Sul como bolsão de elite empresarial."
    ))

    el.append(h1("4. O caso DF — onde teoria encontra território"))
    el.append(p(
        "O DF é simultaneamente unidade da federação e município, sem "
        "câmara de vereadores e sem prefeito; o governador acumula a "
        "função executiva municipal e a Câmara Legislativa Distrital "
        "(24 cadeiras) substitui a estadual. Em janela 1998-2022, são "
        "sete eleições federais consecutivas — sem ciclo municipal "
        "separado para introduzir variação."
    ))
    el.append(KeepTogether([
        Paragraph(
            "Subdivisões administrativas: 35 Regiões Administrativas (RAs) "
            "reconhecidas pela Codeplan, com diferenças socioeconômicas "
            "extremas — Lago Sul registra renda média do responsável de "
            "R$ 19.529 em 2022, enquanto SCIA-Estrutural fica em R$ 1.628 "
            "(proporção de 12 para 1). O DF tem 19 zonas eleitorais "
            "(mapeadas neste projeto), cada uma cobrindo uma ou mais RAs.",
            st_body,
        ),
        Paragraph(
            "<b>Hipótese empírica testada e refutada.</b> A tese "
            "institucional consolidada em SP — densidade de equipamentos "
            "educativo-culturais cosmopolitas como preditor independente "
            "do voto progressista — <i>não se sustenta no DF</i>. Em "
            "regressão OLS sobre Δ% esquerda 2010→2022 por zona, "
            "controlando por log da renda, o coeficiente do índice cai "
            "de β = −0,156 (p = 0,06) para β = −0,08 (p = 0,44), com "
            "sinal negativo: zonas mais ricas/educadas <i>perderam mais "
            "esquerda</i>. A explicação mais econômica é que a elite "
            "educada do DF é majoritariamente funcionalismo de Forças "
            "Armadas, segurança pública, judiciário e Banco Central — "
            "categorias com afinidade estrutural com a coalizão "
            "bolsonarista —, ao contrário da elite paulistana.",
            st_box,
        ),
    ]))

    el.append(PageBreak())

    # ============ PARTE II ============
    el.append(parte("Parte II — Desenho do produto"))

    el.append(h1("5. Granularidade analítica: o que dá e o que não dá"))
    el.append(p(
        "Uma das decisões mais consequentes — e mais facilmente "
        "ignoradas — do desenho de produto eleitoral é a unidade de "
        "análise. A linguagem informal de campanha mistura escalas "
        "incompatíveis: \"esse bairro\", \"essa rua\", \"esse colégio\" "
        "podem corresponder a unidades estatísticas muito diferentes ou "
        "a unidades inexistentes."
    ))

    el.append(tabela(
        [
            [_cb("Nível"), _cb("Disponível"), _cb("Granularidade aproximada"), _cb("Adequação")],
            [_c("Zona eleitoral"), _cc("Sim"), _c("19 unidades no DF, ~50-100k eleitores cada"),
             _c("Diagnóstico macro; insuficiente para decisão tática de campanha")],
            [_c("Local de votação"), _cc("Sim"), _c("~1.300 unidades no DF, ~700-1500 eleitores cada"),
             _c("Operacional para porta-a-porta; equivale a 2-4 quadras")],
            [_c("Seção"), _cc("Sim, com BU desde 2014"),
             _c("~5.000 unidades, ~300-400 eleitores cada"),
             _c("Granularidade máxima do voto público; nível de microcélula tática")],
            [_c("Quarteirão"), _cc("<b>Não</b>"), _c("Não existe como dado"),
             _c("Promessa de quarteirão é tecnicamente falsa — voto é secreto, "
                "endereço de eleitor é dado protegido")],
            [_c("Microrregião eleitoral"), _cc("Construída"),
             _c("Voronoi sobre locais de votação, ~1.300 polígonos no DF"),
             _c("Termo honesto para o produto: \"área de influência da seção X\"")],
        ],
        col_widths=[3.2 * cm, 2.0 * cm, 5.5 * cm, 5.5 * cm],
    ))
    el.append(Spacer(1, 0.3 * cm))
    el.append(caixa(
        "<b>Aviso comercial e ético.</b> Vender \"mapa por quarteirão\" é "
        "uma asserção tecnicamente falsa. O voto é secreto e o boletim "
        "de urna agrega no nível da seção. Endereço de eleitor é dado "
        "protegido pela LGPD e pelo TSE. Microrregião eleitoral — "
        "área de influência da seção construída por Voronoi sobre o "
        "local de votação — é o termo que pode ser entregue e "
        "defendido em escrutínio jornalístico ou jurídico."
    ))

    el.append(h1("6. Quatro tipos de mapa de volatilidade"))
    el.append(p(
        "Volatilidade não é uma medida única; é uma família de medidas "
        "que respondem a perguntas diferentes da campanha. Confundir os "
        "tipos produz ferramentas pouco úteis. As quatro definições a "
        "seguir são operacionalizáveis com os dados disponíveis."
    ))

    el.append(h2("Tipo 1 — Variância intertemporal de campo"))
    el.append(p(
        "Para cada unidade (zona ou seção) e cada campo ideológico "
        "(esquerda/centro/direita por Bolognesi), o desvio padrão da "
        "<i>participação percentual</i> do campo ao longo de 2014, "
        "2018 e 2022. Mede o quanto a unidade <i>oscilou de polo</i>. "
        "Alta variância = terreno de disputa; baixa variância = base "
        "estável (própria ou adversária)."
    ))
    el.append(h2("Tipo 2 — Pedersen por seção"))
    el.append(p(
        "Soma das mudanças absolutas no voto por partido entre dois "
        "ciclos, dividida por 2. É o índice clássico de Pedersen "
        "(<i>European Journal of Political Research</i>, 1979) "
        "agregado em nível microterritorial. Mede churn partidário "
        "independente de direção: uma seção pode ter Pedersen alto "
        "trocando votos entre PSDB e PSD (ambos direita) sem mudar de "
        "polo. Bartolini & Mair (1990) decompõem o índice em "
        "<i>volatilidade entre blocos</i> e <i>dentro de blocos</i>; "
        "no DF, a janela 2018→2022 para Presidente teve V_total = "
        "0,81 mas apenas 12,1% disso é entre blocos — a quase "
        "totalidade da volatilidade presidencial recente é "
        "<i>rotação de partidos dentro do mesmo campo</i>."
    ))
    el.append(h2("Tipo 3 — Inconsistência cross-cargo"))
    el.append(p(
        "Para uma mesma seção em um mesmo ciclo, o desvio entre os "
        "campos do voto para presidente, governador, dep. distrital e "
        "dep. federal. Uma seção \"Bolsonaro + Ibaneis + esquerda no "
        "distrital\" é estatisticamente inconsistente — voto "
        "personalista, em que nome próprio pesa mais que partido. "
        "Útil para identificar terreno de campanha de nome individual, "
        "tipicamente associada a candidatos com vínculo religioso, de "
        "segurança ou de prestação de serviço público local."
    ))
    el.append(h2("Tipo 4 — Decay de incumbência"))
    el.append(p(
        "Para um candidato individual que disputa eleições sucessivas, "
        "a correlação seção-a-seção entre seu voto pessoal no ciclo "
        "anterior e no atual. Alta correlação = base reconhece o nome; "
        "decay (correlação caindo, ou voto absoluto despencando) = "
        "base se desligando. É o mapa decisivo para campanhas de "
        "<i>defesa</i>: indica onde concentrar esforço para reter o "
        "que se tem e onde a perda já é irreversível."
    ))

    el.append(h1("7. Dois diagnósticos diferenciados"))

    el.append(h2("7.1 Candidata a deputada federal, campo direita"))
    el.append(p(
        "<b>Produto-fim:</b> mapa de oportunidade marginal. Identificação "
        "de microrregiões onde o voto agregado de direita em 2022 foi "
        "alto mas <i>disperso</i> entre muitos candidatos a federal — "
        "ou onde houve voto majoritário de direita (Pres/Gov) sem voto "
        "consolidado em federal. São zonas de \"direita disponível\", "
        "sem deputado de referência."
    ))
    el.append(p(
        "<b>Combinação de mapas:</b> Tipo 1 alto + média de direita "
        "crescente entre 2018 e 2022 = expansão; Tipo 3 alto com "
        "componente de direita = eleitor personalista, alvo de "
        "campanha de nome próprio; cruzamento com renda e perfil "
        "ocupacional via Censo 2022 = filtro de afinidade socioeconômica."
    ))
    el.append(p(
        "<b>Entregável:</b> lista de microrregiões ordenadas por retorno "
        "esperado por unidade de esforço, com indicação de tipo de "
        "abordagem por perfil sociodemográfico (porta-a-porta, redes "
        "religiosas, evento setorial)."
    ))

    el.append(h2("7.2 Candidato veterano, trajetória PDT/PSB/PT"))
    el.append(p(
        "<b>Produto-fim:</b> mapa de retenção e ativação. Para um "
        "candidato com mais de quatro décadas de presença pública, a "
        "campanha não é de prospecção mas de <i>defesa de base</i>. As "
        "perguntas operativas são: onde a base histórica aguenta, onde "
        "está erodindo, onde já se foi."
    ))
    el.append(p(
        "<b>Tensão estratégica subjacente:</b> a régua Bolognesi-Ribeiro-Codato "
        "mostra que a posição relacional PDT/PSB/PT — que historicamente "
        "configurou um centro-fluido — efetivamente não existe mais como "
        "categoria consensual. Os escores médios são PT = 2,97 (esquerda), "
        "PSB = 4,05 (centro-esquerda), PDT = 3,92 (centro-esquerda), e o "
        "espaço entre 4,50 e 5,50 está esvaziado. A escolha tática deixa "
        "de ser entre \"manter o centro\" e \"radicalizar\"; é entre "
        "consolidar identificação com o campo esquerda ou construir "
        "candidatura pessoal por <i>cima</i> dos partidos."
    ))
    el.append(p(
        "<b>Combinação de mapas:</b> Tipo 4 sobre o histórico pessoal do "
        "candidato (1998-2022) = mapa de retenção; Tipo 3 baixo + "
        "alinhamento centro-esquerda + idade média alta da seção = base "
        "fiel residual; Tipo 2 baixo mas com migração para outro "
        "candidato do campo esquerda = base perdida para concorrente "
        "intracampo (potencialmente recuperável)."
    ))
    el.append(p(
        "<b>Entregável:</b> diagnóstico realista do teto eleitoral atual; "
        "lista de microrregiões em três tiers (defender / disputar / "
        "abandonar) com justificativa estatística por tier."
    ))

    el.append(h1("8. Achados do projeto DF que sustentam o desenho"))
    el.append(p(
        "A análise por zona realizada para o DF (1998-2022) já fornece "
        "evidência substantiva consistente com o desenho proposto. Dois "
        "achados centrais — sintetizados nos mapas a seguir — orientam "
        "as escolhas de produto."
    ))
    el.append(p(
        "<b>Mapa de volatilidade Governador 2018→2022, por local "
        "(N = 593):</b> o agregado por zona/RA mostra Plano Piloto como "
        "estável (Pedersen ≈ 0,46), mas ao nível do local de votação o "
        "padrão se inverte. Locais individuais do Plano Piloto têm "
        "Pedersen entre 0,55 e 0,71 — a baixa volatilidade agregada "
        "<i>esconde rotação intra-zona</i>: locais vizinhos trocam "
        "votos entre partidos em direções opostas e o agregado cancela. "
        "É exatamente o tipo de padrão que só aparece com granularidade "
        "de local."
    ))

    fig_path = _ROOT / "outputs/figures/mapa_volatilidade_local_governador_2018_2022.png"
    if fig_path.exists():
        el.extend(fig(
            fig_path, w_cm=15,
            legenda="Volatilidade Pedersen por local de votação — Governador, "
            "2018→2022. N = 593 locais com cobertura completa de partidos. "
            "Cores escuras = volatilidade baixa; claras = alta. Pontos "
            "concentrados no quadrante centro/sul revelam o Plano Piloto, "
            "Lago Norte/Sul, Sudoeste/Octogonal e Cruzeiro — onde a rotação "
            "intra-local mais ocorreu.",
        ))

    el.append(p(
        "<b>Mapa de volatilidade Dep. Distrital 2018→2022, por local "
        "(N = 593):</b> padrão diferente do Governador. A rotação "
        "intra-local mais alta está em Lago Sul e Sudoeste/Octogonal, "
        "com periferia oeste (Ceilândia, Samambaia, Recanto das Emas) "
        "marcadamente estável. A leitura é que a infidelidade partidária "
        "no proporcional distrital se concentra na elite educada — "
        "exatamente o eleitor que tem o repertório informacional para "
        "trocar entre nomes do mesmo campo. Nas RAs populares, o voto "
        "distrital é fiel ao partido/candidato de referência local."
    ))

    fig_path_2 = _ROOT / "outputs/figures/mapa_volatilidade_local_deputado_distrital_2018_2022.png"
    if fig_path_2.exists():
        el.extend(fig(
            fig_path_2, w_cm=15,
            legenda="Volatilidade Pedersen por local de votação — Dep. "
            "Distrital, 2018→2022. Padrão distinto do Governador: rotação "
            "intra-local concentrada em Lago Sul e Sudoeste/Octogonal "
            "(amarelo), com periferia oeste (Ceilândia, Samambaia, Recanto "
            "das Emas) marcadamente estável (roxo).",
        ))

    el.append(PageBreak())

    # ============ PARTE III ============
    el.append(parte("Parte III — Implementação"))

    el.append(h1("9. Arquitetura de dados"))
    el.append(p(
        "A granularidade de seção exige cinco alterações no esquema "
        "atual (que opera no nível zona). As alterações são aditivas — "
        "o esquema vigente permanece válido para o diagnóstico macro."
    ))
    el.append(tabela(
        [
            [_cb("Tabela"), _cb("Chave"), _cb("Volume estimado 2010-2024"), _cb("Função")],
            [_c("<b>votacao_secao</b>"), _c("(secao_id, ano, turno, cargo, candidato_id)"),
             _c("5-10 milhões de linhas"),
             _c("Granularidade efetiva do voto público")],
            [_c("<b>locais_votacao</b>"), _c("(local_id)"),
             _c("~1.500 linhas (DF), com lat/lon"),
             _c("Geocodificação para análises espaciais")],
            [_c("<b>secao_pertencimento_espacial</b>"),
             _c("(secao_id, ra_id, setor_censitario_id, voronoi_id)"),
             _c("~5.000 linhas"),
             _c("Ponte para Censo/PDAD no setor; Voronoi para microrregião")],
            [_c("<b>candidato_historico</b>"), _c("(candidato_id, ciclo, partido, cargo)"),
             _c("~30.000 linhas"),
             _c("Resolução de identidade ao longo de ciclos (Tipo 4)")],
            [_c("<b>volatilidade_mv</b>"), _c("(secao_id, ciclo_a, ciclo_b, tipo, valor)"),
             _c("Materializada por demanda"),
             _c("Pré-cálculo das quatro famílias de volatilidade")],
        ],
        col_widths=[3.5 * cm, 4.5 * cm, 3.8 * cm, 4.5 * cm],
    ))
    el.append(Spacer(1, 0.3 * cm))
    el.append(p(
        "Banco recomendado: MySQL 8.0+ com particionamento por ano "
        "(votacao_secao) e índices em (secao_id, cargo) e "
        "(candidato_id, ciclo). Volume cabe em hardware modesto; o "
        "gargalo será de ingestão e validação, não de armazenamento."
    ))

    el.append(h1("10. Cronograma estimado"))
    el.append(tabela(
        [
            [_cb("Fase"), _cb("Conteúdo"), _cb("Tempo"), _cb("Dependências")],
            [_c("1"), _c("Ingestão de boletins de urna por seção 2010-2024 + "
                "validação de totais contra agregados oficiais"),
             _cc("4-6 semanas"), _c("Acesso à infraestrutura TSE; espaço de disco")],
            [_c("2"), _c("Geocodificação de locais de votação + reconciliação "
                "histórica (locais mudam de ciclo para ciclo)"),
             _cc("2-3 semanas"),
             _c("Cadastro TSE; geocoder (IBGE ou OSM); revisão manual")],
            [_c("3"), _c("Construção das microrregiões Voronoi + spatial joins "
                "com Censo 2022 e PDAD"),
             _cc("2 semanas"),
             _c("Fase 2 completa; geobr; shapefiles IBGE")],
            [_c("4"), _c("Cálculo das quatro famílias de volatilidade; "
                "materialização em views"),
             _cc("1-2 semanas"), _c("Fase 1 completa")],
            [_c("5"), _c("Dashboard interativo (Streamlit ou similar) + "
                "geração de relatórios por cliente"),
             _cc("3-4 semanas"), _c("Fases 1-4 completas")],
        ],
        col_widths=[1 * cm, 7 * cm, 2.4 * cm, 5.8 * cm],
    ))
    el.append(Spacer(1, 0.3 * cm))
    el.append(p(
        "Total: 12-17 semanas para a primeira entrega completa. A fase "
        "1 é o gargalo real — boletins de urna por seção exigem "
        "manuseio de arquivos por UF e por ciclo, com schema que muda "
        "(adição de federações em 2022, mudanças de DS_SIT_TOT_TURNO, "
        "etc.). Iniciar a implementação antes do cliente fechar prazo "
        "é, na prática, a única forma de ter folga negocial."
    ))

    el.append(h1("11. Considerações éticas e contratuais"))
    el.append(p(
        "Três cláusulas devem aparecer em qualquer contrato de "
        "diagnóstico eleitoral com este produto."
    ))
    el.append(p(
        "<b>Agregação obrigatória.</b> Toda análise é entregue no nível "
        "de seção ou microrregião. Não há, em nenhuma etapa, "
        "identificação ou reconstrução individual de eleitores. Cruzar "
        "voto agregado de seção com setor censitário (Censo 2022, PDAD) "
        "é permitido e é o produto. Cruzar dado de seção com base de "
        "dados nominais (cadastros, redes sociais, leads de campanha) "
        "para inferir voto individual <b>não é</b>, e é vedado pela "
        "LGPD e pela ética profissional."
    ))
    el.append(p(
        "<b>Separação diagnóstico/persuasão.</b> O produto diagnostica "
        "padrões. Como o cliente decide agir sobre o diagnóstico — "
        "campanha de porta-a-porta, comunicação digital, alocação "
        "orçamentária — é responsabilidade dele. A consultoria não "
        "produz peças de campanha, não opera contas, não compra mídia "
        "direcionada. Esta separação protege contra acusações de "
        "operação política e mantém o produto utilizável por "
        "múltiplos clientes em ciclos sucessivos."
    ))
    el.append(p(
        "<b>Vedações contratuais expressas.</b> O contrato veda o uso "
        "do diagnóstico para: microtargeting manipulativo (mensagens "
        "diferenciadas com conteúdo factualmente incompatível para "
        "públicos sobrepostos); produção ou amplificação de "
        "desinformação; e qualquer ação de supressão de voto. Clientes "
        "que recusam essas cláusulas são exatamente o tipo de cliente "
        "que cria, no médio prazo, exposição reputacional e jurídica "
        "para a consultoria."
    ))

    el.append(h1("12. Referências"))
    el.append(p(
        "Bartolini, S. & Mair, P. (1990). <i>Identity, Competition, and "
        "Electoral Availability: The Stabilization of European "
        "Electorates, 1885-1985</i>. Cambridge University Press."
    ))
    el.append(p(
        "Bobbio, N. (1995). <i>Direita e esquerda: razões e significados "
        "de uma distinção política</i>. São Paulo: Editora UNESP."
    ))
    el.append(p(
        "Bolognesi, B., Ribeiro, E. A. & Codato, A. (2023). \"Uma nova "
        "classificação ideológica dos partidos políticos brasileiros\". "
        "<i>Dados</i>, vol. 66, n. 2, e20210164."
    ))
    el.append(p(
        "Pedersen, M. N. (1979). \"The Dynamics of European Party "
        "Systems: Changing Patterns of Electoral Volatility\". "
        "<i>European Journal of Political Research</i>, 7(1): 1-26."
    ))
    el.append(p(
        "Santos, W. G. dos (1979). <i>Cidadania e Justiça: a política "
        "social na ordem brasileira</i>. Rio de Janeiro: Campus."
    ))
    el.append(p(
        "Singer, A. (2012). <i>Os Sentidos do Lulismo: reforma gradual "
        "e pacto conservador</i>. São Paulo: Companhia das Letras."
    ))

    return el


def main() -> None:
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(SAIDA),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        title="Diagnóstico Estratégico Eleitoral — DF",
    )
    doc.build(conteudo())
    print(f"PDF gerado: {SAIDA}")


if __name__ == "__main__":
    main()
