# /// script
# requires-python = ">=3.11"
# dependencies = ["manifold3d", "trimesh", "numpy"]
# ///
"""Generate the desk-edge cable holder and Bambu Studio two-plate assembly list."""

import json
import sys
from pathlib import Path

from manifold3d import CrossSection as Section, Manifold
import trimesh


def rectangle(x, y, width, depth):
    return Section.square((width, depth)).translate((x, y))


def rounded(x, y, width, depth, radius):
    return rectangle(x + radius, y + radius, width - 2 * radius, depth - 2 * radius).offset(radius, circular_segments=64)


def generate(directory, tight_fit=False):
    directory.mkdir(parents=True, exist_ok=True)
    depth = 52 if tight_fit else 40
    footprint = rounded(0, 0, 56, depth, 2.5)
    left = rectangle(-5, -5, 33, depth + 10)
    neck = 4 if tight_fit else 6
    for center in ((13, 39) if tight_fit else (20,)):
        left -= Section([[(29, center-neck), (29, center+neck),
                          (17, center+10), (17, center-10)]])
    right = rectangle(-5, -5, 70, depth + 10) - left
    fork = rounded(3, -17, 50, 33, 2.5)
    for x, width in [(16, 4.4), (40, 6.0)]:
        fork -= rectangle(x - width / 2, -20, width, 12) + Section.circle(width / 2, 48).translate((x, -8))
    sockets = Section()
    pegs = Manifold()
    for x in [12, 44]:
        sockets += Section.circle(3.17 if tight_fit else 3.2, 48).translate((x, 8))
        pegs += Manifold.cylinder(4, 2.85, 3.255, 48).translate((x, 8, -4))
    pockets = fork.offset(0.10 if tight_fit else 0.22).extrude(2).translate((0, 0, 7))
    bores = sockets.extrude(6).translate((0, 0, 2.5))
    objects = []
    for label, mask in [('Sockel-links', left), ('Sockel-rechts', right)]:
        objects.append((label, (footprint ^ mask.offset(-0.035 if tight_fit else -0.13)).extrude(8) - pockets - bores))
    objects.append(('Kabelgabel', (fork.extrude(5) + pegs).rotate((180, 0, 0))))
    plates = [dict(plate_name=name, need_arrange=True, objects=[]) for name in ['Sockel', 'Kabelgabel']]
    for index, (label, geometry) in enumerate(objects):
        mesh = geometry.to_mesh()
        model = trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts)
        assert model.is_watertight and model.is_volume and len(geometry.decompose()) == 1
        model.apply_translation(-model.bounds[0])
        path = directory / (label + '.stl')
        model.export(path)
        plate = int(index == 2)
        plates[plate]['objects'].append(dict(path=str(path.resolve()), count=1, filaments=[plate + 1]))
    (directory / 'platten.json').write_text(json.dumps(dict(plates=plates)))


if __name__ == '__main__':
    generate(Path(sys.argv[1]), tight_fit="--tight-fit" in sys.argv[2:])
