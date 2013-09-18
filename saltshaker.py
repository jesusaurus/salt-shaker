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


import optparse
import os
import salt.client
import shutil
import subprocess
import tempfile
import yaml


log_levels = ['debug', 'info', 'warning', 'error', 'critical']

op = optparse.OptionParser()
op.add_option('-l', '--log-level', dest='log_level', choices=log_levels,
              default='info', help='Logging output level.')
op.add_option('-s', '--state-dir', dest='state', type=str,
              default='/srv/salt/', help='The state location')
op.add_option('-p', '--pillar-dir', dest='pillar', type=str,
              default='/srv/pillar', help='The pillar location')
op.add_option('-e', '--environment', dest='env', type=str,
              default='base', help='Target environment')
op.add_option('-i', '--id', dest='default_id', type=str,
              default='salt-minion', help='Default minion id to use')
op.add_option('-I', '--id-map', dest='mapfile', type=str,
              default='id.map', help='File containing a mapping from states '
              'to arbitrary id strings.')
op.add_option('-n', '--test', '--dry-run', '--no', dest='test', action='store_true',
              default=False, help='Don\'t actually run any commands')
op.add_option('-L', '--log-file', dest='log_file', type=str,
              default='/tmp/saltshaker.log', help='The log file location')
options, args = op.parse_args()

logger.setLevel(getattr(logging, options.log_level.upper()))

salt_log = logging.getLogger('salt')
salt_log.setLevel(options.log_level.upper())


# create config file with given state/pillar dir
tempdir = tempfile.mkdtemp()
conffile = open(os.path.join(tempdir, 'minion'), 'w')
os.makedirs(os.path.join(tempdir, 'cache'))
os.makedirs(os.path.join(tempdir, 'pki', 'minion'))

config = '''
test: True
state_verbose: False
state_output: full

file_client: local
file_roots:
  {0}:
    - {1}
pillar_roots:
  {0}:
    - {2}

pki_dir: {3}/pki/minion
cachedir: {3}/cache

log_level: {4}
log_level_logfile: {4}
log_file: {5}
'''.format(options.env,
        os.path.abspath(options.state),
        os.path.abspath(options.pillar),
        tempdir,
        options.log_level,
        os.path.abspath(options.log_file),
    )

logger.debug("Config file:\n" + config)
conffile.write(config)
conffile.close()

id_map = {}
if os.path.isfile(options.mapfile):
    with open(options.mapfile, 'r') as mapfile:
        id_map = yaml.safe_load(mapfile)
    logger.debug("ID map:\n" + yaml.safe_dump(id_map))


# Here's where we do the actual work
with open(os.path.join(options.state, "top.sls")) as _top_file:
    state_top = yaml.safe_load(_top_file)

    for env, mapping in state_top.iteritems():
        if env != options.env:
            continue

        for target, states in mapping.iteritems():
            for state in states:
                if state in id_map:
                    if isinstance(id_map[state], list):
                        ids = id_map[state]
                    else:
                        ids = [ id_map[state], ]
                else:
                    ids = [ options.default_id, ]
                for minion_id in ids:
                    logger.info('Prepping salt minion id {0}'.format(minion_id, env))
                    salt_call = salt.client.Caller(c_path=os.path.join(tempdir, 'minion'))
                    salt_call.opts['id'] = minion_id
                    if not options.test:
                        logger.warning('Testing state {0} with minion id {1} and '
                                       'environment {2}'.format(state, minion_id, env))
                        salt_call.function('state.sls', state, env=env, test=True)

logger.info('Removing tempdir')
shutil.rmtree(tempdir)
