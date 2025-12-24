# API Specifications

## API Design

### API Style
- **REST**
- **Versioning:** URL path versioning (`/v1/...`)
- **Base URL:** `https://api.usermanagement.internal/v1`

### Endpoints

#### Authentication Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/auth/register` | Self-registration | No |
| `POST` | `/auth/verify-email` | Verify email OTP | No |
| `POST` | `/auth/resend-verification` | Resend verification email | No |
| `POST` | `/auth/login` | User login | No |
| `POST` | `/auth/mfa/verify` | Verify MFA code | Session Token |
| `POST` | `/auth/token/refresh` | Refresh access token | Refresh Token |
| `POST` | `/auth/logout` | Logout (revoke tokens) | Yes |
| `POST` | `/auth/password/forgot` | Request password reset | No |
| `POST` | `/auth/password/reset` | Reset password with token | No |

#### Authorization Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/authorize` | Check authorization | IAM Role |
| `POST` | `/authorize/batch` | Batch authorization check | IAM Role |

#### User Management Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `POST` | `/users` | Create user (admin) | Yes (Admin) |
| `GET` | `/users` | List users | Yes (Admin) |
| `GET` | `/users/{id}` | Get user by ID | Yes |
| `PUT` | `/users/{id}` | Update user | Yes |
| `DELETE` | `/users/{id}` | Delete user (permanent) | Yes (Admin) |
| `POST` | `/users/{id}/disable` | Disable user | Yes (Admin) |
| `POST` | `/users/{id}/enable` | Enable user | Yes (Admin) |

#### Profile Endpoints (Self-Service)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/me` | Get own profile | Yes |
| `PUT` | `/me` | Update own profile | Yes |
| `POST` | `/me/mfa/setup` | Setup MFA | Yes |

---

## Rate Limiting

### Implementation
Redis-based sliding window with API Gateway as first line of defense.

### Rate Limits by Category

#### Authentication Endpoints
| Endpoint | Limit | Window | Dimension |
|----------|-------|--------|-----------|
| `POST /auth/register` | 10 | 1 hour | IP |
| `POST /auth/login` | 5 | 1 min | IP |
| `POST /auth/mfa/verify` | 5 | 1 min | Session |

#### Authorization Endpoints
| Endpoint | Limit | Window | Dimension |
|----------|-------|--------|-----------|
| `POST /authorize` | 5000 | 1 min | Service (IAM Role) |
| `POST /authorize/batch` | 500 | 1 min | Service (IAM Role) |

#### User Management Endpoints
| Endpoint | Limit | Window | Dimension |
|----------|-------|--------|-----------|
| `GET /users` | 100 | 1 min | User |
| `POST /users` | 20 | 1 min | User |
| `PUT /users/{id}` | 30 | 1 min | User |

### Progressive Lockout (Authentication)
| Consecutive Failures | Lockout Duration |
|----------------------|------------------|
| 3 | 30 seconds |
| 5 | 5 minutes |
| 10 | 1 hour |
| 20 | 24 hours |

---

## Error Handling

### Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "request_id": "req-abc-123"
  },
  "retry": {
    "retryable": false,
    "retry_after_seconds": null
  }
}
```

### Error Codes by Category

#### Authentication Errors (401)
| Code | Description | Retryable |
|------|-------------|-----------|
| `AUTHENTICATION_REQUIRED` | No authentication provided | No |
| `TOKEN_EXPIRED` | Access token has expired | No |
| `TOKEN_INVALID` | Token is malformed or invalid | No |
| `INVALID_CREDENTIALS` | Wrong email or password | No |
| `MFA_REQUIRED` | MFA verification needed | No |

#### Authorization Errors (403)
| Code | Description | Retryable |
|------|-------------|-----------|
| `AUTHORIZATION_DENIED` | User lacks permission | No |
| `USER_DISABLED` | User account is disabled | No |
| `RESOURCE_ACCESS_DENIED` | Access to resource denied | No |

#### Validation Errors (400/422)
| Code | Description | Retryable |
|------|-------------|-----------|
| `VALIDATION_FAILED` | Request validation failed | No |
| `INVALID_EMAIL_FORMAT` | Email format is invalid | No |
| `PASSWORD_TOO_WEAK` | Password doesn't meet requirements | No |
| `USER_NOT_FOUND` | User does not exist | No |
| `RESOURCE_NOT_FOUND` | Requested resource not found | No |
| `USER_ALREADY_EXISTS` | User with email already exists | No |

#### Rate Limit Errors (429)
| Code | Description | Retryable |
|------|-------------|-----------|
| `RATE_LIMIT_EXCEEDED` | Too many requests | Yes |
| `ACCOUNT_LOCKED` | Too many failed attempts | Yes |

#### Service Errors (5xx)
| Code | Description | Retryable |
|------|-------------|-----------|
| `INTERNAL_ERROR` | Unexpected server error | Yes |
| `DEPENDENCY_UNAVAILABLE` | Cognito/AVP unavailable | Yes |
| `REQUEST_TIMEOUT` | Request processing timeout | Yes |

### Consumer Guidelines
| Error Type | Recommended Action |
|------------|-------------------|
| 401 | Re-authenticate user |
| 403 | Do not retry, display error to user |
| 400/422 | Fix input data, do not retry |
| 429 | Wait `retry_after_seconds`, then retry |
| 5xx + `retryable: true` | Retry with exponential backoff (max 3) |