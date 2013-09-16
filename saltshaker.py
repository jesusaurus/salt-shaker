#!/usr/bin/env python

# Give salt the shakedown

import logging
import optparse
import os
import shutil
import subprocess
import tempfile
import yaml


logging.basicConfig(format='%(asctime)s\t%(name)-16s %(levelname)-8s %(message)s')
logger = logging.getLogger('saltshaker')
logger.setLevel(logging.INFO)


op = optparse.OptionParser()
op.add_option('-l', '--log-level', dest='log_level', type=str,
              default='info', help='Logging output level.')
op.add_option('-s', '--state-dir', dest='state', type=str,
              default='/srv/salt/', help='The state location')
op.add_option('-p', '--pillar-dir', dest='pillar', type=str,
              default='/srv/pillar', help='The pillar location')
op.add_option('-t', '--target', dest='target', type=str,
              default='*', help='Minion target')
op.add_option('-e', '--environment', dest='env', type=str,
              default='base', help='Target environment')
op.add_option('-i', '--id', dest='default_id', type=str,
              default='salt-minion', help='Default minion id to use')
op.add_option('-I', '--id-map', dest='mapfile', type=str,
              default='id.map', help='File containing a mapping from states '
              'to arbitrary id strings.')
options, args = op.parse_args()

if options.log_level.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                 'CRITICAL']:
    logger.setLevel(getattr(logging, options.log_level.upper()))


# create config file with given state/pillar dir
tempdir = tempfile.mkdtemp()
conffile = open(os.path.join(tempdir, 'minion'), 'w')
os.makedirs(os.path.join(tempdir, 'cache'))
os.makedirs(os.path.join(tempdir, 'pki', 'minion'))

config = '''
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
'''.format(options.env,
        os.path.abspath(options.state),
        os.path.abspath(options.pillar),
        tempdir,
    )

logger.debug("Config file:\n" + config)
conffile.write(config)
conffile.close()

id_map = {}
if os.path.isfile(options.mapfile):
    id_map = yaml.safe_load(options.mapfile)

with open(os.path.join(options.state, "top.sls")) as _top_file:
    state_top = yaml.safe_load(_top_file)

    for env, mapping in state_top.iteritems():
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
                    command = [
                            'salt-call',
                            '--local',
                            '--log-level', options.log_level,
                            '--log-file', './shaker.log',
                            '--config-dir', tempdir,
                            '--id', minion_id,
                            'state.sls', state,
                            'env={0}'.format(env),
                            'test=True',
                    ]
                    logger.info(' '.join(command))

                    proc = subprocess.Popen(
                            command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                    )
                    (out, err) = proc.communicate()
                    logger.warning(out)
                    logger.error(err)

shutil.rmtree(tempdir)
