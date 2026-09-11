"""Build the Word and PDF documents.

    python -m reporting.build            # both reports
    python -m reporting.build literature # only one
"""
from __future__ import annotations

import sys
import time

from fraudlens import config

from . import literature_report, project_report, results_md
from .engine import html_to_pdf, render_docx, render_html, update_docx_fields_and_export
from .results import Results

DOCS = config.ROOT / "docs"
REPORTS = {
    "project": ("Project_Report", project_report.build),
    "literature": ("Literature_Mapping_Report", literature_report.build),
}


def main(which: list[str]) -> None:
    R = Results()
    print("wrote", results_md.write(R).relative_to(config.ROOT))
    for key in which or list(REPORTS):
        name, builder = REPORTS[key]
        t0 = time.perf_counter()
        doc = builder(R)
        docx = render_docx(doc, DOCS / f"{name}.docx")
        update_docx_fields_and_export(docx)                   # refresh the Word table of contents
        html = render_html(doc, DOCS / "html" / f"{name}.html")
        pdf = html_to_pdf(html, DOCS / f"{name}.pdf")
        print(f"{name}: {docx.name}, {pdf.name} ({time.perf_counter() - t0:.1f}s)")


if __name__ == "__main__":
    main(sys.argv[1:])
