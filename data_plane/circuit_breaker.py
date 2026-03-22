import time
import logging
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class State(Enum):
    """
    CLOSED — Normal operating state. All requests pass through.
    Failures are tracked in a sliding window. When the failure
    count crosses the threshold the breaker trips to OPEN.

    OPEN — Fault state. No requests are forwarded to upstream.
    The sidecar immediately returns 503 without attempting the
    real call. This prevents cascading failures — a dead upstream
    cannot drag down the calling service. After open_duration
    seconds the breaker transitions to HALF_OPEN to test recovery.

    HALF_OPEN — Recovery probe state. Exactly one request is
    allowed through as a probe. If it succeeds the breaker returns
    to CLOSED and normal traffic resumes. If it fails the breaker
    goes back to OPEN and resets the timeout. This is how the
    system self-heals after an outage without human intervention.
    """
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Per-upstream circuit breaker implementing the CLOSED → OPEN →
    HALF_OPEN → CLOSED state machine.

    One instance is created per upstream service. The breaker
    tracks request outcomes in a sliding window and trips open
    when the failure rate exceeds the configured threshold.

    Thresholds:
        failure_threshold — number of failures in window to trip
        window_size       — size of the sliding request window
        open_duration     — seconds to stay OPEN before probing
        half_open_max     — max probe requests allowed in HALF_OPEN
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        window_size: int = 10,
        open_duration: float = 30.0,
        half_open_max: int = 1
    ):
        self.service_name      = service_name
        self.failure_threshold = failure_threshold
        self.window_size       = window_size
        self.open_duration     = open_duration
        self.half_open_max     = half_open_max

        # state
        self.state             = State.CLOSED
        self.last_failure_time = 0.0
        self.probe_sent        = False

        # sliding window — True = success, False = failure
        self.request_window: deque[bool] = deque(maxlen=window_size)

        logger.info(
            f"[CB:{self.service_name}] Initialized — "
            f"threshold={failure_threshold}/{window_size} "
            f"open_duration={open_duration}s"
        )


    def can_pass(self) -> bool:
        """
        Decide whether a request should be forwarded to upstream.
        Returns True if allowed, False if the breaker is blocking.
        """
        if self.state == State.CLOSED:
            return True
        
        if self.state == State.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.open_duration:
                self._enter_half_open()
                return True  # allow probe
            logger.warning(
                f"[CB:{self.service_name}] OPEN - blocking request. "
                f"Retry in {round(self.open_duration - elapsed)}s"
            )
            return False
        
        return False

    def on_success(self) -> None:
        """
        Called after a successful upstream response.
        Updates sliding window and handles HALF_OPEN → CLOSED transition.
        """
        if self.state == State.CLOSED:
            self.request_window.append(True)
            logger.debug(
                f"[CB:{self.service_name}] Success recorded - "
                f"window={list(self.request_window)}"
            )

    def on_failure(self) -> None:
        """
        Called after a failed upstream response (5xx or connection error).
        Updates sliding window and handles CLOSED → OPEN transition.
        """
        if self.state == State.CLOSED:
            self.request_window.append(False)
            failures = self.request_window.count(False)
            logger.warning(
                f"[CB:{self.service_name}] Failure recorded - "
                f"{failures}/{self.failure_threshold} in window"
            )
            if failures >= self.failure_threshold:
                self._trip_open()

    def _trip_open(self) -> None:
        """
        Transition to OPEN state.
        Records failure time and resets probe flag.
        """
        self.state = State.OPEN
        self.last_failure_time = time.time()
        self.probe_sent = False
        logger.warning(
            f"[CB:{self.service_name}] TRIPPED OPEN - "
            f"{self.failure_count} failures in last {len(self.request_window)} requests"
        )

    def _enter_half_open(self) -> None:
        """
        Transition to HALF_OPEN state.
        Resets probe flag to allow exactly one probe request.
        """
        self.state = State.HALF_OPEN
        self.probe_sent = False
        logger.warning(
            f"[CB:{self.service_name}] HALF_OPEN - "
            f"sending probe after {self.open_duration}s timeout"
        )

    @property
    def failure_count(self) -> int:
        """Number of failures in current sliding window."""
        return self.request_window.count(False)

    @property
    def state_info(self) -> dict:
        """Returns current breaker state for observability endpoints."""
        return {
            "service":           self.service_name,
            "state":             self.state.value,
            "failure_count":     self.failure_count,
            "window_size":       len(self.request_window),
            "failure_threshold": self.failure_threshold,
            "open_duration":     self.open_duration,
            "probe_sent":        self.probe_sent
        }