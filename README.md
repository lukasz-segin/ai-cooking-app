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
├── documents_processor/     # App for processing documents
│   ├── __init__.py
│   ├── apps.py
│   ├── migrations/
│   ├── models.py           # Document models
│   ├── serializers.py
│   ├── services/           # Document processing services
│   │   ├── file_processor_service.py
│   │   ├── google_drive_service.py
│   │   ├── openai_service.py
│   │   ├── text_splitter_service.py
│   │   └── vector_service.py
│   ├── urls.py
│   └── views.py
├── documents/              # Directory for document storage
├── Dockerfile              # Dockerfile for containerization
├── docker-compose.local.yml # Local development configuration
├── pyproject.toml          # Poetry dependencies and config
├── poetry.lock             # Lock file for dependencies
└── README.md               # Project documentation
```

## API Endpoints

The application provides the following REST API endpoints:

### Recipes
- `GET /api/recipes/` - List all recipes
- `POST /api/recipes/` - Create a new recipe
- `GET /api/recipes/{id}/` - Retrieve a specific recipe
- `PUT /api/recipes/{id}/` - Update a specific recipe
- `DELETE /api/recipes/{id}/` - Delete a specific recipe

### Document Processing
- `POST /api/documents/process_document/` - Process a PDF document
- `GET /api/documents/{document_id}/` - Get document processing status

## Document Processing

The application includes a document processor that can:
- Process PDF files containing recipes from local storage or Google Drive
- Extract text content using PyPDF2 or Google Drive's conversion capabilities
- Split content into manageable chunks
- Generate embeddings using OpenAI's text-embedding-3-large model (3072 dimensions)
- Store documents and their vector embeddings in PostgreSQL with pgvector

### Setting up Document Processing

1. **Configure Required Services:**

   Ensure you have the following credentials:
   - OpenAI API key (for generating embeddings)
   - Google Drive API credentials (for enhanced document processing)

2. **Google Drive Setup:**

   - Create a service account in Google Cloud Console
   - Download the service account key as JSON
   - Place it in your project root as `service-account.json`
   - Add the following to your environment variables:
     ```
     GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
     ```

3. **Process a Document:**

   You can process documents in two ways:

   a) From local storage:
   ```bash
   curl -X POST http://localhost:8000/api/documents/process_document/ \
      -H "Content-Type: application/json" \
      -d '{"file_name": "your-document.pdf", "use_google_drive": true}'
   ```

   b) Process with Google Drive in batches
   ```bash
   # Process with Google Drive in batches
   curl -X POST http://localhost:8000/api/documents/process_with_google_drive_batched/ \
        -H "Content-Type: application/json" \
        -d '{"file_name": "your-document.pdf", "batch_size": 15}'
   ```

   c) From Google Drive:
   ```bash
   curl -X POST http://localhost:8000/api/documents/process_drive_document/ \
        -H "Content-Type: application/json" \
        -d '{"drive_file_id": "your-google-drive-file-id"}'
   ```

   The system will:
   1. Create a StoredDocument entry with 'pending' status
   2. Process the PDF using either PyPDF2 or Google Drive's conversion
   3. Split the text into chunks
   4. Generate embeddings using OpenAI (3072-dimensional vectors)
   5. Store the chunks with embeddings in the database
   6. Update the document status to 'processed'

4. **Monitor Processing:**

   Check the document status using:
   ```bash
   curl http://localhost:8000/api/documents/{document_id}/
   ```

   Or view processing logs:
   ```bash
   docker compose -f docker-compose.local.yml logs -f web
   ```

### Database Setup

The document processor requires PostgreSQL with pgvector extension. The setup is automatically handled in the Docker environment:

1. The `ankane/pgvector` image is used which includes the pgvector extension
2. An initialization script creates the vector extension during first startup
3. Django migrations will create all necessary tables

If you need to reset the database:
```bash
# Stop containers and remove volumes
docker compose -f docker-compose.local.yml down -v

# Rebuild and start
docker compose -f docker-compose.local.yml up --build
```
OR
```bash
# Stop all containers and remove volumes
docker compose -f docker-compose.local.yml down -v

# Remove all images to ensure clean rebuild
docker rmi $(docker images -q ai-cooking-app-web)

# Rebuild and start with no cache
docker compose -f docker-compose.local.yml build --no-cache
docker compose -f docker-compose.local.yml up
```

If running locally (without Docker), you'll need to:
1. Install PostgreSQL
2. Install pgvector extension:
   ```sql
   CREATE EXTENSION vector;
   ```
3. Create the database and user
4. Run migrations:
   ```bash
   python manage.py migrate
   ```

### Using Document Fixtures

The project includes a pre-processed document fixture that contains recipe data, which can be loaded into your database:

1. **Load the Recipe Document Fixture:**

   ```bash
   # In Docker environment
   docker compose -f docker-compose.local.yml exec web python manage.py loaddata recipe_book_chunks
   
   # In local environment
   poetry run python manage.py loaddata recipe_book_chunks
   ```

   This will populate your database with:
   - A processed recipe document
   - Document chunks with extracted text
   - Vector embeddings for semantic search capabilities

2. **Create Your Own Fixtures:**

   After processing your own documents, you can create fixtures to reuse the data:

   ```bash
   # Export document data as fixture
   docker compose -f docker-compose.local.yml exec web bash -c "python manage.py dumpdata documents_processor.StoredDocument documents_processor.DocumentChunk --indent 4 > /app/documents_processor/fixtures/your_fixture_name.json"
   
   # Load your fixture
   docker compose -f docker-compose.local.yml exec web python manage.py loaddata your_fixture_name
   ```

3. **Automate Fixture Loading:**

   To automatically load fixtures when deploying, add the loaddata command to your deployment scripts or Docker entrypoint.

## Django Admin Interface

The project includes a comprehensive Django Admin interface for managing both recipes and document processing:

### Document Management Admin Features

Access the admin interface at [http://localhost:8000/admin/](http://localhost:8000/admin/) after creating a superuser.

1. **Document List View**: 
   - View all processed documents with their status
   - See document chunk counts with direct links
   - Filter by processing status and creation date
   - Search by title or description

2. **Document Detail View**:
   - View document metadata and processing status
   - See inline previews of all chunks within the document
   - Track processing timestamps

3. **Document Chunk Management**:
   - Browse all text chunks from processed documents
   - See content previews with smart truncation
   - Filter chunks by parent document
   - View embedding dimensions for each chunk
   - Navigate between related documents and chunks

This admin interface provides a convenient way to:
- Monitor document processing status
- Review extracted content quality
- Debug processing issues
- Manage your document database

### Accessing the Admin Interface

1. Create a superuser if you haven't already:
   ```bash
   # In Docker
   docker compose -f docker-compose.local.yml exec web python manage.py createsuperuser
   
   # In local environment
   poetry run python manage.py createsuperuser
   ```

2. Visit [http://localhost:8000/admin/](http://localhost:8000/admin/) and log in with your credentials

3. Navigate to "Stored documents" or "Document chunks" in the admin panel

## Environment Variables

For security reasons, the following environment variables should be set in production:

```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,another-domain.com
OPENAI_API_KEY=your-openai-api-key
POSTGRES_DB=ai_cooking
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
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

Contributions are welcome! If you'd like to contribute, please fork the repository and submit a pull request. For major changes, please 
open an issue first to discuss what you would like to change.

## License

This project is licensed under the [MIT License](LICENSE).
