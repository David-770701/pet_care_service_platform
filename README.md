# Pet Service Platform

A Django + MySQL pet service platform built from a database course project and polished as a portfolio project. It models a real marketplace workflow for pet owners, service merchants, and platform administrators.

## Highlights

- Role-based workflows for pet owners, merchants, and administrators.
- Merchant onboarding with admin approval.
- Service publishing, approval, disabling, and booking.
- Pet profile management with vaccine records and due-date reminders.
- Order lifecycle control: pending, confirmed, paid/completed, and cancelled.
- Review system with automatic merchant average-rating recalculation.
- Database-focused design with foreign keys, uniqueness constraints, and query indexes.

## Tech Stack

- Backend: Django 4.2
- Database: MySQL by default, SQLite available for lightweight local checks
- Frontend: Django templates + Bootstrap 5

## Project Structure

```text
.
+-- src/
|   +-- manage.py
|   +-- pet_service_project/
|   |   +-- settings.py
|   +-- pet_core/
|       +-- models.py
|       +-- views.py
|       +-- urls.py
|       +-- vaccine_logic.py
|       +-- ratings.py
|       +-- templates/pet_core/
+-- docs/
+-- .env.example
```

## Run Locally

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r src/requirements.txt
```

Copy `.env.example` to `.env` or set the same environment variables in your shell.

Initialize the database schema:

```bash
python src/manage.py migrate
```

Start the development server:

```bash
python src/manage.py runserver
```

For a quick SQLite check without MySQL:

```bash
set DJANGO_DB_ENGINE=sqlite
python src/manage.py migrate
python src/manage.py check
```

PowerShell users can set the same variable with:

```powershell
$env:DJANGO_DB_ENGINE="sqlite"
```

Run the test suite:

```bash
python src/manage.py test pet_core
```

## Database Design Notes

The core schema centers on:

- `User`, `PetOwner`, `Merchant`, `Administrator`
- `Pet`, `Vaccine`, `VaccineRecord`
- `ServiceCategory`, `Service`
- `Order`, `VaccineOrderDetail`, `Review`, `FavoriteStore`

The implementation includes indexes for common list/filter pages, including merchant location/category lookup, service state filtering, order lookup, and vaccine reminder queries.

## Portfolio Summary

This project can be described on a resume as:

> Built a Django + MySQL pet service marketplace with owner, merchant, and admin workflows; designed relational models, constraints, indexes, order/review lifecycle logic, and vaccine reminder features.

## GitHub Preparation

Before publishing:

```bash
git init
git add .
git commit -m "Initial pet service platform project"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

Avoid committing private credentials or local database files. Use `.env.example` as the public configuration template.
