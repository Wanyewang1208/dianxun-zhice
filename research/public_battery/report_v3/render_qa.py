"""Rasterize Word-exported PDFs for mandatory page-by-page visual inspection."""
import argparse
import json
from pathlib import Path
import pypdfium2 as pdfium


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    results = []
    for path in args.directory.glob('*.pdf'):
        document = pdfium.PdfDocument(path)
        pages = args.directory / path.stem
        pages.mkdir(exist_ok=True)
        texts = []
        for i in range(len(document)):
            page = document[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            texts.append(text)
            page.render(scale=1.5).to_pil().save(pages / f'page-{i+1:02}.png')
            textpage.close()
            page.close()
        (pages / 'text.txt').write_text('\n\n'.join(texts), encoding='utf-8')
        results.append({'document': path.stem, 'pages': len(document),
                        'page_text_lengths': [len(t.strip()) for t in texts],
                        'visual_inspection_complete': False})
        document.close()
    (args.directory / 'render_summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__': main()
