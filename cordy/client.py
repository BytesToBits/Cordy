from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, Any, Callable, Sequence
from asyncio import get_running_loop

from .auth import Token
from .events import Emitter, Publisher
from .gateway import Sharder
from .http import HTTPSession
from .models import Intents

if TYPE_CHECKING:
    from .auth import StrOrToken
    from .events import CheckFn, CoroFn
    from .gateway import BaseSharder, Shard

__all__ = (
    "Client",
)

logger = getLogger("cordy.client")

class Client:
    """The discord API Gateway client.

    Attributes
    ----------
    token : :class:`~cordy.auth.Token`
        The gateway authorization token.
    intents : :class:`~cordy.models.Intent`
        The gateway intents used by the client
    emitter : :class:`~cordy.events.Emitter`
        The client event emitter. You don't need to interact with this
        if you do not want custom events
    publisher : :class:`~cordy.events.Publisher`
        The event publisher.
    shard_ids : :class:`set`, (``set[int] | None``)
        The shard ids to launch. If :data:`None` then sharder automatically shards the client
    num_shard : :class:`int`, (``int | None``)
        The total number of shards the client has, this number includes shards which are not
        under this client.
    sharder : :class:`~cordy.gateway.BaseSharder`, (``BaseSharder[Shard]``)
        The gateway sharder for the client.

    Parameters
    ----------
    token : :class:`str`, :class:`Token`, (``str | Token``)
        The token for the gateway. Is a string is provided then a bot token is built.
        This is a required argument. All following arguments are keyword only.
    intents : :class:`~cordy.models.Intent`
        This is an optional parameter.
        The gateway intents used by the client. If None, then value returned by :meth:`~cordy.models.Intent.default`
        is used. by default None.
    sharder_cls: type[:class:`~cordy.gateway.BaseSharder`]
        The sharder type to use. Must subclass the :class:`~cordy.gateway.BaseSharder` protocol.
        If :data:`None` then :class:`~cordy.gateway.Sharder` is used. By default :data:`None`
    num_shards : :class:`int`
        The total number of shards. If :data:`None` :attr:`.Client.sharder` provided value will be used.
        By default :data:`None`
    shard_ids : Sequence[:class:`int`]
        A sequence of shard ids that this client should launch. If not :data:`None` then
        ``num_shards`` parameter must be provided.
        If :data:`None` then shards are generated from ``num_shards`` or :attr:`.Client.sharder` provided value will be used.
    """
    num_shards: int | None
    shard_ids: set[int] | None
    http: HTTPSession

    def __init__(
        self, token: StrOrToken, *,
        intents: Intents = None, sharder_cls: type[BaseSharder[Shard]] = Sharder,
        num_shards: int = None, shard_ids: Sequence[int] = None
    ):
        self.intents = intents or Intents.default()
        self.token = token if isinstance(token, Token) else Token(token, bot=True)

        self.emitter = Emitter()
        self.publisher = Publisher(None)
        self.publisher.add(self.emitter)
        self.http = HTTPSession(self.token)

        if shard_ids is not None and num_shards is None:
            raise ValueError("Must provide num_shards if shard ids are provided.")

        if shard_ids is None and num_shards is not None:
            shard_ids = list(range(num_shards))

        self.shard_ids = set(shard_ids) if shard_ids else None
        self.num_shards = num_shards

        # May manipulate client attributes
        self.sharder = sharder_cls(self)
        self._closed_cb: Callable | None = None
        self._closed: bool = False

    @property
    def shards(self) -> list[Shard]:
        "list[:class:`~cordy.gateway.Shard`] : All the shards under this client"
        return self.sharder.shards

    def listen(self, name: str = None) -> Callable[[CoroFn], CoroFn]:
        """This method is used as a decorator.
        Add the decorated function as a listener for the specified event

        Parameters
        ----------
        name : :class:`str`
            The name of the event. If :data:`None` then the
            name of the function is used, by default :data:`None`.

        Returns
        -------
        Callable
            The decorator.
        """
        def deco(func: CoroFn):
            self.publisher.subscribe(name or func.__name__.lower(), func)
            return func
        return deco

    def add_listener(self, func: CoroFn, name: str = None) -> None:
        """Add a listener for the given event.

        Parameters
        ----------
        func : Callable[..., Coroutine]
            The coroutine function to add as a listener. This is a required argument.
        name : :class:`str`
            The name of the event. If :data:`None` then the
            name of the function is used, by default :data:`None`.
        """
        return self.publisher.subscribe(name or func.__name__.lower(), func)

    def remove_listener(self, func: CoroFn, name: str = None) -> None:
        """Remove a registered listener.
        If the listener or event is not found, then does nothing.

        Parameters
        ----------
        func : Callable[..., Coroutine]
            The coroutine function which needs to be unsubscribed. This is a required argument.
        name : :class:`str`
            The name of the event. If :data:`None` then the
            name of the function is used, by default :data:`None`.
        """
        return self.publisher.unsubscribe(func, name)

    async def wait_for(self, name: str, timeout: int = None, check: CheckFn = None) -> tuple[Any, ...]:
        """Wait for an event to occur.

        Parameters
        ----------
        name : :class:`str`
            The name of the event to wait for.
        timeout : :class:`int`
            The time to wait for the event to occur, if :data:`None`
            then wait indefinetly, by default :data:`None`
        check : Callable[..., :class:`bool`]
            The check function, a subroutine returning a boolean,
            the provided arguments are the same as the returned :class:`tuple`.
            If the check function returns :data:`True` then the same data that was
            given to the check function will be returned, or else continue waiting for
            the event. If :data:`None` then return the first event data, by default :data:`None`

        Returns
        -------
        tuple[Any, ...]
            The data associated with the event. This is the same as the arguments received
            by listeners for the event.
        """
        return await self.publisher.wait_for(name, timeout, check)

    async def setup(self) -> None:
        """Initialise client with the current running event loop.
        """
        try:
            loop = get_running_loop()
        except RuntimeError as err:
            raise Exception("Ran Coroutine without a running aysncio event loop") from err
        else:
            if loop is not self.http.session._loop:
                self.http = HTTPSession(self.token)

    async def connect(self) -> None:
        """Launch all shards and connect to gateway.
        """
        if self._closed:
            raise ValueError("Can't connect with a closed client.")

        await self.setup()
        await self.sharder.create_shards()
        await self.sharder.launch_shards()

    async def disconnect(self, *, code: int = 4000, message: str = "") -> None:
        """Disconnect all shards from the gateway

        Parameters
        ----------
        code : :class:`int`
            Optional status code to close the gateway connection, by default 4000
        message : :class:`str`
            A message to close the gateway connection, by default an empty string.
        """
        if self._closed:
            return

        for shard in self.shards:
            await shard.disconnect(code=code, message=message)

        logger.info("Shards %s disconnected from gateway", self.shard_ids)

    async def reconnect(self) -> None:
        """Reconnect all shards to the gateway
        """
        if self._closed:
            raise ValueError("Can't reconnect with a closed client.")

        for shard in self.shards:
            await shard.reconnect()

        logger.info("Shards %s reconnected to gateway", self.shard_ids)

    async def close(self) -> None:
        """Close the client permanently.
        """
        if self._closed:
            return

        await self.disconnect(code=1000, message="Client Closed")
        await self.http.close()

        if self._closed_cb:
            from asyncio import get_running_loop
            get_running_loop().call_soon(self._closed_cb)
            self._closed_cb = None

        logger.info("Client closed") # add user info here

