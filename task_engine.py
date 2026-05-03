"""
task_engine.py — Multi-Step Task Chain Executor for Jarvis
===========================================================
Provides execute_task_chain() which runs a list of action names
sequentially, deduplicates repeated actions, and collects all results
into a combined response string.

Integrates with:
    system_control.execute_action()  — built-in OS actions
    plugin_loader.run_plugin_action() — plugin actions
"""

from typing import List, Optional
from utils import logger


# Lazy imports — avoids circular dependency at module load time
def _get_execute_action():
    from system_control import execute_action
    return execute_action


def _get_run_plugin():
    try:
        from plugin_loader import run_plugin_action
        return run_plugin_action
    except ImportError:
        return None


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
def execute_task_chain(
    actions: List[str],
    *,
    safe_mode: bool = True,
    destructive_actions: Optional[set] = None,
) -> str:
    """
    Execute a sequence of action names one by one, returning a combined
    result string suitable for display in the chat bubble.

    Features:
      - Deduplication: identical action names within a chain run only once.
      - Plugin routing: tries plugin_loader first, falls back to system_control.
      - Error isolation: one failing action doesn't abort the whole chain.
      - safe_mode: skips destructive actions (shutdown/restart) when True.

    Args:
        actions (list[str]):       Ordered list of canonical action names.
        safe_mode (bool):          When True, skip actions in destructive_actions.
        destructive_actions (set): Set of action names considered dangerous.
                                   Defaults to {'shutdown_system', 'restart_system'}.

    Returns:
        str: Newline-joined result messages for each action executed.
    """
    if destructive_actions is None:
        destructive_actions = {"shutdown_system", "restart_system"}

    if not actions:
        logger.warning("execute_task_chain: called with empty actions list.")
        return "No actions specified in task chain."

    execute_action = _get_execute_action()
    run_plugin    = _get_run_plugin()

    seen     : set  = set()
    results  : list = []

    for action in actions:
        action = action.strip()
        if not action:
            continue

        # ── Deduplication ────────────────────────
        if action in seen:
            logger.debug(f"task_engine: skipping duplicate action '{action}'")
            continue
        seen.add(action)

        # ── Safety gate ──────────────────────────
        if safe_mode and action in destructive_actions:
            msg = (
                f"⚠️ Skipped '{action.replace('_', ' ')}' — "
                "requires explicit confirmation outside of task chains."
            )
            logger.warning(f"task_engine: safe_mode blocked '{action}'")
            results.append(msg)
            continue

        # ── Dispatch ─────────────────────────────
        logger.info(f"task_engine: executing '{action}'")
        try:
            # Try plugin registry first; fall back to system_control
            if run_plugin:
                result = run_plugin(action)
                if result is not None:
                    results.append(result)
                    continue

            results.append(execute_action(action))

        except Exception as exc:           # pylint: disable=broad-except
            err_msg = f"❌ Error executing '{action}': {exc}"
            logger.error(f"task_engine: {err_msg}")
            results.append(err_msg)

    return "\n".join(results) if results else "Task chain completed with no output."


def describe_chain(actions: List[str]) -> str:
    """
    Return a human-readable description of what a task chain will do.
    Useful for autonomous-mode preview messages.

    Args:
        actions (list[str]): List of action name strings.

    Returns:
        str: Formatted description string.
    """
    if not actions:
        return "No actions planned."
    numbered = "\n".join(
        f"  {i + 1}. {a.replace('_', ' ').title()}"
        for i, a in enumerate(actions)
    )
    return f"I'll execute the following steps:\n{numbered}"
