# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import sys
import six
import yaml
import click
import traceback
from emoji import emojize
state = {'last_message_type': None}


# Module API

def read_config():
    config = {'documents': ['README.md']}
    if os.path.isfile('goodread.yml'):
        with io.open('goodread.yml', encoding='utf-8') as file:
            config = yaml.load(file.read())
    for index, document in enumerate(config['documents']):
        if isinstance(document, dict):
            if 'main' not in document:
                raise Exception('Document requires "main" property')
        if isinstance(document, six.string_types):
            config['documents'][index] = {'main': document}
    return config


def run_codeblock(codeblock, scope):
    lines = []
    for line in codeblock.strip().split('\n'):
        if ' # ' in line:
            left, right = line.split(' # ')
            left = left.strip()
            right = right.strip()
            if left and right:
                message = '%s != %s' % (left, right)
                line = 'assert %s == %s, "%s"' % (left, right, message)
        lines.append(line)
    exception_line = 1000  # infinity
    exception = None
    try:
        exec('\n'.join(lines), scope)
    except Exception:
        _, exception, tb = sys.exc_info()
        exception_line = traceback.extract_tb(tb)[-1][1]
    return [exception, exception_line]


def print_message(message, type, level=None, exception=None, passed=None, failed=None, skipped=None):
    text = ''
    if type == 'blank':
        return click.echo('')
    elif type == 'separator':
        text = click.style(emojize(':heavy_minus_sign:'*3, use_aliases=True))
    elif type == 'heading':
        text = click.style(emojize(' %s ' % ('#' * (level or 1)), use_aliases=True))
        text += click.style('%s' % message, bold=True)
    elif type == 'success':
        text = click.style(emojize(' :heavy_check_mark:  ', use_aliases=True), fg='green')
        text += click.style('%s' % message)
    elif type == 'failure':
        text = click.style(emojize(' :x:  ', use_aliases=True), fg='red')
        text += click.style('%s\n' % message)
        text += click.style('Exception: %s' % exception, fg='red', bold=True)
    elif type == 'scope':
        text += '---\n\n'
        text += 'Scope (current execution scope):\n'
        text += '%s\n' % list(message)
        text += '\n---\n'
    elif type == 'skipped':
        text = click.style(emojize(' :heavy_minus_sign:  ', use_aliases=True), fg='yellow')
        text += click.style('%s' % message)
    elif type == 'summary':
        color = 'green'
        text = click.style(emojize(' :heavy_check_mark:  ', use_aliases=True), fg='green', bold=True)
        if (failed + skipped) > 0:
            color = 'red'
            text = click.style(emojize(' :x:  ', use_aliases=True), fg='red', bold=True)
        text += click.style('%s: %s/%s' % (message, passed, passed + failed + skipped), bold=True, fg=color)
    if type in ['success', 'failure', 'skipped']:
        type = 'test'
    if text:
        if state['last_message_type'] != type:
            text = '\n' + text
        click.echo(text)
    state['last_message_type'] = type
