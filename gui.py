"""
gui.py — Modern Desktop GUI for Jarvis AI Assistant
=====================================================
Features:
  - AI intent detection (Gemini) + AI action planning (autonomous mode)
  - Plugin system + task chain execution
  - Long-term memory (persisted to long_memory.json)
  - Background agent loop (autonomous task execution)
  - Voice I/O (SpeechRecognition + pyttsx3)
  - Dark theme, chat bubbles, animated status labels

Run:
    python gui.py
"""

import sys
import time
from typing import Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

# ── Jarvis backend imports ───────────────────
from ai_engine import JarvisAI
from memory import ConversationMemory
from system_control import execute_action
from utils import logger, get_greeting, listen_voice, speak_response
from task_engine import execute_task_chain, describe_chain
from long_memory import save_interaction
from agent_loop import AgentLoop
import plugin_loader

# ─────────────────────────────────────────────
# QSS Dark Theme
# ─────────────────────────────────────────────
STYLE_SHEET = """
QMainWindow, QWidget {
    background-color: #0f172a;
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
}

#Header {
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
    padding: 12px 18px;
}

#Title {
    color: #f8fafc;
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 2px;
}

#Subtitle {
    color: #64748b;
    font-size: 11px;
    letter-spacing: 1px;
}

#StatusDot {
    border-radius: 6px;
    min-width: 12px;
    min-height: 12px;
    max-width: 12px;
    max-height: 12px;
}

#StatusText {
    color: #94a3b8;
    font-size: 11px;
}

#ChatArea {
    background-color: #0f172a;
    border: none;
}

#MessageArea {
    background-color: #0f172a;
}

#StatusBar {
    background-color: #0f172a;
    padding: 2px 20px 6px 20px;
}

#StatusBarLabel {
    color: #475569;
    font-size: 12px;
    font-style: italic;
}

#InputSection {
    background-color: #1e293b;
    border-top: 1px solid #334155;
    padding: 14px 16px;
}

QLineEdit {
    background-color: #334155;
    border: 1px solid #475569;
    border-radius: 20px;
    padding: 10px 20px;
    color: #f8fafc;
    font-size: 14px;
    selection-background-color: #2563eb;
}

QLineEdit:focus {
    border: 1px solid #2563eb;
}

QLineEdit:disabled {
    background-color: #1e293b;
    color: #475569;
}

#SendButton {
    background-color: #2563eb;
    color: white;
    border-radius: 20px;
    padding: 10px 22px;
    font-weight: bold;
    font-size: 13px;
    min-width: 60px;
}

#SendButton:hover  { background-color: #3b82f6; }
#SendButton:pressed { background-color: #1d4ed8; }
#SendButton:disabled { background-color: #1e3a5f; color: #475569; }

#MicButton {
    background-color: transparent;
    border: 1.5px solid #475569;
    border-radius: 20px;
    padding: 8px;
    color: #94a3b8;
    font-size: 16px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
}

#MicButton:hover   { border-color: #2563eb; color: #f8fafc; }
#MicButton:pressed { background-color: #1e3a5f; }

/* Active (listening) state applied via inline stylesheet in code */

QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 3px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0px; }
"""

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
_DESTRUCTIVE_ACTIONS = {"shutdown_system", "restart_system"}

# QSS additions for the Autonomous Mode button
STYLE_SHEET_EXTRA = """
#AutoButton {
    background-color: transparent;
    border: 1.5px solid #475569;
    border-radius: 14px;
    padding: 4px 10px;
    color: #64748b;
    font-size: 11px;
    font-weight: bold;
}
#AutoButton:hover { border-color: #a855f7; color: #a855f7; }
#AutoButton[active=true] {
    background-color: #581c87;
    border-color: #a855f7;
    color: #e9d5ff;
}
"""


# ─────────────────────────────────────────────
# Worker: AI Intent Routing + Command Execution
# ─────────────────────────────────────────────
class JarvisWorker(QThread):
    """
    Background thread that:
      1. Calls ai.detect_intent() to classify the input.
      2. For 'system' intents: emits confirm_required for destructive
         actions, or runs each action and collects responses.
      3. For 'ai_query' intents: calls ai.ask() with memory context.

    Signals:
        response_ready(str, str)   — (response_text, category)
        confirm_required(str, str) — (action_name, display_question)
                                     emitted before a destructive action;
                                     the UI must call resume_confirmed()
                                     or resume_cancelled() after the
                                     user responds to the dialog.
    """
    response_ready   = pyqtSignal(str, str)   # (text, category)
    confirm_required = pyqtSignal(str, str)   # (action_name, question)

    def __init__(self, ai_engine: JarvisAI, memory: ConversationMemory):
        super().__init__()
        self.ai = ai_engine
        self.memory = memory
        self._text = ""
        # Confirmation state — set from the UI thread via resume_*
        self._confirmed: Optional[bool] = None

    def process(self, text: str) -> None:
        """Queue ``text`` for processing and start the thread."""
        self._text = text
        self._confirmed = None
        self.start()

    def resume_confirmed(self) -> None:
        """Called by the UI thread when the user clicks 'Yes' on a confirm dialog."""
        self._confirmed = True

    def resume_cancelled(self) -> None:
        """Called by the UI thread when the user clicks 'No' on a confirm dialog."""
        self._confirmed = False

    # ── Autonomous mode flag ───────────────────
    # Set by JarvisWindow when the toggle is active.
    autonomous_mode: bool = False

    def run(self) -> None:
        text = self._text
        try:
            response, category = self._route(text)
        except Exception as exc:           # pylint: disable=broad-except
            logger.error(f"JarvisWorker error: {exc}")
            response = "I'm having trouble connecting to my brain right now. Please try again."
            category = "error"

        self.memory.add_user_message(text)
        self.memory.add_assistant_message(response)
        # Persist to long-term memory in the background thread (non-blocking)
        try:
            save_interaction(text, response)
        except Exception as exc:           # pylint: disable=broad-except
            logger.warning(f"long_memory save failed: {exc}")
        self.response_ready.emit(response, category)

    # ── Private routing logic ──────────────────
    def _route(self, text: str) -> tuple[str, str]:
        """
        Classify ``text`` and dispatch accordingly.

        Autonomous mode: uses plan_actions() for richer multi-step planning.
        Normal mode:     uses detect_intent() for fast classification.
        """
        # ── Autonomous mode: AI planning layer ──
        if self.autonomous_mode and self.ai.is_ready:
            plan = self.ai.plan_actions(text)
            planned = plan.get("actions", [])
            reasoning = plan.get("reasoning", "")
            if planned:
                action_names = [a["action"] for a in planned]
                logger.info(f"Autonomous plan: {action_names} — {reasoning[:60]}")
                preview = describe_chain(action_names)
                result  = execute_task_chain(action_names)
                return f"{preview}\n\n{result}", "agent"
            # Fall through to normal routing if plan is empty

        # ── Normal mode: intent detection ───────
        intent = self.ai.detect_intent(text)
        logger.info(f"Intent: {intent} for input: '{text[:60]}'")

        if intent["type"] == "system":
            actions = intent.get("actions", [])
            if not actions:
                return self.ai.ask(text, self.memory), "ai"

            responses = []
            for action in actions:
                result = self._run_action(action)
                if result is None:
                    responses.append(f"Cancelled: {action.replace('_', ' ')}. ✅")
                else:
                    responses.append(result)
            return "\n".join(responses), "system"

        else:
            return self.ai.ask(text, self.memory), "ai"

    def _run_action(self, action: str) -> Optional[str]:
        """
        Execute a single action, requesting GUI confirmation first if it is
        destructive. Blocks the worker thread (not the UI thread) while
        waiting for the user's response.

        Args:
            action (str): Canonical action name from the registry.

        Returns:
            str:  Result message from execute_action().
            None: If the user cancelled a destructive action.
        """
        if action in _DESTRUCTIVE_ACTIONS:
            # Build a friendly confirmation question
            verb = "SHUTDOWN" if "shutdown" in action else "RESTART"
            question = f"Are you sure you want to {verb} the system?"

            # Emit signal — UI thread will show dialog and call resume_*()
            self._confirmed = None
            self.confirm_required.emit(action, question)

            # Spin-wait for UI thread to set _confirmed (max 30 s)
            import time
            deadline = time.monotonic() + 30
            while self._confirmed is None and time.monotonic() < deadline:
                time.sleep(0.05)

            if not self._confirmed:
                logger.info(f"User cancelled destructive action: {action}")
                return None

        return execute_action(action)


# ─────────────────────────────────────────────
# Worker: Voice Input (Speech Recognition)
# ─────────────────────────────────────────────
class VoiceWorker(QThread):
    """
    Background thread: captures microphone audio and returns
    recognised text via signals.

    Signals:
        recognised(str)   — emitted with transcribed text on success.
        unclear()         — emitted when speech was heard but not understood.
        error(str)        — emitted on mic/network error (human-readable).
    """
    recognised = pyqtSignal(str)
    unclear    = pyqtSignal()
    error      = pyqtSignal(str)

    def run(self) -> None:
        try:
            text = listen_voice(timeout=8, phrase_limit=10)
        except RuntimeError as exc:
            # e.g. mic not found, SpeechRecognition not installed
            logger.error(f"VoiceWorker: {exc}")
            self.error.emit(str(exc))
            return

        if text == "__unclear__":
            self.unclear.emit()
        elif text:
            self.recognised.emit(text)
        else:
            # Empty string = timeout or service error — treat as no input
            self.error.emit("No speech detected. Please try again.")


# ─────────────────────────────────────────────
# Worker: Text-to-Speech
# ─────────────────────────────────────────────
class TTSWorker(QThread):
    """
    Background thread: speaks a response aloud using pyttsx3.
    Emits ``finished`` when done so the UI can update its state.
    """
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._text = ""

    def speak(self, text: str) -> None:
        """Queue ``text`` for TTS and start the thread."""
        self._text = text
        self.start()

    def run(self) -> None:
        speak_response(self._text)
        self.finished.emit()


# ─────────────────────────────────────────────
# Chat Bubble Widget
# ─────────────────────────────────────────────
class ChatBubble(QFrame):
    """
    A single chat message rendered as a coloured rounded bubble.
    """
    # Shared max-width fraction of the window
    _USER_COLOUR   = "#2563eb"
    _JARVIS_COLOUR = "#1e293b"

    def __init__(self, text: str, is_user: bool = True):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setFont(QFont("Ubuntu", 11))

        if is_user:
            self.setStyleSheet(f"""
                background-color: {self._USER_COLOUR};
                color: #ffffff;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 3px;
            """)
            label.setAlignment(Qt.AlignRight)
        else:
            self.setStyleSheet(f"""
                background-color: {self._JARVIS_COLOUR};
                color: #e2e8f0;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom-left-radius: 3px;
                border-bottom-right-radius: 16px;
            """)
            label.setAlignment(Qt.AlignLeft)

        layout.addWidget(label)


# ─────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────
class JarvisWindow(QMainWindow):
    """
    Main application window.

    Owns:
      - JarvisWorker  — AI / system command processing
      - VoiceWorker   — Speech-to-text input
      - TTSWorker     — Text-to-speech output
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS — AI Assistant")
        self.resize(520, 720)
        self.setMinimumSize(420, 580)

        # ── Backend ─────────────────────────────
        self.memory = ConversationMemory(max_turns=5)
        self.ai     = JarvisAI()

        # ── Load plugins (non-blocking, fast) ───
        plugin_loader.load_all_plugins()
        logger.info(f"Plugins loaded: {plugin_loader.list_plugins()}")

        # ── Workers ─────────────────────────────
        self.ai_worker    = JarvisWorker(self.ai, self.memory)
        self.voice_worker = VoiceWorker()
        self.tts_worker   = TTSWorker()

        # ── Agent loop (background daemon) ──────
        self._agent_loop = AgentLoop(
            interval=5.0,
            on_result=self._on_agent_result,
        )
        self._agent_loop.start()

        # ── Autonomous mode state ────────────────
        self._auto_mode: bool = False

        self.ai_worker.response_ready.connect(self._on_ai_response)
        self.ai_worker.confirm_required.connect(self._confirm_destructive)
        self.voice_worker.recognised.connect(self._on_voice_recognised)
        self.voice_worker.unclear.connect(self._on_voice_unclear)
        self.voice_worker.error.connect(self._on_voice_error)
        self.tts_worker.finished.connect(self._on_tts_finished)

        # ── Status animation timer ───────────────
        self._ellipsis_count = 0
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(500)
        self._status_timer.timeout.connect(self._tick_ellipsis)

        self._build_ui()
        self.setStyleSheet(STYLE_SHEET + STYLE_SHEET_EXTRA)

        # ── Greeting ────────────────────────────
        greeting = f"{get_greeting()}, Yash! How can I help you today?"
        self._add_message(greeting, is_user=False)
        self.tts_worker.speak(greeting)

    # ═══════════════════════════════════════════
    # UI Construction
    # ═══════════════════════════════════════════
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_chat_area(), stretch=1)
        layout.addWidget(self._build_status_bar())
        layout.addWidget(self._build_input_section())

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("Header")
        row = QHBoxLayout(header)
        row.setContentsMargins(18, 12, 18, 12)

        # Title block
        col = QVBoxLayout()
        col.setSpacing(2)
        title = QLabel("JARVIS")
        title.setObjectName("Title")
        subtitle = QLabel("Just A Rather Very Intelligent System")
        subtitle.setObjectName("Subtitle")
        col.addWidget(title)
        col.addWidget(subtitle)
        row.addLayout(col)
        row.addStretch()

        # Status indicator + autonomous toggle
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.status_dot = QFrame()
        self.status_dot.setObjectName("StatusDot")
        color = "#10b981" if self.ai.is_ready else "#f59e0b"
        self.status_dot.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        self.status_text = QLabel("Online" if self.ai.is_ready else "Offline")
        self.status_text.setObjectName("StatusText")
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_text)

        # Autonomous mode toggle
        self.auto_btn = QPushButton("🤖 Auto")
        self.auto_btn.setObjectName("AutoButton")
        self.auto_btn.setCheckable(False)
        self.auto_btn.setToolTip("Toggle Autonomous Mode (Jarvis plans + executes multi-step tasks)")
        self.auto_btn.clicked.connect(self._toggle_autonomous)
        status_row.addSpacing(8)
        status_row.addWidget(self.auto_btn)

        row.addLayout(status_row)

        return header

    def _build_chat_area(self) -> QScrollArea:
        self.scroll = QScrollArea()
        self.scroll.setObjectName("ChatArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.msg_container = QWidget()
        self.msg_container.setObjectName("MessageArea")
        self.chat_layout = QVBoxLayout(self.msg_container)
        self.chat_layout.setContentsMargins(20, 20, 20, 10)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()   # keeps bubbles pinned to top

        self.scroll.setWidget(self.msg_container)
        return self.scroll

    def _build_status_bar(self) -> QWidget:
        """Thin strip below chat showing 'Listening…' / 'Thinking…' etc."""
        bar = QWidget()
        bar.setObjectName("StatusBar")
        bar.setFixedHeight(26)
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 0, 20, 0)
        self.status_label = QLabel("")
        self.status_label.setObjectName("StatusBarLabel")
        h.addWidget(self.status_label)
        return bar

    def _build_input_section(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("InputSection")
        row = QHBoxLayout(panel)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(10)

        # Mic button
        self.mic_btn = QPushButton("🎙")
        self.mic_btn.setObjectName("MicButton")
        self.mic_btn.setFixedSize(42, 42)
        self.mic_btn.setToolTip("Click to speak")
        self.mic_btn.clicked.connect(self._start_voice_input)

        # Text field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message or click 🎙 to speak...")
        self.input_field.returnPressed.connect(self._send_text_message)

        # Send button
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.clicked.connect(self._send_text_message)

        row.addWidget(self.mic_btn)
        row.addWidget(self.input_field)
        row.addWidget(self.send_btn)
        return panel

    # ═══════════════════════════════════════════
    # Message Helpers
    # ═══════════════════════════════════════════
    def _add_message(self, text: str, is_user: bool) -> None:
        """Insert a ChatBubble into the chat layout and scroll to bottom."""
        bubble = ChatBubble(text, is_user)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        # Max width: ~75 % of window
        bubble.setMaximumWidth(int(self.width() * 0.75))

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        h = QHBoxLayout(wrapper)
        h.setContentsMargins(0, 0, 0, 0)

        if is_user:
            h.addStretch()
            h.addWidget(bubble)
        else:
            h.addWidget(bubble)
            h.addStretch()

        # Insert before the trailing stretch
        idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(idx, wrapper)

        # Scroll to bottom after Qt processes the layout change
        QApplication.processEvents()
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )

    def _set_status(self, text: str) -> None:
        """Update the slim status bar below the chat."""
        self.status_label.setText(text)

    def _set_busy(self, busy: bool) -> None:
        """Disable/enable interactive controls."""
        self.input_field.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)
        self.mic_btn.setEnabled(not busy)

    # ═══════════════════════════════════════════
    # Ellipsis animation for status messages
    # ═══════════════════════════════════════════
    def _start_ellipsis(self, base: str) -> None:
        self._ellipsis_base = base
        self._ellipsis_count = 0
        self._status_timer.start()
        self._set_status(base)

    def _stop_ellipsis(self) -> None:
        self._status_timer.stop()
        self._set_status("")

    def _tick_ellipsis(self) -> None:
        self._ellipsis_count = (self._ellipsis_count + 1) % 4
        dots = "." * self._ellipsis_count
        self.status_label.setText(f"{self._ellipsis_base}{dots}")

    # ═══════════════════════════════════════════
    # Text Input Flow
    # ═══════════════════════════════════════════
    def _send_text_message(self) -> None:
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._dispatch(text)

    # ═══════════════════════════════════════════
    # Voice Input Flow
    # ═══════════════════════════════════════════
    def _start_voice_input(self) -> None:
        """Kick off the VoiceWorker and update UI to 'Listening' state."""
        if self.voice_worker.isRunning():
            return

        self._set_busy(True)
        self.mic_btn.setEnabled(True)    # keep mic enabled to show state
        self.mic_btn.setStyleSheet("""
            background-color: #dc2626;
            border: 1.5px solid #dc2626;
            border-radius: 20px;
            color: white;
            font-size: 16px;
        """)
        self._start_ellipsis("🎙 Listening")
        logger.info("Voice input started.")
        self.voice_worker.start()

    def _on_voice_recognised(self, text: str) -> None:
        """Voice captured successfully — show it and process like typed input."""
        self._reset_mic_button()
        self._stop_ellipsis()
        self.input_field.setText(text)      # show what was heard briefly
        logger.info(f"Voice recognised: '{text}'")
        self._dispatch(text)
        self.input_field.clear()

    def _on_voice_unclear(self) -> None:
        """Speech heard but couldn't be understood."""
        self._reset_mic_button()
        self._stop_ellipsis()
        self._set_busy(False)
        self._add_message("I didn't catch that. Please try speaking again.", is_user=False)
        logger.warning("Voice input unclear.")

    def _on_voice_error(self, msg: str) -> None:
        """Mic unavailable, package missing, or network error."""
        self._reset_mic_button()
        self._stop_ellipsis()
        self._set_busy(False)
        self._add_message(f"🎙 Voice error: {msg}", is_user=False)
        logger.error(f"Voice error: {msg}")

    def _reset_mic_button(self) -> None:
        """Restore mic button to its default (idle) appearance."""
        self.mic_btn.setStyleSheet("")    # revert to QSS #MicButton rule
        self.mic_btn.setEnabled(True)

    # ═══════════════════════════════════════════
    # Autonomous Mode Toggle
    # ═══════════════════════════════════════════
    def _toggle_autonomous(self) -> None:
        """Toggle autonomous (agent planning) mode on/off."""
        self._auto_mode = not self._auto_mode
        self.ai_worker.autonomous_mode = self._auto_mode
        self._agent_loop.set_safe_mode(not self._auto_mode)

        # Update button appearance via Qt property
        self.auto_btn.setProperty("active", self._auto_mode)
        self.auto_btn.style().unpolish(self.auto_btn)
        self.auto_btn.style().polish(self.auto_btn)

        if self._auto_mode:
            self.auto_btn.setText("🤖 Auto ON")
            self._add_message(
                "🤖 Autonomous Mode ON — I'll plan and execute multi-step tasks automatically.",
                is_user=False,
            )
        else:
            self.auto_btn.setText("🤖 Auto")
            self._add_message(
                "✅ Autonomous Mode OFF — back to direct command routing.",
                is_user=False,
            )
        logger.info(f"Autonomous mode {'enabled' if self._auto_mode else 'disabled'}.")

    def _on_agent_result(self, action: str, result: str) -> None:
        """
        Called by AgentLoop (daemon thread) via on_result callback when a
        background autonomous task completes. Must marshal to the UI thread
        via a QTimer single-shot to stay thread-safe.
        """
        QTimer.singleShot(
            0,
            lambda: self._add_message(
                f"🤖 Agent completed '{action}':\n{result}", is_user=False
            ),
        )

    # ═══════════════════════════════════════════
    # Shared Dispatch (text → AI/system worker)
    # ═══════════════════════════════════════════
    def _dispatch(self, text: str) -> None:
        """Add user bubble and send text to the AI worker. Guards against overlap."""
        if self.ai_worker.isRunning():
            logger.warning("_dispatch: worker busy, ignoring input.")
            self._set_status("⚠️ Still processing — please wait...")
            return
        self._add_message(text, is_user=True)
        self._set_busy(True)
        self._start_ellipsis("🤖 Jarvis is thinking")
        logger.info(f"User input dispatched: '{text}'")
        self.ai_worker.process(text)

    def _on_ai_response(self, response: str, category: str) -> None:
        """AI worker finished — show response and speak it."""
        self._stop_ellipsis()
        self._add_message(response, is_user=False)
        logger.info(f"Response received ({category}): {response[:80]}...")

        # Speak response in background — keep input disabled until done
        self._start_ellipsis("🔊 Speaking")
        self.tts_worker.speak(response)

    def _confirm_destructive(self, action: str, question: str) -> None:
        """
        Show a native Qt confirmation dialog for destructive system actions
        (shutdown / restart). Called in the UI thread via the confirm_required
        signal from JarvisWorker, which blocks its own thread waiting for the
        result via resume_confirmed() / resume_cancelled().

        Args:
            action (str):   Canonical action name (e.g. 'shutdown_system').
            question (str): Human-readable question to show in the dialog.
        """
        verb = "⚠️ Shutdown" if "shutdown" in action else "🔄 Restart"
        dialog = QMessageBox(self)
        dialog.setWindowTitle(f"Confirm {verb}")
        dialog.setText(question)
        dialog.setIcon(QMessageBox.Warning)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(QMessageBox.No)
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: #1e293b;
                color: #f8fafc;
            }
            QLabel { color: #f8fafc; font-size: 13px; }
            QPushButton {
                background-color: #334155;
                color: #f8fafc;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        result = dialog.exec_()
        if result == QMessageBox.Yes:
            self.ai_worker.resume_confirmed()
        else:
            self.ai_worker.resume_cancelled()

    def _on_tts_finished(self) -> None:
        """TTS done — re-enable all controls."""
        self._stop_ellipsis()
        self._set_busy(False)
        self.input_field.setFocus()
        logger.debug("TTS finished.")

    # ═══════════════════════════════════════════
    # Window resize — update bubble max widths
    # ═══════════════════════════════════════════
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        max_w = int(self.width() * 0.75)
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                wrapper = item.widget()
                for j in range(wrapper.layout().count() if wrapper.layout() else 0):
                    child = wrapper.layout().itemAt(j)
                    if child and isinstance(child.widget(), ChatBubble):
                        child.widget().setMaximumWidth(max_w)


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    window = JarvisWindow()
    window.show()
    sys.exit(app.exec_())
