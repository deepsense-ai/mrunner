# -*- coding: utf-8 -*-


def load_neptune_config(neptune_config_path):
    from deepsense.neptune.common.config import neptune_config

    global_config = neptune_config.load_global_config()
    local_config = neptune_config.load_local_config(neptune_config_path)
    neptune_config = neptune_config.NeptuneConfig(global_config=global_config, local_config=local_config)

    if len(neptune_config.name) > 16:
        raise ValueError('Neptune config "name" key (experiment name) shall be at most 16 chars long')

    return neptune_config


def neptune_config_to_dict(neptune_config):
    from deepsense.neptune.common.config.job_config import ConfigKeys
    neptune_config_dict = {
        key: neptune_config.config_dict[key]
        for key in ConfigKeys.NEPTUNE_CONFIG
        if key in neptune_config.config_dict and neptune_config.config_dict[key] is not None
    }
    return neptune_config_dict
