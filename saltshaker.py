#!/usr/bin/env python

# Give salt the shakedown

import logging
import optparse
import os
import shutil
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
options, args = op.parse_args()

if options.log_level.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                 'CRITICAL']:
    logger.setLevel(getattr(logging, options.log_level.upper()))


# create config file with given state/pillar dir
tempdir = tempfile.mkdtemp()
conffile = open(os.path.join(tempdir, 'minion'), 'w')

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
'''.format(options.env,
        os.path.abspath(options.state),
        os.path.abspath(options.pillar)
    )

logger.debug("Config file:\n" + config)
conffile.write(config)
conffile.close()

with open(options.state + "top.sls") as _top_file:
    state_top = yaml.safe_load(_top_file)

    for env, mapping in state_top.iteritems():
        for target, states in mapping.iteritems():
            for state in states:
                logger.info(
                        # TODO: match against needed pillar for each state
                        # maybe by setting the id to the target?
                        "salt-call --local --config-dir {0} "
                        "state.sls {1} env={2} test=True".format(
                            tempdir,
                            state,
                            env
                        )
                )

shutil.rmtree(tempdir)
