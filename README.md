# AniSongLibrary

Rate songs from all your favorite anime!

Built off of anisongdb: https://anisongdb.com/

## Backend
Contains three microservices

### Account
Account performs login/registration of users. Has apis that can get user information

### Library
Library is the store of user song ratings. 

### Catalog
Maintains a record of anime, songs, and people (artists, composers, arrangers). Imports anime and songs from anilist and anisongdb

## Frontend
Built using react
