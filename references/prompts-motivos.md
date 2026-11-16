# Prompts para gerar motivos, barrado e textura

Escreva o prompt em inglês e gere cada motivo numa chamada separada. Repita em todo prompt o bloco de estilo e paleta, para a série sair coerente.

## Bloco de estilo (repita em todos)

```
STYLE: <técnica: watercolor and gouache illustration | flat vector-like gouache | fine ink line with watercolor wash | vintage botanical engraving>, consistent hand, consistent line weight across the series.
PALETTE: <cores com hex>, nothing outside this palette.
```

## Motivo isolado

```
Single isolated <motif: blue six-petal daisy with orange center | swallow in flight | tropical orchid spray> for a textile print, centered, whole motif visible with a generous transparent margin on every side.
<STYLE block>
<PALETTE block>
Fully transparent background (real alpha channel). No fabric, no paper, no ground, no cast shadow, no frame, no text, no watermark. Clean edges with natural soft brush borders, no white halo.
```

Parâmetros: na API, `background: "transparent"` com PNG. No Codex, peça a transparência à ferramenta `image_gen`. Na CLI do Codex, o `gpt-image-2` não faz fundo transparente; pergunte antes de usar o `gpt-image-1.5`.

## Família de motivos (variações do mesmo)

Gere o motivo principal, aprove, e use-o como imagem de referência nas variações:

```
Image 1: approved motif, style reference only.
Create a new isolated motif in exactly the same style, palette and line weight: <variation: the same daisy seen from the side, half-open bud | a smaller three-leaf sprig>.
Fully transparent background, no shadow, no text, generous transparent margin.
```

## Barrado (faixa de bainha)

```
Horizontal ornamental hem border strip for a dress, very wide and short (about 10:1), <description: row of blue and orange flowers with green leaves resting on a thin baseline>, motifs touching the bottom edge, top edge open and airy.
<STYLE block>
<PALETTE block>
Fully transparent background, no fabric, no shadow, no text.
```

Gere em 1536x1024 ou no maior formato largo disponível e recorte a faixa. O compositor redimensiona para a largura do módulo.

## Textura contínua (só se for entrar no rapport)

```
Seamless tileable texture of <fine linen weave | cotton twill | cold-press watercolor paper grain>, neutral light grey, even lighting, no vignette, no objects, no shadows, no text. Must tile perfectly on all four edges.
```

Confira a continuidade antes de usar: o compositor avisa se a textura não emenda ou se o tamanho dela não divide o módulo. Para textura só de apresentação, a emenda não importa.

## Conferência de cada motivo

- O alfa é real (o compositor recusa PNG sem alfa)?
- Há margem transparente nos quatro lados, sem nada cortado?
- Não há halo branco ou cinza na borda?
- O traço e a paleta batem com os outros motivos da série?
