import os


def env(name, default=None):
    return os.getenv(name, default)


def int_env(name, default):
    value = os.getenv(name)
    return int(value) if value else default

