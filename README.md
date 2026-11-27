# StrikeZone 🎯


A web portal for an airsoft community: news, a catalog of games and gear, game registration and player profiles.
The interface is in Russian.

Test deployment: <https://szw.tailf3363e.ts.net/>

## Features

- **News feed.** Staff and moderators can publish news.
- **Catalog.** Games, modules, guns, accessories and equipment.
- **Game registration.** Players register for a game and set their participation status (yes / no / unknown) and can change it at any time or cancel.
- **Capacity and waiting list.** Only players who answered "yes" take a place. When the game is full, new "yes" registrations join a waiting list and are promoted automatically (in order) when someone cancels or the limit is raised.
- **Game calendar.** `/calendar/` shows games by month; every game can be added to Google/Apple/Outlook calendar as an `.ics` file, and `/calendar.ics` is a subscribable feed of upcoming games.
- **Notifications.** Email and Telegram messages to registered players: registration or waiting-list confirmation, a place freed from the waiting list, a changed date/place, a cancelled game and a reminder the day before. Every player chooses the channels and the language in the profile.
- **Participant list.** Per-game list with a status filter and search by first name, last name, callsign or phone number.
- **Player profiles.** Avatar, callsign and contact details.
- **Roles.** Regular players, a `moderators` group (created by a management command) and staff.
- **Languages.** Russian (default), English and Japanese. The language is chosen in the header and remembered in a cookie; the first visit follows the browser language.
- **Health check.** `GET /health/` returns 200 `{"status": "ok"}` when the app can reach the database and 503 otherwise; Docker Compose uses it as the `web` container healthcheck (nginx starts only after `web` is healthy).
- **Telegram notifications.** A message is sent when a new user registers (optional).

## Tech stack

| Area | Technology |
| --- | --- |
| Backend | Python 3.11 (Docker) / 3.12 (CI), Django 5.2 |
| Database | PostgreSQL (SQLite is supported for quick local development) |
| Frontend | Django templates, Bootstrap 5 |
| Serving | Gunicorn behind Nginx |
| Containers | Docker, Docker Compose |
| Quality | pytest + pytest-django, flake8 |
| CI/CD | GitHub Actions, Docker Hub, Tailscale + SSH deployment, Telegram deploy notifications |

## Quick start with Docker

```bash
git clone https://github.com/IvanP1astun/Strike_Zone_Web.git
cd Strike_Zone_Web

cp .env.example .env          # then edit .env: SECRET_KEY, database password, allowed hosts

docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py setup_permissions
docker compose exec web python manage.py createsuperuser
```

The site is available at <http://localhost> (served by Nginx). The application container and the database
are published only on `127.0.0.1` (ports 8000 and 5432).

## Local development (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp .env.example .env
# In .env set DEBUG=True and DB_ENGINE=sqlite for the simplest setup,
# or point POSTGRES_* / DB_HOST at a local PostgreSQL instance.

python manage.py migrate
python manage.py setup_permissions
python manage.py runserver
```

With `DEBUG=True` Django Debug Toolbar is enabled automatically (it is a dev-only dependency).

## Running tests and linting

```bash
pytest
python -m flake8 main/ strikezoneweb/
python manage.py makemigrations --check --dry-run
```

The tests use the database configured in `.env` (PostgreSQL by default, SQLite with `DB_ENGINE=sqlite`).

## Configuration

All settings come from environment variables (a `.env` file is loaded automatically).

| Variable | Description | Default |
| --- | --- | --- |
| `SECRET_KEY` | Django secret key. **Required** when `DEBUG` is off. | – |
| `DEBUG` | `True` enables debug mode. | `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated list of allowed hosts. | `localhost,127.0.0.1` |
| `DB_ENGINE` | `postgres` or `sqlite`. | `postgres` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL credentials. | `strikezone`, `postgres`, empty |
| `DB_HOST`, `DB_PORT` | PostgreSQL host and port (Compose sets `db:5432`). | `localhost`, `5432` |
| `LOG_DIR` | Directory for `django.log`. | `./logs` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Enable Telegram notifications. | empty (disabled) |

## Notifications (email and Telegram)

Only players with a site account can be notified. Everything is optional: without settings nothing is sent
(email is then only written to the log).

**Email.** Set `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`
and `DEFAULT_FROM_EMAIL` in `.env`.

**Telegram for players.**
1. Create a bot in @BotFather and set `TELEGRAM_BOT_TOKEN` (the same bot may be used for admin messages),
   `TELEGRAM_BOT_USERNAME` (without `@`), `TELEGRAM_WEBHOOK_SECRET` (any long random string) and
   `SITE_URL` (public `https://` address of the site).
2. After deploy register the webhook once: `docker compose exec web python manage.py set_telegram_webhook`
   (`--delete` removes it). The site must be reachable over HTTPS.
3. A player opens the profile, presses "Connect Telegram", follows the one-time link and presses Start.
   `/stop` in the chat disconnects.

**Reminders** (the day before a game) are sent by a command that you run once a day, for example from cron
on the server:

```cron
0 10 * * * cd /path/to/Strike_Zone_Web && docker compose exec -T web python manage.py send_game_reminders
```

Each game is reminded only once, running the command more often is safe.

## Translations (i18n)

Russian is the source language: the strings in the code and templates are the original Russian text and
`locale/<lang>/LC_MESSAGES/django.po` holds the English (`en`) and Japanese (`ja`) translations.
GNU gettext is **not** required, a small standard-library script does the work and the compiled `.mo` files are committed:

```bash
python scripts/translations.py extract   # add new strings to the .po files (empty msgstr)
# ...fill in the new msgstr values in locale/en and locale/ja...
python scripts/translations.py compile   # build django.mo
python scripts/translations.py check     # same check as CI: everything translated, .mo up to date
```

Rules for new text: in templates use `{% translate "..." %}` or `{% blocktranslate %}`, in Python use
`gettext_lazy` (models, forms, class-level code) or `gettext` (inside views). To add a language, add it to
`LANGUAGES` in `strikezoneweb/settings.py` and in `scripts/translations.py`.

## CI/CD

The workflow in `.github/workflows/deploy.yml` runs on every push to `main` and on pull requests:

1. **tests**: installs dependencies, runs flake8, checks that all translations are complete, checks that no model changes are missing migrations and runs pytest
   against a PostgreSQL service container. This job also runs on pull requests.
2. **build-and-deploy** (only on `main`): builds the Docker image and pushes it to Docker Hub, connects to the
   server through Tailscale, pulls the latest code over SSH, rebuilds the containers with Docker Compose and applies migrations.
3. **notify-telegram** (only on `main`): reports the deployment result to a Telegram chat.

Required repository secrets: `DOCKER_USERNAME`, `DOCKER_PASSWORD`, `TAILSCALE_AUTHKEY`, `SSH_PRIVATE_KEY`,
`SERVER_HOST`, `SERVER_USER`, `TELEGRAM_CHAT_ID`, `TELEGRAM_TOKEN`.

## Project structure

```text
.
├── main/                     # Main Django app: models, views, forms, templates, tests
│   ├── management/commands/  # setup_permissions, update_game_status
│   ├── templates/            # HTML templates
│   └── tests/                # pytest tests (auth, forms, models, views, notifications)
├── locale/                   # Translations (en, ja): django.po sources and compiled django.mo
├── scripts/translations.py   # extract / compile / check translations (no gettext needed)
├── strikezoneweb/            # Project settings, URLs, WSGI/ASGI
├── nginx.conf                # Nginx configuration (static, media, proxy to Gunicorn)
├── Dockerfile
├── docker-compose.yml        # web (Gunicorn), db (PostgreSQL), nginx
├── requirements.txt          # Runtime dependencies
└── requirements-dev.txt      # Development and CI dependencies
```

## Management commands

- `python manage.py setup_permissions` creates the `moderators` group with its permissions.
- `python manage.py update_game_status` recalculates the status of all games (can be scheduled with cron).
