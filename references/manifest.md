# Manifesto do compositor

Um JSON por projeto. `assets_dir` e `output_dir` são resolvidos a partir da pasta do manifesto, e caminhos absolutos também funcionam. O compositor não gera os motivos: forneça PNGs com transparência real.

```json
{
  "name": "jardim",
  "canvas": {"width": 2400, "height": 2400, "dpi": 300, "background": "#fdfbf7"},
  "repeat": "half-drop",
  "assets_dir": "assets",
  "output_dir": "output",
  "motifs": [
    {"name": "Flor 01", "file": "flor.png", "center": [620, 740], "width": 680, "rotation": -12},
    {"name": "Flor 02", "file": "flor.png", "center": [2050, 1980], "width": 520, "rotation": 23}
  ],
  "border": {"file": "barrado.png", "bottom_margin": 24},
  "texture": {"file": "linho.png", "opacity": 0.3, "blend": "multiply", "scale": 1, "include_in_repeat": false}
}
```

## Campos

| Campo | Obrigatório | Regra |
|---|---|---|
| `name` | sim | Letras, números, `_` ou `-`. Prefixo dos arquivos de saída |
| `canvas.width`, `canvas.height` | sim | De 64 a 30000 px |
| `canvas.dpi` | não | Padrão 300 |
| `canvas.background` | não | Cor do fundo, padrão `#ffffff` |
| `repeat` | não | `straight` (padrão), `half-drop` (altura par) ou `brick` (largura par) |
| `assets_dir`, `output_dir` | sim | Pastas de entrada e saída |
| `motifs[]` | sim | Cada item vira uma ou mais camadas |
| `motifs[].name` | sim | Nome único da camada |
| `motifs[].file` | sim | PNG com alfa dentro de `assets_dir` |
| `motifs[].center` | sim | `[x, y]` em px no módulo |
| `motifs[].width` | sim | Largura final em px. Acima do lado menor do módulo, o compositor avisa |
| `motifs[].rotation` | não | Graus, sentido anti-horário |
| `border.file` | não | Barrado com alfa, redimensionado para a largura do módulo |
| `border.bottom_margin` | não | Distância da base em px |
| `texture.file` | não | Imagem da textura, que pode ser opaca |
| `texture.opacity` | não | De 0 a 1, padrão 1. Vira a opacidade da camada no PSD |
| `texture.blend` | não | `multiply` (padrão) ou `normal` |
| `texture.scale` | não | Escala do ladrilho da textura, padrão 1 |
| `texture.include_in_repeat` | não | `false` (padrão): textura só na colocação. `true`: entra no módulo; o tamanho da textura precisa dividir o módulo |

## Saídas

| Arquivo | Conteúdo |
|---|---|
| `<name>_rapport-tile.png` / `.psd` | Módulo contínuo (fundo + motivos, e textura se `include_in_repeat`) |
| `<name>_rapport-preview-2x2.jpg` | Prévia de 2 × 2 módulos montada com o tipo de repetição real |
| `<name>_placement.png` / `.psd` | Arte de colocação: módulo + barrado + textura |
| `<name>_barrado.png` | Barrado transparente separado |
| `<name>_checks.json` | Métricas, avisos e verificação dos PSDs |

## Camadas do PSD (de baixo para cima)

`Background`, um motivo por camada na ordem do manifesto (quem cruza a borda vira "Nome (peça N de M)"), `Hem Border`, `Texture`. O PSD é RGB 8 bits com compressão RLE e não usa grupos.

## Verificação (`--verify`)

Para cada PSD: lê com psd-tools, renderiza as camadas (não a imagem achatada guardada no arquivo) e compara com o PNG; confere a contagem de camadas e qual está no topo; decodifica a imagem achatada com um segundo leitor (Pillow). Se algo falhar, o script sai com erro e o motivo fica em `verify_*` no `checks.json`.

Os números de emenda são diagnóstico. Inspecione também a prévia, porque textura e motivos de alto contraste elevam a diferença média mesmo com o encaixe correto.

## Ambiente

Testado com Python 3.14.2, Pillow 13.0.0, NumPy 2.5.5, pytoshop 1.2.1 e psd-tools 1.26.1. O `pytoshop` precisa de `six` (declarado no `requirements.txt`). O compositor traz o próprio codificador RLE, então não depende da extensão compilada do `pytoshop`.
