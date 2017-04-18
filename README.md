radiobot
========

A basic Slack integration for curating YouTube playlists.

Getting Started
===============

Create a python virtual environment.

```bash
$ pip install virtualenv
$ virtualenv radiobot
$ source radiobot/bin/activate
```

Use pip to install the required dependencies.

```bash
$ pip install -r requirements.txt
```

Create a [client secrets file](https://developers.google.com/api-client-library/python/guide/aaa_client_secrets) for YouTube:  `./youtubeSecrets.json`

Set environment variables for Slack authentication.

```bash
$ export BOT_ID=replace_with_id
$ export SLACK_BOT_TOKEN=replace_with_token
```

Run the program. The program will prompt for Google authentication on the first run.

```bash
$ python radiobot/radioboyt.py
```

Finally, if successful the program will print the message:

```bash
RadioBot connected and running!
```

Supported Python Versions
=========================

* Python 2.7
