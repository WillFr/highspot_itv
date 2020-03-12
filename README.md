# Usage
Use the following command line to run the program.
`python3 highspot.py [mixtape_file_path] [change_file_path]`

alternatively you can `chmod +x highspot.py` and then run `./highspot.py [mixtape_file_path] [change_file_path]`

To quickly run a test you can use the following :
```
curl https://gist.githubusercontent.com/jmodjeska/0679cf6cd670f76f07f1874ce00daaeb/raw/a4ac53fa86452ac26d706df2e851fb7d02697b4b/mixtape-data.json > mixtape.json
(
    echo "{ \"changes\":["
    echo "      { \"type\": \"create_playlist\", \"payload\": { \"user_id\": \"2\", \"song_ids\": [\"1\"] }},"
    echo "      { \"type\": \"delete_playlist\", \"payload\": { \"playlist_id\": \"2\" } },"
    echo "      { \"type\": \"add_song_to_playlist\", \"payload\": { \"playlist_id\": \"1\", \"song_id\": \"2\"} },"
    echo "      { \"type\": \"add_song_to_playlist\", \"payload\": { \"playlist_id\": \"1\", \"song_id\": \"2\"} }"
    echo "  ]"
    echo "}"
) > change.json
python3 highspot.py mixtape.json change.json
rm mixtape.json
rm change.json
```

# Tests
You can run  unit tests with `python3 -m unittest test_highspot`. This will achieve close to full code coverage.

# Change file format
the change file format follows the following schema :
```
{
    "changes": [
        {
            "type" : "<change_type>",
            "payload" : <associated payload>
        },
        ...
    ]
}
```

The change types can be:
`create_playlist` with the following payload : `{ "user_id": "<user_id associated with the playlist>", "song_ids": [<song_id>, ...] }`. `id` can be added tothe payload but will not be used.

`delete_playlist` with the following payload: `{ "playlist_id": <id fo the playlist to be deleted>}`

`add_song_to_playlist` with the following payload : `{ "playlist_id": <id fo the playlist to be modified>, "song_id": <id of the song to be added> }`

eg:
```
{
    "changes":[
        { "type": "create_playlist", "payload": { "user_id": "2", "song_ids": ["1"] }},
        { "type": "delete_playlist", "payload": { "playlist_id": "2" } },
        { "type": "add_song_to_playlist", "payload": { "playlist_id": "1", "song_id": "2"} },
        { "type": "add_song_to_playlist", "payload": { "playlist_id": "1", "song_id": "2"} }
    ]
}
```

# Design considerations
## Of the use of bare python
For the sake of the interview exercise, I did not want to rely on external libraries which would have been harder to package (I would have had to build an egg etc). However, we could have used external libraries for :
- argument parsing (docopt is a good candidate)
- json schema validation (jsonschema comes to mind)

## Of idempotency
Here we have two cases :
1- delete playlist : this will error out if the playlist does not exist, threfore bbreaking idempotency. The reason is I do believe it makes more sense to notify the user that the delete_playlist operation failed if the playlist id passed does not exist
2- add song to playlist: here I think it makes sense to have idempotency : adding a song that already exist in a playlist should not error out as the intent of the user is clear.

## Shortcomings
1- there is no way to select the destination file, it is hardcoded to `output.json`. This is how I understood the exercise but I could be wrong. It is easily modifiable

2- a single invalid change cancels every other change : I think this makes sense at a small scale, especially considering that cascading failures could happen if we just discarded bad changes and applied good ones. However, at scale, this is debatable.


# Scaling: How to handle very large mixtape files and/or very large change files ?

## Medium scale
For a medium scale, we could optimize the code to still run on one machine:
- we could have a custom json loader to build the user_id set and the sond_id set more efficiently, without loading the entire json. We could build an index of playlist: playlist_is -> location to seek in the file and load the playlist on demand
This would save on memory as we would store only user_ids, song_ids, and the pair (playlist_id, position) instead of full blown objects.
- we could have a custom json loader to "stream" the changes : we would load the file with in a buffer and deserialize each change one at a time before moving the buffer to the next change. This would make the size of the file irrelevant as only one (or a few changes) would have to be loaded in memory

This approach works well for as long as we have enough memory in the system to store the playlist index, song id set and user id set as well as a few changes

## Very large scale
Beyond that, we will be IO bound on the disk, and need to store the indexes elsewhere. An appropriately sized redis instance (big enough that we don't drop any key/values) would be be pretty fast. Basically, we would take the same approach as with the medium scale (custom parsers) but we would store the playlist index, song id set and user id set in the redis cache. We would also use them from the redis cache.

## Additional optimization
It would be worth measuring the performance gain obtained by preprocessing the change list : we could create a new operationto batch add multiple song to a playlist for instance. Similarly we can drop every operation followed by a delete of that playlist.