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


log_levels = ['debug', 'info', 'warning', 'error', 'critical']

op = optparse.OptionParser()
op.add_option('-l', '--log-level', dest='log_level', choices=log_levels,
              default='info', help='Logging output level for salt-shaker.')
op.add_option('-L', '--salt-log-level', dest='salt_log_level', choices=log_levels,
              default='critical', help='Logging output level for salt core.')
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
op.add_option('-I', '--id-map', dest='mapfile', type=str,
              default='id.map', help='File containing a mapping from states '
              'to arbitrary id strings.')
op.add_option('-n', '--test', '--dry-run', '--no', dest='test', action='store_true',
              default=False, help='Don\'t actually run any commands')
op.add_option('-f', '--log-file', dest='log_file', type=str,
              default='/tmp/saltshaker.log', help='The log file location')
options, args = op.parse_args()

logger.setLevel(getattr(logging, options.log_level.upper()))

salt_log = logging.getLogger('salt')
salt_log.setLevel(options.salt_log_level.upper())


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
    'log_level': options.salt_log_level,
    'log_level_logfile': options.salt_log_level,
    'log_file': os.path.abspath(options.log_file),
    'extension_modules': os.path.join(tempdir, 'extmods'),
})
logger.debug('opts dict:\n' + yaml.safe_dump(opts))


id_map = {}
if os.path.isfile(options.mapfile):
    with open(options.mapfile, 'r') as mapfile:
        id_map = yaml.safe_load(mapfile)
    logger.debug("ID map:\n" + yaml.safe_dump(id_map))
else:
    logger.debug("Minion ID: " + options.default_id)


# Here's where we do the actual work
state_list = []
for state in options.state:
    _top_path = os.path.join(state, "top.sls")
    if not os.path.exists(_top_path):
        continue
    logger.info("Loading " + _top_path)
    with open(_top_path) as _top_file:
        state_top = yaml.safe_load(_top_file)
        for env, match in state_top.iteritems():
            for minion, state in match.iteritems():
                state_list.extend(state)
logger.debug("States: \n{0}".format(state_list))

if state_list:
    for state in state_list:
        if state in id_map:
            if isinstance(id_map[state], list):
                ids = id_map[state]
            else:
                ids = [ id_map[state], ]
        else:
            ids = [ options.default_id, ]

        for minion_id in ids:
            logger.info('Prepping salt minion id {0}'.format(minion_id))
            opts['id'] = minion_id
            salt_call = saltshaker.caller.ShakerCaller(opts)
            pillar = salt_call.function('pillar.items')
            logger.debug('Pillar: \n{0}'.format(yaml.dump(pillar)))
            if not options.test:
                logger.warning('Testing state {0} with minion id {1} and '
                               'environment {2}'.format(state, minion_id, env))
                salt_call.function('state.sls', state, env=env, test=True)
            del pillar
            del salt_call
else:
    logger.warning('No states found')


# Clean up the tempdir
logger.info('Removing tempdir')
shutil.rmtree(tempdir)
