"""Export to PDF via a headless browser"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from traitlets import Bool, Int, default

from .webhtml import PLAYWRIGHT_INSTALLED, WebHTMLExporter  # noqa: F401

# NOTE: reexport PLAYWRIGHT_INSTALLED from webhtml for backwards compatibility


class WebPDFExporter(WebHTMLExporter):
    """Writer designed to write to PDF files.

    This inherits from :class:`WebHTMLExporter`. It creates the HTML using the
    template machinery, and then run playwright to create a pdf.
    """

    export_from_notebook = "PDF via HTML"

    paginate = Bool(
        True,
        help="""
        Split generated notebook into multiple pages.

        If False, a PDF with one long page will be generated.

        Set to True to match behavior of LaTeX based PDF generator
        """,
    ).tag(config=True)

    page_render_timeout = Int(
        100,
        help="""
        Time to wait for the page to render before converting to PDF, in milliseconds.
        Increase this value if your notebook has a lot of complex JavaScript
        output that needs more time to load.
        """,
    ).tag(config=True)

    @default("file_extension")
    def _file_extension_default(self):
        return ".pdf"

    @default("template_extension")
    def _template_extension_default(self):
        # NOTE: we use .html.j2 so that the HTMLExporter can find the template
        return ".html.j2"

    @default("template_name")
    def _template_name_default(self):
        return "webpdf"

    def run_playwright(self, html, _postprocess=None):
        """Run playwright."""

        async def _pdf_postprocess(page, browser, playwright):
            """Post-process the PDF output."""
            pdf_params = {"print_background": True}
            if not self.paginate:
                # Floating point precision errors cause the printed
                # PDF from spilling over a new page by a pixel fraction.
                dimensions = await page.evaluate(
                    """() => {
                    const rect = document.body.getBoundingClientRect();
                    return {
                    width: Math.ceil(rect.width) + 1,
                    height: Math.ceil(rect.height) + 1,
                    }
                }"""
                )
                width = dimensions["width"]
                height = dimensions["height"]
                # 200 inches is the maximum size for Adobe Acrobat Reader.
                pdf_params.update(
                    {
                        "width": min(width, 200 * 72),
                        "height": min(height, 200 * 72),
                    }
                )
            return await page.pdf(**pdf_params)

        return super().run_playwright(html, _postprocess=_pdf_postprocess)

    def from_notebook_node(self, nb, resources=None, **kw):
        """Convert from a notebook node."""
        html, resources = super().from_notebook_node(nb, resources=resources, **kw)

        self.log.info("Building PDF")
        pdf_data = self.run_playwright(html)
        self.log.info("PDF successfully created")

        return pdf_data, resources
