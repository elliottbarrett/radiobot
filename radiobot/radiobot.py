import os
import time
import sys
import httplib2
import shelve

from slackclient import SlackClient
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser
from oauth2client.tools import run_flow
from apiclient.discovery import build

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
existing_playlists = shelve.open('playlists.shelf') 

YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"
YOUTUBE_CLIENT_SECRETS_FILE = "youtubeSecrets.json"
YOUTUBE_MISSING_SECRETS_MSG = "Missing Youtube client secrets"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

RADIOLOUNGE_PLAYLIST_ID = existing_playlists["radiolounge"]

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

                if 'youtube.com/watch?v=' in text:
                    handle_youtube(text, username, channel) 

def handle_youtube(text, user, channel):
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

            add_video_to_playlist(vid_id, RADIOLOUNGE_PLAYLIST_ID)
            add_video_to_playlist(vid_id, user_playlist_id)

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
    print "..creating youutbe playlist"
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

if __name__ == "__main__":
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