# Task Manager API

A REST API for managing personal tasks, built with **FastAPI**,
**PostgreSQL**, and **SQLAlchemy**. The project includes CRUD endpoints,
pagination and filtering, JWT-based authentication, user ownership,
database migrations with Alembic, and automated tests.

> **Project status:** This README documents the features implemented
> during development. Before deploying, verify that all tests pass and
> that the Alembic migration history can build the complete schema from
> a brand-new database. The initial migration may have been created as a
> baseline after tables already existed, so it may not create those
> tables on a fresh Docker database.

## Features

-   Create, list, retrieve, update, and delete tasks.
-   PostgreSQL persistence using SQLAlchemy.
-   Pagination with `skip` and `limit`.
-   Filter tasks by completion status.
-   User registration with Argon2 password hashing.
-   JWT access tokens for authentication.
-   Task ownership checks to prevent users from accessing other users'
    tasks.
-   Pydantic request and response schemas.
-   Alembic database migrations.
-   Automated tests using `pytest`, FastAPI's `TestClient`, and an
    isolated SQLite test database.
-   Docker and Docker Compose configuration for local container-based
    development.

## Tech Stack

-   Python 3.12+
-   FastAPI
-   PostgreSQL
-   SQLAlchemy
-   Alembic
-   Pydantic
-   PyJWT
-   pwdlib with Argon2
-   pytest and HTTPX
-   Docker / Docker Compose

## Project Structure

``` text
Task Manager/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── user_models.py
│   ├── schemas.py
│   ├── auth_schemas.py
│   ├── auth.py
│   ├── auth_routes.py
│   └── dependencies.py
├── migrations/
│   ├── versions/
│   └── env.py
├── tests/
│   ├── test_tasks.py
│   └── test_auth.py
├── .env                 # Local secrets; do not commit
├── .env.example         # Recommended template to create
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── create_tables.py
└── test_db.py
```

Your exact files may differ slightly as the project evolves.

## Getting Started Locally

### 1. Clone the repository

``` bash
git clone <your-repository-url>
cd <your-repository-folder>
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the virtual environment's
Python directly:

``` powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Install dependencies

``` bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. Keep it out of version
control.

``` dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/task_manager_db
SECRET_KEY=REPLACE_WITH_A_RANDOM_SECRET
ACCESS_TOKEN_EXPIRE_MINUTES=30
POSTGRES_PASSWORD=REPLACE_WITH_A_STRONG_RANDOM_PASSWORD
```

Replace the example values with your own. Generate a JWT secret with:

``` bash
python -c "import secrets; print(secrets.token_hex(32))"
```

If your PostgreSQL password contains URL-reserved characters, URL-encode
the password or construct the SQLAlchemy URL with a URL-safe approach.
Never publish real credentials, tokens, or `.env` contents.

### 5. Create the PostgreSQL database

Install and start PostgreSQL, then create a database named
`task_manager_db` if it does not already exist. Ensure the host, port,
username, password, and database name match `DATABASE_URL`.

You can test the database connection using the project's
connection-check script, if present:

``` bash
python test_db.py
```

### 6. Apply database migrations

``` bash
alembic current
alembic upgrade head
```

For an existing development database that was created manually, the
migration baseline must first be reconciled with the actual schema. Do
not run `alembic stamp head` blindly: stamping records a revision but
does not execute schema changes.

For a brand-new database, verify that the migration history creates
every required table (`users` and `tasks`) and includes all columns and
constraints. If the original migration was empty because the tables
already existed, create or revise a proper baseline before using a fresh
database.

### 7. Start the API

``` bash
uvicorn app.main:app --reload
```

The local API should be available at:

-   API base: `http://127.0.0.1:8000`
-   Interactive Swagger docs: `http://127.0.0.1:8000/docs`
-   OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

The root path `/` may return `404` if no root endpoint has been defined.
Use `/docs` to explore the API.

## API Endpoints

### Authentication

  -----------------------------------------------------------------------
  Method                  Endpoint                Purpose
  ----------------------- ----------------------- -----------------------
  `POST`                  `/auth/register`        Register a user

  `POST`                  `/auth/login`           Log in using JSON
                                                  credentials and receive
                                                  a token

  `POST`                  `/auth/token`           Form-based token
                                                  endpoint for Swagger
                                                  OAuth2 authorization
  -----------------------------------------------------------------------

Registration expects JSON similar to:

``` json
{
  "email": "user@example.com",
  "password": "ChooseAStrongPassword123!"
}
```

The form-based `/auth/token` endpoint expects `username` (the registered
email) and `password` as form fields.

### Tasks

Task endpoints require a valid bearer token.

  -----------------------------------------------------------------------
  Method                  Endpoint                Purpose
  ----------------------- ----------------------- -----------------------
  `POST`                  `/tasks`                Create a task

  `GET`                   `/tasks`                List the current user's
                                                  tasks

  `GET`                   `/tasks/{task_id}`      Retrieve one of the
                                                  current user's tasks

  `PUT`                   `/tasks/{task_id}`      Update one of the
                                                  current user's tasks

  `DELETE`                `/tasks/{task_id}`      Delete one of the
                                                  current user's tasks
  -----------------------------------------------------------------------

Example task creation request:

``` json
{
  "title": "Learn FastAPI",
  "description": "Build a database-backed API"
}
```

Example partial update:

``` json
{
  "completed": true
}
```

### Pagination and filtering

`GET /tasks` supports:

-   `skip`: number of records to skip; defaults to `0`.
-   `limit`: number of records to return; defaults to `10`, maximum
    `100`.
-   `completed`: optional Boolean filter.

Examples:

``` text
GET /tasks?skip=0&limit=10
GET /tasks?skip=10&limit=10
GET /tasks?completed=true
GET /tasks?completed=false
```

Use the **Authorize** button in Swagger UI to authenticate with a token.
The token-based OAuth2 endpoint is `/auth/token`.

## Running Tests

Run the test suite from the repository root:

``` bash
python -m pytest -v
```

To run individual test files:

``` bash
python -m pytest tests/test_tasks.py -v
python -m pytest tests/test_auth.py -v
```

The authentication tests are designed to use an isolated in-memory
SQLite database through dependency overrides, so they should not modify
the PostgreSQL development database. Ensure every test module uses
consistent database overrides and cleans them up after each test.

## Docker

Docker Desktop and Docker Compose are required.

Build and start the services:

``` bash
docker compose up --build -d
```

Inspect service status and logs:

``` bash
docker compose ps
docker compose logs -f api
docker compose logs -f db
```

Stop the services:

``` bash
docker compose down
```

The Compose configuration uses a separate PostgreSQL container and a
persistent Docker volume. It does **not** automatically use or copy the
PostgreSQL database installed on your Windows host.

Before relying on Docker, make sure the migration history can initialize
a completely empty database. If the API container starts before
migrations have been applied, apply migrations using the configured
container environment, for example:

``` bash
docker compose run --rm api alembic upgrade head
```

This command is only sufficient if the migrations fully create the
schema from scratch. Review and fix the migration baseline first if the
initial migration is empty. Do not delete the database volume unless you
intentionally want to remove its stored data.

## Security Notes

-   Store secrets in environment variables, not source code.
-   Keep `.env` out of Git; commit a `.env.example` containing
    placeholders instead.
-   Use HTTPS in production.
-   Use strong, unique JWT signing secrets and rotate them if exposed.
-   Passwords should be stored only as secure hashes, never as
    plaintext.
-   Protect every task query with the authenticated user's ownership
    condition.
-   Use a production-grade database and backup strategy.
-   Do not expose database ports publicly unless required and properly
    secured.
-   Review CORS, rate limiting, logging, token expiry, and error
    handling before production deployment.
-   OAuth2 password flow is useful for this learning project; production
    applications should generally use a modern identity flow such as
    OpenID Connect Authorization Code with PKCE.

## Roadmap

-   [ ] Confirm all unit and security tests pass.
-   [ ] Reconcile Alembic migrations so a clean database can be
    initialized from scratch.
-   [ ] Add a health-check endpoint.
-   [ ] Add CI to run tests automatically.
-   [ ] Improve logging and transaction error handling.
-   [ ] Finalize Docker startup and migration handling.
-   [ ] Deploy to a hosting provider.
-   [ ] Add screenshots, API examples, and architecture documentation.

## Contributing

1.  Create a feature branch.
2.  Make a focused change.
3.  Add or update tests.
4.  Run `python -m pytest -v`.
5.  Open a pull request with a clear description.

## License

Choose and add a license before distributing this project publicly. If
no license is provided, default copyright rules apply.
