# CLAUDE.md - AI Cooking App

## Build Commands
- Start local development: `docker compose -f docker-compose.local.yml up --build`
- Run Django server: `poetry run python manage.py runserver`
- Run migrations: `poetry run python manage.py migrate`
- Run specific test: `poetry run python manage.py test path.to.test`
- Clean rebuild: `docker compose -f docker-compose.local.yml down -v && docker compose -f docker-compose.local.yml build --no-cache && docker compose -f docker-compose.local.yml up`

## Code Style
- Formatting: Black with default line length (88 characters)
- Imports: Use isort for organizing imports
- Type hints: Use Python type annotations for function parameters and return values
- Naming: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- Error handling: Use try/except blocks with specific exceptions and proper logging
- Models: Define __str__ methods for all Django models
- Django conventions: Follow Django's MTV pattern and DRF viewset structure
- Logging: Use the standard Python logging module with appropriate levels