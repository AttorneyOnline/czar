from server import commands
from server.exceptions import ClientError, AreaError, ArgumentError, ServerError

import datetime
import logging

logger = logging.getLogger("timer")


class Timer:
    """Represents a single instance of a timer.

    Used by both Area (timer IDs 1-20) and AreaManager/Hub (timer ID 0).
    The `parent` attribute references whichever object owns the timer
    (an Area or an AreaManager); both expose `broadcast_ooc()` and `owners`.
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
