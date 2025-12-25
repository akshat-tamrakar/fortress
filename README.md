# Fortress

**Enterprise-grade User Management Service** built with Django and AWS managed services.

Fortress provides authentication, authorization, and user lifecycle management for large-scale enterprise applications. It demonstrates scalability thinking, security-first design, and clean service boundaries while leveraging AWS Cognito, Amazon Verified Permissions, and other managed services to minimize custom infrastructure.

## Features

### Core Capabilities

- **Authentication** - User registration, email verification, login with MFA support
- **Authorization** - ABAC-based access control using Amazon Verified Permissions (Cedar policies)
- **User Management** - Full lifecycle management (create, read, update, delete, enable/disable)
- **Self-Service Profile** - Users can view and update their own profiles
- **Service-to-Service Auth** - IAM-based authentication for microservice integration

### Security

- Multi-factor authentication (TOTP app-based)
- JWT-based stateless authentication
- Fail-closed authorization model
- Rate limiting with progressive lockout
- Immediate token revocation for disabled users
- AWS SigV4 for service-to-service calls

### Scale & Performance

- Designed for 1M users, 10K concurrent sessions
- Redis-backed authorization caching (<10ms cached, <100ms uncached)
- Sliding window rate limiting
- Horizontal scalability via AWS managed services

## Architecture

```
┌─────────────────┐      ┌─────────────────────────────────────────┐
│ Microservices   │─────▶│        User Management Service          │
│ (IAM Auth)      │      │                                         │
│                 │      │  ┌─────────────┐  ┌──────────────────┐  │
└─────────────────┘      │  │   Cognito   │  │       AVP        │  │
                         │  │ (users/auth)│  │ (authorization)  │  │
                         │  └─────────────┘  └──────────────────┘  │
                         │                                         │
                         │  ┌─────────────┐                        │
                         │  │    Redis    │                        │
                         │  │  (caching)  │                        │
                         │  └─────────────┘                        │
                         └─────────────────────────────────────────┘
```

### Design Principles

- **Cognito-first approach** - All user data stored in AWS Cognito
- **Service abstraction** - Downstream services never call Cognito/AVP directly
- **Managed services** - Minimize custom infrastructure (no DynamoDB/RDS for user data)
- **Security-first** - MFA, ABAC, fail-closed authorization, immediate revocation

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Django 5.x + Django REST Framework |
| Language | Python 3.11+ |
| Package Manager | uv |
| User Store | Amazon Cognito |
| Authorization Engine | Amazon Verified Permissions (Cedar) |
| Cache | Amazon ElastiCache (Redis) |
| API Gateway | Amazon API Gateway |
| Compute | AWS Lambda / Amazon ECS |
| Linting & Formatting | Ruff |
| Testing | pytest + pytest-django |

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- AWS Account with Cognito and Verified Permissions configured
- Redis (local or ElastiCache for production)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/akshat-tamrakar/fortress.git
cd fortress
```

2. **Install dependencies using uv**

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync
```

3. **Run migrations**

```bash
uv run python manage.py migrate
```

4. **Start the development server**

```bash
uv run python manage.py runserver
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_auth.py
```

### Code Quality

```bash
# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Run both lint and format
uv run ruff check --fix . && uv run ruff format .
```

### Development Dependencies

Install development dependencies:

```bash
uv sync --group dev
```

## API Documentation

### Base URL

```
https://api.usermanagement.internal/v1
```

### Key Endpoints

#### Authentication
- `POST /auth/register` - Self-registration
- `POST /auth/login` - User login
- `POST /auth/mfa/verify` - Verify MFA code
- `POST /auth/logout` - Logout and revoke tokens

#### Authorization (IAM-only)
- `POST /authorize` - Single authorization check
- `POST /authorize/batch` - Batch authorization checks

#### User Management (Admin)
- `GET /users` - List all users
- `POST /users` - Create user
- `GET /users/{id}` - Get user details
- `PUT /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user (permanent)

#### Self-Service
- `GET /me` - Get own profile
- `PUT /me` - Update own profile

For complete API specifications, see [docs/api-specifications.md](docs/api-specifications.md).

## Project Structure

```
fortress/
├── docs/                       # Documentation
│   ├── api-specifications.md   # Complete API reference
│   └── user-management-service-poc.md  # Architecture & design decisions
├── fortress/                   # Main application (to be created)
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                       # Django apps (to be created)
│   ├── authentication/
│   ├── authorization/
│   └── users/
├── pyproject.toml             # Project configuration
├── uv.lock                    # Dependency lock file
└── README.md                  # This file
```

## Documentation

- **[API Specifications](docs/api-specifications.md)** - Complete REST API documentation with endpoints, rate limits, and error codes
- **[POC Analysis](docs/user-management-service-poc.md)** - Architecture decisions, design philosophy, and technical specifications

## User Types

| Type | Description | Cognito Pool |
|------|-------------|--------------|
| **End Users** | Application users | End User Pool |
| **Admin Users** | Platform administrators | Admin User Pool |

## Rate Limiting

Rate limiting is enforced via Redis-based sliding window:

- **Authentication**: 5 login attempts/min per IP
- **Authorization**: 5000 checks/min per service
- **User Management**: 100 reads/min, 20 creates/min per user

See [docs/api-specifications.md](docs/api-specifications.md) for complete rate limit specifications.

## Security

### Authentication
- Email + password with MFA (TOTP)
- JWT tokens (15 min access, 7 day refresh)
- Immediate revocation for disabled users

### Authorization
- ABAC model with Cedar policies
- Fail-closed by default
- Authorization caching (60s TTL)

### Password Policy
- Minimum 12 characters
- Requires uppercase, lowercase, numbers, special characters
- Temporary passwords expire in 7 days

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file.

## Author

**Akshat Tamrakar**  
Email: akshat1997tamrakar@gmail.com

## POC Status

This is a Proof of Concept demonstrating:
- ✅ Scalable architecture supporting 1M users
- ✅ Security-first approach (MFA, ABAC, fail-closed)
- ✅ Clean service boundaries
- ✅ Operational readiness (error handling, rate limiting, observability)

### Known Limitations (POC)
- Hard delete only (no soft delete/recovery)
- No state audit tracking
- Single tenant only
- Limited Cognito query capabilities

See [docs/user-management-service-poc.md](docs/user-management-service-poc.md) for future enhancements.

---

**Note**: This service is designed to be consumed by other microservices only. It abstracts AWS Cognito and Amazon Verified Permissions behind a unified REST API, ensuring downstream services never interact with AWS services directly.
