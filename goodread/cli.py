# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import click
from .document import DocumentList
from . import helpers


# Main program

@click.command()
@click.argument('paths', nargs=-1)
@click.option('-e', '--edit', is_flag=True)
@click.option('-s', '--sync', is_flag=True)
@click.option('-x', '--exit-first', is_flag=True)
def cli(paths, edit, sync, exit_first):

    # Prepare
    config = helpers.read_config()
    documents = DocumentList(paths, config)

    # Edit
    if edit:
        documents.edit()

    # Sync
    elif sync:
        documents.sync()

    # Test
    else:
        success = documents.test(exit_first=exit_first)
        if not success:
            exit(1)


if __name__ == '__main__':
    cli()
