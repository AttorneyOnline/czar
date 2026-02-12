from typing import Callable, Optional
from unittest.mock import MagicMock

import oyaml as yaml

from server.client import Client

# Default config loaded from config_sample/config.yaml.
# Tests can override individual keys via CommandClient(config={...}).
with open("config_sample/config.yaml") as _f:
    DEFAULT_CONFIG = yaml.safe_load(_f)


class MockClient:
    """Mock client for both protocol-level and command-level tests.

    When constructed with a *transport* (protocol tests), ``send_command``
    encodes AO packets onto the transport and ``disconnect`` closes it.

    When constructed without a transport (command tests), ``send_command``
    and ``send_ooc`` are MagicMock instances so tests can use
    ``assert_called_*``.  The sample config is loaded as a base and
    individual keys can be overridden via *config*.

    Real Client methods (e.g. ``auth_mod``) are bound here so tests
    exercise production logic.

    Args:
        transport: asyncio transport for protocol tests.
        config: Dict of config overrides merged on top of DEFAULT_CONFIG.
            Example: ``MockClient(config={"modpass": "plaintext"})``
    """

    # Real Client methods bound on MockClient instances.
    auth_mod = Client.auth_mod

    def __init__(self, transport=None, config=None):
        self.transport = transport
        self.ipid = "test-ipid"
        self.id = 0
        self.name = ""
        self.showname = "TestUser"
        self.is_mod = False
        self.mod_profile_name = None
        self.available_areas_only = False

        if transport is not None:
            # Protocol-level: server/area set later by the protocol handler
            self.server = None
            self.area = None
        else:
            # Command-level: set up server config and mock sub-objects
            merged = dict(DEFAULT_CONFIG)
            if config:
                merged.update(config)
            self.server = MagicMock()
            self.server.config = merged
            self.server.command_aliases = {}
            self.area = MagicMock()
            self.send_ooc = MagicMock()
            self.send_command = MagicMock()

    def send_command(self, command: str, *args) -> None:
        """Encode and write an AO-style command to the transport.

        Example: send_command("decryptor", "NOENCRYPT") ->
        b"decryptor#NOENCRYPT#%"
        """
        msg = command
        if args:
            msg += "#" + "#".join(str(a) for a in args)
        msg += "#%"
        self.transport.write(msg.encode("utf-8"))

    def disconnect(self) -> None:
        try:
            self.transport.close()
        except Exception:
            pass


class MockClientManager:
    """Minimal client manager stub used by AOProtocol.

    Only the `new_client_preauth` method is used during handshake to apply
    a pre-auth limit; here we simply allow all connections.
    """

    def new_client_preauth(self, client: "MockClient") -> bool:  # noqa: ARG002
        return True


class MockServer:
    """Tiny server façade exposing only what AOProtocol touches in tests.

    Attributes
    - config: dict with at least `timeout` key
    - client_manager: object exposing `new_client_preauth`
    """

    def __init__(self, timeout: float = 1.0, client_factory: Optional[Callable] = None):
        self.config = {"timeout": timeout}
        self.client_manager = MockClientManager()
        self._client_factory = client_factory or (lambda transport: MockClient(transport))

    def new_client(self, transport):
        return self._client_factory(transport)

    def remove_client(self, client):  # noqa: ARG002
        # Not needed for initial handshake tests
        pass


def make_protocol_factory(server) -> Callable[[], object]:
    """Return a factory suitable for `loop.create_server`.

    Example usage:
        loop.create_server(make_protocol_factory(server), host, port)
    """
    from server.network.aoprotocol import AOProtocol

    return lambda: AOProtocol(server)
