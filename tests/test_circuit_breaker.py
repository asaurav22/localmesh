from data_plane.circuit_breaker import CircuitBreaker, State


def test_initial_state_is_closed():
    cb = CircuitBreaker("test-service")
    assert cb.state == State.CLOSED


def test_can_pass_when_closed():
    cb = CircuitBreaker("test-service")
    assert cb.can_pass() is True


def test_trips_open_after_threshold_failures():
    cb = CircuitBreaker("test-service", failure_threshold=5, window_size=10)
    for _ in range(5):
        cb.on_failure()
    assert cb.state == State.OPEN


def test_does_not_trip_below_threshold():
    cb = CircuitBreaker("test-service", failure_threshold=5, window_size=10)
    for _ in range(4):
        cb.on_failure()
    assert cb.state == State.CLOSED


def test_sliding_window_clears_old_failures():
    """
    4 failures followed by 6 successes should NOT trip the breaker.
    The window size is 10 - after 6 successes the 4 old failures
    are still in the window but below threshold.
    Then add 1 more success pushing window to show failures drop off.
    """
    cb = CircuitBreaker("test-service", failure_threshold=5, window_size=10)

    # 4 failures
    for _ in range(4):
        cb.on_failure()
    assert cb.failure_count == 4
    assert cb.state == State.CLOSED

    # 6 successes - window now has [F,F,F,F,T,T,T,T,T,T]
    for _ in range(6):
        cb.on_success()
    assert cb.state == State.CLOSED
    assert cb.failure_count == 4

    # 1 more success - window slides: [F,F,F,T,T,T,T,T,T,T]
    cb.on_success()
    assert cb.failure_count == 3
    assert cb.state == State.CLOSED


def test_success_does_not_prevent_trip_if_failures_persist():
    """5 failures in a 10-window should trip even with prior successes."""
    cb = CircuitBreaker("test-service", failure_threshold=5, window_size=10)
    for _ in range(3):
        cb.on_success()
    for _ in range(5):
        cb.on_failure()
    assert cb.state == State.OPEN


def test_state_info_structure():
    cb = CircuitBreaker("test-service")
    info = cb.state_info
    assert "service"   in info
    assert "state"     in info
    assert "failure_count" in info
    assert info["state"] == "closed"


def test_last_failure_time_set_on_trip():
    import time
    cb = CircuitBreaker("test-service", failure_threshold=3, window_size=5)
    before = time.time()
    for _ in range(3):
        cb.on_failure()
    assert cb.last_failure_time >= before


def test_cannot_pass_when_open():
    cb = CircuitBreaker("test-service", failure_threshold=3, window_size=5)
    for _ in range(3):
        cb.on_failure()
    assert cb.state == State.OPEN
    assert cb.can_pass() is False


def test_transitions_to_half_open_after_timeout():
    import time
    cb = CircuitBreaker("test-service", failure_threshold=3, window_size=5, open_duration=1)
    for _ in range(3):
        cb.on_failure()
    assert cb.state == State.OPEN
    time.sleep(1.1)
    result = cb.can_pass()
    assert cb.state == State.HALF_OPEN
    assert result is True  # probe allowed


def test_503_retry_after_in_state_info():
    cb = CircuitBreaker("test-service", failure_threshold=3, window_size=5)
    for _ in range(3):
        cb.on_failure()
    info = cb.state_info
    assert info["state"] == "open"
    assert info["open_duration"] == 30.0
