"""Compose transparent motifs into a wrapped textile tile and layered PSDs.

Repeats: straight, half-drop and brick. Every motif occurrence becomes its own
PSD layer; occurrences that cross the tile edge become adjacent layers, one
per piece. Layers are RLE compressed (what Photoshop writes for 8-bit). Outputs a rapport tile (PNG + PSD), a 2x2 preview that respects the
repeat type, a placement artwork (PNG + PSD) with optional hem border and
texture, and a checks report.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageColor
from pytoshop import enums
import pytoshop.util as psd_util
from pytoshop.image_data import ImageData
from pytoshop.image_resources import GenericImageResourceBlock
from pytoshop.user.nested_layers import Image as PSDLayer
from pytoshop.user.nested_layers import nested_layers_to_psd

REPEAT_TYPES = ("straight", "half-drop", "brick")
BLEND_MODES = {"normal": enums.BlendMode.normal, "multiply": enums.BlendMode.multiply}
VERIFY_TOLERANCE = 3  # max channel difference accepted between PSD render and PNG


# ---------------------------------------------------------------- helpers

def path_from(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def open_asset(path: Path, *, require_alpha: bool = True) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
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


def lattice(repeat: str, size: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return the two translation vectors of the repeat."""
    w, h = size
    if repeat == "straight":
        return (w, 0), (0, h)
    if repeat == "half-drop":
        return (w, h // 2), (0, h)
    return (w, 0), (w // 2, h)  # brick


def lattice_offsets(repeat: str, size: tuple[int, int], reach: int = 2):
    a, b = lattice(repeat, size)
    for i in range(-reach, reach + 1):
        for j in range(-reach, reach + 1):
            yield i * a[0] + j * b[0], i * a[1] + j * b[1]


def motif_pieces(image: Image.Image, center: list[float], width: int, rotation: float,
                 size: tuple[int, int], repeat: str) -> list[Image.Image]:
    """One full-canvas RGBA image per piece of the occurrence inside the tile."""
    image = resized_to_width(image, width)
    if rotation:
        image = image.rotate(rotation, Image.Resampling.BICUBIC, expand=True)
    x0 = round(center[0] - image.width / 2)
    y0 = round(center[1] - image.height / 2)
    pieces = []
    for dx, dy in lattice_offsets(repeat, size):
        x, y = x0 + dx, y0 + dy
        left, top = max(0, x), max(0, y)
        right, bottom = min(size[0], x + image.width), min(size[1], y + image.height)
        if left >= right or top >= bottom:
            continue
        crop = image.crop((left - x, top - y, right - x, bottom - y))
        if crop.getbbox() is None:
            continue
        piece = Image.new("RGBA", size)
        piece.alpha_composite(crop, (left, top))
        pieces.append(piece)
    return pieces


def tiled_texture(source: Image.Image, size: tuple[int, int], scale: float) -> Image.Image:
    if scale != 1:
        source = source.resize((max(1, round(source.width * scale)),
                                max(1, round(source.height * scale))),
                               Image.Resampling.LANCZOS)
    out = Image.new("RGBA", size)
    for x in range(0, size[0], source.width):
        for y in range(0, size[1], source.height):
            out.paste(source, (x, y))
    return out


def apply_texture(base: Image.Image, texture: Image.Image, opacity: float, blend: str) -> Image.Image:
    """Composite texture over an opaque base exactly as Photoshop layer opacity would."""
    base_rgb = np.asarray(base.convert("RGB")).astype(np.float64)
    tex = np.asarray(texture).astype(np.float64)
    alpha = (tex[:, :, 3:4] / 255.0) * opacity
    top = tex[:, :, :3]
    if blend == "multiply":
        top = base_rgb * top / 255.0
    result = base_rgb * (1 - alpha) + top * alpha
    out = Image.fromarray(np.clip(np.round(result), 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return out


# ---------------------------------------------------------------- PSD

def psd_image_layer(name: str, image: Image.Image, *, opacity: int = 255,
                    blend: str = "normal") -> PSDLayer:
    box = image.getbbox()
    if not box:
        raise ValueError(f"Camada vazia: {name}")
    crop = np.asarray(image.crop(box).convert("RGBA"))
    return PSDLayer(
        name=name,
        opacity=opacity,
        blend_mode=BLEND_MODES[blend],
        channels={0: crop[:, :, 0], 1: crop[:, :, 1], 2: crop[:, :, 2], -1: crop[:, :, 3]},
        top=box[1], left=box[0], bottom=box[3], right=box[2],
        color_mode=enums.ColorMode.rgb,
    )


def motif_layers(name: str, pieces: list[Image.Image]) -> list[PSDLayer]:
    """One layer per piece, kept adjacent. No layer groups: pytoshop writes
    group dividers with zero channels, which is not how Photoshop writes them
    and is a compatibility risk for other editors."""
    if len(pieces) == 1:
        return [psd_image_layer(name, pieces[0])]
    total = len(pieces)
    return [psd_image_layer(f"{name} (peça {i} de {total})", piece)
            for i, piece in enumerate(pieces, 1)]


def ascii_name(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return plain[:255] or "Layer"


def packbits_encode(row) -> bytes:
    """PackBits (PSD RLE) encoder. Python-level work is proportional to the
    number of runs of 3+ equal bytes, not to the row length."""
    data = np.ascontiguousarray(row, dtype=np.uint8).ravel()
    size = data.size
    if size == 0:
        return b""
    out = bytearray()

    def literal(start: int, stop: int) -> None:
        while start < stop:
            count = min(128, stop - start)
            out.append(count - 1)
            out.extend(data[start:start + count].tobytes())
            start += count

    change = np.flatnonzero(np.diff(data)) + 1
    starts = np.concatenate(([0], change))
    ends = np.concatenate((change, [size]))
    pending = 0
    for index in np.flatnonzero(ends - starts >= 3):
        start, end = int(starts[index]), int(ends[index])
        literal(pending, start)
        value, length = int(data[start]), end - start
        while length >= 2:
            count = min(128, length)
            out.append(257 - count)
            out.append(value)
            length -= count
        pending = end - length  # a single leftover byte joins the next literal
    literal(pending, size)
    return bytes(out)


def patch_pytoshop() -> None:
    """pytoshop 1.2.1 fixes for current Python: unicode layer names and a
    PackBits encoder (its compiled extension is not built for new Pythons)."""
    psd_util.encode_unicode_string = lambda value: (
        struct.pack(">I", len(value)) + value.encode("utf_16_be")
    )
    import pytoshop.codecs as psd_codecs
    psd_codecs.compressors[enums.Compression.rle] = compress_rle_even


def compress_rle_even(fd, image, depth, version) -> None:
    """Write one channel as PSD RLE: row byte counts, then PackBits rows.
    Keeps every channel block an even number of bytes by appending a PackBits
    no-op (0x80) to the last row, so readers that expect 2-byte alignment
    (Pillow, some lightweight editors) stay in sync. Photoshop ignores 0x80."""
    rows = [packbits_encode(row) for row in image]
    if rows and sum(len(row) for row in rows) % 2:
        rows[-1] += b"\x80"
    width = ">u2" if version == 1 else ">u4"
    fd.write(np.array([len(row) for row in rows], dtype=width).tobytes())
    fd.write(b"".join(rows))


def write_psd(layers_bottom_to_top: list, composite: Image.Image, path: Path, dpi: int) -> None:
    # RLE is what Photoshop itself writes for 8-bit files and what non-Adobe
    # editors (Photopea, GIMP, Krita, Pillow) decode reliably; ZIP is not.
    patch_pytoshop()
    # pytoshop orders layers top-most first; our lists are built bottom to top.
    psd = nested_layers_to_psd(
        list(reversed(layers_bottom_to_top)), enums.ColorMode.rgb,
        compression=enums.Compression.rle, depth=enums.ColorDepth.depth8,
        size=composite.size,
    )
    rgb = np.asarray(composite.convert("RGB"))
    psd.image_data = ImageData(channels=np.moveaxis(rgb, 2, 0), compression=enums.Compression.rle)
    resolution = struct.pack(">IHHIHH", dpi * 65536, 1, 1, dpi * 65536, 1, 1)
    psd.image_resources.blocks.append(GenericImageResourceBlock(resource_id=1005, data=resolution))
    # Legacy Pascal names in plain ASCII; the Unicode name block (what
    # Photoshop shows) keeps accents.
    for record in psd.layer_and_mask_info.layer_info.layer_records:
        record.name = ascii_name(record.name)
    with path.open("wb") as stream:
        psd.write(stream)


def verify_psd(path: Path, expected: Image.Image, expected_layers: int, *, top_layer: str) -> dict:
    from psd_tools import PSDImage
    psd = PSDImage.open(path)
    leaves = [layer for layer in psd.descendants() if not layer.is_group()]
    rendered = psd.composite(force=True).convert("RGB")
    diff = np.asarray(ImageChops.difference(rendered, expected.convert("RGB")))
    top_name = psd[-1].name if len(psd) else None
    result = {
        "layers_read": len(leaves),
        "layers_expected": expected_layers,
        "render_max_diff": int(diff.max()),
        "top_layer": top_name,
        "top_layer_expected": top_layer,
    }
    result["second_reader"] = second_reader_check(path, expected)
    result["ok"] = (len(leaves) == expected_layers
                    and result["render_max_diff"] <= VERIFY_TOLERANCE
                    and top_name == top_layer
                    and result["second_reader"]["ok"])
    return result


def second_reader_check(path: Path, expected: Image.Image) -> dict:
    """Decode the merged image with Pillow, an independent reader that only
    accepts raw/RLE data, like many viewers, thumbnailers and lightweight
    editors. Catches files that psd-tools reads but other programs cannot.
    Pillow's layer parser assumes R,G,B,A channel order (Photoshop writes
    alpha first), so only the merged image is judged here."""
    try:
        with Image.open(path) as image:
            image.load()
            merged_diff = int(np.asarray(ImageChops.difference(
                image.convert("RGB"), expected.convert("RGB"))).max())
        return {"ok": merged_diff <= VERIFY_TOLERANCE, "merged_max_diff": merged_diff}
    except Exception as error:  # noqa: BLE001 - report any decoder failure
        return {"ok": False, "error": f"{type(error).__name__}: {error}"}


# ---------------------------------------------------------------- checks

def seam_metrics(image: Image.Image, repeat: str) -> dict[str, float | bool]:
    arr = np.asarray(image.convert("RGB")).astype(np.int16)
    height, width = arr.shape[:2]
    a, b = lattice(repeat, (width, height))
    # pixel (W-1, y) touches neighbour pixel (0, y - a.y); (x, H-1) touches (x - b.x, 0)
    right_neighbour = np.roll(arr[:, 0], a[1], axis=0)
    bottom_neighbour = np.roll(arr[0], b[0], axis=0)
    vertical = float(np.abs(arr[:, -1] - right_neighbour).mean())
    horizontal = float(np.abs(arr[-1] - bottom_neighbour).mean())
    xs = np.unique(np.linspace(0, width - 2, min(128, width - 1), dtype=int))
    ys = np.unique(np.linspace(0, height - 2, min(128, height - 1), dtype=int))
    inner_v = float(np.abs(arr[:, xs] - arr[:, xs + 1]).mean())
    inner_h = float(np.abs(arr[ys] - arr[ys + 1]).mean())
    return {
        "seam_vertical": round(vertical, 3),
        "seam_horizontal": round(horizontal, 3),
        "interior_vertical_sample": round(inner_v, 3),
        "interior_horizontal_sample": round(inner_h, 3),
        "vertical_diagnostic_pass": vertical <= max(1, 1.5 * inner_v),
        "horizontal_diagnostic_pass": horizontal <= max(1, 1.5 * inner_h),
    }


def repeat_preview(tile: Image.Image, repeat: str, max_side: int = 1600) -> Image.Image:
    """2x2 module area rendered with the real lattice of the repeat."""
    scale = min(1, max_side / max(tile.size))
    small = tile.resize((max(1, round(tile.width * scale)), max(1, round(tile.height * scale))),
                        Image.Resampling.LANCZOS)
    size = (small.width * 2, small.height * 2)
    preview = Image.new("RGB", size)
    for dx, dy in lattice_offsets(repeat, small.size, reach=3):
        if -small.width < dx < size[0] and -small.height < dy < size[1]:
            preview.paste(small, (dx, dy))
    return preview


# ---------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--verify", action="store_true",
                        help="Re-read both PSDs with psd-tools, render the layers and compare to the PNGs")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    config = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    warnings: list[str] = []

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

    repeat = str(config.get("repeat", "straight"))
    if repeat not in REPEAT_TYPES:
        raise ValueError(f"repeat deve ser um de {REPEAT_TYPES}")
    if repeat == "half-drop" and size[1] % 2:
        raise ValueError("half-drop exige altura par")
    if repeat == "brick" and size[0] % 2:
        raise ValueError("brick exige largura par")

    assets = path_from(base, config["assets_dir"])
    out = path_from(base, config["output_dir"])
    out.mkdir(parents=True, exist_ok=True)

    background = Image.new("RGBA", size, color + (255,))
    repeat_img = background.copy()
    repeat_layers: list = [psd_image_layer("Background", background)]
    motif_images: dict[str, Image.Image] = {}
    seen_names: set[str] = set()
    split_motifs: list[str] = []

    motifs = config["motifs"]
    if not motifs:
        raise ValueError("motifs não pode ficar vazio")
    cache: dict[str, Image.Image] = {}
    for item in motifs:
        layer_name = str(item["name"])
        if layer_name in seen_names:
            raise ValueError(f"Nome de camada duplicado: {layer_name}")
        seen_names.add(layer_name)
        center = item["center"]
        if len(center) != 2:
            raise ValueError(f"center inválido: {layer_name}")
        width = int(item["width"])
        if width > min(size):
            warnings.append(f"{layer_name}: largura {width}px maior que o lado menor do módulo; "
                            "o motivo pode se sobrepor a si mesmo na repetição")
        file_name = item["file"]
        if file_name not in cache:
            cache[file_name] = open_asset(assets / file_name)
        pieces = motif_pieces(cache[file_name], center, width, float(item.get("rotation", 0)),
                              size, repeat)
        if not pieces:
            raise ValueError(f"{layer_name}: motivo fora do módulo")
        if len(pieces) > 1:
            split_motifs.append(layer_name)
        repeat_layers.extend(motif_layers(layer_name, pieces))
        merged = Image.new("RGBA", size)
        for piece in pieces:
            merged.alpha_composite(piece)
        motif_images[layer_name] = merged
        repeat_img.alpha_composite(merged)

    # texture
    texture_cfg = config.get("texture")
    texture_img = None
    texture_opacity = 1.0
    texture_blend = "normal"
    texture_in_repeat = False
    if texture_cfg:
        texture_opacity = float(texture_cfg.get("opacity", 1))
        if not 0 < texture_opacity <= 1:
            raise ValueError("texture.opacity deve ser maior que 0 e até 1")
        texture_blend = str(texture_cfg.get("blend", "multiply"))
        if texture_blend not in BLEND_MODES:
            raise ValueError(f"texture.blend deve ser um de {tuple(BLEND_MODES)}")
        scale = float(texture_cfg.get("scale", 1))
        if scale <= 0:
            raise ValueError("texture.scale deve ser positivo")
        source = Image.open(path_from(assets, texture_cfg["file"])).convert("RGBA")
        texture_img = tiled_texture(source, size, scale)
        texture_in_repeat = bool(texture_cfg.get("include_in_repeat", False))
        if texture_in_repeat:
            tw, th = max(1, round(source.width * scale)), max(1, round(source.height * scale))
            if size[0] % tw or size[1] % th:
                warnings.append(f"Textura {tw}x{th}px não divide o módulo {size[0]}x{size[1]}px: "
                                "vai aparecer emenda na repetição. Ajuste texture.scale ou o tamanho do módulo")
            tex_seams = seam_metrics(tiled_texture(source, (tw, th), 1), "straight")
            if not (tex_seams["vertical_diagnostic_pass"] and tex_seams["horizontal_diagnostic_pass"]):
                warnings.append("A textura não parece contínua nas bordas; confira antes de usar no rapport")

    tile_composite = repeat_img
    tile_layers = list(repeat_layers)
    if texture_img is not None and texture_in_repeat:
        tile_composite = apply_texture(repeat_img, texture_img, texture_opacity, texture_blend)
        tile_layers.append(psd_image_layer("Texture", texture_img,
                                           opacity=round(texture_opacity * 255), blend=texture_blend))

    tile = tile_composite.convert("RGB")
    tile.save(out / f"{name}_rapport-tile.png", dpi=(dpi, dpi), compress_level=3)
    write_psd(tile_layers, tile, out / f"{name}_rapport-tile.psd", dpi)
    repeat_preview(tile, repeat).save(out / f"{name}_rapport-preview-2x2.jpg", quality=90,
                                      subsampling=0, dpi=(dpi, dpi))

    # placement
    placement = repeat_img.copy()
    placement_layers = list(repeat_layers)
    border_cfg = config.get("border")
    border_overlaps: dict[str, int] = {}
    if border_cfg:
        strip = resized_to_width(open_asset(assets / border_cfg["file"]), size[0])
        bottom_margin = int(border_cfg.get("bottom_margin", 0))
        if bottom_margin < 0 or strip.height + bottom_margin > size[1]:
            raise ValueError("Barrado não cabe no módulo")
        strip.save(out / f"{name}_barrado.png", dpi=(dpi, dpi), compress_level=3)
        border = Image.new("RGBA", size)
        border.alpha_composite(strip, (0, size[1] - strip.height - bottom_margin))
        border_alpha = np.asarray(border.getchannel("A")) > 0
        for layer_name, image in motif_images.items():
            overlap = int(np.count_nonzero(border_alpha & (np.asarray(image.getchannel("A")) > 0)))
            if overlap:
                border_overlaps[layer_name] = overlap
        if border_overlaps:
            names = ", ".join(border_overlaps)
            warnings.append(f"O barrado cobre parte de: {names}. Mova os centros para cima ou aceite o corte")
        placement_layers.append(psd_image_layer("Hem Border", border))
        placement.alpha_composite(border)
    if texture_img is not None:
        placement = apply_texture(placement, texture_img, texture_opacity, texture_blend)
        placement_layers.append(psd_image_layer("Texture", texture_img,
                                                opacity=round(texture_opacity * 255), blend=texture_blend))

    placement_rgb = placement.convert("RGB")
    png_path = out / f"{name}_placement.png"
    psd_path = out / f"{name}_placement.psd"
    placement_rgb.save(png_path, dpi=(dpi, dpi), compress_level=3)
    write_psd(placement_layers, placement_rgb, psd_path, dpi)

    if split_motifs:
        warnings.append("Motivos que cruzam a borda viraram camadas separadas, uma por peça "
                        f"({', '.join(split_motifs)}). Mover só uma peça quebra o rapport: "
                        "para reposicionar, mude center no manifesto e rode de novo")

    checks = {
        "size": list(size), "dpi": dpi, "repeat": repeat,
        "motifs": len(motifs), "motifs_split_at_edge": split_motifs,
        "tile_psd_layers": len(tile_layers),
        "placement_psd_layers": len(placement_layers),
        "has_border": bool(border_cfg), "border_overlaps_px": border_overlaps,
        "has_texture": bool(texture_cfg), "texture_in_repeat": texture_in_repeat,
        **seam_metrics(tile, repeat),
        "warnings": warnings,
    }
    if args.verify:
        top_tile = "Texture" if texture_in_repeat else (tile_layers[-1].name)
        checks["verify_tile_psd"] = verify_psd(out / f"{name}_rapport-tile.psd", tile,
                                               len(tile_layers), top_layer=top_tile)
        checks["verify_placement_psd"] = verify_psd(psd_path, placement_rgb,
                                                    len(placement_layers),
                                                    top_layer=placement_layers[-1].name)
    (out / f"{name}_checks.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False),
                                             encoding="utf-8")
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if args.verify and not (checks["verify_tile_psd"]["ok"] and checks["verify_placement_psd"]["ok"]):
        raise SystemExit("Falha na verificação do PSD: veja verify_* em checks.json")


if __name__ == "__main__":
    main()
