"""Create a small example project (transparent motifs, hem border, seamless texture).

Usage:
    python scripts/criar_exemplo.py examples/jardim
    python scripts/compose_psd.py --manifest examples/jardim/manifest.json --verify
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def flower(size: int, petal: tuple, center: tuple) -> Image.Image:
    img = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(img)
    c, r = size / 2, size * 0.18
    for i in range(6):
        a = i * math.pi / 3
        x, y = c + size * 0.24 * math.cos(a), c + size * 0.24 * math.sin(a)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=petal)
    draw.ellipse((c - size * 0.12, c - size * 0.12, c + size * 0.12, c + size * 0.12), fill=center)
    return img


def leaf(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size // 2))
    ImageDraw.Draw(img).ellipse((4, 4, size - 4, size // 2 - 4), fill=(86, 150, 90, 255))
    return img


def border(width: int, height: int) -> Image.Image:
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)
    step = height
    for x in range(0, width, step):
        draw.ellipse((x + 8, 8, x + step - 8, height - 8), fill=(200, 60, 70, 255))
    return img


def linen(size: int) -> Image.Image:
    rng = np.random.default_rng(7)
    noise = rng.normal(235, 12, (size, size)).clip(0, 255)
    weave = (np.sin(np.arange(size) * 2 * math.pi / 8) * 6)
    tex = (noise + weave[None, :] + weave[:, None]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([tex] * 3, axis=2), "RGB")


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/jardim")
    assets = target / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    flower(600, (110, 140, 240, 255), (235, 140, 60, 255)).save(assets / "flor-azul.png")
    flower(600, (240, 150, 170, 255), (250, 220, 90, 255)).save(assets / "flor-rosa.png")
    leaf(400).save(assets / "folha.png")
    border(2400, 240).save(assets / "barrado.png")
    linen(200).save(assets / "linho.png")  # 200 divides the 2400 px module
    manifest = {
        "name": "jardim",
        "canvas": {"width": 2400, "height": 2400, "dpi": 300, "background": "#dff08f"},
        "repeat": "half-drop",
        "assets_dir": "assets",
        "output_dir": "output",
        "motifs": [
            {"name": "Flor azul 01", "file": "flor-azul.png", "center": [2320, 2300], "width": 520, "rotation": -12},
            {"name": "Flor azul 02", "file": "flor-azul.png", "center": [700, 600], "width": 380, "rotation": 20},
            {"name": "Flor rosa 01", "file": "flor-rosa.png", "center": [1500, 1200], "width": 460},
            {"name": "Folha 01", "file": "folha.png", "center": [400, 1600], "width": 300, "rotation": 35},
            {"name": "Folha 02", "file": "folha.png", "center": [1800, 400], "width": 260, "rotation": -25},
        ],
        "border": {"file": "barrado.png", "bottom_margin": 24},
        "texture": {"file": "linho.png", "opacity": 0.35, "blend": "multiply",
                    "scale": 1, "include_in_repeat": False},
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exemplo criado em {target}")


if __name__ == "__main__":
    main()
