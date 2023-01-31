import os
import json
import yaml
from awslambdaric.lambda_context import LambdaContext
import subprocess
import shutil


def handler(event, context: LambdaContext):

    os.environ['HOME'] = '/root'

    article = event.get('article')
    block = event.get('block')
    linter_configs = event.get('linter_configs')

    payload_errors = []

    if article and block:
        payload_errors.append('Lambda payload must contain either an article key or a block key')
    if not article and not block:
        payload_errors.append('Lambda payload must contain either an article key or a block key')
    if not linter_configs:
        payload_errors.append('Lambda payload must contain the linter configs to serve as rules')

    if payload_errors:
        return {"payload_errors": payload_errors}


    root = '/tmp'
    files_dir = os.path.join(root, 'files')
    try:
        os.mkdir(files_dir)
    except FileExistsError:
        shutil.rmtree(files_dir)
        os.mkdir(files_dir)
    except Exception as e:
        return 'Fail to create temporary files directory'

    config_dir = os.path.join(root, 'configs')
    try:
        os.mkdir(config_dir)
    except FileExistsError:
        shutil.rmtree(config_dir)
        os.mkdir(config_dir)
    except Exception as e:
        return 'Fail to create temporary config directory'

    for config in event['linter_configs']:
        config_file = config["name"] + '.yml'
        config_filename = os.path.join(config_dir, config_file)
        with open(config_filename, 'w+', encoding='utf-8') as file:
            yaml.dump(config['linter_config'], file)

    if article:
        try:
            for _block in article['doc']['blocks']:
                _block_key = _block['key']
                filename = os.path.join(files_dir, _block_key)
                with open(filename, 'w+') as file:
                    file.write(_block['text'])
        except Exception as e:
            return 'Fail to parse article'

    if block:
        try:
            block_key = block['key']
            filename = os.path.join(files_dir, block_key)
            with open(filename, 'w+') as file:
                file.write(block['text'])
        except Exception as e:
            return 'Fail to parse block'

    try:
        result = subprocess.run(['vale', f'{files_dir}', '--output', 'JSON'], stdout=subprocess.PIPE)
        shutil.rmtree(files_dir)
    except Exception as e:
        return 'Fail to lint content'

    parsed_result: dict = json.loads(result.stdout)
    response_parsed_result = {}
    for key, value in parsed_result.items():
        _key = key.replace(files_dir, '')
        block_key = _key[1:]
        response_parsed_result[block_key] = value

    if article:
        response_dict = {
            'article_id': article['id'],
            'linted_blocks': response_parsed_result
        }
    if block:
        response_dict = {
            'block_key': block['key'],
            'linted_blocks': response_parsed_result
        }

    return response_dict
