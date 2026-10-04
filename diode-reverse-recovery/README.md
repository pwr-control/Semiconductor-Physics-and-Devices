# Diode reverse recovery: the DS1112SG60 note and the physics behind it

Three documents, two of them written in deliberately simple English.

| File | What it is |
|---|---|
| [`original/plecs_diode_parameters_ds1112sg.pdf`](original/plecs_diode_parameters_ds1112sg.pdf) | The original calculation note, in Italian (Rev. 01, 2026-10-01): how the PLECS *Diode with Reverse Recovery* and Simscape *Lauritzen–Ma* parameters of a 13.8 kV DS1112SG60 diode stack are derived from the datasheet. |
| [`plecs_diode_parameters_ds1112sg_simple_english.md`](plecs_diode_parameters_ds1112sg_simple_english.md) | The same note, section by section, in plain English. Same numbers, tables, equations and code listing. |
| [`physics_of_reverse_recovery.md`](physics_of_reverse_recovery.md) | A companion document that explains the physics behind chapter 5 of the note: stored charge, lifetime, why the current goes through zero, the peak, the tail, the apparent lifetime, the floor and the ceiling, the triangle, the $\sqrt{1-u}$ rule. Written for a power-electronics and control engineer; the diode is treated as a first-order lag whose state is the stored charge. |

Each Markdown document also exists as LaTeX and as a compiled PDF, for reading offline or where the Markdown math does not render well:

| Markdown (master copy) | LaTeX source | PDF |
|---|---|---|
| `plecs_diode_parameters_ds1112sg_simple_english.md` | [`plecs_diode_parameters_ds1112sg_simple_english.tex`](plecs_diode_parameters_ds1112sg_simple_english.tex) | [`plecs_diode_parameters_ds1112sg_simple_english.pdf`](plecs_diode_parameters_ds1112sg_simple_english.pdf) |
| `physics_of_reverse_recovery.md` | [`physics_of_reverse_recovery.tex`](physics_of_reverse_recovery.tex) | [`physics_of_reverse_recovery.pdf`](physics_of_reverse_recovery.pdf) |

The `.tex` files are generated from the Markdown by [`scripts/build_tex.py`](scripts/build_tex.py) (pandoc plus a fixed preamble) and compile on their own with `pdflatex` and a standard TeX Live. Edit the Markdown and rerun the script; or edit the `.tex` directly if the LaTeX version is to become the master copy.

Supporting material:

- [`figures/`](figures/): the eight figures used by the physics document, as SVG (for the Markdown) and PDF (for the LaTeX).
- [`scripts/make_figures.py`](scripts/make_figures.py): regenerates the figures from the charge-control model with the parameters of the note (Python 3, NumPy, Matplotlib).
- [`scripts/build_tex.py`](scripts/build_tex.py): regenerates the `.tex` files from the Markdown, and compiles them with `--pdf` (pandoc, pdflatex).

Suggested reading order, if the recovery chapter is the hard part: the physics document first (sections 1 to 8 give the picture, 9 to 13 decode §5.1 to §5.4 of the note one by one), then the simple-English note.
