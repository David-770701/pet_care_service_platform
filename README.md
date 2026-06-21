# Pet Care Service Platform

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![Database](https://img.shields.io/badge/Database-MySQL%208.0-orange)

## Project Overview

Pet Care Service Platform is a Django + MySQL web application for a pet service marketplace. It supports three roles: pet owners, merchants, and platform administrators.

Core workflows include merchant registration and approval, service publishing and review, pet profile management, service booking, order status management, reviews, merchant rating recalculation, and vaccine reminders.

## Tech Stack

| Part | Technology |
| --- | --- |
| Backend | Python 3.12, Django 4.2 |
| Database | MySQL 8.0, PyMySQL |
| Frontend | Django Templates, Bootstrap 5 |

## Project Structure

```text
project/
|-- manage.py                  # Django command entry
|-- requirements.txt           # Python dependencies
|-- README.md                  # Project setup guide
|-- config/                    # Django project configuration
|   |-- settings.py
|   |-- urls.py
|   |-- asgi.py
|   |-- wsgi.py
|-- pet_services/              # Main Django application
|   |-- models.py
|   |-- urls.py
|   |-- forms.py
|   |-- auth_views.py
|   |-- owner_views.py
|   |-- merchant_views.py
|   |-- admin_views.py
|   |-- public_views.py
|   |-- templates/
|   |-- static/
|   |-- migrations/
```

## Requirements

- Python 3.12
- MySQL 8.0 or compatible version
- pip

## Run Locally

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the MySQL database:

```sql
CREATE DATABASE pet_service_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

The default local database connection is:

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=pet_service_db
MYSQL_USER=root
MYSQL_PASSWORD=
```

If your local MySQL configuration is different, set these environment variables before running Django.

Initialize the database schema:

```bash
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

## Common Commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test pet_services
python manage.py createsuperuser
```

## Main Features

- Role-based pages for pet owners, merchants, and administrators
- Merchant registration, approval, rejection, and account status management
- Service category management, service publishing, approval, listing, and booking
- Pet profile and vaccine record management
- Order lifecycle management
- Review submission and merchant average-rating recalculation
- Favorite merchant list for pet owners

## Database Notes

The core schema includes users, pet owners, merchants, administrators, pets, vaccines, services, orders, reviews, and favorite stores. Migrations are included, so a new developer can recreate the schema with `python manage.py migrate`.
