import logging
import optparse
import yaml


logging.basicConfig(format='%(asctime)s\t%(name)-16s %(levelname)-8s %(message)s')
logger = logging.getLogger('saltshaker')
logger.setLevel(logging.INFO)


op = optparse.OptionParser()
op.add_option('-l', '--log-level', dest='log_level', type=str,
              default='info', help='Logging output level.')
op.add_option('-s', '--state-top', dest='state', type=str,
              default='state/top.sls', help='Location of the state top file')
op.add_option('-p', '--pillar-top', dest='pillar', type=str,
              default='pillar/top.sls', help='Location of the pillar top file')
op.add_option('-t', '--target', dest='target', type=str,
              default='*', help='Minion target')
options, args = op.parse_args()

if options.log_level.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR',
                                 'CRITICAL']:
    logger.setLevel(getattr(logging, options.log_level.upper()))


with open(options.state) as _top_file:
    state_top = yaml.safe_load(_top_file)

    for env, mapping in state_top.iteritems():
        for target, states in mapping.iteritems():
            for state in states:
                logger.info(
                        "salt-call --local '{0}' state.sls {1} env={2} "
                        "test=True".format(target, state, env)
                )
