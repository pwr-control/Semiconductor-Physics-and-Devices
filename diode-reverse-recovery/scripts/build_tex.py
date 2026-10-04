#!/usr/bin/env python3
"""Build the LaTeX versions of the two Markdown documents.

    python3 build_tex.py            # writes ../<name>.tex for both documents
    python3 build_tex.py --pdf      # ... and compiles them with pdflatex

The Markdown files are the master copies. This script converts them with
pandoc (needs the ``pandoc`` binary, or ``pip install pypandoc_binary``)
after a few text substitutions that pdflatex needs (unicode symbols, figure
blocks, table captions, links to files of the repository), and wraps the
result in the pwr-control LaTeX template of ``../../AAA_template_latex_settings``
(``settings.tex`` and the title page ``titlepage.tex``), following the usage
block of that folder's README.
"""

import os
import re
import string
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.normpath(os.path.join(HERE, ".."))
REPO_URL = ("https://github.com/pwr-control/Semiconductor-Physics-and-Devices"
            "/blob/main/diode-reverse-recovery/")
TEMPLATE = "../AAA_template_latex_settings"   # relative to the document folder

# ------------------------------------------------------------ title pages
# One entry per document: the \Doc... macros that titlepage.tex expects.
AUTHOR = "Davide Bagnara"
REVISION = "00"
DATE = "October 2026"
META_A = ("Project Repository",
          "https://github.com/pwr-control/Semiconductor-Physics-and-Devices.git",
          "Semiconductor-Physics-and-Devices.git")

DOCS = {
    "plecs_diode_parameters_ds1112sg_simple_english": {
        "category": "Technical Note",
        "field": "Semiconductor Physics and Devices",
        "title": (r"{\fontsize{20}{24}\selectfont\bfseries "
                  r"DS1112SG60 diode stack at 13.8\,kV:} \\[16pt]" "\n    "
                  r"{\fontsize{16}{20}\selectfont\bfseries how the PLECS and "
                  r"Simscape diode parameters are obtained from the datasheet}"),
        "subtitle": ("Plain-English version of the calculation note "
                     "``Parametri PLECS e Simscape del DS1112SG60'' "
                     "(Rev.~01, 2026-10-01, Secom Proposal Engineering)."),
        "abstract": (
            "Two DS1112SG60 fast-recovery diodes in series rectify 13.8\\,kV. "
            "This note derives, from the Dynex datasheet and from the operating "
            "point of the circuit (60\\,A, 0.107\\,A/\\textmu s), every parameter "
            "of the PLECS \\emph{Diode with Reverse Recovery} model: the static "
            "characteristic, the off resistance, the junction capacitance, the "
            "recovered charge, the peak reverse current and the recovery time. "
            "Because the datasheet stops at a current slope thirty times higher "
            "than the one of the circuit, the stored charge is bracketed by a "
            "floor and a ceiling extrapolation, and twelve parameter sets cover "
            "the uncertainty. The same data are then mapped onto the "
            "charge-controlled diode of Lauritzen and Ma used by the "
            "MATLAB/Simscape model. Every number, formula and table of the "
            "Italian note is kept; only the language is simpler."),
        "history": (
            "00 & October 2026 & First issue. Plain-English rewrite of the "
            "Italian note Rev.~01, generated from the Markdown master with "
            "\\texttt{scripts/build\\_tex.py}. & \\DocAuthor \\\\"),
        "meta_b": ("Framework", "PLECS 5.0, MATLAB/Simscape"),
    },
    "physics_of_reverse_recovery": {
        "category": "Technical Note",
        "field": "Semiconductor Physics and Devices",
        "title": (r"{\fontsize{20}{24}\selectfont\bfseries "
                  r"The physics of diode reverse recovery,} \\[16pt]" "\n    "
                  r"{\fontsize{16}{20}\selectfont\bfseries in plain English}"),
        "subtitle": ("A companion to chapter 5 of the DS1112SG60 "
                     "PLECS/Simscape parameter note."),
        "abstract": (
            "Why does a high-voltage diode keep conducting after its current has "
            "crossed zero, and where does the recovered charge come from? This "
            "note explains chapter 5 of the DS1112SG60 parameter note with one "
            "idea: the charge stored in the diode is a first-order lag of the "
            "current, with the carrier lifetime as time constant. From this "
            "follow the charge left at the zero crossing, the peak reverse "
            "current, the exponential tail, the charge budget, the apparent "
            "lifetime read from the datasheet, the floor and ceiling "
            "extrapolations, the PLECS triangle and the unbalance rule of a "
            "series stack. The derivations are collected in an appendix. All "
            "figures are computed with the nominal parameter set of the note."),
        "history": (
            "00 & October 2026 & First issue. Generated from the Markdown "
            "master with \\texttt{scripts/build\\_tex.py}. & \\DocAuthor \\\\"),
        "meta_b": ("Figures", "\\texttt{scripts/make\\_figures.py} "
                              "(Python, NumPy, Matplotlib)"),
    },
}

PREAMBLE = string.Template(r"""\documentclass[11pt,a4paper,numbers=noenddot]{scrartcl}
\input{${tpl}/settings}
% The documents of this repository are one folder below the root, not two as
% settings.tex assumes: point the header logo to the right place.
\rhead{\includegraphics[height=0.75cm]{${tpl}/pwr-control_logo_doc.png}}
\usepackage[T1]{fontenc}
% ------------------------------------------------- pandoc helper macros
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\providecommand{\pandocbounded}[1]{#1}
\setlength{\LTpre}{0.8em}
\setlength{\LTpost}{0.8em}
\setlength{\emergencystretch}{3em} % long file names in links: looser lines rather than overfull ones

\newcommand{\DocCategory}{${category}}
\newcommand{\DocField}{${field}}
\newcommand{\DocTitle}{%
    ${title}
}
\newcommand{\DocSubtitle}{${subtitle}}
\newcommand{\DocAuthor}{${author}}
\newcommand{\DocRevision}{${revision}}
\newcommand{\DocDate}{${date}}
\newcommand{\DocAbstract}{${abstract}}

% one line per revision: Rev. & Date & Description & Authors \\
\newcommand{\RevisionHistory}{%
    ${history}
}

\newcommand{\MetaLabelA}{${meta_a_label}}
\newcommand{\MetaValueAUrl}{${meta_a_url}}
\newcommand{\MetaValueALabel}{${meta_a_text}}
\newcommand{\MetaLabelB}{${meta_b_label}}
\newcommand{\MetaValueB}{${meta_b_text}}
""")


def capitalise(cap):
    """The Markdown captions start in lower case after the bold label;
    the LaTeX captions (and the lists of figures and tables) start in upper case."""
    return cap[0].upper() + cap[1:] if cap[:1].islower() else cap


def github_links(s):
    """Links to files of the repository become links to GitHub."""
    def repl(m):
        text, path = m.group(1), m.group(2)
        return "[%s](%s%s)" % (text, REPO_URL, path)
    return re.sub(r"\[([^\]]+)\]\(((?:original|figures|scripts)/[^)]+|[\w_]+\.md)\)",
                  repl, s)


def figure_blocks(s):
    """``![alt](figures/x.svg)`` followed by ``**Figure N:** caption`` becomes
    a LaTeX figure with the PDF version of the same figure. The figures are
    numbered in order of appearance in the Markdown, so LaTeX gives them the
    same numbers; ``Figure N`` in the text becomes a reference."""
    pat = re.compile(r"!\[[^\]]*\]\(figures/(\w+)\.svg\)\n\n\*\*Figure (\d+):\*\* (.+?)\n")
    seen = []

    def repl(m):
        name, num, cap = m.group(1), int(m.group(2)), m.group(3).strip()
        seen.append(num)
        cap = capitalise(cap).replace("%", "\\%").replace("&", "\\&")   # raw LaTeX: escape
        short = re.split(r"(?<=[a-z])\. ", cap, maxsplit=1)[0]   # first sentence
        short = "[%s.]" % short if short != cap else ""
        return ("```{=latex}\n\\begin{figure}[htbp]\n\\centering\n"
                "\\includegraphics[width=\\linewidth]{figures/%s.pdf}\n"
                "\\caption%s{%s}\\label{fig:%d}\n\\end{figure}\n```\n"
                % (name, short, cap, num))
    s = pat.sub(repl, s)
    if seen:
        assert seen == list(range(1, len(seen) + 1)), \
            "figures must be numbered in order of appearance: %s" % seen
        s = re.sub(r"\bFigures (\d) and (\d)\b",
                   r"Figures \\ref{fig:\1} and \\ref{fig:\2}", s)
        s = re.sub(r"\bFigure (\d)\b", r"Figure \\ref{fig:\1}", s)
    return s, bool(seen)


def table_captions(s):
    """``**Table N: caption**`` above a pipe table becomes a pandoc table
    caption, so LaTeX numbers the table and lists it."""
    pat = re.compile(r"^\*\*Table (\d+): (.+?)\*\*\n\n(?=\|)", flags=re.M)
    n = len(pat.findall(s))
    s = pat.sub(lambda m: "Table: %s\n\n" % capitalise(m.group(2).strip()), s)
    return s, n > 0


SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
       "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "-"}

TEXT_MAP = [
    ("≈", r"$\approx$"), ("≫", r"$\gg$"), ("±", r"$\pm$"), ("×", r"$\times$"),
    ("−", r"$-$"), ("·", r"$\cdot$"), ("Ω", r"$\Omega$"), ("§", r"\S"),
    ("°", r"\textdegree{}"), ("–", "--"), ("—", "---"),
]


def fix_text(s):
    """Unicode that pdflatex cannot take in text mode."""
    s = re.sub(r"10([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)",
               lambda m: "$10^{%s}$" % "".join(SUP[c] for c in m.group(1)), s)
    s = re.sub(r"(?<=[A-Za-z])([²³])", lambda m: "$^{%s}$" % SUP[m.group(1)], s)
    s = re.sub(r"(?<=\S)([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)",
               lambda m: "$^{%s}$" % "".join(SUP[c] for c in m.group(1)), s)
    # a closing $ must not touch a digit (pandoc rule), so the digit goes inside
    s = re.sub(r"±([0-9.]+)", lambda m: "$\\pm %s$" % m.group(1), s)
    s = re.sub(r"−([0-9.]+)", lambda m: "$-%s$" % m.group(1), s)
    s = re.sub(r"×([0-9.]+)", lambda m: "$\\times %s$" % m.group(1), s)
    for a, b in TEXT_MAP:
        s = s.replace(a, b)
    return s


def fix_math(s):
    """Unicode inside a math segment."""
    s = s.replace("–", "-")
    s = s.replace("\\ °\\text{C}", "\\ ^\\circ\\text{C}")
    s = s.replace("°", "^\\circ")
    # µ only ever appears inside \text{...} here, where inputenc handles it
    return s


def split_segments(s):
    """Yield (kind, text) with kind in {'code', 'math', 'text'} so that the
    substitutions can be applied to the right pieces only."""
    pat = re.compile(r"(```.*?```|`[^`\n]+`|\$\$.+?\$\$|\$[^$\n]+?\$)", flags=re.S)
    pos = 0
    for m in pat.finditer(s):
        if m.start() > pos:
            yield "text", s[pos:m.start()]
        t = m.group(0)
        yield ("code" if t.startswith("`") else "math"), t
        pos = m.end()
    if pos < len(s):
        yield "text", s[pos:]


HEADING_MATH = [
    ("dI_r/dt", r"$\mathrm{d}I_r/\mathrm{d}t$"), ("I_F0", r"$I_{F0}$"),
    ("V_RRM", r"$V_{RRM}$"), ("V_f0", r"$V_{f0}$"), ("r_t", r"$r_t$"),
    ("R_off", r"$R_{off}$"), ("C_j", r"$C_j$"), ("Q_rr", r"$Q_{rr}$"),
    ("I_rrm", r"$I_{rrm}$"), ("t_rr", r"$t_{rr}$"), ("T_M", r"$T_M$"),
    ("I_s", r"$I_s$"), ("R_s", r"$R_s$"), (" tau ", r" $\tau$ "),
    (" a to ", r" $a$ to "), (" N and", r" $N$ and"),
]


def headings(md):
    """The Markdown headings carry their numbers and spell symbols in plain
    text (GitHub anchors). In LaTeX the sections are numbered by the class,
    the headings without a number stay unnumbered, the appendices follow
    \\appendix, and the symbols become math."""
    out = []
    in_appendix = False
    for line in md.split("\n"):
        if line.startswith("#"):
            m = re.match(r"^(#{2,3}) \d+(?:\.\d+)* (.*)$", line)
            if m:
                line = "%s %s" % (m.group(1), m.group(2))
            else:
                m = re.match(r"^## Appendix [A-Z]: (.*)$", line)
                if m:
                    title = m.group(1)
                    line = "## " + title[0].upper() + title[1:]
                    if not in_appendix:
                        line = "```{=latex}\n\\appendix\n```\n\n" + line
                        in_appendix = True
                elif line.startswith("## "):
                    line += " {-}"
            for a, b in HEADING_MATH:
                line = line.replace(a, b)
        out.append(line)
    return "\n".join(out)


def preprocess(md):
    # the title, the subtitle line of the rewrite and the Contents section
    # are replaced by the title page and \tableofcontents
    md = re.sub(r"\A# .*?\n", "", md)
    md = re.sub(r"\n\*\*Plain-English version of the calculation note.*?\*\*\n", "\n", md)
    md = re.sub(r"\n## Contents\n.*?(?=\n## |\n---\n)", "\n", md, flags=re.S)
    md = re.sub(r"\n---\n", "\n", md)
    md = headings(md)
    md, has_figures = figure_blocks(md)   # before the links, which would rewrite the image paths
    md, has_tables = table_captions(md)
    md = github_links(md)
    # one inline code span holds an Omega; make it text so it can be typeset
    md = md.replace("`roff_s = roff = 2.9 MΩ`", "`roff_s = roff` = 2.9 MΩ")
    out = []
    for kind, t in split_segments(md):
        if kind == "text":
            t = fix_text(t)
        elif kind == "math":
            t = fix_math(t)
        out.append(t)
    return "".join(out), has_figures, has_tables


# tables whose text cells are long get explicit column widths (fractions of
# \linewidth), recognised by their header row
WIDTHS = [
    ("Rev. & Date & Author & Description", [0.06, 0.13, 0.14, 0.58]),
    ("Symbol & Meaning", [0.27, 0.68]),
    ("Parameter & Value & Origin & Type", [0.13, 0.15, 0.45, 0.18]),
    ("What it is & In the physics", [0.2, 0.25, 0.25, 0.22]),
    ("File & What it is", [0.3, 0.65]),
]


def postprocess(tex):
    # pandoc wraps uncaptioned tables in a group that the caption package
    # (loaded by settings.tex) cannot digest; longtable steps the table
    # counter at every table, so step it back after an uncaptioned one
    tex = re.sub(r"\{\\def\\LTcaptype\{none\}[^\n]*\n(.*?\\end\{longtable\}\n)\}",
                 r"\1\\addtocounter{table}{-1}% uncaptioned table: not counted",
                 tex, flags=re.S)
    # unnumbered sections do not set the running header by themselves
    tex = re.sub(r"(\\section\*\{(.+?)\}\\label\{[^}]*\}\n\\addcontentsline\{toc\}\{section\}\{.+?\}\n)",
                 r"\1\\markboth{\2}{}\n", tex)
    # long file names in monospace may break after a slash or an underscore
    tex = re.sub(r"\\texttt\{([^{}]{25,})\}",
                 lambda m: "\\texttt{%s}" % m.group(1).replace("/", "/\\allowbreak{}")
                                                     .replace("\\_", "\\_\\allowbreak{}"), tex)

    def widths(m):
        spec, rest = m.group(1), m.group(2)
        for header, ws in WIDTHS:
            if header in rest:
                spec = "@{}" + "".join(r">{\raggedright\arraybackslash}p{%g\linewidth}" % w
                                       for w in ws) + "@{}"
                break
        return "\\begin{longtable}[]{%s}\n%s" % (spec, rest)
    tex = re.sub(r"\\begin\{longtable\}\[\]\{(@\{\}.*?@\{\})\}\n((?:[^\n]*\n){1,3})",
                 widths, tex)
    # all tables in a smaller font, single spaced
    tex = tex.replace(r"\begin{longtable}", "{\\small\\singlespacing\n" + r"\begin{longtable}")
    tex = tex.replace(r"\end{longtable}", r"\end{longtable}" + "\n}")
    # the remarks of the note go in the grey box of the template
    tex = tex.replace(r"\begin{quote}", r"\begin{mybox}")
    tex = tex.replace(r"\end{quote}", r"\end{mybox}")
    # code listings smaller and single spaced
    tex = tex.replace(r"\begin{verbatim}", "{\\small\\singlespacing" + r"\begin{verbatim}")
    tex = tex.replace(r"\end{verbatim}", r"\end{verbatim}}")
    return tex


def build(name, meta, pdf=False):
    src = os.path.join(DOC, name + ".md")
    md, has_figures, has_tables = preprocess(open(src, encoding="utf-8").read())
    body = subprocess.run(
        ["pandoc", "-f", "markdown+tex_math_dollars+pipe_tables+raw_tex",
         "-t", "latex", "--no-highlight", "--wrap=preserve",
         "--shift-heading-level-by=-1", "--columns=1000"],
        input=md, capture_output=True, text=True, check=True).stdout
    body = postprocess(body)
    fields = dict(tpl=TEMPLATE, author=AUTHOR, revision=REVISION, date=DATE,
                  meta_a_label=META_A[0], meta_a_url=META_A[1], meta_a_text=META_A[2],
                  meta_b_label=meta["meta_b"][0], meta_b_text=meta["meta_b"][1],
                  **{k: v for k, v in meta.items() if k != "meta_b"})
    tex = (PREAMBLE.substitute(fields)
           + "\n\\begin{document}\n\\input{%s/titlepage}\n\\tableofcontents\n" % TEMPLATE
           + ("\\listoffigures\n" if has_figures else "")
           + ("\\listoftables\n" if has_tables else "")
           + "\\newpage\n\\begin{onehalfspace}\n\n"
           + body + "\n\\end{onehalfspace}\n\\end{document}\n")
    dst = os.path.join(DOC, name + ".tex")
    open(dst, "w", encoding="utf-8").write(tex)
    print("wrote", os.path.relpath(dst))
    if pdf:
        for _ in range(3):
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                                "-halt-on-error", name + ".tex"],
                               cwd=DOC, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout[-3000:])
                sys.exit("pdflatex failed on " + name)
        for ext in (".aux", ".log", ".out", ".toc", ".lof", ".lot"):
            try:
                os.remove(os.path.join(DOC, name + ext))
            except FileNotFoundError:
                pass
        print("compiled", name + ".pdf")


if __name__ == "__main__":
    if shutil.which("pandoc") is None:
        try:
            import pypandoc  # noqa: F401
            os.environ["PATH"] += os.pathsep + os.path.dirname(pypandoc.get_pandoc_path())
        except ImportError:
            sys.exit("pandoc not found: install it, or pip install pypandoc_binary")
    want_pdf = "--pdf" in sys.argv
    for name, meta in DOCS.items():
        build(name, meta, pdf=want_pdf)
