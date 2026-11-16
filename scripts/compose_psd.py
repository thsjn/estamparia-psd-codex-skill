"""Compose transparent motifs into a wrapped textile tile and layered PSD."""
from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageColor
from pytoshop import enums
import pytoshop.util as psd_util
from pytoshop.image_data import ImageData
from pytoshop.image_resources import GenericImageResourceBlock
from pytoshop.user.nested_layers import Image as PSDLayer, nested_layers_to_psd


def path_from(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def open_asset(path: Path, *, require_alpha: bool = True) -> Image.Image:
    source = Image.open(path)
    if require_alpha and "A" not in source.getbands():
        raise ValueError(f"Motivo sem canal alfa: {path}")
    image = source.convert("RGBA")
    if require_alpha and image.getchannel("A").getextrema()[0] == 255:
        raise ValueError(f"Motivo sem áreas transparentes: {path}")
    alpha = np.asarray(image.getchannel("A"))
    alpha = np.where(alpha < 12, 0, alpha).astype(np.uint8)
    image.putalpha(Image.fromarray(alpha, "L"))
    box = image.getbbox()
    if not box:
        raise ValueError(f"Imagem vazia: {path}")
    return image.crop(box)


def resized_to_width(image: Image.Image, width: int) -> Image.Image:
    if width < 1:
        raise ValueError("A largura de um motivo deve ser positiva")
    height = max(1, round(image.height * width / image.width))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def clipped_paste(canvas: Image.Image, image: Image.Image, x: int, y: int) -> None:
    left, top = max(0, x), max(0, y)
    right, bottom = min(canvas.width, x + image.width), min(canvas.height, y + image.height)
    if left < right and top < bottom:
        canvas.alpha_composite(image.crop((left - x, top - y, right - x, bottom - y)), (left, top))


def wrapped_motif(image: Image.Image, center: list[int], width: int,
                  rotation: float, size: tuple[int, int]) -> Image.Image:
    image = resized_to_width(image, width)
    if rotation:
        image = image.rotate(rotation, Image.Resampling.BICUBIC, expand=True)
    tile = Image.new("RGBA", size)
    x = round(center[0] - image.width / 2)
    y = round(center[1] - image.height / 2)
    for dx in (-size[0], 0, size[0]):
        for dy in (-size[1], 0, size[1]):
            clipped_paste(tile, image, x + dx, y + dy)
    return tile


def psd_layer(name: str, image: Image.Image) -> PSDLayer:
    box = image.getbbox()
    if not box:
        raise ValueError(f"Camada vazia: {name}")
    crop = np.asarray(image.crop(box).convert("RGBA"))
    return PSDLayer(
        name=name,
        channels={0: crop[:, :, 0], 1: crop[:, :, 1],
                  2: crop[:, :, 2], -1: crop[:, :, 3]},
        top=box[1], left=box[0], bottom=box[3], right=box[2],
        color_mode=enums.ColorMode.rgb,
    )


def write_psd(layers: list[PSDLayer], composite: Image.Image,
              path: Path, dpi: int) -> None:
    # pytoshop 1.2.1 needs this encoding correction on current Python.
    psd_util.encode_unicode_string = lambda value: (
        struct.pack(">I", len(value)) + value.encode("utf_16_be")
    )
    psd = nested_layers_to_psd(
        layers, enums.ColorMode.rgb, compression=enums.Compression.zip,
        depth=enums.ColorDepth.depth8, size=composite.size,
    )
    rgb = np.asarray(composite.convert("RGB"))
    psd.image_data = ImageData(channels=np.moveaxis(rgb, 2, 0),
                               compression=enums.Compression.zip)
    resolution = struct.pack(">IHHIHH", dpi * 65536, 1, 1,
                             dpi * 65536, 1, 1)
    psd.image_resources.blocks.append(
        GenericImageResourceBlock(resource_id=1005, data=resolution)
    )
    with path.open("wb") as stream:
        psd.write(stream)


def seam_metrics(image: Image.Image) -> dict[str, float | bool]:
    arr = np.asarray(image.convert("RGB"))
    width, height = image.size
    xs = np.unique(np.linspace(0, width - 2, min(128, width - 1), dtype=int))
    ys = np.unique(np.linspace(0, height - 2, min(128, height - 1), dtype=int))
    vertical = float(np.abs(arr[:, 0].astype(np.int16) - arr[:, -1]).mean())
    horizontal = float(np.abs(arr[0].astype(np.int16) - arr[-1]).mean())
    inner_v = float(np.abs(arr[:, xs].astype(np.int16) - arr[:, xs + 1]).mean())
    inner_h = float(np.abs(arr[ys].astype(np.int16) - arr[ys + 1]).mean())
    return {
        "seam_vertical": vertical,
        "seam_horizontal": horizontal,
        "interior_vertical_sample": inner_v,
        "interior_horizontal_sample": inner_h,
        "vertical_diagnostic_pass": vertical <= max(1, 1.5 * inner_v),
        "horizontal_diagnostic_pass": horizontal <= max(1, 1.5 * inner_h),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--verify", action="store_true",
                        help="Read PSD with psd-tools and compare composite to placement PNG")
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    config = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    name = str(config["name"])
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
        raise ValueError("name deve conter apenas letras, números, _ ou -")
    canvas = config["canvas"]
    size = (int(canvas["width"]), int(canvas["height"]))
    if not all(64 <= dimension <= 30000 for dimension in size):
        raise ValueError("Cada dimensão deve estar entre 64 e 30000 px")
    dpi = int(canvas.get("dpi", 300))
    if dpi < 1:
        raise ValueError("dpi deve ser positivo")
    color = ImageColor.getrgb(canvas.get("background", "#ffffff"))
    assets = path_from(base, config["assets_dir"])
    out = path_from(base, config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)

    repeat = Image.new("RGBA", size, color + (255,))
    layers = [psd_layer("Background", repeat)]
    seen_names: set[str] = set()
    motifs = config["motifs"]
    if not motifs:
        raise ValueError("motifs não pode ficar vazio")
    for item in motifs:
        layer_name = str(item["name"])
        if layer_name in seen_names:
            raise ValueError(f"Nome de camada duplicado: {layer_name}")
        seen_names.add(layer_name)
        center = item["center"]
        if len(center) != 2:
            raise ValueError(f"center inválido: {layer_name}")
        image = open_asset(assets / item["file"])
        layer = wrapped_motif(image, center, int(item["width"]),
                              float(item.get("rotation", 0)), size)
        layers.append(psd_layer(layer_name, layer))
        repeat.alpha_composite(layer)

    texture = config.get("texture")
    texture_layer = None
    if texture:
        source = Image.open(assets / texture["file"]).convert("RGBA")
        texture_layer = source.resize(size, Image.Resampling.LANCZOS)
        opacity = float(texture.get("opacity", 1))
        if not 0 < opacity <= 1:
            raise ValueError("texture.opacity deve ser maior que 0 e até 1")
        alpha = texture_layer.getchannel("A").point(lambda value: round(value * opacity))
        texture_layer.putalpha(alpha)
        if texture.get("include_in_repeat", False):
            layers.append(psd_layer("Texture", texture_layer))
            repeat.alpha_composite(texture_layer)
            texture_layer = None

    tile = repeat.convert("RGB")
    tile.save(out / f"{name}_rapport-tile.png", dpi=(dpi, dpi), compress_level=3)
    scale = min(1, 1600 / max(size))
    small_size = (max(1, round(size[0] * scale)), max(1, round(size[1] * scale)))
    small = tile.resize(small_size, Image.Resampling.LANCZOS)
    preview = Image.new("RGB", (small.width * 2, small.height * 2))
    for x in (0, small.width):
        for y in (0, small.height):
            preview.paste(small, (x, y))
    preview.save(out / f"{name}_rapport-preview-2x2.jpg", quality=90,
                 subsampling=0, dpi=(dpi, dpi))

    placement = repeat.copy()
    border_config = config.get("border")
    if border_config:
        strip = resized_to_width(open_asset(assets / border_config["file"]), size[0])
        bottom_margin = int(border_config.get("bottom_margin", 0))
        if strip.height + bottom_margin > size[1] or bottom_margin < 0:
            raise ValueError("Barrado não cabe no módulo")
        strip.save(out / f"{name}_barrado.png", dpi=(dpi, dpi), compress_level=3)
        border = Image.new("RGBA", size)
        border.alpha_composite(strip, (0, size[1] - strip.height - bottom_margin))
        layers.append(psd_layer("Hem Border", border))
        placement.alpha_composite(border)
    if texture_layer is not None:
        layers.append(psd_layer("Placement Texture", texture_layer))
        placement.alpha_composite(texture_layer)

    placement_rgb = placement.convert("RGB")
    png_path = out / f"{name}_placement.png"
    psd_path = out / f"{name}_placement.psd"
    placement_rgb.save(png_path, dpi=(dpi, dpi), compress_level=3)
    write_psd(layers, placement_rgb, psd_path, dpi)
    checks = {"size": list(size), "dpi": dpi, "motif_layers": len(motifs),
              "total_layers": len(layers), "has_border": bool(border_config),
              "has_texture": bool(texture), **seam_metrics(tile)}
    if args.verify:
        from psd_tools import PSDImage
        psd = PSDImage.open(psd_path)
        checks["psd_layers_read"] = len(psd)
        checks["psd_composite_matches_png"] = (
            ImageChops.difference(psd.composite().convert("RGB"),
                                  placement_rgb).getbbox() is None
        )
        if len(psd) != len(layers) or not checks["psd_composite_matches_png"]:
            raise RuntimeError("Falha na verificação do PSD")
    (out / f"{name}_checks.json").write_text(
        json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == "__main__":
    main()
