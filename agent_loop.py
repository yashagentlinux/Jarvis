"""
agent_loop.py — Background Autonomous Agent for Jarvis
=======================================================
Runs a periodic background loop that can:
  - Execute scheduled/queued tasks
  - Check for pending automated jobs
  - Run follow-up actions in autonomous mode

Usage:
    agent = AgentLoop(ai_engine, memory)
    agent.start()          # non-blocking
    agent.enqueue("launch_firefox")
    agent.stop()
"""

import threading
import queue
import time
from typing import Optional, Callable

from utils import logger


class AgentLoop:
    """
    A lightweight background agent that processes a task queue on a
    configurable interval. Does NOT block the UI or any other thread.

    Args:
        interval (float):          Seconds between idle poll cycles.
        on_result (callable|None): Called with (action, result) after each
                                   task completes — wire this to the GUI to
                                   display autonomous results as chat bubbles.
    """

    def __init__(
        self,
        interval: float = 5.0,
        on_result: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.interval   = interval
        self.on_result  = on_result
        self._queue: queue.Queue = queue.Queue()
        self._stop_event          = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._safe_mode: bool = True

    # ── Lifecycle ─────────────────────────────
    def start(self) -> None:
        """Start the background agent thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("AgentLoop: already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="JarvisAgentLoop",
            daemon=True,          # exits when main process exits
        )
        self._thread.start()
        logger.info("AgentLoop: started.")

    def stop(self) -> None:
        """Signal the agent to stop after the current task completes."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("AgentLoop: stopped.")

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Queue Management ──────────────────────
    def enqueue(self, action: str) -> None:
        """
        Add a single action name to the pending task queue.

        Args:
            action (str): Canonical action name (e.g. 'launch_firefox').
        """
        self._queue.put(action)
        logger.info(f"AgentLoop: enqueued '{action}' (queue size={self._queue.qsize()})")

    def enqueue_chain(self, actions: list) -> None:
        """Add multiple actions to the queue in order."""
        for a in actions:
            self.enqueue(a)

    def pending_count(self) -> int:
        """Return number of tasks waiting in the queue."""
        return self._queue.qsize()

    # ── Safe Mode ─────────────────────────────
    def set_safe_mode(self, enabled: bool) -> None:
        """
        Toggle safe mode. When enabled, destructive actions in the queue
        are logged and skipped rather than executed autonomously.
        """
        self._safe_mode = enabled
        logger.info(f"AgentLoop: safe_mode={'ON' if enabled else 'OFF'}")

    # ── Internal Loop ─────────────────────────
    _DESTRUCTIVE = {"shutdown_system", "restart_system"}

    def _loop(self) -> None:
        """Main agent loop — runs in its own daemon thread."""
        logger.debug("AgentLoop: loop entered.")
        while not self._stop_event.is_set():
            try:
                action = self._queue.get(timeout=self.interval)
            except queue.Empty:
                # Idle tick — hook for future scheduled tasks
                logger.debug("AgentLoop: idle tick.")
                continue

            self._execute(action)
            self._queue.task_done()

        logger.debug("AgentLoop: loop exited.")

    def _execute(self, action: str) -> None:
        """Run a single queued action and call on_result if set."""
        # Safety gate
        if self._safe_mode and action in self._DESTRUCTIVE:
            msg = f"⚠️ Autonomous mode skipped destructive action: '{action}'"
            logger.warning(msg)
            if self.on_result:
                self.on_result(action, msg)
            return

        # Try plugin first, then system_control
        result = None
        try:
            from plugin_loader import run_plugin_action
            result = run_plugin_action(action)
        except ImportError:
            pass

        if result is None:
            try:
                from system_control import execute_action
                result = execute_action(action)
            except Exception as exc:   # pylint: disable=broad-except
                result = f"❌ Agent error executing '{action}': {exc}"
                logger.error(result)

        logger.info(f"AgentLoop: '{action}' → {str(result)[:80]}")
        if self.on_result and result:
            self.on_result(action, result)
