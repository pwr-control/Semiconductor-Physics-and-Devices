#!/usr/bin/env python3
"""Build the LaTeX versions of the two Markdown documents.

    python3 build_tex.py            # writes ../<name>.tex for both documents
    python3 build_tex.py --pdf      # ... and compiles them with pdflatex

The Markdown files are the master copies. This script converts them with
pandoc (needs the ``pandoc`` binary, or ``pip install pypandoc_binary``)
after a few text substitutions that pdflatex needs (unicode symbols, figure
blocks, links to files of the repository), and wraps the result in a
self-contained preamble so that each .tex file compiles on its own with
pdflatex and the packages of a standard TeX Live.
"""

import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.normpath(os.path.join(HERE, ".."))
REPO_URL = ("https://github.com/pwr-control/Semiconductor-Physics-and-Devices"
            "/blob/main/diode-reverse-recovery/")

DOCS = {
    "plecs_diode_parameters_ds1112sg_simple_english": {
        "title": ("DS1112SG60 diode stack at 13.8\\,kV: how the PLECS and "
                  "Simscape diode parameters are obtained from the datasheet"),
        "subtitle": ("Plain-English version of the calculation note "
                     "``Parametri PLECS e Simscape del DS1112SG60'', Rev.~01, "
                     "2026-10-01 (Secom Proposal Engineering, D.~Bagnara)"),
    },
    "physics_of_reverse_recovery": {
        "title": "The physics of diode reverse recovery, in plain English",
        "subtitle": ("A companion to chapter 5 of the DS1112SG60 note"),
    },
}

PREAMBLE = r"""\documentclass[a4paper,11pt]{article}
% ---------------------------------------------------------------- packages
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
% Computer Modern in T1 encoding (cm-super); add lmodern if you have it
\usepackage{textcomp}
\usepackage[margin=2.4cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{booktabs,longtable,array,calc}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage[colorlinks=true,linkcolor=blue!50!black,urlcolor=blue!50!black,
            citecolor=blue!50!black]{hyperref}
% ------------------------------------------------- pandoc helper macros
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\providecommand{\pandocbounded}[1]{#1}
\setcounter{secnumdepth}{-\maxdimen} % section numbers are written in the titles
\setlength{\parskip}{0.45em}
\setlength{\parindent}{0pt}
\setlength{\LTpre}{0.8em}
\setlength{\LTpost}{0.8em}
\renewcommand{\arraystretch}{1.15}
"""


def github_links(s):
    """Links to files of the repository become links to GitHub."""
    def repl(m):
        text, path = m.group(1), m.group(2)
        return "[%s](%s%s)" % (text, REPO_URL, path)
    return re.sub(r"\[([^\]]+)\]\(((?:original|figures|scripts)/[^)]+|[\w_]+\.md)\)",
                  repl, s)


def figure_blocks(s):
    """``![alt](figures/x.svg)`` followed by ``*Figure N: caption*`` becomes a
    LaTeX figure numbered N with the PDF version of the same figure."""
    pat = re.compile(r"!\[[^\]]*\]\(figures/(\w+)\.svg\)\n\n\*\*Figure (\d+):\*\* (.+?)\n")

    def repl(m):
        name, num, cap = m.group(1), int(m.group(2)), m.group(3).strip()
        cap = cap.replace("%", "\\%").replace("&", "\\&")   # raw LaTeX: escape
        return ("```{=latex}\n\\begin{figure}[htbp]\n\\centering\n"
                "\\setcounter{figure}{%d}\n"
                "\\includegraphics[width=\\linewidth]{figures/%s.pdf}\n"
                "\\caption{%s}\\label{fig:%d}\n\\end{figure}\n```\n"
                % (num - 1, name, cap, num))
    return pat.sub(repl, s)


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


def heading_math(md):
    """The Markdown headings spell symbols in plain text (GitHub anchors);
    the LaTeX headings get proper math."""
    out = []
    for line in md.split("\n"):
        if line.startswith("#"):
            for a, b in HEADING_MATH:
                line = line.replace(a, b)
        out.append(line)
    return "\n".join(out)


def preprocess(md):
    # title line and the Contents section are replaced by \maketitle and \tableofcontents
    md = re.sub(r"\A# .*?\n", "", md)
    md = heading_math(md)
    md = re.sub(r"\n## Contents\n.*?(?=\n## |\n---\n)", "\n", md, flags=re.S)
    md = re.sub(r"\n---\n", "\n", md)
    md = figure_blocks(md)      # before the links, which would rewrite the image paths
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
    return "".join(out)


def postprocess(tex):
    # the two wide tables with long text cells get explicit column widths
    tex = tex.replace(
        r"\begin{longtable}[]{@{}llll@{}}" + "\n" + r"\toprule\noalign{}" + "\n"
        r"Rev. & Date & Author & Description \\",
        r"\begin{longtable}[]{@{}>{\raggedright\arraybackslash}p{0.06\linewidth}"
        r">{\raggedright\arraybackslash}p{0.13\linewidth}"
        r">{\raggedright\arraybackslash}p{0.14\linewidth}"
        r">{\raggedright\arraybackslash}p{0.58\linewidth}@{}}" + "\n"
        + r"\toprule\noalign{}" + "\n" + r"Rev. & Date & Author & Description \\")
    tex = tex.replace(
        r"\begin{longtable}[]{@{}ll@{}}" + "\n" + r"\toprule\noalign{}" + "\n"
        r"Symbol & Meaning \\",
        r"\begin{longtable}[]{@{}>{\raggedright\arraybackslash}p{0.27\linewidth}"
        r">{\raggedright\arraybackslash}p{0.68\linewidth}@{}}" + "\n"
        + r"\toprule\noalign{}" + "\n" + r"Symbol & Meaning \\")
    tex = tex.replace(
        r"\begin{longtable}[]{@{}llll@{}}" + "\n" + r"\toprule\noalign{}" + "\n"
        r"Parameter & Value & Origin & Type \\",
        r"\begin{longtable}[]{@{}>{\raggedright\arraybackslash}p{0.13\linewidth}"
        r">{\raggedright\arraybackslash}p{0.15\linewidth}"
        r">{\raggedright\arraybackslash}p{0.45\linewidth}"
        r">{\raggedright\arraybackslash}p{0.18\linewidth}@{}}" + "\n"
        + r"\toprule\noalign{}" + "\n" + r"Parameter & Value & Origin & Type \\")
    tex = tex.replace(
        r"\begin{longtable}[]{@{}llll@{}}" + "\n" + r"\toprule\noalign{}" + "\n"
        r"What it is & In the physics",
        r"\begin{longtable}[]{@{}>{\raggedright\arraybackslash}p{0.2\linewidth}"
        r">{\raggedright\arraybackslash}p{0.25\linewidth}"
        r">{\raggedright\arraybackslash}p{0.25\linewidth}"
        r">{\raggedright\arraybackslash}p{0.22\linewidth}@{}}" + "\n"
        + r"\toprule\noalign{}" + "\n" + r"What it is & In the physics")
    tex = tex.replace(
        r"\begin{longtable}[]{@{}ll@{}}" + "\n" + r"\toprule\noalign{}" + "\n"
        r"File & What it is \\",
        r"\begin{longtable}[]{@{}>{\raggedright\arraybackslash}p{0.3\linewidth}"
        r">{\raggedright\arraybackslash}p{0.65\linewidth}@{}}" + "\n"
        + r"\toprule\noalign{}" + "\n" + r"File & What it is \\")
    # all tables in a smaller font
    tex = tex.replace(r"\begin{longtable}", r"{\small" + "\n" + r"\begin{longtable}")
    tex = tex.replace(r"\end{longtable}", r"\end{longtable}" + "\n}")
    # code listings a bit smaller
    tex = tex.replace(r"\begin{verbatim}", r"{\small\begin{verbatim}")
    tex = tex.replace(r"\end{verbatim}", r"\end{verbatim}}")
    return tex


def build(name, meta, pdf=False):
    src = os.path.join(DOC, name + ".md")
    md = preprocess(open(src, encoding="utf-8").read())
    body = subprocess.run(
        ["pandoc", "-f", "markdown+tex_math_dollars+pipe_tables+raw_tex",
         "-t", "latex", "--no-highlight", "--wrap=preserve",
         "--shift-heading-level-by=-1", "--columns=1000"],
        input=md, capture_output=True, text=True, check=True).stdout
    body = postprocess(body)
    tex = (PREAMBLE
           + "\\title{%s\\\\[0.6em]{\\large %s}}\n" % (meta["title"], meta["subtitle"])
           + "\\author{}\n\\date{Rev.~00, 2026-10-04}\n"
           + "\\begin{document}\n\\maketitle\n"
           + "\\noindent\\emph{Generated by \\texttt{scripts/build\\_tex.py} from the "
             "Markdown file \\texttt{%s.md}, which is the master copy.}\n\n"
             % name.replace("_", "\\_")
           + "\\tableofcontents\n\\bigskip\n\n"
           + body + "\n\\end{document}\n")
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
        for ext in (".aux", ".log", ".out", ".toc"):
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
