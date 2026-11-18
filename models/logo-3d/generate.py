# /// script
# requires-python = ">=3.11"
# dependencies = ["manifold3d","numpy","scipy","shapely>=2.1","svgelements","trimesh"]
# ///
"""Rebuild the print files and viewer contours with uv run models/logo-3d/generate.py."""

from pathlib import Path
from svgelements import SVG, Path as SVGPath, Move, Line, Close
import manifold3d as m, numpy as np, trimesh, json, math, zipfile
from xml.etree import ElementTree as E

root_dir = Path(__file__).resolve().parents[2]
out = root_dir / "static/logo-3d"
cs = m.CrossSection
motif = cs()
for path in SVG.parse(
    str(root_dir / "static/images/icons/logos/git-nrw.svg")
).elements():
    if not isinstance(path, SVGPath):
        continue
    rings = []
    for sub in path.as_subpaths():
        coords = []
        for seg in sub:
            if isinstance(seg, Move):
                continue
            n = (
                1
                if isinstance(seg, (Line, Close))
                else max(2, math.ceil(abs(seg.end - seg.start) / 5))
            )
            for i in range(n):
                p = seg.point(i / n)
                x, y = p.x, p.y
                coords.append((x * 0.094, (660 - y) * 0.094))
        rings.append(coords)
    motif += cs(rings, m.FillRule.EvenOdd)


# Rectified front plane, traced in the double-size photo crop (82,358)-(677,581).
def on_face(u, v):
    return ((u - 42) / 6.0, (437 - 0.015 * (u - 150) - v) / 6.0)


# Keep the official glyph contours, using the blue ink extents as landmarks.
beaver = cs()
letters = []
for part in motif.decompose():
    if part.bounds()[0] < 67:
        beaver += part
    else:
        letters.append(part)


# Preserve all original contours and relative positions within each group.
def uniform(part, scale, left, bottom):
    x, y, _, _ = part.bounds()
    return part.translate((-x, -y)).scale(scale).translate(on_face(left, bottom))


beaver = uniform(beaver, 378 / (6 * (beaver.bounds()[3] - beaver.bounds()[1])), 46, 419)
word = cs()
for letter in letters:
    word += letter
scale = 656 / (6 * (word.bounds()[2] - word.bounds()[0]))
# Stem baseline relative to the descender of the original g.
bottom = 332 + (578.016 - 473.416) * 0.094 * scale * 6
word = uniform(word, scale, 492, bottom)
motif = beaver + word
# A round offset is the union of a disk swept along every logo edge.
# The stand only fills the area below the letters and between the feet.
padding = 3.1
padded = motif.offset(padding, circular_segments=96)
# Continue the descending outer stroke of the w to the rounded toe.
from shapely.geometry import LineString, Polygon

last_letter = max(word.decompose(), key=lambda c: c.bounds()[2])
w_border = Polygon(last_letter.offset(padding).to_polygons()[0])


def right_edge(y):
    line = LineString([(0, y), (220, y)])
    return w_border.intersection(line).bounds[2]


top_y = 27.0
slope = (right_edge(top_y) - right_edge(23)) / 4
toe_x = right_edge(top_y) - (top_y - 9) * slope
rim = SVGPath(
    f"M{right_edge(top_y)},{top_y} L{toe_x},9 C{toe_x - slope},8 {toe_x + 1.8},6.7 {toe_x + 1.8},2 Q{toe_x + 1.8},0 {toe_x + 0.7},0"
)
toe = []
for segment in rim:
    if isinstance(segment, Move):
        continue
    for fraction in np.linspace(0, 1, 25):
        point = segment.point(fraction)
        toe.append((point.x, point.y))
# Low bridges between components leave the visible type outline to the offset.
support = cs(
    [
        [
            (20, 0),
            (20, 9),
            (46, 14),
            (54, 27),
            (65, 34),
            (74, 25),
            (78, 20),
            (175, 20),
            (right_edge(top_y) - 3, top_y),
        ]
        + toe
    ],
    m.FillRule.EvenOdd,
)
baseplane = cs.square((220, 85)).translate((-10, 1))
shell = (padded + support) ^ baseplane
shell = cs(
    [
        p
        for p in shell.to_polygons()
        if np.sum(p[:, 0] * np.roll(p[:, 1], -1) - p[:, 1] * np.roll(p[:, 0], -1)) > 0
    ]
)
assert (motif - shell).area() < 0.001
assert len(shell.decompose()) == 1
base = shell.simplify(0.015).extrude(12)
motif = motif.simplify(0.012)
blue = motif.extrude(1.6)
models = [base, blue.translate((0, 0, 12))]


def mesh(s):
    a = s.to_mesh()
    t = trimesh.Trimesh(a.vert_properties[:, :3], a.tri_verts, process=True)
    print(t.is_watertight, t.is_winding_consistent, t.volume)
    assert t.is_watertight and t.is_winding_consistent and t.volume > 0
    return t


for name, s in [
    ("aufsteller", models[0] + models[1]),
    ("traeger", base),
    ("relief", blue),
]:
    t = mesh(s)
    t.export(out / (name + ".stl"))
    print(name, t.extents, t.body_count)
# A single build item holds both registered volumes. Each has a base material.
root = E.Element(
    "model",
    {
        "xmlns": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
        "unit": "millimeter",
        "xml:lang": "de-DE",
    },
)
res = E.SubElement(root, "resources")
mats = E.SubElement(res, "basematerials", id="1")
for name, color in [("Elfenbein", "#F4EADBFF"), ("git.nrw Blau", "#003057FF")]:
    E.SubElement(mats, "base", name=name, displaycolor=color)
for i, s in enumerate(models):
    obj = E.SubElement(
        res,
        "object",
        id=str(i + 2),
        type="model",
        pid="1",
        pindex=str(i),
        name=["Träger", "Relief"][i],
    )
    geom = E.SubElement(obj, "mesh")
    verts = E.SubElement(geom, "vertices")
    t = mesh(s)
    for v in t.vertices:
        E.SubElement(verts, "vertex", dict(zip("xyz", [f"{x:.6f}" for x in v])))
    tris = E.SubElement(geom, "triangles")
    for f in t.faces:
        E.SubElement(tris, "triangle", dict(zip(["v1", "v2", "v3"], map(str, f))))
comp = E.SubElement(
    E.SubElement(res, "object", id="4", type="model", name="git.nrw"), "components"
)
for i in ["2", "3"]:
    E.SubElement(comp, "component", objectid=i)
E.SubElement(E.SubElement(root, "build"), "item", objectid="4")
with zipfile.ZipFile(out / "aufsteller.3mf", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("3D/3dmodel.model", E.tostring(root, encoding="utf-8"))
    z.writestr(
        "_rels/.rels",
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>',
    )
    z.writestr(
        "[Content_Types].xml",
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>',
    )
from shapely import Polygon, maximum_inscribed_circle


def anchor(c):
    pts = c.to_polygons()
    poly = Polygon(pts[0], pts[1:])
    line = maximum_inscribed_circle(poly, tolerance=0.04)
    return tuple(line.coords[0]), line.length


pocket = motif.offset(0.18).simplify(0.012)
holes = cs()
pins = m.Manifold()
pin_shapes = cs()
for c in motif.decompose():
    (x, y), inscribed = anchor(c)
    r = min(1.45, inscribed - 0.14)
    height = 1.4 if r < 1 else 2.4
    socket = cs.circle(r, 32).translate((x, y))
    holes += socket
    pin_shapes += socket
    pin = m.Manifold.cylinder(height, r - 0.20, r + 0.055, 32)
    pins += pin.translate((x, y, -height))
base_fit = (
    base
    - pocket.extrude(1).translate((0, 0, 11.4))
    - holes.extrude(3.45).translate((0, 0, 8.65))
)
inserts = motif.extrude(2.2) + pins
assert (base_fit ^ inserts.translate((0, 0, 11.4))).volume() < 2.5
for name, s, count in [
    ("stecktraeger", base_fit, 1),
    ("steckrelief", inserts.rotate((180, 0, 0)).translate((0, 64, 2.2)), 14),
]:
    t = mesh(s)
    assert t.body_count == count
    t.export(out / (name + ".stl"))
    t = trimesh.load(out / (name + ".stl"))
    assert t.is_watertight and t.body_count == count
rings = lambda s: [p.round(4).tolist() for p in s.to_polygons()]
sections = [shell.simplify(0.015) - holes, shell.simplify(0.015) - pocket, pin_shapes]


def js_const(name, shapes):
    return (
        f"const {name} = "
        + json.dumps([rings(shape) for shape in shapes], separators=(",", ":"))
        + ";\n"
    )


(out / "geometry.js").write_text(
    js_const("contours", [shell, motif]) + js_const("fitContours", sections)
)
from tempfile import TemporaryDirectory

factor = 600 / (shell.bounds()[2] - shell.bounds()[0])
outer = shell.simplify(0.015).scale(factor)
logo = motif.scale(factor)
solid = outer.extrude(32) + logo.extrude(4).translate((0, 0, 32))


def left_mask(x):
    # Female on the left. Two tapered tabs on the right engage along Z.
    rect = cs.square((x + 100, 400)).translate((-100, -50))
    for y in (30, 52):
        tab = cs([[(x + 1, y - 6), (x + 1, y + 6), (x - 11, y + 10), (x - 11, y - 10)]])
        assert tab.area() > 0 and (tab - outer).area() < 0.01
        rect -= tab
    return rect


l, r = left_mask(225), left_mask(386)
whole = cs.square((800, 400)).translate((-100, -50))
areas = [l, r - l, whole - r]


def printable(path, s):
    t = mesh(s)
    t.apply_translation(-t.bounds[0])
    t.export(path)
    checked = trimesh.load(path)
    assert checked.is_watertight and checked.is_volume and checked.body_count == 1
    assert max(checked.extents[:2]) < 245
    print(path.name, checked.extents)


with TemporaryDirectory() as tmp:
    folder = Path(tmp)
    parts = []
    for i, (area, label) in enumerate(zip(areas, ["links", "mitte", "rechts"])):
        section = area.offset(-0.13)
        part = solid ^ section.extrude(40)
        parts.append(part)
        target = folder / f"{i + 1}-{label}.stl"
        printable(target, part)
        if i == 0:
            (out / "600-links.stl").write_bytes(target.read_bytes())
    assert all((a ^ b).is_empty() for i, a in enumerate(parts) for b in parts[i + 1 :])
    coupon = cs.square((38, 24)).translate((204, 18)).extrude(5)
    for i in [0, 1]:
        printable(folder / f"passprobe-{i + 1}.stl", parts[i] ^ coupon)
    (folder / "Montage.txt").write_text("""git.nrw · Aufsteller 600 mm
Je eine STL-Datei mittig auf eine eigene P1S-Druckplatte legen, Rückseite unten.
Drei Segmente in der gespeicherten Ausrichtung und bei 100 % drucken.
Weiß bis einschließlich 32 mm, die erste Schicht darüber dunkelblau drucken.
Das Relief ist in jedes Segment integriert. Gesamttiefe 36 mm.

Für einen schnellen Test die beiden 5 mm hohen Passproben drucken.
Sie bilden einen der Schwalbenschwänze mit dem gleichen seitlichen Spiel wie am Aufsteller ab.
Die Segmente flach mit dem Motiv nach oben auf den Tisch legen. Die Schwalbenschwänze
von oben in das Nachbarteil schieben, bis alle Rückseiten bündig aufliegen.
Danach den Aufsteller an der Unterkante mit beiden Händen aufrichten.
""")
    with zipfile.ZipFile(
        out / "aufsteller-600-p1s.zip", "w", zipfile.ZIP_DEFLATED
    ) as z:
        for p in sorted(folder.iterdir()):
            z.write(p, p.name)

# Individually printable colours for the full-size assembly.
with TemporaryDirectory() as tmp:
    folder = Path(tmp)
    sockets = cs()
    preview = []
    pocket = logo.offset(0.22).simplify(0.012)
    for i, piece in enumerate(sorted(logo.decompose(), key=lambda part: part.bounds()[0]), 1):
        center, clearance = anchor(piece)
        radius = min(3.2, clearance - 0.3)
        socket = cs.circle(radius, 48).translate(center)
        sockets += socket
        peg = m.Manifold.cylinder(4, radius - 0.35, radius + 0.055, 48)
        insert = piece.extrude(5) + peg.translate((*center, -4))
        printable(folder / f"blau-{i:02}.stl", insert.rotate((180, 0, 0)))
        preview.append([rings(piece), rings(socket)])
    panels = []
    for label, area in zip(["links", "mitte", "rechts"], areas):
        face = outer ^ area.offset(-0.13)
        middle = face - sockets
        top = face - pocket
        panel = face.extrude(32) - sockets.extrude(6).translate((0,0,26.5)) - pocket.extrude(2).translate((0,0,31))
        printable(folder / f"weiss-{label}.stl", panel)
        panels.append([rings(face), rings(middle), rings(top)])
    (folder/"Montage.txt").write_text("600-mm-Steckmodell · P1S · 100 %\n3 weiße Träger flach mit den Taschen nach oben drucken. Die 14 blauen Teile liegen mit der Sichtseite unten und dem Zapfen oben. Die weißen Segmente von oben an den Schwalbenschwänzen zusammenfügen. Anschließend die blauen Teile von vorn in die passenden Konturtaschen drücken.\n")
    with zipfile.ZipFile(out/"steckmodell-600-p1s.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.iterdir()):
            archive.write(path,path.name)
    with (out/"geometry.js").open("a") as js:
        js.write("const assembly = "+json.dumps({"panels":panels,"inserts":preview},separators=(",",":"))+";\n")
