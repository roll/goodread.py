# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import sys
import requests
import traceback
import subprocess
from . import helpers


# Module API

class DocumentList(object):

    # Public

    def __init__(self, paths, config):
        self._documents = []
        config = helpers.read_config()
        for path in paths or [item['main'] for item in config['documents']] or ['README.md']:
            main_path = path
            edit_path = None
            sync_path = None
            for item in config['documents']:
                if path == item['main']:
                    edit_path = item.get('edit')
                    sync_path = item.get('sync')
                    break
            document = Document(main_path, edit_path=edit_path, sync_path=sync_path)
            self._documents.append(document)

    def edit(self):
        for document in self._documents:
            document.edit()

    def sync(self):
        success = True
        for document in self._documents:
            valid = document.test(sync=True)
            success = success and valid
            if valid:
                document.sync()
        return success

    def test(self, exit_first=False):
        success = True
        for number, document in enumerate(self._documents, start=1):
            valid = document.test(exit_first=exit_first)
            success = success and valid
            helpers.print_message(None,
                type=('separator' if number < len(self._documents) else 'blank'))
        return success


class Document(object):

    # Public

    def __init__(self, main_path, edit_path=None, sync_path=None):
        self._main_path = main_path
        self._edit_path = edit_path
        self._sync_path = sync_path

    def edit(self):

        # No edit path
        if not self._edit_path:
            return

        # Check synced
        if self._main_path != self._edit_path:
            main_contents = _load_document(self._main_path)
            sync_contents = _load_document(self._sync_path)
            if main_contents != sync_contents:
                raise Exception('Document "%s" is out of sync' % self._edit_path)

        # Remote document
        if not self._edit_path.startswith('http'):
            subprocess.run(['editor', self._edit_path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Local document
        else:
            subprocess.run(['xdg-open', self._edit_path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def sync(self):

        # No sync path
        if not self._sync_path:
            return

        # Remote document
        if self._main_path.startswith('http'):
            raise Exception('Remote document can not be synced')

        # Save remote to local
        contents = requests.get(self._sync_path).text
        with io.open(self._main_path, 'w', encoding='utf-8') as file:
            file.write(contents)

    def test(self, sync=False, report=False, exit_first=False):

        # No test path
        path = self._sync_path if sync else self._main_path
        if not path:
            return True

        # Test document
        contents = _load_document(path)
        elements = _parse_document(contents)
        report = _validate_document(elements, exit_first=exit_first)

        return report if report else report['valid']


# Internal

def _load_document(path):

    # Remote document
    if path.startswith('http'):
        return requests.get(path).text

    # Local document
    else:
        with io.open(path, encoding='utf-8') as file:
            return file.read()


def _parse_document(contents):
    elements = []
    codeblock = ''
    capture = False

    # Parse file lines
    for line in contents.splitlines(True):

        # Heading
        if line.startswith('#'):
            heading = line.strip(' #\n')
            level = len(line) - len(line.lstrip('#'))
            if (elements and
                    elements[-1]['type'] == 'heading' and
                    elements[-1]['level'] == level):
                continue
            elements.append({
                'type': 'heading',
                'value': heading,
                'level': level,
            })

        # Codeblock
        if line.startswith('```python'):
            if 'goodread' in line:
                capture = True
            codeblock = ''
            continue
        if line.startswith('```'):
            if capture:
                elements.append({
                    'type': 'codeblock',
                    'value': codeblock,
                })
            capture = False
        if capture:
            codeblock += line
            continue

    return elements


def _validate_document(elements, exit_first=False):
    scope = {}
    passed = 0
    failed = 0
    skipped = 0
    title = None
    exception = None

    # Test elements
    for element in elements:

        # Heading
        if element['type'] == 'heading':
            helpers.print_message(element['value'],
                type='heading', level=element['level'])
            if title is None:
                title = element['value']
                helpers.print_message(None, type='separator')

        # Codeblock
        elif element['type'] == 'codeblock':
            exception_line = 1000  # infinity
            try:
                exec(helpers.instrument_codeblock(element['value']), scope)
            except Exception:
                _, exception, tb = sys.exc_info()
                exception_line = traceback.extract_tb(tb)[-1][1]
            lines = element['value'].strip().splitlines()
            for line_number, line in enumerate(lines, start=1):
                if line_number < exception_line:
                    helpers.print_message(line, type='success')
                    passed += 1
                elif line_number == exception_line:
                    helpers.print_message(line, type='failure', exception=exception)
                    if exit_first:
                        helpers.print_message(scope, type='scope')
                        raise exception
                    failed += 1
                elif line_number > exception_line:
                    helpers.print_message(line, type='skipped')
                    skipped += 1

    # Print summary
    if title is not None:
        helpers.print_message(title,
            type='summary', passed=passed, failed=failed, skipped=skipped)

    return {
        'valid': exception is None,
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
    }
