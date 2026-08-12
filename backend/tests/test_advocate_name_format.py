"""Regression tests for the centralized advocate-name formatting.

Covers the display-layer rule "Adv. <Name>" for advocate/lawyer users:

  * Backend server.format_advocate_name defaults (used when a client does not
    send advocate_name) — no double prefix, empty -> "Advocate".
  * build_render_context applies the default only when the client did not
    provide advocate_name (client value wins, so lawyer edits are preserved).
  * Client-provided values are never rewritten.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "nyaysetu_test_advocate")

import mongomock_motor

mock_client = mongomock_motor.AsyncMongoMockClient()
mock_db = mock_client["nyaysetu_test_advocate"]

import server


# ---------------------------------------------------------------- pure helper

def test_format_advocate_name_prepends_prefix():
    assert server.format_advocate_name("Jaydeep Jadav") == "Adv. Jaydeep Jadav"


def test_format_advocate_name_does_not_double_prefix():
    assert server.format_advocate_name("Adv. Jaydeep Jadav") == "Adv. Jaydeep Jadav"
    assert server.format_advocate_name("adv. Jaydeep Jadav") == "adv. Jaydeep Jadav"
    assert server.format_advocate_name("ADV. Jaydeep Jadav") == "ADV. Jaydeep Jadav"
    assert server.format_advocate_name("Adv Jaydeep Jadav") == "Adv Jaydeep Jadav"


def test_format_advocate_name_trims_and_falls_back():
    assert server.format_advocate_name("  Jaydeep Jadav  ") == "Adv. Jaydeep Jadav"
    assert server.format_advocate_name("") == "Advocate"
    assert server.format_advocate_name(None) == "Advocate"


# ------------------------------------------------------ render-context default

async def test_render_context_defaults_to_adv_prefix():
    user = {"name": "Jaydeep Jadav"}
    ctx = await server.build_render_context(user, None, {}, "en")
    assert ctx["advocate_name"] == "Adv. Jaydeep Jadav"


async def test_render_context_does_not_double_prefix_stored_adv():
    user = {"name": "Adv. Jaydeep Jadav"}
    ctx = await server.build_render_context(user, None, {}, "en")
    assert ctx["advocate_name"] == "Adv. Jaydeep Jadav"


async def test_render_context_keeps_client_value():
    # The lawyer's entered/edited value wins — never overwritten by the prefix.
    user = {"name": "Adv. Jaydeep Jadav"}
    ctx = await server.build_render_context(user, None, {"advocate_name": "Ramesh Patel"}, "en")
    assert ctx["advocate_name"] == "Ramesh Patel"


async def test_render_context_falls_back_to_advocate():
    ctx = await server.build_render_context({"name": None}, None, {}, "en")
    assert ctx["advocate_name"] == "Advocate"
