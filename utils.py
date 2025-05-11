
def get_site_config(site_name, lang, version):
    if version.startswith('v'):
        version = version[1:]

    config_dict = {
        'emqx': {
            'name': 'EMQX',
            'directory_url': 'https://assets.emqx.com/data/json/ce-{version}.json',
            'base_url': f'https://docs.emqx.com/{lang}/emqx/v{version}/'
        },
        'enterprise': {
            'name': 'EMQX Enterprise',
            'directory_url': 'https://assets.emqx.com/data/json/ee-{version}.json',
            'base_url': f'https://docs.emqx.com/{lang}/enterprise/v{version}/'
        },
        'ekuiper': {
            'name': 'eKuiper',
            'directory_url': 'https://raw.githubusercontent.com/lf-edge/ekuiper/master/docs/directory.json',
            'base_url': f'https://ekuiper.org/docs/{lang}/latest/'
        },
        'neuron': {
            'name': 'Neuron',
            'directory_url': 'https://raw.githubusercontent.com/emqx/neuron-docs/master/directory.json',
            'base_url': f'https://docs.emqx.com/{lang}/neuron/latest/'
        },
        'neuronex': {
            'name': 'NeuronEX',
            'directory_url': 'https://raw.githubusercontent.com/emqx/neuronex-docs/master/directory.json',
            'base_url': f'https://docs.emqx.com/{lang}/neuronex/latest/'
        },
        'cloud': {
            'name': 'EMQX Platform',
            'directory_url': 'https://raw.githubusercontent.com/emqx/cloud-docs/refs/heads/master/directory.json',
            'base_url': f'https://docs.emqx.com/{lang}/cloud/latest/'
        },
        'nanomq': {
            'name': 'NanoMQ',
            'directory_url': 'https://raw.githubusercontent.com/nanomq/nanomq/master/docs/directory.json',
            'base_url': f'https://nanomq.io/docs/{lang}/latest/'
        },
        'emqx-ecp': {
            'name': 'EMQX ECP',
            'directory_url': 'https://raw.githubusercontent.com/emqx/emqx-ecp-docs/refs/heads/main/ecp/directory.json',
            'base_url': f'https://docs.emqx.com/{lang}/emqx-ecp/latest/'
        } 
    }

    if site_name not in config_dict:
        raise ValueError(f'Invalid site name: {site_name}')

    return config_dict[site_name]


def get_children_url(_d):
    urls = []
    for _path in _d:
        if _path.get('path'):
            if _path['path'].startswith('http://') or _path['path'].startswith('https://'):
                continue
            urls.append(_path['path'])
        if _path.get('children'):
            urls.extend(get_children_url(_path['children']))
    return urls
