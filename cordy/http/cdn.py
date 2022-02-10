from __future__ import annotations

from typing import ClassVar, Final, Literal, Sequence

from yarl import URL

CDNParameters = Literal[
    "guild_id",
    "hash",
    "user_id",
    "id",
    "achievement_id",
]

class CDNRoute:
    _CACHE: ClassVar[dict[str, CDNRoute]] = {}
    CDN: Final = URL("https://cdn.discordapp.com/")

    path: str
    formats: Sequence[str]

    def __new__(cls, path: str):
        path = path.rpartition(".")[0].lstrip("/")
        self = cls._CACHE.get(path, None)

        if self is not None:
            return self
        else:
            self = super().__new__(cls)

            self.path = path
            self.formats = ["png",]
            cls._CACHE[path] = self
            return self

    # TODO: Validation
    def make_url(self, format: str = "png", **params) -> URL:
        if format not in self.formats:
            raise ValueError("Invalid format provided")
        try:
            # ignore because we are handling invalid key
            return self.BASE / (self.path.format_map(params) + "." + format) # type: ignore[arg-type]
        except KeyError as err:
            raise ValueError("All arguments needed for cdn-route not provided") from err

PNG = "png"
JPEG = ("jpeg", "jpg")
WEBP = "webp"
GIF = "gif"
LOTTIE = "json"


for i in (
    CDNRoute("emojis/{id}"),
    CDNRoute("icons/{guild_id}/{hash}"),
    CDNRoute("banners/{user_id}/{hash}"),
    CDNRoute("avatars/{user_id}/{hash}"),
    CDNRoute("guilds/{guild_id}/users/{user_id}/avatars/{hash}")
):
    i.formats = (*JPEG, PNG, WEBP, GIF)

for i in (
    CDNRoute("splashes/{guild_id}/{hash}"),
    CDNRoute("discovery-splashes/{guild_id}/{hash}"),
    CDNRoute("banners/{guild_id}/{hash}"),
    CDNRoute("app-icons/{id}/{hash}"),
    CDNRoute("app-assets/{id}/achievements/{achievement_id}/icons/{hash}"),
    CDNRoute("app-assets/{id}/store/{hash}"),
    CDNRoute("team-icons/{id}/{hash}"),
    CDNRoute("role-icons/{id}/{hash}")
):
    i.formats = (*JPEG, PNG, WEBP)

CDNRoute("stickers/{id}").formats = (PNG, LOTTIE)