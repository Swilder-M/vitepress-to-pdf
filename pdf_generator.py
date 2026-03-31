import asyncio
import io
import os
import tempfile

from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

CONCURRENCY = 6
PAGE_TIMEOUT = 30000


def _read_css(css_path):
    with open(css_path, 'r') as f:
        return f.read()


def _build_header_html(title):
    return (
        '<div style="width:100%; text-align:center; font-size:10px;'
        f' font-family:sans-serif; padding:5px 0;">{title}</div>'
    )


def _build_toc_html(toc_entries):
    """Generate TOC HTML.

    toc_entries: list of (title, level, page_number)
    """
    items_html = ''
    for title, level, page_num in toc_entries:
        level_class = 'level-1' if level <= 1 else 'level-2'
        items_html += (
            f'<li class="toc-item {level_class}">'
            f'<span class="toc-title"><span class="toc-text">{title}</span></span>'
            f'<span class="toc-page">{page_num}</span>'
            f'</li>\n'
        )

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; }}
body {{ padding: 40px 50px; }}
h1 {{ text-align: center; margin-bottom: 20px; font-size: 24px; }}
ul {{ list-style: none; }}
.toc-item {{
    display: flex;
    align-items: baseline;
    padding: 3px 0;
    font-size: 14px;
}}
.toc-item.level-1 {{
    font-weight: bold;
    font-size: 16px;
    padding-top: 8px;
}}
.toc-item.level-2 {{
    padding-left: 30px;
    font-weight: normal;
}}
.toc-title {{
    flex: 1;
    overflow: hidden;
}}
.toc-text {{
    background: #fff;
    padding-right: 5px;
}}
.toc-title::after {{
    content: "";
    display: inline-block;
    width: 100%;
    border-bottom: 1px dotted #000;
    margin-left: 5px;
    position: relative;
    top: -4px;
}}
.toc-page {{
    flex-shrink: 0;
    padding-left: 5px;
    background: #fff;
    text-align: right;
    min-width: 30px;
}}
</style>
</head>
<body>
<h1>Contents</h1>
<ul>
{items_html}
</ul>
</body>
</html>'''


def _stamp_page_numbers(writer, skip_pages=1):
    """Stamp page numbers on all pages except the first `skip_pages` pages."""
    total_pages = len(writer.pages)
    total_numbered = total_pages - skip_pages

    for i in range(skip_pages, total_pages):
        page = writer.pages[i]
        page_num = i - skip_pages + 1

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=A4)
        text = f'{page_num} / {total_numbered}'
        c.setFont('Helvetica', 8)
        text_width = c.stringWidth(text, 'Helvetica', 8)
        x = (A4[0] - text_width) / 2
        c.drawString(x, 25, text)
        c.save()
        packet.seek(0)

        overlay = PdfReader(packet).pages[0]
        page.merge_page(overlay)


async def _render_page(context, url, css_text, header_html, semaphore, tmp_dir, index):
    """Render a single URL to PDF, return pdf_path."""
    async with semaphore:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until='networkidle', timeout=PAGE_TIMEOUT)
            await page.add_style_tag(content=css_text)
            await page.add_style_tag(
                content='@media print { .VPDoc .container, .content-container { max-width: 100%; } }'
            )

            pdf_path = os.path.join(tmp_dir, f'page_{index:04d}.pdf')
            await page.pdf(
                path=pdf_path,
                format='A4',
                print_background=True,
                display_header_footer=True,
                header_template=header_html,
                footer_template='<span></span>',
                margin={
                    'top': '80px',
                    'bottom': '60px',
                    'left': '50px',
                    'right': '50px',
                },
            )
            return pdf_path
        finally:
            await page.close()


async def _render_cover(context, cover_url, tmp_dir):
    """Render cover page to PDF."""
    page = await context.new_page()
    try:
        await page.goto(cover_url, wait_until='networkidle', timeout=PAGE_TIMEOUT)
        pdf_path = os.path.join(tmp_dir, 'cover.pdf')
        await page.pdf(
            path=pdf_path,
            format='A4',
            print_background=True,
            display_header_footer=False,
        )
        return pdf_path
    finally:
        await page.close()


async def _render_toc(context, toc_html, header_html, tmp_dir):
    """Render TOC HTML to PDF."""
    page = await context.new_page()
    try:
        await page.set_content(toc_html, wait_until='networkidle')
        pdf_path = os.path.join(tmp_dir, 'toc.pdf')
        await page.pdf(
            path=pdf_path,
            format='A4',
            print_background=True,
            display_header_footer=True,
            header_template=header_html,
            footer_template='<span></span>',
            margin={
                'top': '80px',
                'bottom': '60px',
                'left': '50px',
                'right': '50px',
            },
        )
        return pdf_path
    finally:
        await page.close()


async def generate_pdf_document(
    url_entries,
    cover_url,
    product_name,
    version_display,
    output_path,
    css_path='vitepress-assets/docs.css',
    concurrency=CONCURRENCY,
):
    """Generate a complete PDF document.

    url_entries: list of {'url': str, 'title': str, 'level': int}
    """
    css_text = _read_css(css_path)
    header_title = f'{product_name} {version_display} Docs'.strip()
    header_html = _build_header_html(header_title)
    semaphore = asyncio.Semaphore(concurrency)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()

        with tempfile.TemporaryDirectory() as tmp_dir:
            # 1. Render cover
            print('Rendering cover page...')
            cover_path = await _render_cover(context, cover_url, tmp_dir)

            # 2. Render all content pages concurrently
            urls = [entry['url'] for entry in url_entries]
            print(f'Rendering {len(urls)} content pages (concurrency={concurrency})...')
            tasks = [
                _render_page(context, url, css_text, header_html, semaphore, tmp_dir, i)
                for i, url in enumerate(urls)
            ]
            pdf_paths = await asyncio.gather(*tasks)

            # 3. Collect page counts per document
            print('Building table of contents...')
            page_counts = []
            for pdf_path in pdf_paths:
                reader = PdfReader(pdf_path)
                page_counts.append(len(reader.pages))

            # 4. Generate TOC with iterative page count adjustment
            cover_pages = len(PdfReader(cover_path).pages)
            toc_pages_estimate = 2

            for iteration in range(3):
                toc_page_offset = cover_pages + toc_pages_estimate

                # Build TOC entries with correct page numbers
                toc_entries = []
                cumulative_page = toc_page_offset
                for i, entry in enumerate(url_entries):
                    toc_entries.append((entry['title'], entry['level'], cumulative_page + 1))
                    cumulative_page += page_counts[i]

                toc_html = _build_toc_html(toc_entries)
                toc_path = await _render_toc(context, toc_html, header_html, tmp_dir)
                actual_toc_pages = len(PdfReader(toc_path).pages)

                if actual_toc_pages == toc_pages_estimate:
                    break
                toc_pages_estimate = actual_toc_pages
                print(f'  TOC iteration {iteration + 1}: {actual_toc_pages} pages')

            # 5. Merge all PDFs
            print('Merging PDFs...')
            writer = PdfWriter()

            for page in PdfReader(cover_path).pages:
                writer.add_page(page)

            for page in PdfReader(toc_path).pages:
                writer.add_page(page)

            for pdf_path in pdf_paths:
                for page in PdfReader(pdf_path).pages:
                    writer.add_page(page)

            # 6. Stamp page numbers (skip cover)
            print('Stamping page numbers...')
            _stamp_page_numbers(writer, skip_pages=cover_pages)

            # 7. Write output
            with open(output_path, 'wb') as f:
                writer.write(f)

            print(f'PDF generated: {output_path}')

        await browser.close()
