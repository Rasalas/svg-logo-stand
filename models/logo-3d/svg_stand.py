# /// script
# requires-python = ">=3.11"
# dependencies = ["manifold3d", "numpy", "scipy", "svgelements", "trimesh"]
# ///
"""Generate a single-piece, two-height STL from a filled vector silhouette."""

import argparse
import math
from pathlib import Path
from xml.etree import ElementTree

import manifold3d as m
import trimesh
from svgelements import Close, Line, Move, Path as VectorPath, Shape, SVG


def positive_mm(value):
    mm = float(value)
    if not math.isfinite(mm) or mm <= 0:
        raise argparse.ArgumentTypeError("Maß muss positiv und endlich sein")
    return mm


def silhouette(source, width):
    unsupported = {
        "text",
        "image",
        "mask",
        "clipPath",
        "filter",
        "pattern",
        "linearGradient",
        "radialGradient",
    }
    tags = {node.tag.split("}")[-1] for node in ElementTree.parse(source).iter()}
    if tags & unsupported:
        raise ValueError(
            "Bitte als flächige Vektor-Silhouette exportieren. Enthalten: "
            + ", ".join(sorted(tags & unsupported))
        )

    paths = []
    for shape in SVG.parse(str(source)).elements():
        if not isinstance(shape, Shape):
            continue
        if float(shape.values.get("opacity", 1)) == 0 or shape.values.get(
            "visibility"
        ) in {"hidden", "collapse"}:
            continue
        if (
            shape.stroke.value is not None
            and shape.stroke.opacity
            and shape.stroke_width
        ):
            raise ValueError("Bitte sichtbare Strichkonturen in Flächen umwandeln.")
        if shape.fill.value is not None and shape.fill.opacity:
            path = VectorPath(shape)
            if path.bbox() is not None:
                paths.append((path, shape.values.get("fill-rule") == "evenodd"))
    if not paths:
        raise ValueError("Keine gefüllten Vektorkonturen gefunden.")

    left = min(path.bbox()[0] for path, _ in paths)
    right = max(path.bbox()[2] for path, _ in paths)
    if right <= left:
        raise ValueError("Die Vorlage hat keine sichtbare Breite.")
    scale = width / (right - left)
    result = m.CrossSection()
    for path, even_odd in paths:
        rings = []
        for subpath in path.as_subpaths():
            points = []
            for segment in subpath:
                if isinstance(segment, Move):
                    continue
                count = (
                    1
                    if isinstance(segment, (Line, Close))
                    else max(4, math.ceil(segment.length() * scale / 0.35))
                )
                for index in range(count):
                    p = segment.point(index / count)
                    points.append(((p.x - left) * scale, -p.y * scale))
                end = segment.end
            if points:
                points.append(((end.x - left) * scale, -end.y * scale))
                rings.append(points)
        rule = m.FillRule.EvenOdd if even_odd else m.FillRule.NonZero
        result += m.CrossSection(rings, rule)
    if result.is_empty():
        raise ValueError("Die Vorlage enthält keine druckbare Fläche.")
    return result.simplify(0.005).translate((0, -result.bounds()[1]))


def stand(motif, padding, base_depth, relief_height):
    padded = motif.offset(padding, circular_segments=96)
    left, bottom, right, _ = padded.bounds()
    # The rail gives separated letters a common, flat standing edge.
    rail_height = padding
    backing = m.CrossSection.square((right - left, rail_height)).translate(
        (left, bottom)
    )
    for island in padded.decompose():
        outline = island.to_polygons()[0]
        solid_island = m.CrossSection([outline])
        x, y = min(outline, key=lambda point: point[1])
        # Connect an elevated island (such as an i dot) down to the rail.
        low = max(left, x - padding / 2)
        high = min(right, x + padding / 2)
        stem = m.CrossSection.square((high - low, y - bottom + padding)).translate(
            (low, bottom)
        )
        backing += solid_island + stem
    return backing.simplify(0.005).extrude(base_depth) + motif.extrude(relief_height).translate(
        (0, 0, base_depth)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Eine gefüllte SVG-Silhouette als Aufsteller mit gerader Standkante exportieren. Alle Maße in mm."
    )
    parser.add_argument("svg", type=Path)
    parser.add_argument("stl", type=Path)
    parser.add_argument(
        "--width",
        type=positive_mm,
        default=190,
        help="Gesamtbreite einschließlich Rand (190)",
    )
    parser.add_argument(
        "--padding", type=positive_mm, default=3.1, help="Randbreite (3.1)"
    )
    parser.add_argument(
        "--base-depth", type=positive_mm, default=12, help="Trägertiefe (12)"
    )
    parser.add_argument(
        "--relief-height", type=positive_mm, default=1.6, help="Reliefhöhe (1.6)"
    )
    args = parser.parse_args()
    if args.width <= 2 * args.padding:
        parser.error("Die Gesamtbreite muss größer als der doppelte Rand sein.")
    if args.stl.suffix.lower() != ".stl":
        parser.error("Zieldatei muss die Endung .stl haben.")
    try:
        motif = silhouette(args.svg, args.width - 2 * args.padding)
        solid = stand(motif, args.padding, args.base_depth, args.relief_height)
        data = solid.to_mesh()
        mesh = trimesh.Trimesh(
            vertices=data.vert_properties[:, :3], faces=data.tri_verts
        )
        if not mesh.is_volume or not mesh.is_watertight or len(solid.decompose()) != 1:
            raise ValueError(
                "Die Konturen ergeben keinen einzelnen geschlossenen Druckkörper."
            )
        mesh.apply_translation(-mesh.bounds[0])
        args.stl.write_bytes(mesh.export(file_type="stl"))
    except (OSError, ValueError, ElementTree.ParseError) as error:
        parser.exit(1, f"{error}\n")
    print(f"{args.stl} · {' × '.join(f'{mm:.1f}' for mm in mesh.extents)} mm")


if __name__ == "__main__":
    main()
