# TasteMender: A stateless music recommendation API

[![codecov](https://codecov.io/gh/RadValentin/taste-mender/graph/badge.svg?token=JfbmGuIWGl)](https://codecov.io/gh/RadValentin/taste-mender)

> [!NOTE]
> Originally developed as a final project for the BSc Computer Science degree at Goldsmiths, University of London (available [here](https://github.com/RadValentin/CM3070-FP-Music-Recommendation)). This repository continues that work, aiming to transform it into a deployable music discovery web app.

## Installation

1. Install required software: `Python@3.14.6`, `PostgreSQL@18.4`, `Node.js@v24.15.0`

2. Create a config file in `backend/.env` with DB login information, see `.env.example`

3. Create the DB and user

```sql
--Optional commands if DB/USER were created previously
--REVOKE ALL ON SCHEMA public FROM django;
--DROP DATABASE IF EXISTS taste_mender_db;
--DROP USER IF EXISTS django;
CREATE USER django WITH PASSWORD 'password';
CREATE DATABASE taste_mender_db WITH ENCODING 'UTF8' OWNER django;
GRANT ALL PRIVILEGES ON DATABASE taste_mender_db TO django;
GRANT ALL PRIVILEGES ON SCHEMA public TO django;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO django;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO django;

-- Needed for creating a DB when running tests
ALTER USER django CREATEDB;
```

4. Load data into the DB (ingest), see below

5. Install Django dependencies, check that everything is running:
```bash
cd backend/
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

6. Install React dependencies:
```bash
cd frontend/
npm install
npm run dev
```

## Building the database from scratch
Ideally you should have access to a backup of the DB in `pg_dump` format and to the features .NPZ file. If this isn't the case you can replicate the DB from scratch using the instructions below. For development, the **sample** data should be enough.

The first step is to download the dataset dumps from AcousticBrainz, these contain track metadata and the audio features used to determine song similarity, link: https://acousticbrainz.org/download. I recommend using a structure like this:

- `AcousticBrainz`
  - `Sample`
    - `acousticbrainz-highlevel-sample-json-20220623-0.tar.zst`
  - `High-Level`
    - `acousticbrainz-highlevel-json-20220623-0.tar.zst`
    - `acousticbrainz-highlevel-json-20220623-1.tar.zst`
    - `...`

You download the datasets from a browser or by using these commands:

```bash
# Sample DB dump with 100k entries, good for development
mkdir Sample
cd Sample
wget -P . https://data.metabrainz.org/pub/musicbrainz/acousticbrainz/dumps/acousticbrainz-sample-json-20220623/acousticbrainz-highlevel-sample-json-20220623-0.tar.zst

# Full DB dump with 30M entries, good for production
mkdir High-level
cd High-level
wget -r -np -nH --cut-dirs=5 -P . https://data.metabrainz.org/pub/musicbrainz/acousticbrainz/dumps/acousticbrainz-highlevel-json-20220623/

# Check that the downloaded files aren't corrupted
sha256sum -c sha256sums
```

Then update the project's `.env` file with the paths to the dumps, ex:

```bash
AB_HIGHLEVEL_ROOT=D:/Datasets/AcousticBrainz/High-level
AB_SAMPLE_ROOT=D:/Datasets/AcousticBrainz/Sample
```

Finally you can now build the SQLite database and the features file (`features_and_index.npz`):

```bash
# Build the Django DB and the in-memory vector store for audio features
python manage.py build_db # Use all available parts of dataset OR
python manage.py build_db --parts 2 # Use 2 parts of dataset OR
python manage.py build_db --sample # Use the sample dataset with 100k entries
```

## Repo Structure

- `backend/`
  - `music_recommendation/` - the main Django project
  - `recommend_api/` - recommendation API
    - `services/`
      - `recommender.py` - recommendation logic
      - `youtube_sources.py` - gets playable sources for tracks
    - `tests/` - unit tests
    - `api.py` - endpoint views
  - `ingest/` - scripts for building the DB
    - `management/commands/`
      - `build_db.py` - dataset ingest and DB build command
      - `recommend.py` - command for showing recommendations
- `frontend/` - standalone app that consumes the API

## How It Works

### Dataset Ingest

Track data is loaded from the [DB dumps](https://acousticbrainz.org/download) of the AcousticBrainz dataset. The build pipeline does the following:

1. Stream JSON data from `.tar.zst` archives, processing the archives in parallel
1. Extract relevant information from each file (title, audio features, metadata), discarding those that have missing or invalid data
1. Build a hashmap (`track_index`) of duplicate tracks indexed by their MusicBrainz ID (`musicbrainz_recordingid`)
1. Merge duplicates into a single entry by selecting the most common value for each field (title, audio features, metadata)
1. Build the DB models:
  1. `Track` from `track_index`
  1. `Artist`, `Album` and M2M pairings (`AlbumArtist`, `TrackArtist`) from the track metadata
1. Extract audio features to a separate file (`features_and_index.npz`), this will be loaded into memory by the Django app to allow for fast searching

Because many popular tracks are duplicated in the dataset, the final number of tracks that the app will be working with is considerably lower than what was ingested.

$$finalSize = datasetSize - duplicateCount - tracksMissingData - tracksMissingArtist$$

For the sample dataset (100k tracks), 85732 unique entries will be loaded:
$$85732 = 100000 - 11182 - 4 - 3082$$

## Deploy with Docker
This project uses [Docker](https://docs.docker.com/) to build and manage a reproducible environment that runs the same both locally and in production. This removes the need of having some special setup that exists solely on the server and isn't included in the repo.

### Setting up the server
```sh
ssh root@your-server-ip
cd ~

# install Nginx
sudo apt update
sudo apt install -y nginx

# enable and start
sudo systemctl enable nginx
sudo systemctl start nginx

# open ports so nginx can serve front-end
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo systemctl reload ufw
sudo ufw status

# install Certbot and generate SSL certificates
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d taste-mender.com -d www.taste-mender.com
# set up certificate auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# create Nginx config
sudo touch /etc/nginx/sites-available/taste-mender
sudo nano /etc/nginx/sites-available/taste-mender
```

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name taste-mender.com www.taste-mender.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS config
server {
    listen 443 ssl http2;
    server_name taste-mender.com www.taste-mender.com;

    # SSL certificates from Certbot
    ssl_certificate /etc/letsencrypt/live/taste-mender.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/taste-mender.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        proxy_pass http://localhost:8000/static/;
        # Cache static files
        expires 30d;
    }
}
```

```sh
# Enable the config
sudo ln -s /etc/nginx/sites-available/taste-mender /etc/nginx/sites-enabled/
sudo nginx -t  # check config syntax
sudo systemctl reload nginx

# Setup project
git clone https://github.com/RadValentin/taste-mender.git taste-mender
cd taste-mender

# IMPORTANT: copy `features_and_index.npz` that was built locally during ingest to backend/

# create .env file in backend/
touch backend/.env
# add production values, required values: DJANGO_ALLOWED_HOSTS, DJANGO_SECRET_KEY, DATABASE_URL,
# YOUTUBE_API_KEY (see .env.example for full list)
nano backend/.env
```

### Deploy and run
If the server is already set up (see below), this is all that's required to start/update the app:

```sh
ssh root@taste-mender-droplet-ip
cd ~/taste-mender/backend

git pull origin main
docker-compose down
docker-compose up -d --build

# run migrations
docker-compose exec django python manage.py migrate
```

```sh
# Restore DB from local file
docker exec -i taste-mender-postgres pg_restore -U django -d taste_mender_db --clean --if-exists --no-owner --no-privileges < ~/backup.sql

# Restart DB container to clear any RAM overhead left behind by restore
docker compose restart postgres
```

```sh
# check logs
docker logs -f taste-mender-web

docker stop taste-mender-web
```

> [!TIP]
> If running Docker on Windows the `Vmmem` process might persist even after the Docker Engine is shut down, you can stop it with this command:
>```sh
>wsl --shutdown
>```
