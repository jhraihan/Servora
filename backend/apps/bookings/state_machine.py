from apps.common.exceptions import InvalidStateTransition

from .models import Booking

State = Booking.State

ALLOWED_TRANSITIONS = {
    State.SCHEDULED: {
        State.IN_PROGRESS,
        State.CANCELLED_CUSTOMER,
        State.CANCELLED_PROVIDER,
    },
    State.IN_PROGRESS: {
        State.AWAITING_CONFIRM,
        State.CANCELLED_CUSTOMER,
        State.CANCELLED_PROVIDER,
    },
    State.AWAITING_CONFIRM: {
        State.COMPLETED,
        State.DISPUTED,
    },
    State.COMPLETED: {
        State.DISPUTED,
    },
    State.CANCELLED_CUSTOMER: set(),
    State.CANCELLED_PROVIDER: set(),
    State.DISPUTED: {
        State.COMPLETED,
    },
}


def can_transition(from_state, to_state):
    return to_state in ALLOWED_TRANSITIONS.get(from_state, set())


def assert_can_transition(from_state, to_state):
    if not can_transition(from_state, to_state):
        raise InvalidStateTransition(
            "A booking in state '%s' cannot move to '%s'."
            % (from_state, to_state),
            details={"from_state": from_state, "to_state": to_state},
        )


def reachable_from(from_state):
    return sorted(ALLOWED_TRANSITIONS.get(from_state, set()))
