# Manifesto do compositor

Use um JSON por projeto. Caminhos em `assets_dir` e `output_dir` são resolvidos a partir do diretório do manifesto; caminhos absolutos também funcionam. Cada entrada em `motifs` vira uma camada independente no PSD. O compositor não gera os motivos: forneça PNGs com transparência verdadeira.

```json
{
  "name": "jardim",
  "canvas": {"width": 2400, "height": 2400, "dpi": 300, "background": "#fdfbf7"},
  "assets_dir": "assets",
  "output_dir": "output",
  "motifs": [
    {"name": "Flor 01", "file": "flor.png", "center": [620, 740], "width": 680, "rotation": -12},
    {"name": "Flor 02", "file": "flor.png", "center": [2050, 1980], "width": 520, "rotation": 23}
  ],
  "border": {"file": "barrado.png", "bottom_margin": 24},
  "texture": {"file": "linho.png", "opacity": 0.18, "include_in_repeat": false}
}
```

Campos obrigatórios: `name`, `canvas.width`, `canvas.height`, `assets_dir`, `output_dir`, `motifs`. Em cada motivo: `name`, `file`, `center`, `width`; `rotation` é opcional e usa graus. `border` e `texture` são opcionais. O barrado é redimensionado para a largura do módulo e incluído só na arte de colocação. `texture.include_in_repeat` só deve ser usado se a imagem da textura for comprovadamente contínua nas duas bordas; o padrão é `false`.

O compositor escreve `<name>_rapport-tile.png`, `<name>_rapport-preview-2x2.jpg`, `<name>_placement.png`, `<name>_placement.psd`, `<name>_checks.json` e, quando fornecido, `<name>_barrado.png`. Execute `python scripts/compose_psd.py --manifest caminho/do/manifesto.json --verify` para reler o PSD com psd-tools e comparar sua composição com o PNG. Os números de emenda são um diagnóstico; inspecione também a prévia, pois textura e motivos de alto contraste podem elevar a diferença média mesmo com posicionamento correto.

Bibliotecas necessárias: Pillow para PNG/transformações, NumPy para canais e métricas, pytoshop para gravar camadas PSD; psd-tools para leitura e verificação. O conjunto Pillow 12.3.0, NumPy 2.4.0, pytoshop 1.2.1 e psd-tools 1.26.1 funcionou no ambiente local com Python 3.14.2. Isso registra um ambiente verificado, não uma exigência de versões fixas.
