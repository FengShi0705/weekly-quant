from pathlib import Path

import yaml


def load_config(path="config.yaml"):
    path = Path(path).resolve()
    with open(path) as f:
        cfg = yaml.safe_load(f)
    root = path.parent
    cfg["_root"] = root
    cfg["universe"]["file"] = root / cfg["universe"]["file"]
    cfg["data"]["cache_dir"] = root / cfg["data"]["cache_dir"]
    cfg["paths"]["reports"] = root / cfg["paths"]["reports"]
    cfg["paths"]["holdings"] = root / cfg["paths"]["holdings"]
    cfg["paths"]["score_history"] = root / cfg["paths"]["score_history"]
    return cfg
