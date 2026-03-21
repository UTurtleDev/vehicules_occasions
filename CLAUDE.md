# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Django 6.0.3 web app for managing used vehicles ("véhicules d'occasions"). Language: French. Python 3.12. Package manager: `uv`.

## Commands

```bash
# Install dependencies
uv sync

# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Run tests
python manage.py test

# Create superuser
python manage.py createsuperuser
```

## Architecture

**Custom User model** (`users/models.py`): Extends `AbstractUser` with email as `USERNAME_FIELD` (unique, required). First and last name are required. Username field exists but email is the primary identifier.

**Settings** (`config/settings.py`): Uses `django-environ` to read from `.env`. Dev uses SQLite; production uses MySQL (`utf8mb4`, strict mode). French locale (`fr-fr`), Europe/Paris timezone.

**URLs** (`config/urls.py`): Admin at `/admin/`, users app included at root. Static/media served in DEBUG mode.

**Apps:** Only `users` app exists currently — no vehicle-related models yet.

## Environment

`.env` file required at project root. Key variables:
- `DEBUG` — `True` for dev
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — MySQL for production (ignored when `DEBUG=True`, SQLite used instead)
