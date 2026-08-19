"""插件加载器 - 动态加载插件模块"""

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict, List, Type

from app.plugin_system.base import PluginBase


def load_plugin_from_file(filepath: str) -> List[Type[PluginBase]]:
    """从单个Python文件加载插件类"""
    plugins = []
    filepath = Path(filepath).resolve()
    module_name = filepath.stem

    try:
        spec = importlib.util.spec_from_file_location(
            f"user_plugin_{module_name}", str(filepath)
        )
        if spec is None or spec.loader is None:
            return plugins

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, PluginBase)
                and attr is not PluginBase
            ):
                plugins.append(attr)

    except Exception as e:
        print(f"加载插件失败 [{filepath}]: {e}")

    return plugins


def load_plugins_from_dir(directory: str) -> List[Type[PluginBase]]:
    """从目录加载所有插件"""
    plugins = []
    dir_path = Path(directory)

    if not dir_path.exists():
        return plugins

    for py_file in dir_path.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        plugins.extend(load_plugin_from_file(str(py_file)))

    return plugins


def load_builtin_plugins() -> List[Type[PluginBase]]:
    """加载内置插件"""
    builtin_dir = Path(__file__).parent.parent.parent / "plugins"
    return load_plugins_from_dir(str(builtin_dir))


def load_user_plugins() -> List[Type[PluginBase]]:
    """加载用户插件"""
    user_dir = Path(__file__).parent.parent.parent / "user_plugins"
    return load_plugins_from_dir(str(user_dir))