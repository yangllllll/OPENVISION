"""插件管理器 - 管理所有已注册的插件"""

from typing import Dict, List, Optional, Type

from app.plugin_system.base import PluginBase
from app.plugin_system.loader import load_builtin_plugins, load_user_plugins


class PluginManager:
    """插件管理器（单例）"""

    _instance: Optional["PluginManager"] = None

    def __new__(cls) -> "PluginManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._plugin_classes: Dict[str, Type[PluginBase]] = {}
        self._category_map: Dict[str, List[str]] = {}

    def reload_all(self):
        """重新加载所有插件"""
        self._plugin_classes.clear()
        self._category_map.clear()
        self._load_builtin()
        self._load_user()

    def _load_builtin(self):
        for pc in load_builtin_plugins():
            self._register(pc)

    def _load_user(self):
        for pc in load_user_plugins():
            self._register(pc)

    def _register(self, plugin_class: Type[PluginBase]):
        self._plugin_classes[plugin_class.plugin_id] = plugin_class
        cat = plugin_class.plugin_category
        if cat not in self._category_map:
            self._category_map[cat] = []
        self._category_map[cat].append(plugin_class.plugin_id)

    def get_plugin_class(self, plugin_id: str) -> Optional[Type[PluginBase]]:
        return self._plugin_classes.get(plugin_id)

    def create_instance(self, plugin_id: str) -> Optional[PluginBase]:
        pc = self._plugin_classes.get(plugin_id)
        if pc:
            return pc()
        return None

    def get_all_plugins(self) -> Dict[str, Type[PluginBase]]:
        return dict(self._plugin_classes)

    def get_categories(self) -> List[str]:
        return list(self._category_map.keys())

    def get_plugins_by_category(self, category: str) -> List[Type[PluginBase]]:
        ids = self._category_map.get(category, [])
        return [self._plugin_classes[pid] for pid in ids if pid in self._plugin_classes]