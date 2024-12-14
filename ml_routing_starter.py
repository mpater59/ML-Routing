import argparse
import yaml

from traffic_control.emulation.traffic_control_learning import traffic_control_main as emu_env
from traffic_control.simulation.traffic_control_learning import traffic_control_main as sim_env

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-tf', '--topology-file', dest='topo_file', default='topo.yaml',
                        help='Topology file in .yaml format')
    parser.add_argument('-ef', '--environment-file', dest='env_file', default='env.yaml',
                        help='Environment file in .yaml format')
    parser.add_argument('-mn', '--model-name', dest='model_name', default='Test',
                        help='Name of the running model')
    parser.add_argument('-sm', '--save-model', dest='save_model', action='store_true', default=False,
                        help='Save model to .zip file')
    parser.add_argument('-e', '--emulation', dest='emulation', action='store_true', default=False,
                        help='Run model in emulation environment (default: simulation env)')
    parser.add_argument('-dl', '--disable-learning', dest='disable_learning', action='store_true',
                        default=False, help='Disable learning for simulated env (default: false)')
    parser.add_argument('-s', '--seed', dest='seed', type=int, default=None,
                        help='Seed for random function in traffic simulation (default: current timestamp)')
    parser.add_argument('-sr', '--save-results', dest='save_results', action='store_true',
                        default=False, help='Save results for simulated env (default: false)')
    parser.add_argument('-tn', '--timesteps-number', dest='timesteps_number', type=int, default=1000,
                        help='Number of timesteps (default 1000)')
    parser.add_argument('-dar', '--disable-action-reward', dest='disable_action_reward',
                        action='store_true',
                        default=False, help='Run only one loop for learning - only for testing (default: false)')
    args = parser.parse_args()

    topo_info = {}
    with open(args.topo_file) as f:
        try:
            topo_info = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)

    env_info = {}
    with open(args.env_file) as f:
        try:
            env_info = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)

    if args.emulation is True:
        emu_env(topo_info, env_info, args.model_name, args.save_model)
    else:
        sim_env(topo_info, env_info, args.model_name, args.save_model, args.disable_learning, args.seed,
                args.save_results, args.timesteps_number, args.disable_action_reward)
