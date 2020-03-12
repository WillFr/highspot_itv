import unittest
import os
import tempfile
import json
import sys

import highspot

class TestStringMethods(unittest.TestCase):
    def test_attempt_to_load_json_invalid(self):
        file = tempfile.NamedTemporaryFile(mode='w+t')

        caught = None
        try:
            file.writelines("abc")
            file.flush()
            highspot._attempt_to_load_json(file.name)
        except ValueError as ex:
            caught = ex
        finally:
            file.close()
        self.assertTrue(caught is not None)

    def test_attempt_to_load_json_valid(self):
        file = tempfile.NamedTemporaryFile(mode='w+t')
        try:
            file.writelines("{ \"a\": \"1\"}")
            file.flush()
            value = highspot._attempt_to_load_json(file.name)
            self.assertEqual(value, { "a" : "1"})
        finally:
            file.close()

    def test_is_playlist_valid(self):
        user_input = {
            "id": "1",
            "user_id": "2",
            "song_ids": ["8", "32"]
        }
        self.assertTrue(highspot._is_playlist(user_input, { "8", "32", "23" }, { "2", "3" }))

    def test_is_playlist_invalid(self):
        valid_song_ids = { "8", "32", "23" }
        valid_user_ids = { "2", "3" }
        self.assertFalse(highspot._is_playlist({}, valid_song_ids, valid_user_ids))
        self.assertFalse(highspot._is_playlist({ "id": "1", "user_id": "2", "song_ids": "8" }, valid_song_ids, valid_user_ids))
        self.assertFalse(highspot._is_playlist({ "id": "1", "user_id": "2", "song_ids": [] }, valid_song_ids, valid_user_ids))
        self.assertFalse(highspot._is_playlist({ "id": "1", "user_id": "2", "song_ids": ["9"] }, valid_song_ids, valid_user_ids))
        self.assertFalse(highspot._is_playlist({ "id": "1", "user_id": "4", "song_ids": ["8"] }, valid_song_ids, valid_user_ids))

    def test_validate_mixtape_schema_valid(self):
        user_input = {
            "users": [
                { "id": "1", "name": "Albin Jaye" },
                { "id": "2", "name": "Dipika Crescentia" },
            ],
            "playlists": [
                { "id": "1", "user_id": "1", "song_ids": ["1", "2"] },
                { "id": "2", "user_id": "2", "song_ids": ["1", "2"] },
            ],
            "songs": [
                { "id": "1", "artist": "Camila Cabello", "title": "Never Be the Same" },
                { "id": "2", "artist": "Zedd", "title": "The Middle" }
            ]
        }

        song_index, user_index, playlist_index = highspot._validate_mixtape_schema(user_input)
        self.assertEqual(
            song_index,
            {
                "1": { "id": "1", "artist": "Camila Cabello", "title": "Never Be the Same" },
                "2": { "id": "2", "artist": "Zedd", "title": "The Middle" }
            })

        self.assertEqual(
            user_index,
            {
                "1": { "id": "1", "name": "Albin Jaye" },
                "2": { "id": "2", "name": "Dipika Crescentia" }
            })

        self.assertEqual(
            playlist_index,
            {
                "1": { "id": "1", "user_id": "1", "song_ids": ["1", "2"] },
                "2": { "id": "2", "user_id": "2", "song_ids": ["1", "2"] }
            })

    def test_validate_mixtape_schema_invalid(self):
        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema("abc")

        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema({ "users": "abc", "playlists": [], "songs": []})

        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema({ "users": [], "playlists": "abc", "songs": []})

        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema({ "users": [], "playlists": [], "songs": "abc"})

        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema({ "users": [], "playlists": [], "songs": [{"a":1}]})

        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema({ "users": [], "playlists": [], "songs": [{"id":"1", "artist":"A", "title":"a"}, {"id":"1", "artist":"B", "title":"b"}]})

        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema({ "users": [{"a":1}], "playlists": [], "songs": []})

        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema({ "users": [{"id":"1", "name":"A"}, {"id":"1", "name":"B"}], "playlists": [], "songs": []})

        with self.assertRaises(AssertionError):
            highspot._validate_mixtape_schema({ "users": [{"id":"1", "name":"A"}], "playlists": [{"id":"1", "user_id":"1", "song_ids":[]}, {"id":"1", "user_id":"1", "song_ids":[]}], "songs": []})

    def test_validate_change_schema_valid(self):
        user_input = {
            "changes":[
                { "type": "abc", "payload": { "a": 1, "b": "2" } },
                { "type": "def", "payload": { "b": 2, "c": "3" } },
            ]
        }
        highspot._validate_change_schema(user_input)

    def test_validate_change_schema_invalid(self):
        user_input = {
            "changes":[
                { "payload": { "a": 1, "b": "2" } },
                { "type": "def" },
            ]
        }
        with self.assertRaises(AssertionError):
            highspot._validate_change_schema(user_input)

    def test_apply_changes(self):
        mixtape_json = {
            "users": [
                { "id": "1", "name": "Albin Jaye" },
                { "id": "2", "name": "Dipika Crescentia" },
            ],
            "playlists": [
                { "id": "1", "user_id": "1", "song_ids": ["1"] },
                { "id": "2", "user_id": "2", "song_ids": ["1", "2"] },
            ],
            "songs": [
                { "id": "1", "artist": "Camila Cabello", "title": "Never Be the Same" },
                { "id": "2", "artist": "Zedd", "title": "The Middle" }
            ]
        }

        change_json = {
            "changes":[
                { "type": "create_playlist", "payload": { "user_id": "2", "song_ids": ["1"] }},
                { "type": "delete_playlist", "payload": { "playlist_id": "2" } },
                { "type": "add_song_to_playlist", "payload": { "playlist_id": "1", "song_id": "2"} },
                { "type": "add_song_to_playlist", "payload": { "playlist_id": "1", "song_id": "2"} }
            ]
        }
        song_index, user_index, playlist_index = highspot._validate_mixtape_schema(mixtape_json)
        highspot._apply_changes(mixtape_json, change_json, song_index, user_index, playlist_index)

        assert mixtape_json == {
            "users": [
                { "id": "1", "name": "Albin Jaye" },
                { "id": "2", "name": "Dipika Crescentia" },
            ],
            "playlists": [
                { "id": "1", "user_id": "1", "song_ids": ["1", "2"] },
                { "id": "3", "user_id": "2", "song_ids": ["1"] }
            ],
            "songs": [
                { "id": "1", "artist": "Camila Cabello", "title": "Never Be the Same" },
                { "id": "2", "artist": "Zedd", "title": "The Middle" }
            ]
        }
        assert 2 not in playlist_index

    def test_apply_changes_invalid(self):
        mixtape_json = {
            "users": [
                { "id": "1", "name": "Albin Jaye" },
                { "id": "2", "name": "Dipika Crescentia" },
            ],
            "playlists": [
                { "id": "1", "user_id": "1", "song_ids": ["1"] },
                { "id": "2", "user_id": "2", "song_ids": ["1", "2"] },
            ],
            "songs": [
                { "id": "1", "artist": "Camila Cabello", "title": "Never Be the Same" },
                { "id": "2", "artist": "Zedd", "title": "The Middle" }
            ]
        }
        song_index, user_index, playlist_index = highspot._validate_mixtape_schema(mixtape_json)

        change_json = {
            "changes":[
                { "type": "unsupported", "payload": { "user_id": "2", "song_ids": ["1"] }}
            ]
        }
        with self.assertRaises(highspot.InvalidPayloadException):
            highspot._apply_changes(mixtape_json, change_json, song_index, user_index, playlist_index)

        change_json = {
            "changes":[
                { "type": "create_playlist", "payload": { "user_id": "10", "song_ids": ["1"] }},
            ]
        }
        with self.assertRaises(highspot.InvalidPayloadException):
            highspot._apply_changes(mixtape_json, change_json, song_index, user_index, playlist_index)

        change_json = {
            "changes":[
                { "type": "delete_playlist", "payload": { "playlist_id": "20" } },
            ]
        }
        with self.assertRaises(highspot.InvalidPayloadException):
            highspot._apply_changes(mixtape_json, change_json, song_index, user_index, playlist_index)

        change_json = {
            "changes":[
                { "type": "add_song_to_playlist", "payload": { "playlist_id": "10", "song_id": "2"} },
            ]
        }
        with self.assertRaises(highspot.InvalidPayloadException):
            highspot._apply_changes(mixtape_json, change_json, song_index, user_index, playlist_index)

    def test_end_to_end(self):
        mixtape_file = tempfile.NamedTemporaryFile(mode='w+t')
        change_file = tempfile.NamedTemporaryFile(mode='w+t')

        mixtape_json = {
            "users": [
                { "id": "1", "name": "Albin Jaye" },
                { "id": "2", "name": "Dipika Crescentia" },
            ],
            "playlists": [
                { "id": "1", "user_id": "1", "song_ids": ["1"] },
                { "id": "2", "user_id": "2", "song_ids": ["1", "2"] },
            ],
            "songs": [
                { "id": "1", "artist": "Camila Cabello", "title": "Never Be the Same" },
                { "id": "2", "artist": "Zedd", "title": "The Middle" }
            ]
        }

        change_json = {
            "changes":[
                { "type": "create_playlist", "payload": { "user_id": "2", "song_ids": ["1"] }},
                { "type": "delete_playlist", "payload": { "playlist_id": "2" } },
                { "type": "add_song_to_playlist", "payload": { "playlist_id": "1", "song_id": "2"} },
                { "type": "add_song_to_playlist", "payload": { "playlist_id": "1", "song_id": "2"} },
            ]
        }

        try:
            json.dump(mixtape_json, mixtape_file)
            mixtape_file.flush()
            json.dump(change_json, change_file)
            change_file.flush()
            sys.argv = ["./highspot.py", mixtape_file.name, change_file.name]
            highspot.main()
            with open("output.json") as f:
                output = json.load(f)

            assert output == {
                                "users": [
                                    { "id": "1", "name": "Albin Jaye" },
                                    { "id": "2", "name": "Dipika Crescentia" },
                                ],
                                "playlists": [
                                    { "id": "1", "user_id": "1", "song_ids": ["1", "2"] },
                                    { "id": "3", "user_id": "2", "song_ids": ["1"] }
                                ],
                                "songs": [
                                    { "id": "1", "artist": "Camila Cabello", "title": "Never Be the Same" },
                                    { "id": "2", "artist": "Zedd", "title": "The Middle" }
                                ]
                            }

        finally:
            mixtape_file.close()
            change_file.close()
            os.remove("output.json")

if __name__ == '__main__':
    unittest.main()