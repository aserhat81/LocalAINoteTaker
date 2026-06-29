import threading
import time

import requests


class ModelSessionManager:
    """Reference-counted access to the local FLM LLM service."""

    def __init__(self, flm_manager, note_taker_busy=None):
        self.flm_manager = flm_manager
        self.note_taker_busy = note_taker_busy or (lambda: False)
        self._lock = threading.RLock()
        self._owners = {}
        self._started_by_owner = set()
        self._restore_asr_owner = set()

    def acquire(self, model_name, owner):
        model_name = (model_name or self.flm_manager.DEFAULT_MODEL).strip() or self.flm_manager.DEFAULT_MODEL
        owner = owner or "unknown"

        with self._lock:
            should_wait = False
            if owner in self._owners:
                current_model, count = self._owners[owner]
                if current_model != model_name:
                    raise RuntimeError(f"{owner} already owns model session {current_model}")
                self._owners[owner] = (model_name, count + 1)
                return

            if self.note_taker_busy():
                raise RuntimeError("Note Taker is currently using the local AI service.")

            active_owners = {m for m, _ in self._owners.values()}
            if active_owners and model_name not in active_owners:
                raise RuntimeError("Another module is using a different local AI model.")

            if self.flm_manager.is_running:
                if self.flm_manager.service_mode == "llm" and self.flm_manager.current_model == model_name:
                    self._owners[owner] = (model_name, 1)
                    return
                if self.flm_manager.service_mode == "external":
                    self._owners[owner] = (model_name, 1)
                    return
                if self.flm_manager.service_mode == "asr":
                    self.flm_manager.stop_service(emit_status=False)
                    self._restore_asr_owner.add(owner)
                    self._owners[owner] = (model_name, 1)
                    self._started_by_owner.add(owner)
                    self.flm_manager.start_llm_service(model_name)
                    should_wait = True
                else:
                    raise RuntimeError("Local AI service is busy with another mode.")
            else:
                self._owners[owner] = (model_name, 1)
                self._started_by_owner.add(owner)
                self.flm_manager.start_llm_service(model_name)
                should_wait = True

        if should_wait:
            self._wait_until_ready(model_name)

    def release(self, model_name, owner):
        owner = owner or "unknown"
        with self._lock:
            if owner not in self._owners:
                return

            current_model, count = self._owners[owner]
            if count > 1:
                self._owners[owner] = (current_model, count - 1)
                return

            del self._owners[owner]
            started_here = owner in self._started_by_owner
            restore_asr = owner in self._restore_asr_owner
            self._started_by_owner.discard(owner)
            self._restore_asr_owner.discard(owner)
            has_other_owners = bool(self._owners)

            if started_here and not has_other_owners:
                self.flm_manager.stop_service(emit_status=False)
                if restore_asr:
                    self.flm_manager.start_service(current_model)

    def _wait_until_ready(self, model_name, timeout_seconds=300):
        deadline = time.time() + timeout_seconds
        last_error = None
        while time.time() < deadline:
            try:
                resp = requests.get("http://127.0.0.1:52625/v1/models", timeout=2)
                if resp.status_code == 200:
                    return
            except Exception as exc:
                last_error = exc
            time.sleep(2)
        raise RuntimeError(f"Local AI model did not become ready: {last_error}")
