# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Django 6.0.3 web app for managing used vehicles ("véhicules d'occasions"). Multi-garage SaaS: a user belongs to one or more garages, with a per-garage role. Language: French (code, comments, UI). Python 3.12. Package manager: `uv`.

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

# Load demo data (5 garages, 20 users, 100 vehicles, 221 repair lines)
python manage.py loaddata fixtures/donnees_demo.json
```

Demo account credentials are listed in `notes.txt` (gitignored scratch file).

## Apps

| App | Role |
|-----|------|
| `users` | Custom user model, landing page, htmx login modal |
| `garages` | Garage, membership/roles, active-garage session switching, access mixins, accounting settings |
| `vehicules` | Vehicle, Marque, Modele, stock list, detail/create/edit/sell, dashboard, exports |
| `remise_en_etat` | Reconditioning costs attached to a vehicle |
| `abonnements` | Subscription plans (free/pro/entreprise), not yet enforced |

## Architecture

**Custom User model** (`users/models.py`): Extends `AbstractUser` with email as `USERNAME_FIELD` (unique, required). First and last name are required. Username field exists but email is the primary identifier.

**Multi-garage access control** — this is the core invariant, do not bypass it:

- `Garage.membres` is a M2M through `GarageMembre`, which carries a `role`: `gestionnaire` (read + write) or `lecture` (read only).
- The **active garage** lives in the session (`garages.utils.GARAGE_SESSION_KEY`). `get_garage_actif()` falls back to the user's first garage if the session is empty or stale.
- `garages.utils.get_garage_ecriture()` is the **single source of truth for write permission**. Both `GarageEcritureMixin` (which authorizes views) and `garages.context_processors.garage_actif` (which decides whether action buttons render) call it, so UI and backend cannot diverge.
- Views inherit `GarageLectureMixin` (queryset = vehicles across **all** the user's garages) or `GarageEcritureMixin` (queryset = active garage only, and only if gestionnaire; raises `PermissionDenied` in `dispatch()` otherwise).
- `GarageEcritureMixin` is a thin subclass of `GarageEcritureRequisMixin`, which carries only the authorization (`dispatch()` + `get_garage_ecriture()`) and says nothing about the queryset. Views in write mode that operate on something other than `Vehicule` (accounting settings) inherit the bare guard.
- Never query `Vehicule.objects` directly in a view. Always start from a mixin's `get_queryset()`, or garage isolation leaks.

**Vehicle costs exist in two parallel forms** (`vehicules/models.py`):

- **Python properties** (`prix_achat`, `frais_reel`, `cout_revient`, `marge_fiscale`, `marge_interne`, `jours_detention`) — readable, one instance at a time. Use on detail pages.
- **SQL annotations** via `Vehicule.objects.avec_couts()` — same values, computed by the database, aggregatable. Use whenever summing, sorting, or filtering on a cost (dashboard, sort by margin, "sold at a loss").

Rules when touching this:
- Annotations carry a `_calc` suffix (`prix_achat_calc`, `marge_interne_calc`…). A property is a data descriptor, so annotating `prix_achat` would crash when Django writes the value onto the instance.
- Reconditioning costs use a **`Subquery`, never `Sum()` on the relation**. A `Sum()` joins, duplicating the vehicle row once per repair line and corrupting every other aggregate in the same query. `vehicules/tests.py` covers this.
- `marge_*_calc` is NULL until the vehicle is sold, so `Sum()`/`Avg()` naturally count sales only.
- `prix_achat` includes auction fee and transport, by design (accounting decision, settled).

**Dashboard** (`vehicules.views.TableauDeBordView`, `/vehicules/tableau-de-bord/`): two independent readings of the same stock. "Stock" is a snapshot at today's date and **ignores the period filter**; "Activité" covers vehicles sold within the period, bounded on `date_vente`. Marque/énergie/transmission filters apply to both. Filters are plain GET params, built with the `vo_filters` template tags.

**Exports** (`/vehicules/exports/`, reachable from the user-name menu in the navbar): one shared period selector, two files.

- Period helpers (`PERIODES`, `bornes_periode`, `date_ou_none`, `moyenne_entiere`, `pourcentage`) live in `vehicules/utils.py`, shared by the dashboard and the exports. The exports declare their own shorter list, `PERIODES_EXPORT`, and add the `mois_dernier` code.
- `vehicules/exports.py` holds the pure logic (no HTTP): `synthese()`, `lignes_ecritures()`, `ecrire_csv()`. `vehicules/pdf.py` is the only module that imports ReportLab.
- Scope is the **active garage only**, not all the user's garages like the dashboard — a file leaving for an accountant must not mix two garages. Reading is enough (`lecture` role can export); only the *settings* page requires `gestionnaire`.
- The synthesis (PDF) shows **`marge_interne`** (net of reconditioning costs); the accounting entries (CSV) use **`marge_fiscale`** (the taxable base, costs excluded). The same sale legitimately shows two different margins.

**Accounting entries follow the second-hand-vehicle VAT-on-margin scheme**, which is *not* obvious and must not be "simplified":

- The entry never carries the sale price, only the **margin**, split into three lines: margin incl. VAT debited to "Ventes totale", margin excl. VAT credited to "Ventes au prix d'achat HT", VAT credited to "TVA collectée".
- **VAT is derived by subtraction** (`TTC - HT`), never computed on its own, so that HT + VAT always adds back exactly to TTC whatever the rate.
- Accounts and rate are per-garage (`garages.models.ParametrageComptable`, defaults `707000000` / `707010000` / `445710090` and 20 %). `ParametrageComptable.pour(garage)` returns an **unsaved** instance when none exists — an export is a GET and must not write to the database.
- Sales with a **zero or negative fiscal margin are excluded** from the CSV (no margin, no VAT to collect) and listed on the export page so nothing vanishes silently.
- CSV format: `;` separator, UTF-8 **BOM**, CRLF, `dd/mm/yyyy` dates, comma decimals with no thousands separator and no `€`. Never pipe those amounts through the `euros` filter: its U+202F narrow space and `€` break Excel's number parsing.
- Line 1 is the **header row** (`ENTETES_CSV` in `vehicules/exports.py`), taken verbatim from the accountant's model. The accounting software matches columns on those labels at import — do not rename them without checking on that side. An empty period still yields the header alone, which imports cleanly where a truly empty file often fails.
- Quantize every amount to 2 decimals — SQLite's float noise on annotated values is invisible on screen but lands verbatim in a CSV.
- ReportLab's built-in fonts use `WinAnsiEncoding`, which lacks U+202F: `vehicules.pdf.montant()` swaps it for U+00A0, otherwise amounts print as `12?345?€`.

**Filtering convention**: query params, no forms. `vehicules/templatetags/vo_filters.py` provides `toggle_qs` (multi-select facets), `set_qs` (single-select), `page_qs`, `is_active`, and the `euros` display filter. Facet counts are computed excluding the facet's own filter, so an option never drops to zero just because a sibling is checked. Sanitize numeric params (`v.isdigit()`) before `__in` lookups.

**Settings** (`config/settings.py`): Uses `django-environ` to read from `.env`. Dev uses SQLite; production uses MySQL (`utf8mb4`, strict mode). French locale (`fr-fr`), Europe/Paris timezone. `LoginRequiredMiddleware` is active — public views must be decorated `@login_not_required`.

**URLs** (`config/urls.py`): `/admin/`, `users` at root, `/vehicules/`, `/garages/`, `/remise-en-etat/`. Static/media served in DEBUG mode.

**Frontend**: server-rendered Django templates, dark theme with gold accent. Design tokens (CSS custom properties) live in `static/css/style.css`; per-page stylesheets in `static/<app>/css/<page>.css`, each scoped under a page-level class (`.vo-list`, `.vo-dash`) to avoid collisions. Pages combine classes to reuse a shell rather than duplicate it: the dashboard and the exports page carry `.vo-list .vo-dash` (sidebar + KPI cards), the accounting settings page carries `.vo-ajout .vo-param` (form shell). Changing `.vo-list .sidebar` or `.vo-ajout input` therefore moves several pages at once. htmx (CDN, in `base.html`) handles the login modal and garage switching. JavaScript is used sparingly and only for simple interactions.

The user-name dropdown in the navbar (`<details class="navbar-profile">`) is the entry point for account-level pages — Exports, Paramètres comptables — above the logout form.

## Environment

`.env` file required at project root. Key variables:
- `DEBUG` — `True` for dev
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — MySQL for production (ignored when `DEBUG=True`, SQLite used instead)

## Notes

- SQLite has no real `DECIMAL` type, so annotated money values show float noise (`383.700000000001`) in dev. Absent on MySQL, and invisible once formatted through `|euros`.
- No vehicle deletion flow exists yet.
- `abonnements` models exist but no plan limit is enforced anywhere.
- `reportlab` is a pure-Python dependency: nothing to install on the server beyond `uv sync`.
- A few source files are stored in Unicode **NFD** (macOS decomposed accents: `garages/models.py`, `vehicules/models.py`, `vehicules/admin.py`). Search-and-replace on an accented string will silently fail to match there — anchor on ASCII-only text, or normalize the file to NFC first.
