"""
plugin_loader.py — Dynamic Plugin Architecture for Jarvis
==========================================================
Auto-discovers and loads all Python files in the ``plugins/`` directory.

Each plugin module must expose:
    name    (str)          — unique plugin identifier
    actions (list[str])    — canonical action names this plugin handles
    execute(action, params) → str  — handler called with action + optional params

Public API:
    load_all_plugins()          — discover and import every plugin
    get_all_actions()           — merged dict {action_name: plugin_module}
    run_plugin_action(action, params={})  → str | None
    list_plugins()              → list[str] (plugin names)
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils import logger

# ─────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────
# Maps canonical action name → loaded plugin module
_PLUGIN_REGISTRY: Dict[str, Any] = {}    # {action_name: module}
_LOADED_PLUGINS:  Dict[str, Any] = {}    # {plugin_name: module}

PLUGINS_DIR = Path(__file__).parent / "plugins"


# ─────────────────────────────────────────────
# Discovery & Loading
# ─────────────────────────────────────────────
def load_all_plugins() -> int:
    """
    Scan the ``plugins/`` directory, import every ``*.py`` file (excluding
    ``__init__.py``), validate the plugin interface, and register its actions.

    Returns:
        int: Number of successfully loaded plugins.
    """
    if not PLUGINS_DIR.exists():
        logger.warning(f"plugin_loader: plugins directory not found at '{PLUGINS_DIR}'")
        return 0

    loaded = 0
    for plugin_path in sorted(PLUGINS_DIR.glob("*.py")):
        if plugin_path.stem.startswith("_"):
            continue
        if _load_single_plugin(plugin_path):
            loaded += 1

    logger.info(
        f"plugin_loader: {loaded} plugin(s) loaded, "
        f"{len(_PLUGIN_REGISTRY)} total actions registered."
    )
    return loaded


def _load_single_plugin(path: Path) -> bool:
    """
    Import one plugin file, validate its interface, and register its actions.

    Args:
        path (Path): Absolute path to the plugin ``*.py`` file.

    Returns:
        bool: True if loaded successfully.
    """
    module_name = f"plugins.{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            logger.warning(f"plugin_loader: could not create spec for '{path.name}'")
            return False

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)          # type: ignore[attr-defined]

        # ── Validate interface ───────────────────
        if not hasattr(module, "name"):
            logger.warning(f"plugin_loader: '{path.name}' missing 'name' attribute — skipped.")
            return False
        if not hasattr(module, "actions") or not isinstance(module.actions, list):
            logger.warning(f"plugin_loader: '{path.name}' missing 'actions' list — skipped.")
            return False
        if not hasattr(module, "execute") or not callable(module.execute):
            logger.warning(f"plugin_loader: '{path.name}' missing 'execute()' function — skipped.")
            return False

        # ── Register ────────────────────────────
        _LOADED_PLUGINS[module.name] = module
        for action in module.actions:
            if action in _PLUGIN_REGISTRY:
                logger.warning(
                    f"plugin_loader: action '{action}' already registered by "
                    f"'{_PLUGIN_REGISTRY[action].name}'; overwriting with '{module.name}'."
                )
            _PLUGIN_REGISTRY[action] = module
            logger.debug(f"plugin_loader: registered '{action}' → plugin '{module.name}'")

        logger.info(f"plugin_loader: loaded plugin '{module.name}' from '{path.name}' "
                    f"({len(module.actions)} action(s))")
        return True

    except Exception as exc:           # pylint: disable=broad-except
        logger.error(f"plugin_loader: failed to load '{path.name}' — {exc}")
        return False


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
def run_plugin_action(action: str, params: Optional[Dict] = None) -> Optional[str]:
    """
    Execute a plugin action if one is registered for ``action``.

    Args:
        action (str):          Canonical action name.
        params (dict|None):    Optional parameters forwarded to execute().

    Returns:
        str:  Result message from the plugin.
        None: If no plugin handles this action (caller should fall back).
    """
    plugin = _PLUGIN_REGISTRY.get(action)
    if plugin is None:
        return None   # not handled — let system_control try

    try:
        logger.info(f"plugin_loader: running '{action}' via plugin '{plugin.name}'")
        return plugin.execute(action, params or {})
    except Exception as exc:           # pylint: disable=broad-except
        logger.error(f"plugin_loader: '{plugin.name}.execute({action})' failed — {exc}")
        return f"Plugin error in '{action}': {exc}"


def get_all_actions() -> Dict[str, str]:
    """
    Return a mapping of every plugin-registered action → plugin name.

    Returns:
        dict: {action_name: plugin_name}
    """
    return {action: mod.name for action, mod in _PLUGIN_REGISTRY.items()}


def list_plugins() -> List[str]:
    """Return names of all successfully loaded plugins."""
    return list(_LOADED_PLUGINS.keys())


def reload_plugins() -> int:
    """
    Clear the registry and reload all plugins from disk.
    Useful for hot-reloading during development.

    Returns:
        int: Number of plugins loaded after reload.
    """
    _PLUGIN_REGISTRY.clear()
    _LOADED_PLUGINS.clear()
    # Remove old plugin modules from sys.modules
    to_remove = [k for k in sys.modules if k.startswith("plugins.")]
    for key in to_remove:
        del sys.modules[key]
    return load_all_plugins()
