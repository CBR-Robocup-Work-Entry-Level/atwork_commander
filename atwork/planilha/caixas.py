"""Caixas de selecao nativas do Excel ("checkbox na celula"), gravadas a mao.

O recurso e' do Excel 365 (2024) e funciona no Windows, Mac, web e celular:
um toque marca e desmarca. O openpyxl nao o conhece, entao a planilha e' salva
normalmente e o .xlsx (um zip de XMLs) e' ajustado depois, imitando o que o
proprio Excel grava:

- a celula guarda VERDADEIRO/FALSO (t="b");
- o estilo dela leva a extensao `xfComplement`, que aponta para o pacote
  `featurePropertyBag.xml` declarando o controle "Checkbox";
- o pacote e' registrado em [Content_Types].xml e em workbook.xml.rels.

Para saber QUAIS estilos viram caixa, as celulas de caixa recebem um formato de
numero exclusivo (FORMATO_MARCA). Ele nao muda nada na tela: o Excel nunca
aplica formato de numero a VERDADEIRO/FALSO. Num programa sem o recurso a
celula aparece como VERDADEIRO/FALSO, e as formulas continuam funcionando.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

FORMATO_MARCA = '0;-0;0;"caixa"'

PARTE = "xl/featurePropertyBag/featurePropertyBag.xml"
CONTEUDO_PARTE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<FeaturePropertyBags xmlns="http://schemas.microsoft.com/office/spreadsheetml/2022/'
    'featurepropertybag"><bag type="Checkbox"/><bag type="XFControls"><bagId k="CellControl">'
    '0</bagId></bag><bag type="XFComplement"><bagId k="XFControls">1</bagId></bag>'
    '<bag type="XFComplements" extRef="XFComplementsMapperExtRef"><a k="MappedFeaturePropertyBags">'
    '<bagId>2</bagId></a></bag></FeaturePropertyBags>'
)
TIPO_CONTEUDO = (
    f'<Override PartName="/{PARTE}" ContentType="application/vnd.ms-excel.featurepropertybag+xml"/>'
)
TIPO_RELACAO = "http://schemas.microsoft.com/office/2022/11/relationships/FeaturePropertyBag"
EXTENSAO_XF = (
    '<extLst><ext uri="{C7286773-470A-42A8-94C5-96B5CB345126}" '
    'xmlns:xfpb="http://schemas.microsoft.com/office/spreadsheetml/2022/featurepropertybag">'
    '<xfpb:xfComplement i="0"/></ext></extLst>'
)


def _marcar_estilos(styles: str) -> tuple[str, int]:
    """Poe a extensao de caixa em todo <xf> de cellXfs que usa o formato-marca."""
    marca = FORMATO_MARCA.replace('"', "&quot;")
    ids = [
        m.group(1)
        for m in re.finditer(r'<numFmt numFmtId="(\d+)" formatCode="([^"]*)"\s*/>', styles)
        if m.group(2) in (marca, FORMATO_MARCA)
    ]
    if not ids:
        return styles, 0

    inicio = styles.index("<cellXfs")
    fim = styles.index("</cellXfs>", inicio)
    bloco = styles[inicio:fim]
    marcados = 0

    def trocar(m: re.Match) -> str:
        nonlocal marcados
        xf = m.group(0)
        num = re.search(r'numFmtId="(\d+)"', xf)
        if num is None or num.group(1) not in ids or "xfComplement" in xf:
            return xf
        marcados += 1
        if xf.endswith("/>"):
            return xf[:-2] + ">" + EXTENSAO_XF + "</xf>"
        return xf[: -len("</xf>")] + EXTENSAO_XF + "</xf>"

    bloco = re.sub(r"<xf\b[^>]*/>|<xf\b[^>]*>.*?</xf>", trocar, bloco, flags=re.S)
    return styles[:inicio] + bloco + styles[fim:], marcados


def _registrar(partes: dict[str, bytes]) -> None:
    tipos = partes["[Content_Types].xml"].decode("utf-8")
    if PARTE not in tipos:
        tipos = tipos.replace("</Types>", TIPO_CONTEUDO + "</Types>")
        partes["[Content_Types].xml"] = tipos.encode("utf-8")

    rels = partes["xl/_rels/workbook.xml.rels"].decode("utf-8")
    if TIPO_RELACAO not in rels:
        usados = {int(n) for n in re.findall(r'Id="rId(\d+)"', rels)}
        novo = max(usados, default=0) + 1
        rels = rels.replace(
            "</Relationships>",
            f'<Relationship Id="rId{novo}" Type="{TIPO_RELACAO}" '
            f'Target="featurePropertyBag/featurePropertyBag.xml"/></Relationships>',
        )
        partes["xl/_rels/workbook.xml.rels"] = rels.encode("utf-8")
    partes[PARTE] = CONTEUDO_PARTE.encode("utf-8")


def aplicar(caminho: Path | str) -> int:
    """Transforma em caixa de selecao as celulas com o formato-marca. Devolve quantos
    estilos foram marcados (0 = a planilha nao tinha caixa nenhuma)."""
    caminho = Path(caminho)
    with zipfile.ZipFile(caminho) as z:
        ordem = z.namelist()
        partes = {nome: z.read(nome) for nome in ordem}

    styles, marcados = _marcar_estilos(partes["xl/styles.xml"].decode("utf-8"))
    if not marcados:
        return 0
    partes["xl/styles.xml"] = styles.encode("utf-8")
    _registrar(partes)
    if PARTE not in ordem:
        ordem.append(PARTE)

    temporario = caminho.with_suffix(".tmp.xlsx")
    with zipfile.ZipFile(temporario, "w", zipfile.ZIP_DEFLATED) as z:
        for nome in ordem:
            z.writestr(nome, partes[nome])
    temporario.replace(caminho)
    return marcados
