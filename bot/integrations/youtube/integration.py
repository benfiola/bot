from __future__ import annotations

import asyncio
import datetime
import logging
from typing import List, Optional
import urllib.parse

import pydantic
import pytube
import requests.auth

from bot.integrations.base import Integration as IntegrationBase
from bot.media import Media


logger = logging.getLogger(__name__)


class Integration(IntegrationBase):
    """
    Youtube integration
    """

    name = "youtube"

    def __init__(self, api_key: str):
        self.client = Client(api_key)

    async def search(self, query: str) -> List[Video]:
        """
        Searches youtube for a video.
        :param query:
        :return:
        """
        logger.debug(f"search: {query}")
        return await self.client.search_list(query)

    async def get(self, video_id: str) -> Video:
        """
        Gets a video (by video id) from youtube.
        :param video_id:
        :return:
        """
        logger.debug(f"get: {video_id}")
        videos = await self.client.video_list(video_id)
        assert videos, f"video not found: {video_id}"
        return videos[0]

    async def get_from_url(self, url: str) -> Optional[Video]:
        """
        Parses a youtube URL and returns a `Video` object if a video is found.
        :param url:
        :return:
        """
        logger.debug(f"get: {url}")
        video_id = video_id_from_url(url)
        if not video_id:
            return None

        return await self.get(video_id)

    @staticmethod
    async def convert(video: Video) -> Media:
        """
        Converts a youtube `Video` into a `Media` object.
        :param video:
        :return:
        """
        return Media(url=await video.url(), title=video.title, duration=video.duration)


class Video(pydantic.BaseModel):
    id: str
    duration: datetime.timedelta
    title: str

    async def url(self) -> str:
        return await video_id_to_stream_url(self.id)


class Auth(requests.auth.AuthBase):
    api_key: str

    def __init__(self, api_key: str):
        self.api_key = api_key

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        """
        Adds api key to query parameters in youtube v3 API URL\
        :param r:
        :return:
        """
        r.prepare_url(r.url, params=dict(key=self.api_key))
        return r


class Client:
    api_key: str

    def __init__(self, api_key: str):
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = requests.Session()
        self.session.auth = Auth(api_key)

    async def video_list(self, *video_ids: str) -> List[Video]:
        """
        Implementation of GET https://www.googleapis.com/youtube/v3/videos API

        Returns videos in order of `video_ids` list.
        :param video_ids:
        :return:
        """

        def inner():
            url = f"{self.base_url}/videos"

            params = dict()
            params["part"] = "contentDetails,snippet"
            params["id"] = ",".join(video_ids)
            params["maxResults"] = 50

            return self.session.get(url, params=params)

        response = await asyncio.get_event_loop().run_in_executor(None, inner)
        response.raise_for_status()

        data = response.json()
        videos = []
        for item in data["items"]:
            video_id = item["id"]
            title = item["snippet"]["title"]
            duration = pydantic.parse_obj_as(datetime.timedelta, item["contentDetails"]["duration"])
            video = Video(id=video_id, title=title, duration=duration)
            videos.append(video)

        return videos

    async def search_list(self, query: str) -> List[Video]:
        """
        Implementation of GET https://www.googleapis.com/youtube/v3/search API

        Calls to `videos` API with video ids from search results to obtain full
         set of needed information.

        :param query:
        :return:
        """

        def inner():
            url = f"{self.base_url}/search"

            params = dict()
            params["part"] = "snippet"
            params["q"] = query
            params["type"] = "video"
            params["maxResults"] = 50

            return self.session.get(url, params=params)

        response = await asyncio.get_event_loop().run_in_executor(None, inner)
        response.raise_for_status()

        data = response.json()
        video_ids = [item["id"]["videoId"] for item in data["items"]]

        return await self.video_list(*video_ids)


async def video_id_to_stream_url(video_id: str) -> str:
    """
    Utilizes pytube to viable audio streams for the given youtube URL.

    Prioritizes the highest bitrate of the streams found.
    :param video_id:
    :return:
    """
    url = f"https://www.youtube.com/watch?v={video_id}"

    container = pytube.YouTube(url)
    streams = container.streams.filter(only_audio=True, audio_codec="opus")
    streams = sorted(streams, key=lambda s: s.bitrate, reverse=True)
    assert streams, f"youtube stream not found: {video_id}"
    stream = streams[0]

    logger.debug(f"video id to stream url: ({video_id}) -> ({stream.url})")
    return stream.url


def video_id_from_url(url: str) -> Optional[str]:
    """
    Attempts to obtain a video_url from a variety of youtube URL formats.
    :param url:
    :return:
    """
    parts = urllib.parse.urlparse(url)

    query = urllib.parse.parse_qs(parts.query)
    video_id = query.get("v")
    if video_id:
        # video_id is a `v` query parameter in the url
        video_id = video_id[0]
        logger.debug(f"video id from url: ({url}) -> ({video_id})")
    else:
        # video_id is the last part of the url path
        path = parts.path
        video_id = path.split("/")[-1]

    video_id = video_id.strip()
    if not video_id:
        video_id = None

    logger.debug(f"video id from url: ({url}) -> ({video_id})")
    return video_id
