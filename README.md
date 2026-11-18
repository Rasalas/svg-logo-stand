# SVG Logo Stand

Generate a printable two-height stand from a filled SVG silhouette. The git.nrw example also includes a segmented 600 mm stand and a rotatable exploded view.

[Open the 3D viewer and print downloads](https://rasalas.github.io/svg-logo-stand/static/logo-3d/)

## Use your own SVG

With uv installed, run this from the repository root. Width includes the padding. All dimensions are in millimetres.

```sh
uv run models/logo-3d/svg_stand.py logo.svg stand.stl --width 190 --padding 3.1 --base-depth 12 --relief-height 1.6
```

Use filled vector paths on a transparent background. Convert strokes and text to paths before exporting. Filled colours merge into one relief. This command produces a one-piece STL. Place the flat back on the print bed. For two colours, change filament at the first layer above the base depth.

## Print the git.nrw example

![Assembled git.nrw stand](images/aufsteller.png)

- [P1S + AMS test print](static/logo-3d/git-nrw-p1s-ams.3mf) — open as a Bambu Studio project. Map filament 1 to the backing colour and filament 2 to the logo colour. Preset: 0.4 mm nozzle, 0.20 mm layers, textured PEI, two PLA filaments. Slicer-verified switch at layer 61 (12.2 mm).

- [Small one-piece test print](static/logo-3d/aufsteller.stl) — 189.9 × 68.4 × 13.6 mm. Change colour above 12 mm.
- [600 mm single-piece stand](static/logo-3d/aufsteller-600-einteilig.stl) — one solid for large-format printers. Print back down and change colour above 32 mm.
- [600 mm push-fit version](static/logo-3d/steckmodell-600-p1s.zip) — three ivory backing panels and fourteen navy inserts. Print the panels back down and the inserts face down. Join the backing panels along their dovetails, then press the inserts into their matching pockets. Parts are oriented and individually sized for the Bambu Lab P1S.
- [600 mm colour-change version](static/logo-3d/aufsteller-600-p1s.zip) — three panels with integral relief. Change filament above 32 mm. The two small coupons in this archive reproduce the panel joint.

Run `uv run models/logo-3d/generate.py` to rebuild the example and its viewer geometry. The panel seams, pins and arrangement are specific to this example. Meshes were checked digitally. Physical fit has not been tested.
