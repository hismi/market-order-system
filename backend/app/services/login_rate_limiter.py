from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

from app.core.config import Settings


class LoginRateLimitError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Cok fazla hatali giris denemesi.")


@dataclass
class LoginAttemptState:
    failed_attempts: int
    first_failed_at: float
    blocked_until: float | None = None


class LoginRateLimiter:
    def __init__(self) -> None:
        self._attempts: dict[str, LoginAttemptState] = {}

    def check_allowed(self, key: str, settings: Settings) -> None:
        state = self._attempts.get(key)
        if state is None:
            return

        now = monotonic()
        if self._is_window_expired(state, settings, now):
            self._attempts.pop(key, None)
            return

        if state.blocked_until is not None and state.blocked_until > now:
            raise LoginRateLimitError(int(state.blocked_until - now) + 1)

        if state.blocked_until is not None and state.blocked_until <= now:
            self._attempts.pop(key, None)

    def record_failure(self, key: str, settings: Settings) -> None:
        now = monotonic()
        state = self._attempts.get(key)
        if state is None or self._is_window_expired(state, settings, now):
            state = LoginAttemptState(failed_attempts=0, first_failed_at=now)

        state.failed_attempts += 1
        if state.failed_attempts >= settings.login_rate_limit_max_attempts:
            state.blocked_until = now + settings.login_rate_limit_lockout_seconds

        self._attempts[key] = state

    def record_success(self, key: str) -> None:
        self._attempts.pop(key, None)

    def clear(self) -> None:
        self._attempts.clear()

    def _is_window_expired(
        self,
        state: LoginAttemptState,
        settings: Settings,
        now: float,
    ) -> bool:
        return now - state.first_failed_at > settings.login_rate_limit_window_seconds


login_rate_limiter = LoginRateLimiter()
