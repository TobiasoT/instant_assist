from datetime import timedelta
from livekit.api.access_token import AccessToken, VideoGrants
import os

from source.locations_and_config import config


def make_token(identity: str, room: str, hours:int=24 ) -> str:
    # set LIVEKIT_API_KEY, LIVEKIT_API_SECRET in your env first
    return (
        AccessToken(
            api_key = config.livekit_api_key,
            api_secret = config.livekit_api_secret,
        )
        .with_identity(identity)
        .with_grants(VideoGrants(room_join=True, room=room))
        .with_ttl(timedelta(hours=hours))
        .to_jwt()
    )
 