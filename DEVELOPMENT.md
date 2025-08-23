# Development Guide

This guide explains how to set up and work with the Django marketplace application's development environment.

## Quick Start

```bash
# Clone the repository
git clone <your-repo-url>
cd marketplace

# Set up development environment
make dev-setup

# Start development server
make runserver
```

## Development Environment Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Node.js 16+ (for frontend assets)

### Installation

1. **Install Python dependencies:**
   ```bash
   make install
   ```

2. **Set up pre-commit hooks:**
   ```bash
   make install-pre-commit
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

4. **Run database migrations:**
   ```bash
   make migrate
   ```

5. **Create superuser:**
   ```bash
   make superuser
   ```

## Available Commands

### Testing

```bash
make test              # Run all tests
make test-modular      # Run modular system tests
make test-coverage     # Run tests with coverage report
```

### Code Quality

```bash
make lint              # Run all linting checks
make format            # Format code with black and isort
make security          # Run security checks
make performance       # Run performance tests
```

### Development

```bash
make runserver         # Start development server
make shell             # Start Django shell
make migrate           # Run database migrations
make migrate-modules   # Run modular architecture migration
make collectstatic     # Collect static files
```

### Maintenance

```bash
make clean             # Clean up cache files
make check-all         # Run all checks (lint, test, security)
make ci                # Run CI checks locally
```

## Code Quality Tools

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality before commits:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security scanning
- **pyupgrade**: Python version compatibility

### Configuration Files

- **`.flake8`**: Flake8 linting rules
- **`pyproject.toml`**: Black, isort, mypy, pytest, and coverage configuration
- **`.pre-commit-config.yaml`**: Pre-commit hook configuration

## Testing

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific test file
python manage.py test tests.test_modular_system

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Test Structure

- **`tests/test_modular_system.py`**: Comprehensive tests for the modular architecture
- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test component interactions
- **Performance tests**: Test system performance under load

## Modular Architecture

### Services

The application uses a service layer pattern:

- **`UserService`**: User management and authentication
- **`WalletService`**: Financial operations and balance management
- **`VendorService`**: Vendor profile and approval management
- **`ProductService`**: Product catalog management
- **`OrderService`**: Order processing and management
- **`DisputeService`**: Dispute resolution
- **`MessagingService`**: Communication system
- **`SupportService`**: Support ticket management

### Modules

Each Django app is encapsulated in a module:

- **`AccountsModule`**: User account management
- **`WalletsModule`**: Financial operations
- **`VendorsModule`**: Vendor management
- **`ProductsModule`**: Product catalog
- **`OrdersModule`**: Order processing
- **`DesignSystemModule`**: Design system and theming

## Database

### Migrations

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations
```

### Fixtures

```bash
# Load test data
python manage.py loaddata fixtures/test_data.json

# Dump current data
python manage.py dumpdata > fixtures/current_data.json
```

## Static Files

### Development

```bash
# Collect static files
make collectstatic

# Watch for changes (if using django-extensions)
python manage.py runserver_plus --reloader
```

## Environment Variables

Create a `.env` file in the project root:

```bash
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:password@localhost:5432/dbname
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure virtual environment is activated
2. **Database connection**: Check PostgreSQL is running and credentials are correct
3. **Static files not loading**: Run `make collectstatic`
4. **Pre-commit hooks failing**: Run `make format` to fix formatting issues

### Getting Help

- Check the [main README](../README.md) for project overview
- Review the [modular architecture documentation](../MODULAR_ARCHITECTURE_README.md)
- Check the [migration guide](../MIGRATION_GUIDE.md) for architecture details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Check code quality: `make lint`
6. Commit with a descriptive message
7. Push and create a pull request

## CI/CD

The project uses GitHub Actions for continuous integration:

- **Tests**: Run on Python 3.9, 3.10, and 3.11
- **Code Quality**: Linting, formatting, and type checking
- **Security**: Bandit and safety checks
- **Performance**: Load testing and benchmarks
- **Coverage**: Code coverage reporting

Check the [`.github/workflows/django-tests.yml`](../.github/workflows/django-tests.yml) file for details.