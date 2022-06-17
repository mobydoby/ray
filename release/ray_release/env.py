import os

from ray_release.exception import ReleaseTestConfigError

DEFAULT_ENV = "prod"


def load_environment(environment_name: str):
    this_dir = os.path.dirname(__file__)
    env_file = os.path.join(this_dir, "environments", f"{environment_name}.env")

    if not os.path.exists(env_file):
        raise ReleaseTestConfigError(
            f"Unknown environment with name: {environment_name}"
        )

    with open(env_file, "r") as f:
        for line in f.readlines():
            if not line:
                continue
            key, val = line.strip().split("=", maxsplit=1)
            os.environ[key] = val.strip('"')
