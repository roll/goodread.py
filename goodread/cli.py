# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import sys
import click
import traceback
from emoji import emojize


# Helpers

def parse_document(path):
    elements = []
    codeblock = ''
    capture = False

    # Parse file lines
    with io.open(path, encoding='utf-8') as file:
        for line in file:

            # Heading
            if line.startswith('#'):
                heading = line.strip('#\n ')
                if not elements or elements[-1]['type'] == 'codeblock':
                    elements.append({
                        'type': 'heading',
                        'value': heading,
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


def test_document(elements):
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
            report(element['value'], type='heading')
            if title is None:
                title = element['value']

        # Codeblock
        elif element['type'] == 'codeblock':
            exception_line = 1000  # infinity
            try:
                exec(instrument(element['value']), scope)
            except Exception:
                _, exception, tb = sys.exc_info()
                exception_line = traceback.extract_tb(tb)[-1][1]
            for line_number, line in enumerate(element['value'].strip().split('\n'), start=1):
                if line_number < exception_line:
                    report(line, type='success')
                    passed += 1
                elif line_number == exception_line:
                    report(line, type='failure', exception=exception)
                    failed += 1
                elif line_number > exception_line:
                    report(line, type='skipped')
                    skipped += 1

    # Report summary
    if title is not None:
        report(title, type='summary', passed=passed, failed=failed, skipped=skipped)

    return exception is None


def instrument(codeblock):
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
    return '\n'.join(lines)


def report(text, type, exception=None, passed=None, failed=None, skipped=None):
    message = None
    if type == 'heading':
        message = click.style(emojize('\n #  ', use_aliases=True))
        message += click.style('%s\n' % text, bold=True)
    elif type == 'success':
        message = click.style(emojize(' :heavy_check_mark:  ', use_aliases=True), fg='green')
        message += click.style('%s' % text)
    elif type == 'failure':
        message = click.style(emojize(' :x:  ', use_aliases=True), fg='red')
        message += click.style('%s\n' % text)
        message += click.style('Exception: %s' % exception, fg='red', bold=True)
    elif type == 'skipped':
        message = click.style(emojize(' :heavy_minus_sign:  ', use_aliases=True), fg='yellow')
        message += click.style('%s' % text)
    elif type == 'summary':
        color = 'green'
        message = click.style(emojize('\n :heavy_check_mark:  ', use_aliases=True), fg='green', bold=True)
        if (failed + skipped) > 0:
            color = 'red'
            message = click.style(emojize('\n :x:  ', use_aliases=True), fg='red', bold=True)
        message += click.style('%s: %s/%s\n' % (text, passed, passed + failed + skipped), bold=True, fg=color)
    if message:
        click.echo(message)


# Main program

@click.command()
@click.argument('path', required=False, default='README.md')
def cli(path):
    elements = parse_document(path)
    success = test_document(elements)
    if not success:
        exit(1)


if __name__ == '__main__':
    cli()
