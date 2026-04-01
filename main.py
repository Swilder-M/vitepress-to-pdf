import argparse
import asyncio

import requests

from pdf_generator import generate_pdf_document
from utils import get_children_url, get_site_config


def get_urls_from_config(directory_url, base_url, lang):
    print(f'Getting urls from {directory_url}')
    directory_config = requests.get(directory_url).json()
    if lang == 'zh':
        directory_config = directory_config['cn']
    else:
        directory_config = directory_config[lang]

    all_items = get_children_url(directory_config)
    url_entries = []

    for item in all_items:
        _path = item['path']
        if 'release_notes/' in _path:
            continue
        if _path == './':
            _full_url = base_url
        else:
            if _path.lower().endswith('.md'):
                _path = ''.join(_path.split('.md')[:-1])
            _full_url = base_url + _path + '.html'
        url_entries.append({
            'url': _full_url,
            'title': item['title'],
            'level': item['level'],
        })
    return url_entries


def gen_pdf(product, version, lang='zh'):
    site_config = get_site_config(product, lang, version)
    product_name = site_config['name']
    directory_url = site_config['directory_url']
    base_url = site_config['base_url']

    url_entries = get_urls_from_config(directory_url, base_url, lang)
    print(f'Total urls: {len(url_entries)}')

    version = version.replace('v', '')
    if version == 'latest':
        version_display = ''
    else:
        version_display = 'V' + version

    output_path = f'{product}-{version}-{lang}.pdf'

    asyncio.run(generate_pdf_document(
        url_entries=url_entries,
        product_name=product_name,
        version_display=version_display,
        output_path=output_path,
    ))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate PDF For Vitepress')
    parser.add_argument('--product', type=str, help='product name', required=True)
    parser.add_argument('--version', type=str, help='product version', required=True)
    parser.add_argument('--lang', type=str, help='language', required=True)
    args = parser.parse_args()
    gen_pdf(args.product, args.version, args.lang)
