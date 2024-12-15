import logging
import os
import shutil

from traffic_control.simulation.sdn_env import SDN_env
from stable_baselines3 import PPO
from stable_baselines3.common.logger import configure
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv


# GLOBALS
LOGGER = logging


def traffic_control_main(topo_info, env_file, model_name, save_model, disable_learning, seed, save_results, timesteps,
                         disable_action_reward):

    log_file = f"traffic_control/simulation/logs/{model_name}.log"
    tensor_log_file = f"traffic_control/simulation/logs/{model_name}_tensor.log"
    model_log_file = f"traffic_control/simulation/logs/{model_name}_model_logs"
    model_file = f"traffic_control/saved_models/{model_name}.zip"
    result_path = f"measurements/simulation/results/{model_name}/"
    if os.path.exists(result_path) and save_results is True:
        shutil.rmtree(result_path)
    if save_results is True:
        os.makedirs(result_path)
    LOGGER.basicConfig(
        filename=log_file,
        filemode='a',
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logging.info("Initializing the SDN environment")
    env = SDN_env(topo_info, env_file, disable_action_reward, seed, result_path, save_results)

    # print(env.state)
    # print(env.ospf_paths)
    # print(env.topo_paths)
    # print(env.link_loads)
    # print(env.current_connections)
    # exit()
    if disable_learning is True:
        vec_env = make_vec_env(lambda: env, n_envs=1)
    else:
        vec_env = make_vec_env(lambda: env, n_envs=16, vec_env_cls=SubprocVecEnv)

    total_timesteps = timesteps

    logging.info("Initializing the DQN model")
    if os.path.isfile(model_file):
        model = PPO.load(model_file, env=vec_env)
        logging.info(f"Model loaded successfully from {model_file}. Continuing training")
    else:
        model = PPO(
            "MultiInputPolicy",  # "MlpPolicy",
            vec_env,
            verbose=2,
            learning_rate=0.0003,
            n_steps=2048,
            batch_size=1024,
            n_epochs=10,
            gamma=0.7,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            tensorboard_log=tensor_log_file,
            device="cuda"
        )
        with open(log_file, 'w') as _:
            pass
        logging.info(f"No model found at {model_file}. Creating a new model")

    model_logger = configure(model_log_file, ["stdout", "log", "csv", "tensorboard"])
    model.set_logger(model_logger)

    try:
        logging.info("Starting online learning. Press Ctrl+C to terminate")
        while True:
            model.learn(total_timesteps=total_timesteps, reset_num_timesteps=False)
            logging.info(f"Completed {total_timesteps} timesteps of learning")
            if save_model is True:
                logging.info(f"Saving model to {model_file}")
                model.save(model_file)
                logging.info("Model saved successfully")
            if disable_learning is True:
                break
    except KeyboardInterrupt:
        logging.info("Online learning stopped")

    if save_model is True:
        logging.info(f"Saving model to {model_file}")
        model.save(model_file)
        logging.info("Model saved successfully")
