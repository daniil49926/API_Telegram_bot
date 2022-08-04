import os
import sentry_sdk
from load_env import load_environ
from bot_logic import run_bot


if __name__ == '__main__':
    load_environ()
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        traces_sample_rate=1.0
    )

    run_bot()
