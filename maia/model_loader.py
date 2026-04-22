import yaml
import os

from .tourney import RandomEngine, StockfishEngine, LC0Engine


def load_model_config(config_dir_path, lc0_depth=None, lc0Path=None, noise=False, temperature=0, temp_decay=0):
    with open(os.path.join(config_dir_path, 'config.yaml')) as f:
        config = yaml.safe_load(f.read())

    engine_type = config['engine']
    options = config.get('options', {}).copy()

    if engine_type == 'stockfish':
        model = StockfishEngine(**options)
    elif engine_type == 'random':
        model = RandomEngine()
    elif engine_type in ('lc0', 'lc0_23'):
        if lc0_depth is not None:
            options['nodes'] = lc0_depth
            options['movetime'] = options.get('movetime', 10) * lc0_depth / 10
        options['weightsPath'] = os.path.join(config_dir_path, options['weightsPath'])
        model = LC0Engine(
            lc0Path=lc0Path if lc0Path is not None else 'lc0',
            noise=noise,
            temperature=temperature,
            temp_decay=temp_decay,
            **options,
        )
    else:
        raise NotImplementedError(f"{engine_type} is not a known engine type")

    return model, config
