"""High level runners for cordy only apps
"""

from __future__ import annotations

import asyncio
import signal
import sys
from asyncio.runners import _cancel_all_tasks  # type: ignore[attr-defined]
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .client import Client

__all__ = (
    "run", "run_all", "launch", "launch_all"
)

def _set_fut(fut: asyncio.Future):
    if not fut.done():
        fut.set_result(True)

async def run(client: Client):
    """Start a client and await till it is stopped

    Parameters
    ----------
    client : :class:`cordy.client.Client`
        The Client to be ran.
    """
    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    client._closed_cb = partial(_set_fut, fut)

    await client.connect()
    try:
        await fut
    finally:
        await client.close()

async def run_all(clients: Iterable[Client]):
    """Start multiple clients and await till all have stopped.

    Parameters
    ----------
    clients : Iterable[:class:`cordy.client.Client`]
        The iterable of clients to be ran.
    """
    loop = asyncio.get_running_loop()
    await asyncio.gather(*(loop.create_task(run(client)) for client in set(clients)))

def launch(client: Client):
    """Run the client until it is closed.
    Cleanup due to unforseen cancellation is handled.

    Parameters
    ----------
    client : :class:`~cordy.client.Client`
        The client to run.
    """
    return run_loop(run(client))

def launch_all(clients: Iterable[Client]):
    """launch all the given clients util all clients are closed.
    Cleanup for each client due to unforseen cancellation is handled.

    Parameters
    ----------
    clients : Iterable[:class:`~cordy.client.Client`]
        All the clients to launch.
    """
    return run_loop(run_all(clients))

# Proactor Transport require open event loop.
DEFAULT_CLOSE = not sys.platform.startswith("win")

def run_loop(coro, *, close: bool = DEFAULT_CLOSE, debug: bool = None):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        # just schedule coro if running
        asyncio.ensure_future(coro)
        if loop.is_running():
            return

    policy = asyncio.get_event_loop_policy()
    try:
        loop = policy.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if debug is not None:
        loop.set_debug(debug)

    def stop_loop(loop):
        loop.stop()

    try:
        loop.add_signal_handler(signal.SIGINT, stop_loop, loop)
        loop.add_signal_handler(signal.SIGTERM, stop_loop, loop)
    except NotImplementedError:
        pass

    try:
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            _cancel_all_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            if close:
                loop.close()
