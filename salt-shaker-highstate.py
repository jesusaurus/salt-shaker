#!/usr/bin/env python

# Copyright 2012-2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

# Give salt the shakedown


# Don't let other modules highjack the logging
# I'm looking at you, salt.client
import logging
logging.basicConfig(format='%(asctime)s\t%(name)-16s %(levelname)-8s %(message)s')
logger = logging.getLogger('saltshaker')
logger.setLevel(logging.INFO)


import saltshaker.caller


import optparse
import os
import salt.config
import shutil
import subprocess
import tempfile
import yaml


def test_minion_id(minion_id):
    logger.info("Testing salt highstate on : %s" % minion_id)
    # create a tempdir to run from
    tempdir = tempfile.mkdtemp()
    os.makedirs(os.path.join(tempdir, 'cache'))
    os.makedirs(os.path.join(tempdir, 'pki', 'minion'))

    opts = salt.config.DEFAULT_MINION_OPTS
    opts.update({
        'test': True,
        'state_verbose': False,
        'state_output': 'full',
        'file_client': 'local',
        'file_roots': { options.env: [
            os.path.abspath(path) for path in options.state ] },
        'pillar_roots': { options.env: [
            os.path.abspath(path) for path in options.pillar ] },
        'pillar_opts': False,
        'pki_dir': os.path.join(tempdir, 'pki', 'minion'),
        'cachedir': os.path.join(tempdir, 'cache'),
        'log_level': options.log_level,
        'log_level_logfile': options.log_level,
        'log_file': os.path.abspath(options.log_file),
        'extension_modules': os.path.join(tempdir, 'extmods'),
    })
    opts['id'] = minion_id.strip()

    salt_call = saltshaker.caller.ShakerCaller(opts)
    pillar = salt_call.function('pillar.items')
    logger.info('Pillar: \n{0}'.format(yaml.dump(pillar)))
    logger.warning('Testing highstate with minion id {0} '.format(minion_id))

    salt_call.function('state.highstate', test=True)


    del pillar
    del salt_call

    logger.info('Removing tempdir')
    shutil.rmtree(tempdir)


log_levels = ['debug', 'info', 'warning', 'error', 'critical']

op = optparse.OptionParser()
op.add_option('-l', '--log-level', dest='log_level', choices=log_levels,
              default='info', help='Logging output level.')
op.add_option('-s', '--state-dir', dest='state', type=str, action='append',
              default=['/srv/salt/'], help='The state location(s), '
              'can be specified multiple times.')
op.add_option('-p', '--pillar-dir', dest='pillar', type=str, action='append',
              default=['/srv/pillar'], help='The pillar location(s), '
              'can be specified multiple times.')
op.add_option('-e', '--environment', dest='env', type=str,
              default='base', help='Target environment')
op.add_option('-i', '--id', dest='default_id', type=str,
              default='salt-minion', help='Default minion id to use')
op.add_option('-I', '--id-list', dest='id_list_file', type=str,
              default='id.list', help='File containing a list of minion ids')
op.add_option('-n', '--test', '--dry-run', '--no', dest='test', action='store_true',
              default=False, help='Don\'t actually run any commands')
op.add_option('-L', '--log-file', dest='log_file', type=str,
              default='/tmp/saltshaker.log', help='The log file location')
options, args = op.parse_args()

logger.setLevel(getattr(logging, options.log_level.upper()))

salt_log = logging.getLogger('salt')
salt_log.setLevel(options.log_level.upper())

id_list = []
if os.path.isfile(options.id_list_file):
    with open(options.id_list_file, 'r') as key_id_list:
        for key_id in key_id_list:
            test_minion_id(key_id)
else:
    logger.info("Minion ID: " + options.default_id)
    test_minion_id(options.default_id)
