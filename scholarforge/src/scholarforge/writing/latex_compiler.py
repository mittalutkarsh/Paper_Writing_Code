"""Markdown → LaTeX Converter and Compiler."""

import re
import subprocess
from pathlib import Path

from ..utils.logger import get_logger
from .models import LaTeXOutput, PaperDraft

logger = get_logger(__name__)


def _markdown_to_latex(text: str) -> str:
    """Convert Markdown formatting to LaTeX.
    
    Args:
        text: Markdown text
        
    Returns:
        LaTeX text
    """
    # Bold: **text** -> \textbf{text}
    text = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', text)
    
    # Italic: *text* -> \textit{text}
    text = re.sub(r'\*(.*?)\*', r'\\textit{\1}', text)
    
    # Code blocks
    text = re.sub(r'```(.*?)```', r'\\begin{verbatim}\1\\end{verbatim}', text, flags=re.DOTALL)
    
    # Inline code
    text = re.sub(r'`(.*?)`', r'\\texttt{\1}', text)
    
    return text


def _generate_bibtex_entry(citation: dict) -> str:
    """Generate a BibTeX entry from citation data.
    
    Args:
        citation: Citation dict with key, title, authors, etc.
        
    Returns:
        BibTeX entry string
    """
    key = citation.get('key', 'unknown')
    title = citation.get('title', '')
    authors = citation.get('authors', [])
    year = citation.get('year', 2024)
    venue = citation.get('venue', '')
    doi = citation.get('doi', '')
    arxiv_id = citation.get('arxiv_id', '')
    
    # Format authors
    author_str = ' and '.join(authors) if authors else 'Anonymous'
    
    # Determine entry type
    if arxiv_id and not venue:
        entry_type = 'misc'
        extra = f"  eprint = {{{arxiv_id}}},\n  archivePrefix = {{arXiv}},\n"
    elif venue:
        entry_type = 'inproceedings'
        extra = f"  booktitle = {{{venue}}},\n"
    else:
        entry_type = 'article'
        extra = ""
    
    bib = f"""@{entry_type}{{{key},
  title = {{{title}}},
  author = {{{author_str}}},
  year = {{{year}}},
{extra}"""
    
    if doi:
        bib += f"  doi = {{{doi}}},\n"
    
    bib += "}\n\n"
    
    return bib


def compile_paper(
    draft: PaperDraft,
    citations: list[dict],
    conference: str,
    output_dir: str
) -> LaTeXOutput:
    """Convert paper draft to LaTeX and compile to PDF.
    
    Args:
        draft: Paper draft
        citations: List of citation dicts
        conference: Conference format (icml2026 or iclr2026)
        output_dir: Output directory
        
    Returns:
        LaTeXOutput with paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    figures_dir = output_path / "figures"
    figures_dir.mkdir(exist_ok=True)
    
    # Load template
    template_dir = Path(__file__).parent.parent.parent.parent / "templates" / conference
    
    if conference == "icml2026":
        template = _get_icml_template()
    elif conference == "iclr2026":
        template = _get_iclr_template()
    else:
        template = _get_icml_template()
    
    # Convert sections to LaTeX
    sections_tex = []
    for section_name, content in draft.sections.items():
        section_label = section_name.lower().replace(' ', '_')
        latex_content = _markdown_to_latex(content)
        
        sections_tex.append(f"\\section{{{section_name}}}\\label{{sec:{section_label}}}")
        sections_tex.append(latex_content)
        sections_tex.append("")
    
    # Fill in template (use replace to avoid KeyError on LaTeX braces in template)
    sections_joined = "\n\n".join(sections_tex)
    tex_content = template \
        .replace("{title}", draft.title) \
        .replace("{abstract}", draft.abstract) \
        .replace("{sections}", sections_joined)
    
    # Write .tex file
    tex_path = output_path / "paper.tex"
    tex_path.write_text(tex_content)
    logger.info(f"Wrote LaTeX: {tex_path}")
    
    # Generate .bib file
    bib_content = ""
    for citation in citations:
        bib_content += _generate_bibtex_entry(citation)
    
    bib_path = output_path / "references.bib"
    bib_path.write_text(bib_content)
    logger.info(f"Wrote BibTeX: {bib_path}")
    
    # Try to compile PDF
    pdf_path = None
    if _has_pdflatex():
        try:
            pdf_path = _compile_latex(str(tex_path), str(output_path))
        except Exception as e:
            logger.warning(f"LaTeX compilation failed: {e}")
    else:
        logger.info("pdflatex not found, skipping PDF compilation")
    
    return LaTeXOutput(
        tex_path=str(tex_path),
        bib_path=str(bib_path),
        pdf_path=pdf_path,
        figures_dir=str(figures_dir)
    )


def _has_pdflatex() -> bool:
    """Check if pdflatex is available."""
    try:
        subprocess.run(['pdflatex', '--version'], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _compile_latex(tex_path: str, output_dir: str) -> str:
    """Compile LaTeX to PDF.
    
    Args:
        tex_path: Path to .tex file
        output_dir: Output directory
        
    Returns:
        Path to generated PDF
    """
    import os
    
    tex_file = Path(tex_path).name
    
    # Run pdflatex -> bibtex -> pdflatex -> pdflatex
    commands = [
        ['pdflatex', '-interaction=nonstopmode', tex_file],
        ['bibtex', tex_file.replace('.tex', '')],
        ['pdflatex', '-interaction=nonstopmode', tex_file],
        ['pdflatex', '-interaction=nonstopmode', tex_file],
    ]
    
    for cmd in commands:
        result = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            logger.warning(f"LaTeX command failed: {' '.join(cmd)}")
            logger.debug(result.stderr)
    
    pdf_path = Path(output_dir) / tex_file.replace('.tex', '.pdf')
    if pdf_path.exists():
        logger.info(f"Generated PDF: {pdf_path}")
        return str(pdf_path)
    else:
        raise RuntimeError("PDF generation failed")


def _get_icml_template() -> str:
    """Get ICML 2026 template."""
    return r"""\documentclass{article}
\usepackage[accepted]{icml2026}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}

\begin{document}

\twocolumn[
\icmltitle{{{title}}}

\begin{icmlauthorlist}
\icmlauthor{Author Name}{affil}
\end{icmlauthorlist}

\icmlaffiliation{affil}{Institution}

\icmlcorrespondingauthor{Author}{email@example.com}

\icmlkeywords{Machine Learning}

\vskip 0.3in
]

\printAffiliationsAndNotice

\begin{abstract}
{abstract}
\end{abstract}

{sections}

\bibliography{{references}}
\bibliographystyle{{icml2026}}

\end{document}
"""


def _get_iclr_template() -> str:
    """Get ICLR 2026 template."""
    return r"""\documentclass{article}
\usepackage{iclr2026_conference}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{natbib}
\usepackage{hyperref}

\title{{{title}}}

\author{Author Name \\
Institution \\
\texttt{email@example.com}}

\begin{document}

\maketitle

\begin{abstract}
{abstract}
\end{abstract}

{sections}

\bibliography{{references}}
\bibliographystyle{plainnat}

\end{document}
"""
