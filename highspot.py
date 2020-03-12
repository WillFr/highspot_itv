#!/usr/bin/env python3

import json
import sys
import os

class InvalidPayloadException(Exception):
    pass


def _is_playlist(user_input, valid_song_ids, valid_user_ids):
    """Verify the schema of a playlist user_input. A playlist must contain at least one song
    and have a valid song ids and user ids.

    Arguments:
        user_input {dict} -- the potential playlist.
        valid_song_ids {set} -- a set of valid song ids.
        valid_user_ids {set} -- a set of valid user ids.
    
    Returns:
        [type] -- [description]
    """
    return isinstance(user_input, dict) \
            and user_input.keys() == {"id", "user_id", "song_ids"} \
            and isinstance(user_input["song_ids"], list) \
            and any(user_input["song_ids"]) \
            and all(song_id in valid_song_ids for song_id in user_input["song_ids"]) \
            and user_input["user_id"] in valid_user_ids

def _attempt_to_load_json(file_path):
    """Attempts to load a json file and raises a descriptive error message if it fails.

    Arguments:
        file_path {str} -- the file path to be loaded.
    
    Raises:
        ValueError: in case the json is not valid, this will be raised.
    
    Returns:
        dict -- a dictionary equivalent to the json content.
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except ValueError as ex:
        # Let's augment the initial exception with a descriptive first line.
        raise ValueError(f"The file {file_path} is not proper json.\n{ex}")

def _validate_mixtape_schema(mixtape_json):
    """Validates the schma of a mixtape and returns and index id->object for users, playlist and songs,
    as well as the highest id in playlists.

    Arguments:
        mixtape_json {dict} -- the dict representing the mixtape to be validated.
    
    Returns:
        [tuple] -- song_index, user_index, playlist_index
    """
    assert isinstance(mixtape_json, dict)
    assert "playlists" in mixtape_json and isinstance(mixtape_json["playlists"], list)
    assert "songs" in mixtape_json and isinstance(mixtape_json["songs"], list)
    assert "users" in mixtape_json and isinstance(mixtape_json["users"], list)

    assert all(song.keys() == {"id", "artist", "title"} for song in mixtape_json["songs"])
    song_index = { song["id"]:song for song in mixtape_json["songs"]}
    assert len(song_index) == len(mixtape_json["songs"]) # let's make sure every id is unique

    assert all(user.keys() == {"id", "name"} for user in mixtape_json["users"])
    user_index = { user["id"]:user for user in mixtape_json["users"]}
    assert len(user_index) == len(mixtape_json["users"]) # let's make sure every id is unique

    assert all(_is_playlist(playlist, song_index, user_index) for playlist in mixtape_json["playlists"])
    playlist_index = { playlist["id"]:playlist for playlist in mixtape_json["playlists"]}
    assert len(playlist_index) == len(mixtape_json["playlists"]) # let's make sure every id is unique

    return song_index, user_index, playlist_index

def _validate_change_schema(change_json):
    """validates the schema of a change file.

    Arguments:
        change_json {dict} -- the dict representing the change.json
    """
    assert "changes" in change_json and isinstance(change_json["changes"], list)
    assert all(change.keys() == {"type", "payload"} for change in change_json["changes"])

def _apply_changes(mixtape_json, change_json, song_index, user_index, playlist_index):
    """Apply a change set to a mixtape_json

    Arguments:
        mixtape_json {dict} -- a dict representing the mixtape.
        change_json {dict} -- a dict representing the changes to be applied on the mixtape
        song_index {[type]} -- a dict song_id -> song_dict
        user_index {[type]} -- a dict user_id -> user_dict
        playlist_index {[type]} -- a dict playlist_id -> playlist_dict

    Raises:
        InvalidPayloadException: If a part of the payload is invalid, this will be raised.
    """
    for operation in change_json["changes"]:
        if operation["type"] == "create_playlist":
            operation["payload"]["id"] = None
            if not _is_playlist(operation["payload"], song_index, user_index):
                raise InvalidPayloadException(f"Invalid payload, it is not a proper playlist: " + str(operation["payload"]))
            max_playlist_id = max((int(p) for p in playlist_index.keys())) if any(playlist_index) else 0
            max_playlist_id += 1
            operation["payload"]["id"] = str(max_playlist_id)
            mixtape_json["playlists"].append(operation["payload"])
        elif operation["type"] == "delete_playlist":
            if operation["payload"].keys() != {"playlist_id"} or operation["payload"]["playlist_id"] not in playlist_index:
                raise InvalidPayloadException(f"Invalid payload, it should contain a `playlist id` and the playlist id should exist inthe mixtape: " + str(operation["payload"]))
            mixtape_json["playlists"].remove(playlist_index[operation["payload"]["playlist_id"]])
            playlist_index.pop(operation["payload"]["playlist_id"])
        elif operation["type"] == "add_song_to_playlist":
            if operation["payload"].keys() != {"playlist_id", "song_id"} or operation["payload"]["playlist_id"] not in playlist_index or operation["payload"]["song_id"] not in song_index:
                raise InvalidPayloadException(f"Invalid payload : " + str(operation["payload"]))
            playlist = playlist_index[operation["payload"]["playlist_id"]]
            if operation["payload"]["song_id"] not in playlist["song_ids"]:
                playlist["song_ids"].append(operation["payload"]["song_id"])
        else:
            raise InvalidPayloadException(f'Operation {operation["type"]} is not supported.')

def main():
    if len(sys.argv) != 3:
        print("Incorrect usage - please use `highspot.py [mixtape_file_path] [change_file_path]`")
        exit(1)

    mixtape_file_path = sys.argv[1]
    change_file_path = sys.argv[2]

    for path in [mixtape_file_path, change_file_path]:
        if not os.path.exists(path):
            print(f"No such file : {path}")

    try:
        mixtape_json = _attempt_to_load_json(mixtape_file_path)
        change_json = _attempt_to_load_json(change_file_path)
    except ValueError as ex:
        print(ex)
        exit(1)

    try:
        song_index, user_index, playlist_index = _validate_mixtape_schema(mixtape_json)
        _validate_change_schema(change_json)
    except AssertionError as ex:
        print(ex)
        exit(1)

    _apply_changes(mixtape_json, change_json, song_index, user_index, playlist_index)
    with open("./output.json", "w") as f:
        json.dump(mixtape_json, f, indent=2)


if __name__ == '__main__':
    main()