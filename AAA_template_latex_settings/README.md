# LaTeX template — pwr-control documents

Shared LaTeX settings and title page used by the LaTeX versions of the documents of this repository. `settings.tex`, `titlepage.tex` and the logo are copies of the template kept in [`repositories-documentation/AAA_template_latex_settings`](https://github.com/pwr-control/repositories-documentation/tree/main/AAA_template_latex_settings); when that one changes, copy it here again.

## Files

| File | Purpose |
|---|---|
| `settings.tex` | Packages, page geometry, header/footer, theorem environments, `mybox`, SI units, colors. Loaded once; a second `\input` is ignored. |
| `titlepage.tex` | Title page built from the `\Doc...` macros defined by the document, including the revision history table. |
| `pwr-control_logo_doc.png` | Logo placed in the header of every page. |

## Usage

In this repository the documents live one level below the root (`<topic>/<name>.tex`), so the template is reached with `../AAA_template_latex_settings/`. `settings.tex` is shared with repositories where the documents are two levels deep, and its header logo path (`../../AAA_template_latex_settings/...`) is therefore redefined by the document right after the settings are loaded.

```latex
\documentclass[11pt,a4paper]{scrartcl}
\input{../AAA_template_latex_settings/settings}
\rhead{\includegraphics[height=0.75cm]{../AAA_template_latex_settings/pwr-control_logo_doc.png}}

\newcommand{\DocCategory}{Technical Note}
\newcommand{\DocField}{Semiconductor Physics and Devices}
\newcommand{\DocTitle}{%
    {\fontsize{20}{24}\selectfont\bfseries Main title:} \\[16pt]
    {\fontsize{16}{20}\selectfont\bfseries subtitle of the title.}
}
\newcommand{\DocSubtitle}{One line describing the document.}
\newcommand{\DocAuthor}{Davide Bagnara}
\newcommand{\DocRevision}{00}
\newcommand{\DocDate}{Month Year}
\newcommand{\DocAbstract}{Abstract of the document.}

% one line per revision: Rev. & Date & Description & Authors \\
\newcommand{\RevisionHistory}{%
    00 & Month Year & First issue. & \DocAuthor \\
}

\newcommand{\MetaLabelA}{Project Repository}
\newcommand{\MetaValueAUrl}{https://github.com/pwr-control/Semiconductor-Physics-and-Devices.git}
\newcommand{\MetaValueALabel}{Semiconductor-Physics-and-Devices.git}
\newcommand{\MetaLabelB}{Framework}
\newcommand{\MetaValueB}{PLECS 5.0, MATLAB/Simscape}

\begin{document}
\input{../AAA_template_latex_settings/titlepage}
\tableofcontents
\listoffigures
\listoftables
\newpage
\begin{onehalfspace}

% ... body ...

\end{onehalfspace}
\end{document}
```

The `.tex` files of `diode-reverse-recovery/` are generated in exactly this form by `diode-reverse-recovery/scripts/build_tex.py` from their Markdown masters.

## Notes

- The document class is `scrartcl`: the top sectioning level is `\section`,
  there is no `\chapter`.
- Equations are numbered per section (`\numberwithin{equation}{section}`).
- `esint` is loaded after `amsmath` on purpose: both define `\iint` and
  friends, and the four names are released before `esint` is loaded.
- `figures/` stays inside each document folder; only the logo lives here.
- The template needs a full TeX Live (`texlive-latex-extra`, `texlive-science`, `texlive-pictures`, `texlive-plain-generic`, `texlive-fonts-recommended`, `cm-super` on Debian/Ubuntu): it loads `tikz`, `pgfplots`, `siunitx`, `physics`, `chemmacros`, `mdframed` and friends.
