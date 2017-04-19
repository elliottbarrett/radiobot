import os
import time
import sys
import httplib2

from enum import Enum
from slackclient import SlackClient
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser
from oauth2client.tools import run_flow
from apiclient.discovery import build

class ContinueType(Enum):
    NONE = 0
    STANDARD = 1
    USER_ONLY = 2
    GROUP_ONLY = 3
    ALBUM_LIST = 4

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
existing_playlists = {}

YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_CLIENT_SECRETS_FILE = "youtubeSecrets.json"
YOUTUBE_MISSING_SECRETS_MSG = "Missing Youtube client secrets"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

RADIOLOUNGE_PLAYLIST_ID = ""
RADIOLOUNGE_ALBUM_PLAYLIST_ID = ""

BOT_ID = os.environ.get('BOT_ID')
AT_BOT = "<@" + BOT_ID + ">"

RADIOBOT_HELP_MSG = """I can do the following: 
    help - Print this message
    ignore - Video provided in message will not be added to a playlist
    skipme - Video provided will not be added to your personal playlist 
    mine - Video provided will not be added to the collaborative playlist
    album - Adds video to the 'albums' playlist only

Commands are not case sensitive"""

def send_slack(text, channel):
    slack_client.api_call("chat.postMessage", channel=channel, text=text, as_user=True)

def slack_username(uid):
    info = slack_client.api_call("users.info",
        token=os.environ.get('SLACK_BOT_TOKEN'),
        user=uid)
    if info['ok']:
        return info['user']['name']
    else:
        return "--Get user error"

def radiobot_do_work(slack_rtm_output):
    output_list = slack_rtm_output
    # print output_list
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output:
                # return text after the @ mention, whitespace removed
                text = output['text']
                user = output['user']
                username = slack_username(user)

                channel = output['channel']

                continue_type = ContinueType.STANDARD
                if AT_BOT in text:
                    continue_type = handle_bot_command(text, username, channel)

                if 'youtube.com/watch?v=' in text:
                    handle_youtube(text, username, channel, continue_type) 

def handle_bot_command(text, user, channel):
    """
    Handles @ mentions, should return a ContinueType indicating which next actions are valid
    during the last stage of handle_youtube (if executed)
    """

    tokens = text.split(" ")
    if tokens[0] != AT_BOT:
        return ContinueType.STANDARD

    if len(tokens) >= 2:
        command = tokens[1].upper()
        params = tokens[2:]

        if command == "IGNORE":
            return ContinueType.NONE
        elif command == "MINE":
            return ContinueType.USER_ONLY
        elif command == "SKIPME":
            return ContinueType.GROUP_ONLY
        elif command == "HELP":
            send_slack(RADIOBOT_HELP_MSG, channel)
            return ContinueType.NONE
        elif command == "ALBUM":
            return ContinueType.ALBUM_LIST
        elif command == "420":
            send_slack(":420: :bong: :bud: :bobmarley: :bud: :bong: :420:", channel)
            return ContinueType.STANDARD
        else:
            send_slack("Sorry, I didn't get that - ignoring your input just in case", channel)
            return ContinueType.NONE


def handle_youtube(text, user, channel, continue_type):
    global existing_playlists
    try:
        vid_id = text.split("v=")[1].replace(">", "")
        if " " in vid_id:
            vid_id = vid_id.split(" ")[0]
        link_part = text.split("v=")[0]
        if "youtube.com/" in link_part:
            user_playlist_id = ""

            if user in existing_playlists.keys():
                user_playlist_id = existing_playlists[user]
            else:
                user_playlist_id = create_youtube_playlist(user)
                existing_playlists[user] = user_playlist_id

            if (continue_type == ContinueType.GROUP_ONLY or continue_type == ContinueType.STANDARD):
                add_video_to_playlist(vid_id, RADIOLOUNGE_PLAYLIST_ID)

            if (continue_type == ContinueType.USER_ONLY or continue_type == ContinueType.STANDARD):
                add_video_to_playlist(vid_id, user_playlist_id)

            if (continue_type == ContinueType.ALBUM_LIST):
                add_video_to_playlist(vid_id, RADIOLOUNGE_ALBUM_PLAYLIST_ID)

    except:
        print "Boo :("

# YOUTUBE
flow = flow_from_clientsecrets(YOUTUBE_CLIENT_SECRETS_FILE,
    message=YOUTUBE_MISSING_SECRETS_MSG,
    scope=YOUTUBE_SCOPE)

storage = Storage("%s-oauth2.json" % sys.argv[0])
credentials = storage.get()

if credentials is None or credentials.invalid:
    flags = argparser.parse_args()
    credentials = run_flow(flow, storage, flags)

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))

def create_youtube_playlist(name):
    playlists_insert_response = youtube.playlists().insert(
      part="snippet,status",
      body=dict(
        snippet=dict(
          title=name,
          description=name + "'s selections"
        ),
        status=dict(
          privacyStatus="public"
        )
      )
    ).execute()
    print playlists_insert_response
    return playlists_insert_response["id"]

def add_video_to_playlist(video_id, playlist_id):
    add_video_response=youtube.playlistItems().insert(
        part="snippet",
        body={
            'snippet': {
              'playlistId': playlist_id, 
              'resourceId': {
                      'kind': 'youtube#video',
                  'videoId': video_id
                }
            }
        }
    ).execute()
    print add_video_response

def playlists_title_to_id():
    """
    Request YouTube for playlists owned by the authenticated User and return a { title: id } dictioanry.
    """
    title_to_id = {}
    playlists_list_request = youtube.playlists().list(
      part="id,snippet",
      mine=True,
    )
    while playlists_list_request:
        playlists_list_response = playlists_list_request.execute()
        items = playlists_list_response.get('items', [])
        title_to_id.update({ item["snippet"]["title"] : item["id"] for item in items })
        playlists_list_request = youtube.playlists().list_next(playlists_list_request, playlists_list_response)

    return title_to_id

if __name__ == "__main__":
    # cache the playlists on start.
    existing_playlists.update(playlists_title_to_id())

    if "albums" in existing_playlists.keys():
        RADIOLOUNGE_ALBUM_PLAYLIST_ID = existing_playlists["albums"]
    else:
        existing_playlists["albums"] = create_youtube_playlist("albums")
        RADIOLOUNGE_ALBUM_PLAYLIST_ID = existing_playlists["albums"]

    READ_WEBSOCKET_DELAY = 1 # seconds
    if slack_client.rtm_connect():
        print("RadioBot connected and running!")
        while True:
            radiobot_do_work(slack_client.rtm_read())
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")


# TODO:
# - Composite user playlist feature
# - Host radiobot somewhere persistent
# - "Ignore video" feature (personal & global)
# - Deal with "playlist full" response
# - Tagged/Named playlists
# - "Acknowledge 4:20" feature
# - Spotify, I _suppose_ (edited)