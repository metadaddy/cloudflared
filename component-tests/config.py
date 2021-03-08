#!/usr/bin/env python
import base64
import copy
import os
import yaml

from dataclasses import dataclass, InitVar

from constants import METRICS_PORT

from util import LOGGER

# frozen=True raises exception when assigning to fields. This emulates immutability


@dataclass(frozen=True)
class TunnelBaseConfig:
    no_autoupdate: bool = True
    metrics: str = f'localhost:{METRICS_PORT}'

    def merge_config(self, additional):
        config = copy.copy(additional)
        config['no-autoupdate'] = self.no_autoupdate
        config['metrics'] = self.metrics
        return config


@dataclass(frozen=True)
class NamedTunnelBaseConfig(TunnelBaseConfig):
    # The attributes of the parent class are ordered before attributes in this class,
    # so we have to use default values here and check if they are set in __post_init__
    tunnel: str = None
    credentials_file: str = None
    ingress: list = None

    def __post_init__(self):
        if self.tunnel is None:
            raise TypeError("Field tunnel is not set")
        if self.credentials_file is None:
            raise TypeError("Field credentials_file is not set")
        if self.ingress is None:
            raise TypeError("Field ingress is not set")

    def merge_config(self, additional):
        config = super(NamedTunnelBaseConfig, self).merge_config(additional)
        config['tunnel'] = self.tunnel
        config['credentials-file'] = self.credentials_file
        # In some cases we want to override default ingress, such as in config tests
        if 'ingress' not in config:
            config['ingress'] = self.ingress
        return config


@dataclass(frozen=True)
class NamedTunnelConfig(NamedTunnelBaseConfig):
    full_config: dict = None
    additional_config: InitVar[dict] = {}

    def __post_init__(self, additional_config):
        # Cannot call set self.full_config because the class is frozen, instead, we can use __setattr__
        # https://docs.python.org/3/library/dataclasses.html#frozen-instances
        object.__setattr__(self, 'full_config',
                           self.merge_config(additional_config))

    def get_url(self):
        return "https://" + self.ingress[0]['hostname']


@dataclass(frozen=True)
class ClassicTunnelBaseConfig(TunnelBaseConfig):
    hostname: str = None
    origincert: str = None

    def __post_init__(self):
        if self.hostname is None:
            raise TypeError("Field tunnel is not set")
        if self.origincert is None:
            raise TypeError("Field credentials_file is not set")

    def merge_config(self, additional):
        config = super(ClassicTunnelBaseConfig, self).merge_config(additional)
        config['hostname'] = self.hostname
        config['origincert'] = self.origincert
        return config


@dataclass(frozen=True)
class ClassicTunnelConfig(ClassicTunnelBaseConfig):
    full_config: dict = None
    additional_config: InitVar[dict] = {}

    def __post_init__(self, additional_config):
        # Cannot call set self.full_config because the class is frozen, instead, we can use __setattr__
        # https://docs.python.org/3/library/dataclasses.html#frozen-instances
        object.__setattr__(self, 'full_config',
                           self.merge_config(additional_config))

    def get_url(self):
        return "https://" + self.hostname


@dataclass
class ComponentTestConfig:
    cloudflared_binary: str
    named_tunnel_config: NamedTunnelConfig
    classic_tunnel_config: ClassicTunnelConfig


def build_config_from_env():
    config_path = get_env("COMPONENT_TESTS_CONFIG")
    config_content = base64.b64decode(
        get_env("COMPONENT_TESTS_CONFIG_CONTENT")).decode('utf-8')
    config_yaml = yaml.safe_load(config_content)

    credentials_file = get_env("COMPONENT_TESTS_CREDENTIALS_FILE")
    write_file(credentials_file, config_yaml["credentials_file"])

    origincert = get_env("COMPONENT_TESTS_ORIGINCERT")
    write_file(origincert, config_yaml["origincert"])

    write_file(config_content, config_path)


def write_file(content, path):
    with open(path, 'w') as outfile:
        outfile.write(content)
        outfile.close


def get_env(env_name):
    val = os.getenv(env_name)
    if val is None:
        raise Exception(f"{env_name} is not set")
    return val


if __name__ == '__main__':
    build_config_from_env()
