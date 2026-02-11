import datetime
from unittest.mock import MagicMock, patch

from server.timer import Timer


class _FakeParent:
    """Minimal stand-in for Area / AreaManager — exposes broadcast_ooc and owners."""

    def __init__(self, owners=()):
        self.owners = set(owners)
        self.broadcast_ooc = MagicMock()
        # Area-like attribute used by the area-swap path
        self.area_manager = MagicMock()
        self.area_manager.areas = [self]


def _make_caller(area=None):
    caller = MagicMock()
    caller.area = area
    caller.area.area_manager = area.area_manager if area else MagicMock()
    return caller


# --- timer_expired ---


def test_timer_expired_resets_state_and_calls_commands():
    parent = _FakeParent()
    timer = Timer(1, parent=parent)
    timer.static = datetime.timedelta(seconds=30)
    timer.started = True
    timer.schedule = MagicMock()

    with patch.object(timer, "call_commands") as mock_cc:
        timer.timer_expired()

    assert timer.static == datetime.timedelta(0)
    assert timer.started is False
    timer.schedule.cancel.assert_called_once()
    parent.broadcast_ooc.assert_called_once_with("Timer 1 has expired.")
    mock_cc.assert_called_once()


def test_timer_expired_noop_when_no_parent():
    timer = Timer(1)
    timer.schedule = MagicMock()
    timer.timer_expired()
    timer.schedule.cancel.assert_called_once()
    # static/started should remain untouched
    assert timer.static is None
    assert timer.started is False


def test_timer_expired_hub_timer_displays_timer_0():
    parent = _FakeParent()
    timer = Timer(0, parent=parent)
    timer.static = datetime.timedelta(seconds=10)
    timer.started = True

    with patch.object(timer, "call_commands"):
        timer.timer_expired()

    parent.broadcast_ooc.assert_called_once_with("Timer 0 has expired.")


# --- call_commands ---


@patch("server.timer.commands")
def test_call_commands_executes_queued_commands(mock_commands):
    parent = _FakeParent()
    caller = _make_caller(area=parent)
    parent.owners.add(caller)

    timer = Timer(0, parent=parent, caller=caller)
    timer.commands = ["foo bar baz", "qux"]

    timer.call_commands()

    assert mock_commands.call.call_count == 2
    mock_commands.call.assert_any_call(caller, "foo", "bar baz")
    mock_commands.call.assert_any_call(caller, "qux", "")
    assert timer.commands == []


@patch("server.timer.commands")
def test_call_commands_skips_if_caller_not_owner(mock_commands):
    parent = _FakeParent()
    caller = _make_caller(area=parent)
    # caller is NOT in parent.owners

    timer = Timer(0, parent=parent, caller=caller)
    timer.commands = ["foo"]

    timer.call_commands()

    mock_commands.call.assert_not_called()
    # commands remain untouched
    assert timer.commands == ["foo"]


@patch("server.timer.commands")
def test_call_commands_clears_on_error(mock_commands):
    from server.exceptions import ClientError

    mock_commands.call.side_effect = ClientError("boom")

    parent = _FakeParent()
    caller = _make_caller(area=parent)
    parent.owners.add(caller)

    timer = Timer(0, parent=parent, caller=caller)
    timer.commands = ["bad", "also_bad"]

    timer.call_commands()

    # First command tried, then all cleared
    assert mock_commands.call.call_count == 1
    assert timer.commands == []
    caller.send_ooc.assert_called_once_with("[Timer 0] boom")


@patch("server.timer.commands")
def test_call_commands_clears_on_unexpected_error(mock_commands):
    mock_commands.call.side_effect = RuntimeError("unexpected")

    parent = _FakeParent()
    caller = _make_caller(area=parent)
    parent.owners.add(caller)

    timer = Timer(3, parent=parent, caller=caller)
    timer.commands = ["bad"]

    timer.call_commands()

    assert timer.commands == []
    caller.send_ooc.assert_called_once()
    assert "[Timer 3]" in caller.send_ooc.call_args[0][0]


# --- area swap for area timers (id != 0) ---


@patch("server.timer.commands")
def test_area_timer_swaps_caller_area(mock_commands):
    """Area timers (id != 0) temporarily set caller.area to the timer's parent."""
    parent = _FakeParent()
    original_area = _FakeParent()
    original_area.area_manager.areas = [original_area]

    caller = MagicMock()
    caller.area = original_area
    parent.owners.add(caller)

    timer = Timer(5, parent=parent, caller=caller)
    timer.commands = ["testcmd"]

    swapped_areas = []

    def capture_call(c, cmd, arg):
        swapped_areas.append(c.area)

    mock_commands.call.side_effect = capture_call

    timer.call_commands()

    # During execution, caller.area should have been the timer's parent
    assert swapped_areas == [parent]
    # After execution, caller.area should be restored
    assert caller.area == original_area


@patch("server.timer.commands")
def test_hub_timer_does_not_swap_caller_area(mock_commands):
    """Hub timers (id == 0) do NOT swap caller.area."""
    parent = _FakeParent()
    original_area = _FakeParent()

    caller = MagicMock()
    caller.area = original_area
    parent.owners.add(caller)

    timer = Timer(0, parent=parent, caller=caller)
    timer.commands = ["testcmd"]

    swapped_areas = []

    def capture_call(c, cmd, arg):
        swapped_areas.append(c.area)

    mock_commands.call.side_effect = capture_call

    timer.call_commands()

    # caller.area should remain the original throughout
    assert swapped_areas == [original_area]
    assert caller.area == original_area
