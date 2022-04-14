from __future__ import annotations
from enum import IntEnum

from typing import TYPE_CHECKING, Any, Union

from .flags import FrozenFlag as FF, FrozenFlags
from ..types import Overwrite as OverwriteP

if TYPE_CHECKING:
    from cordy.models.snowflake import Snowflake

class Permissions(FrozenFlags):
    __slots__ = ()

    create_invite = FF(1)
    """:class:`bool`: Whether invite can be created"""
    kick_members = kick = FF(1 << 1)
    """:class:`bool`: Whether members can be kicked"""
    ban_members = ban = FF(1 << 2)
    """:class:`bool`: Whether members can be banned"""
    administrator = FF(1 << 3)
    """:class:`bool`: Whether user is an administrator, this permission has similar effect to setting all permissions :data:`True`"""

    manage_channels = FF(1 << 4)
    """:class:`bool`: Whether user can manage channels"""
    manage_guild = FF(1 << 5)
    """:class:`bool`: Whether user can manage the server"""
    add_reactions = FF(1 << 6)
    """:class:`bool`: Whether user can add reactions to messages"""
    view_audit_log = FF(1 << 7)
    """:class:`bool`: Whether user can view the audit log"""
    priority_speaker = FF(1 << 8)
    """:class:`bool`: Whether user can use priority speaker in a voice channel"""
    stream = FF(1 << 9)
    """:class:`bool`: Whether user can start a stream in a voice channel"""
    view_channel = FF(1 << 10)
    """:class:`bool`: Whether user can view a channel"""
    send_messages = FF(1 << 11)
    """:class:`bool`: Whether user can send messages in a channel"""
    send_tts_messages = use_tts = FF(1 << 12)
    """:class:`bool`: Whether user can send text-to-speech messages"""
    manage_messages = FF(1 << 13)
    """:class:`bool`: Whether user can delete messages"""
    embed_links = FF(1 << 14)
    """:class:`bool`: Whether the links sent by user will be auto-embedded"""
    attach_files = FF(1 << 15)
    """:class:`bool`: Whether user can attach files to messages"""
    read_message_history = read_messages = FF(1 << 16)
    """:class:`bool`: Whether user can read message in a text channel"""
    mention_everyone = FF(1 << 17)
    """:class:`bool`: Whether user can do a ``@everyone`` & ``@here`` mention"""
    use_external_emojis = external_emojis = FF(1 << 18)
    """:class:`bool`: Whether user can use emojis from other servers"""
    view_guild_insights = FF(1 << 19)
    """:class:`bool`: Whether user can view guild insights"""

    connect = FF(1 << 20)
    """:class:`bool`: Whether user can connect to a voice channel"""
    speak = FF(1 << 21)
    """:class:`bool`: Whether user can speak in a voice channel"""
    mute_members = mute = FF(1 << 22)
    """:class:`bool`: Whether user can mute members in a voice channel"""
    deafen_members = deafen = FF(1 << 23)
    """:class:`bool`: Whether user can deafen members in a voice channel"""
    move_members = move = FF(1 << 24)
    """:class:`bool`: Whether user can move members between voice channels"""
    voice_activity = use_vad = FF(1 << 25)
    """:class:`bool`: Whether user can use voice activity detection to speak in a voice channel"""

    change_nickname = change_nick = FF(1 << 26)
    """:class:`bool`: Whether user can chenge their own nickname"""
    manage_nicknames = manage_nicks = FF(1 << 27)
    """:class:`bool`: Whether user can change nickname of other members"""
    manage_roles = FF(1 << 28)
    """:class:`bool`: Whether user can manage roles"""
    manage_webhooks = FF(1 << 29)
    """:class:`bool`: Whether user can manage webhooks"""
    manage_emojis = manage_stickers = manage_emojis_and_stickers = FF(1 << 30)
    """:class:`bool`: Whether user can manage emojis and stickers"""

    use_application_commands = use_app_cmds = FF(1 << 31)
    """:class:`bool`: Whether user can use application commands"""
    request_to_speak = FF(1 << 32) # unstable, 4/14/2022
    """:class:`bool`: Whether user can request to speak in a stage channel"""
    manage_events = FF(1 << 33)
    """:class:`bool`: Whether user can create, edit, and delete scheduled events"""
    manage_threads = FF(1 << 34)
    """:class:`bool`: Whether user can delete and archive threads, and view all private threads"""
    create_public_threads = FF(1 << 35)
    """:class:`bool`: Whether user can create public and announcement threads"""
    create_private_threads = FF(1 << 36)
    """:class:`bool`: Whether user can create private threads"""
    use_external_stickers = external_stickers = FF(1 << 37)
    """:class:`bool`: Whether user can use external stickers"""
    send_messages_in_threads = FF(1 << 38)
    """:class:`bool`: Whether user can send messages in threads"""
    use_embedded_activities = embedded_activities = FF(1 << 39)
    """:class:`bool`: Whether user can use Activities in a voice channel"""
    moderate_members = FF(1 << 40)
    """:class:`bool`: Whether user can time-out members"""


TriStated = Union[bool, None]

class Overwrite:
    __slots__ = ("value",)

    def __init__(self, value: int) -> None:
        self.value = value

    def __set__(self, inst: Overwrites, value: TriStated) -> None:
        if value is None:
            inst._allow &= ~self.value
            inst._deny &= ~self.value
        elif value:
            inst._allow |= self.value
            inst._deny &= ~self.value
        else:
            inst._allow &= ~self.value
            inst._deny |= self.value

    def __get__(self, inst: Overwrites, _) -> TriStated:
        try:
            return (None, False, True)[2 * (inst._allow & self.value == self.value) + (inst._deny & self.value == self.value)]
        except IndexError:
            raise ValueError(f"{repr(inst)} of type {type(inst)} has invalid allow and deny fields")

class OverwriteType(IntEnum):
    Role = 0
    Member = 1

class Overwrites:
    __slots__ = (
        "id",
        "type",
        "_allow",
        "_deny"
    )

    id: Snowflake
    type: OverwriteType
    _allow: int
    _deny: int

    @classmethod
    def from_data(cls, data: OverwriteP):
        self = object.__new__(cls)
        self.id = Snowflake(data["id"])
        self.type = OverwriteType(data["type"])
        self._allow = int(data["allow"])
        self._deny = int(data["deny"])

last: Any = [None, None]
for k, v in Permissions.__dict__.items():
    if isinstance(v, FF):
        if v is last[1]:
            setattr(Overwrites, k, last[0])
        else:
            last[1] = v
            last[0] = Overwrite(v.value)
            setattr(Overwrites, k, last[0])