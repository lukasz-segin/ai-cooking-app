# ai-cooking-app

**ai-cooking-app** is a Django REST Framework application designed to manage recipes with an AI-driven API. The project uses Python 3.12, Poetry for dependency management, and Docker for containerization, ensuring a robust, production-ready environment.

## Overview

- **API Endpoints:** Provides RESTful endpoints for listing and creating recipes.
- **Admin Interface:** Uses Django Admin to manage recipes.
- **Containerization:** Packaged using Docker and Docker Compose for consistent deployment.
- **Dependency Management:** Managed with Poetry.
- **Python Version:** Built using Python 3.12.

## Technologies

- **Python:** 3.12
- **Django:** 5.1.6
- **Django REST Framework:** 3.15.2
- **Poetry:** For dependency management
- **Gunicorn:** For serving the Django application
- **WhiteNoise:** For serving static files
- **Docker & Docker Compose:** For containerization and deployment

## Project Structure

```
ai-cooking-app/
├── ai_cooking_project/      # Django project folder
│   ├── __init__.py
│   ├── asgi.py             # ASGI configuration
│   ├── settings.py         # Project settings
│   ├── urls.py             # Main URL configuration
│   └── wsgi.py             # WSGI configuration
├── recipes/                 # App for managing recipes
│   ├── __init__.py
│   ├── apps.py             # App configuration
│   ├── migrations/         # Database migrations
│   │   └── 0001_initial.py
│   ├── models.py           # Recipe model definition
│   ├── serializers.py      # DRF serializers
│   ├── urls.py             # API endpoints
│   └── views.py            # API views
├── Dockerfile              # Dockerfile for containerization
├── docker-compose.local.yml # Local development configuration
├── pyproject.toml          # Poetry dependencies and config
├── poetry.lock             # Lock file for dependencies
└── README.md               # Project documentation
```

## API Endpoints

The application provides the following REST API endpoints:

- `GET /api/recipes/` - List all recipes
- `POST /api/recipes/` - Create a new recipe
- `GET /api/recipes/{id}/` - Retrieve a specific recipe
- `PUT /api/recipes/{id}/` - Update a specific recipe
- `DELETE /api/recipes/{id}/` - Delete a specific recipe

## Environment Variables

For security reasons, the following environment variables should be set in production:

```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,another-domain.com
```

> **Note:** The default development settings use SQLite as the database. For production, consider using PostgreSQL or another production-grade database.

## Getting Started

### Prerequisites

- **Python 3.12:** Ensure Python 3.12 is installed (locally or in your Docker base image).
- **Poetry:** Install via [Poetry installation guide](https://python-poetry.org/docs/#installation).
- **Docker & Docker Compose:** Install following [Docker's documentation](https://docs.docker.com/compose/).

### Local Setup with Poetry

1. **Clone the Repository:**

   ```bash
   git clone git@github.com:lukasz-segin/ai-cooking-app.git
   cd ai-cooking-app
   ```

2. **Configure Python Environment:**

   Make sure Poetry uses Python 3.12:

   ```bash
   poetry env use python3.12
   poetry install
   ```

3. **Set Environment Variables:**

   Create a `.env` file in the project root:

   ```bash
   DJANGO_SECRET_KEY=your-development-secret-key
   DJANGO_DEBUG=True
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
   ```

4. **Run Migrations:**

   ```bash
   poetry run python manage.py makemigrations
   poetry run python manage.py migrate
   ```

5. **Create a Superuser:**

   ```bash
   poetry run python manage.py createsuperuser
   ```

6. **Start the Development Server:**

   ```bash
   poetry run python manage.py runserver
   ```

   Access the API at [http://localhost:8000/api/recipes/](http://localhost:8000/api/recipes/) and the Django Admin at [http://localhost:8000/admin/](http://localhost:8000/admin/).

### Running with Docker

#### Build and Start Containers

1. **Build the Docker Image:**

   ```bash
   docker compose -f docker-compose.local.yml build --no-cache
   ```

2. **Start the Containers:**

   ```bash
   docker compose -f docker-compose.local.yml up
   ```

   The application should be accessible at [http://localhost:8000/](http://localhost:8000/).

#### Create a Superuser in Docker

```bash
docker compose -f docker-compose.local.yml run --rm web python manage.py createsuperuser
```

### Static Files

Static files are handled by WhiteNoise, which is already configured in the project. To collect static files:

```bash
poetry run python manage.py collectstatic --noinput
```

The static files will be collected to the `staticfiles` directory and served by WhiteNoise in production.

### Production Deployment

For production deployment, ensure you:

1. Set proper environment variables:
   - Set `DJANGO_DEBUG=False`
   - Set a strong `DJANGO_SECRET_KEY`
   - Configure `DJANGO_ALLOWED_HOSTS`

2. Use a production-grade database (PostgreSQL recommended)

3. Configure proper logging

4. Set up proper SSL/TLS certificates

The Dockerfile uses Gunicorn to serve the app:

```dockerfile
CMD ["gunicorn", "ai_cooking_project.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## Contributing

Contributions are welcome! If you'd like to contribute, please fork the repository and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the [MIT License](LICENSE).
