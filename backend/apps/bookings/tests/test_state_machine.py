import itertools

import pytest

from apps.bookings.models import Booking
from apps.bookings.state_machine import (
    ALLOWED_TRANSITIONS, assert_can_transition, can_transition,
    reachable_from,
)
from apps.common.exceptions import InvalidStateTransition

State = Booking.State

LEGAL = [
    (State.SCHEDULED, State.IN_PROGRESS),
    (State.SCHEDULED, State.CANCELLED_CUSTOMER),
    (State.SCHEDULED, State.CANCELLED_PROVIDER),
    (State.IN_PROGRESS, State.AWAITING_CONFIRM),
    (State.IN_PROGRESS, State.CANCELLED_CUSTOMER),
    (State.IN_PROGRESS, State.CANCELLED_PROVIDER),
    (State.AWAITING_CONFIRM, State.COMPLETED),
    (State.AWAITING_CONFIRM, State.DISPUTED),
    (State.COMPLETED, State.DISPUTED),
    (State.DISPUTED, State.COMPLETED),
]


@pytest.mark.parametrize("from_state,to_state", LEGAL)
def test_legal_transitions_are_allowed(from_state, to_state):
    assert can_transition(from_state, to_state) is True
    assert_can_transition(from_state, to_state)


def test_every_illegal_transition_raises():
    legal = set(LEGAL)
    checked = 0

    for from_state, to_state in itertools.product(State.values, repeat=2):
        if (from_state, to_state) in legal:
            continue
        checked += 1
        assert can_transition(from_state, to_state) is False
        with pytest.raises(InvalidStateTransition):
            assert_can_transition(from_state, to_state)

    assert checked == len(State.values) ** 2 - len(legal)


def test_cancelled_states_are_terminal():
    assert reachable_from(State.CANCELLED_CUSTOMER) == []
    assert reachable_from(State.CANCELLED_PROVIDER) == []


def test_completed_can_only_move_to_disputed():
    assert reachable_from(State.COMPLETED) == [State.DISPUTED]


def test_no_state_transitions_to_itself():
    for state in State.values:
        assert can_transition(state, state) is False


def test_scheduled_cannot_skip_to_completed():
    assert can_transition(State.SCHEDULED, State.COMPLETED) is False


def test_in_progress_cannot_skip_confirmation():
    assert can_transition(State.IN_PROGRESS, State.COMPLETED) is False


def test_cancelled_booking_cannot_be_revived():
    for target in State.values:
        assert can_transition(State.CANCELLED_PROVIDER, target) is False


def test_error_carries_both_states():
    with pytest.raises(InvalidStateTransition) as exc:
        assert_can_transition(State.SCHEDULED, State.COMPLETED)

    assert exc.value.details["from_state"] == State.SCHEDULED
    assert exc.value.details["to_state"] == State.COMPLETED
    assert exc.value.status_code == 409


def test_every_state_is_in_the_transition_table():
    assert set(ALLOWED_TRANSITIONS) == set(State.values)
