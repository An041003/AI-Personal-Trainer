# AI Personal Trainer

Rebuild scaffold for the AI Personal Trainer project from `Agent.md`, `Architecture.md`, `exercises.csv`, and `nutrition_atoms_seed.csv`.

## Stack

- Backend: Django, Django REST Framework, PostgreSQL, pgvector, OpenAI SDK.
- Frontend: React, Vite, Tailwind CSS, React Router, lucide-react.
- Seed data: `backend/seed/exercises.csv` and `backend/seed/nutrition_atoms_seed.csv`.

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Create PostgreSQL database and enable pgvector:

```sql
CREATE DATABASE aipt_db;
CREATE USER aipt_user WITH PASSWORD 'aipt_password';
ALTER ROLE aipt_user SET client_encoding TO 'utf8';
ALTER ROLE aipt_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE aipt_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE aipt_db TO aipt_user;
\c aipt_db
CREATE EXTENSION IF NOT EXISTS vector;
```

Then run:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py import_exercises --csv seed/exercises.csv
python manage.py seed_nutrition_atoms --csv seed/nutrition_atoms_seed.csv
python manage.py backfill_exercise_embeddings --batch-size 64
python manage.py runserver
```

Open API docs at `http://127.0.0.1:8000/api/docs/`.

## Frontend Setup

Node.js is required.

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Environment

Copy `backend/.env.example` to `backend/.env` and fill `OPENAI_API_KEY` before using AI-backed generation. Without a key, the current MVP returns deterministic fallbacks for development instead of failing the UI.

