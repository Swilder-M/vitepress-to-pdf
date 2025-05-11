import argparse
import requests
import pdfkit

from utils import get_children_url, get_site_config


def get_urls_from_config(directory_url, base_url, lang):
    directory_config = requests.get(directory_url).json()
    if lang == 'zh':
        directory_config = directory_config['cn']
    else:
        directory_config = directory_config[lang]

    all_path = get_children_url(directory_config)
    all_urls = []

    for _path in all_path:
        if 'release_notes/' in _path:
            continue
        if _path == './':
            _full_url = base_url
        else:
            if _path.lower().endswith('.md'):
                _path = ''.join(_path.split('.md')[:-1])
            _full_url = base_url + _path + '.html'
        all_urls.append(_full_url)
    return all_urls


def gen_pdf(product, version, lang='zh'):
    site_config = get_site_config(product, lang, version)
    product_name = site_config['name']
    directory_url = site_config['directory_url']
    base_url = site_config['base_url']

    urls = get_urls_from_config(directory_url, base_url, lang)
    print('Urls:')
    for i in urls:
        print(i)

    version = version.replace('v', '')
    if version == 'latest':
        version_display = ''
    else:
        version_display = 'V' + version

    options = {
        'print-media-type': None,
        'user-style-sheet': 'vitepress-assets/docs.css',
        'dump-outline': 'vitepress-assets/toc.xml',
        'enable-local-file-access': None,
        'javascript-delay': 10000,
        'header-center': f'{product_name} {version_display} Docs',
        'header-font-size': 10,
        'header-spacing': 5,
        'footer-center': '[page] / [topage]',
        'footer-font-size': 8,
        'page-offset': -1,
        # 'enable-internal-links': None,
        # 'keep-relative-links': None
        # 'dump-default-toc-xsl': None
    }
    toc = {
        'xsl-style-sheet': 'vitepress-assets/toc.xsl'
    }
    cover = f'https://doc-cover.iotworker.com/?product={product_name}'

    kit = pdfkit.PDFKit(urls, 'url', options=options, verbose=True,
             toc=toc, cover=cover, cover_first=True)
    print('Command:')
    print(' '.join(kit.command()))

    pdfkit.from_url(urls, f'{product}-{version}-{lang}.pdf',
             options=options, verbose=True,
             toc=toc, cover=cover, cover_first=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate PDF For Vitepress')
    parser.add_argument('--product', type=str, help='product name', required=True)
    parser.add_argument('--version', type=str, help='product version', required=True)
    parser.add_argument('--lang', type=str, help='language', required=True)
    args = parser.parse_args()
    gen_pdf(args.product, args.version, args.lang)
