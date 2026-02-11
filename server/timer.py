from server import commands
from server.exceptions import ClientError, AreaError, ArgumentError, ServerError

import datetime
import logging

logger = logging.getLogger("timer")


class Timer:
    """A countdown timer that can broadcast expiration and run commands.

    Hubs own timer ID 0 (global). Areas own timer IDs 1-20 (local).
    When the timer expires, it broadcasts an OOC message to the parent
    and executes any queued commands as the caller.

    Attributes:
        id: Timer identifier (0 for hub-level, 1-20 for area-level).
        set: Whether a duration has been configured.
        started: Whether the timer is actively counting down.
        static: The remaining time as a `datetime.timedelta`, or ``None``.
        target: The `datetime.datetime` when the timer expires, or ``None``.
        parent: The owning Area or AreaManager; must expose
            ``broadcast_ooc()`` and ``owners``.
        caller: The Client who set the timer; used for command execution.
        schedule: Handle for the pending asyncio callback, or ``None``.
        commands: List of OOC command strings to run on expiration.
        format: Qt-style time format string sent to clients.
        interval: Client-side tick interval in milliseconds.
    """

    def __init__(
        self,
        timer_id,
        Set=False,
        started=False,
        static=None,
        target=None,
        parent=None,
        caller=None,
    ):
        self.id = timer_id
        self.set = Set
        self.started = started
        self.static = static
        self.target = target
        self.parent = parent
        self.caller = caller
        self.schedule = None
        self.commands = []
        self.format = "hh:mm:ss.zzz"
        self.interval = 16

    def timer_expired(self):
        if self.schedule:
            self.schedule.cancel()
        if self.parent is None:
            return

        self.static = datetime.timedelta(0)
        self.started = False

        self.parent.broadcast_ooc(f"Timer {self.id} has expired.")
        self.call_commands()

    def call_commands(self):
        if self.caller is None:
            return
        if self.parent is None:
            return
        if self.caller not in self.parent.owners:
            return
        # We clear out the commands as we call them in order one by one
        while len(self.commands) > 0:
            # Take the first command in the list and run it
            cmd = self.commands.pop(0)
            args = cmd.split(" ")
            cmd = args.pop(0).lower()
            arg = ""
            if len(args) > 0:
                arg = " ".join(args)[:1024]
            try:
                # Area timers (id != 0) temporarily swap the caller into
                # the timer's parent area so commands execute in context.
                if self.id != 0:
                    old_area = self.caller.area
                    old_hub = self.caller.area.area_manager
                    self.caller.area = self.parent
                commands.call(self.caller, cmd, arg)
                if self.id != 0:
                    if old_area and old_area in old_hub.areas:
                        self.caller.area = old_area
            except (ClientError, AreaError, ArgumentError, ServerError) as ex:
                self.caller.send_ooc(f"[Timer {self.id}] {ex}")
                # Command execution critically failed somewhere. Clear out all commands so the timer doesn't screw with us.
                self.commands.clear()
                return
            except Exception as ex:
                self.caller.send_ooc(
                    f"[Timer {self.id}] An internal error occurred: {ex}. Please inform the staff of the server about the issue."
                )
                logger.error("Exception while running a command")
                # Command execution critically failed somewhere. Clear out all commands so the timer doesn't screw with us.
                self.commands.clear()
                return
