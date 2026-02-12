from unittest.mock import patch

import pytest

from server.commands.admin import ooc_cmd_login
from server.exceptions import ArgumentError, ClientError
from tests.mock.mocks import CommandClient


@patch("server.commands.admin.database")
def test_login_success(mock_db):
    client = CommandClient()
    ooc_cmd_login(client, "mod")

    assert client.is_mod is True
    assert client.mod_profile_name == "Admin"
    client.area.broadcast_area_list.assert_called_once_with(client)
    client.area.broadcast_evidence_list.assert_called_once()
    client.send_ooc.assert_called_once_with("Logged in as a moderator.")
    client.server.webhooks.login.assert_called_once_with(client, "Admin")


@patch("server.commands.admin.database")
def test_login_no_password_raises(mock_db):
    client = CommandClient()
    with pytest.raises(ArgumentError, match="You must specify the password."):
        ooc_cmd_login(client, "")


@patch("server.commands.admin.database")
def test_login_wrong_password_raises(mock_db):
    client = CommandClient()
    with pytest.raises(ClientError, match="Invalid password."):
        ooc_cmd_login(client, "wrong")

    assert client.is_mod is False


@patch("server.commands.admin.database")
def test_login_already_logged_in_raises(mock_db):
    client = CommandClient()
    client.is_mod = True
    with pytest.raises(ClientError, match="Already logged in."):
        ooc_cmd_login(client, "mod")


@patch("server.commands.admin.database")
def test_login_simple_string_modpass(mock_db):
    """When modpass is a plain string instead of a dict."""
    client = CommandClient(config={"modpass": "plainpass"})
    ooc_cmd_login(client, "plainpass")

    assert client.is_mod is True
    assert client.mod_profile_name == "default"
    client.send_ooc.assert_called_once_with("Logged in as a moderator.")
