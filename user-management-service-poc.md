# User Management Service – POC Analysis

## Overview

This document describes the **design analysis and architectural decisions** for a **User Management Service** intended as a **Proof of Concept (POC)** for a large-scale enterprise application.

The goal of this POC is to demonstrate **scalability thinking, security-first design, and clean service boundaries**, rather than delivering a production-ready IAM solution.

---

## 1. Purpose & Scope

### Primary Purpose

The service is responsible for:

* User authentication
* Authorization
* User lifecycle management

### Scope

* Application-specific user management
* Single-tenant system
* Internal-facing service consumed by other microservices

### Out of Scope (for POC)

* Cross-tenant access
* External consumers
* Advanced compliance workflows
* Full audit pipelines
* Graceful degradation patterns

---

## 2. Consumers & Boundaries

### Consumers

* Internal microservices only

### Responsibility Boundaries

* Authentication and identity are delegated to managed services
* Authorization decisions are centralized
* Downstream services remain **authorization-agnostic**

This enforces a **clear separation of concerns**:

| Concern | Owner |
|---------|-------|
| Identity & trust | Amazon Cognito |
| Business authorization | Amazon Verified Permissions |
| User lifecycle & orchestration | User Management Service |

### Service Abstraction

All Cognito and AVP interactions are **abstracted behind the User Management Service interface**. Downstream services:

* Do not call Cognito directly
* Do not call AVP directly
* Interact only with User Management Service APIs

```
┌─────────────────┐      ┌─────────────────────────────────────────┐
│ Order Service   │─────▶│        User Management Service          │
│ Report Service  │      │  ┌─────────────┐  ┌──────────────────┐  │
│ Admin Service   │      │  │   Cognito   │  │       AVP        │  │
└─────────────────┘      │  │  (wrapped)  │  │    (wrapped)     │  │
                         │  └─────────────┘  └──────────────────┘  │
                         └─────────────────────────────────────────┘
```

---

## 3. User Model & Identity

### User Types

| Type | Description | Cognito Pool |
|------|-------------|--------------|
| End Users | Application users | End User Pool |
| Admin Users | Platform administrators | Admin User Pool |

### Identity Uniqueness

* Users are uniquely identified by **email**
* Email uniqueness is enforced globally (single-tenant)
* **Email is immutable** — changing email creates a new user

### User Creation Flow

| Method | Flow | Initiator |
|--------|------|-----------|
| Self-Registration | User signs up → Email OTP verification → Active | User |
| Admin-Initiated | Admin creates user → Email OTP sent → User verifies → Active | Admin |

### Verification Mechanism

* **Method:** Email OTP
* **OTP Expiry:** 15 minutes
* **Max Attempts:** 3 per OTP

### Profile Data Distribution

| Attribute | User Management Service | Cognito |
|-----------|-------------------------|---------|
| User ID | ✓ | ✓ (sub) |
| Email | ✓ | ✓ |
| User State | ✓ | — |
| Profile attributes | ✓ | — |
| Password | — | ✓ |
| MFA configuration | — | ✓ |
| MFA secrets | — | ✓ |

**Sync Strategy:** User Management Service is the source of truth for user state and profile. Cognito is the source of truth for credentials and MFA.

### Tenancy

* Single-tenant system
* Tenant context is implicit, not modeled explicitly
* Design remains tenant-aware for future extensibility

**Future-Proofing for Multi-Tenancy:**

| Design Choice | Purpose |
|---------------|---------|
| `tenant_id` field in DynamoDB schema (nullable) | Easy to enable per-tenant queries |
| Tenant context in service layer | Abstracted for future injection |
| Separate partition key strategy | Supports tenant isolation |

---

## 4. Authentication Strategy

### Authentication Model

* Username (email) & password
* Multi-factor authentication (TOTP app-based)

### Identity Provider

* Delegated to **Amazon Cognito**
* **Separate user pools** for End Users and Admin Users
* Cognito is responsible for:
  * Credential storage
  * MFA enforcement
  * Token issuance
  * Password policies

### Token Lifecycle

| Token Type | Expiry | Purpose |
|------------|--------|---------|
| Access Token | 15 minutes | API authorization |
| ID Token | 15 minutes | User identity claims |
| Refresh Token | 7 days | Obtain new access tokens |

**Refresh Strategy:**
* Client refreshes access token before expiry
* Refresh tokens are rotated on use
* Refresh token reuse detected and rejected

### JWT Claims Strategy

**Approach:** Minimal claims in token

| Claim | Included | Rationale |
|-------|----------|-----------|
| `sub` | ✓ | User identifier |
| `email` | ✓ | User email |
| `token_use` | ✓ | Token type (access/id) |
| `user_type` | ✓ | end_user / admin |
| User state | ✗ | Checked per request for immediate revocation |
| Permissions | ✗ | Managed by AVP, not embedded |

### Session Strategy

* Stateless authentication using JWTs
* Tokens are validated by User Management Service
* No server-side session storage

### Immediate Revocation Strategy

Since JWTs are stateless, immediate revocation for suspended/deactivated users is handled via:

```
Every Authenticated Request:
    │
    ▼
┌─────────────────────────┐
│ 1. Validate JWT         │ ← Signature, expiry, issuer
│    (stateless)          │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ 2. Check User State     │ ← From cache (30s TTL) or DB
│    (stateful check)     │
└─────────────────────────┘
    │
    ├── State = Active → Proceed
    │
    └── State = Suspended/Deactivated → 403 Forbidden
```

**Implementation:**
* User state cached in Redis (30-second TTL)
* State change immediately invalidates cache
* Every request validates current state

---

## 5. Authorization Model

### Authorization Style

* **ABAC-first model**
* Authorization decisions are made using:
  * User attributes
  * Resource attributes
  * Action context

### Policy Engine

* **Amazon Verified Permissions (AVP)**
* Cedar policies evaluate:
  * Principal
  * Action
  * Resource
  * Context

### Core Resources & Actions

| Resource | Actions | Description |
|----------|---------|-------------|
| `User` | `create`, `read`, `update`, `delete`, `list` | User CRUD operations |
| `User` | `suspend`, `activate`, `deactivate` | State management |
| `User` | `reset-password`, `update-mfa` | Credential management |
| `AdminUser` | `create`, `read`, `update`, `delete`, `list` | Admin user management |
| `Policy` | `read`, `list` | Policy viewing (management via AVP console) |
| `AuditLog` | `read`, `list` | Audit log access |

### Action Matrix by User Type

| Action | End User (Self) | End User (Others) | Admin |
|--------|-----------------|-------------------|-------|
| `User:read` | ✓ | ✗ | ✓ |
| `User:update` | ✓ (limited) | ✗ | ✓ |
| `User:delete` | ✗ | ✗ | ✓ |
| `User:suspend` | ✗ | ✗ | ✓ |
| `User:list` | ✗ | ✗ | ✓ |
| `AdminUser:*` | ✗ | ✗ | ✓ |

### Authorization Caching

**Strategy:** Hybrid (TTL + Event-Driven Invalidation)

| Component | Configuration |
|-----------|---------------|
| Cache Store | Redis (ElastiCache) |
| Default TTL | 60 seconds |
| Cache Key | `authz:{user_id}:{action}:{resource_type}:{resource_id}` |

**Invalidation Triggers:**

| Event | Invalidation Scope |
|-------|-------------------|
| User state change | All entries for user |
| User attribute change | All entries for user |
| Policy update | Full cache flush |

```python
# Invalidation on user state change
def on_user_state_change(user_id: str, new_state: str):
    cache.delete_pattern(f"authz:{user_id}:*")
    cache.set(f"user_state:{user_id}", new_state, ttl=30)
```

### Failure Mode

**Policy:** Fail-Closed

If AVP is unavailable:
* Authorization requests return **denied**
* Cached decisions (within TTL) may be used
* Error logged with high severity
* Alert triggered

```python
def check_authorization(user_id, action, resource):
    try:
        # Try cache first
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Call AVP
        decision = avp_client.is_authorized(...)
        cache.set(cache_key, decision, ttl=60)
        return decision
        
    except AVPUnavailableError:
        # Fail closed - deny access
        logger.error("authz.avp.unavailable", user_id=user_id, action=action)
        return False
```

---

## 6. User Lifecycle Management

### User States

| State | Description | Can Authenticate | Can Be Authorized |
|-------|-------------|------------------|-------------------|
| `Created` | Record exists, pending verification | No | No |
| `Unverified` | Awaiting email OTP verification | No | No |
| `PasswordResetRequired` | Must reset password on next login | Limited | No |
| `Active` | Fully enabled | Yes | Yes |
| `Suspended` | Temporarily blocked | No | No |
| `Deactivated` | Permanently disabled | No | No |
| `Deleted` | Soft-deleted, recoverable | No | No |

### State Machine

```
                    ┌──────────────────────────────────────────────┐
                    │                                              │
                    ▼                                              │
┌─────────┐    ┌────────────┐    ┌─────────┐    ┌─────────────┐   │
│ Created │───▶│ Unverified │───▶│ Active  │───▶│ Deactivated │───┘
└─────────┘    └────────────┘    └─────────┘    └─────────────┘
                                      │ ▲             │
                                      │ │             │
                                      ▼ │             │
                                 ┌───────────┐        │
                                 │ Suspended │        │
                                 └───────────┘        │
                                      │               │
                                      ▼               ▼
                                 ┌─────────────────────┐
                                 │      Deleted        │
                                 └─────────────────────┘
```

### Valid State Transitions

| From State | To State | Trigger | Side Effects |
|------------|----------|---------|--------------|
| `Created` | `Unverified` | Registration initiated | OTP sent |
| `Unverified` | `Active` | OTP verified | — |
| `Unverified` | `Deleted` | Admin action / Expiry | — |
| `Active` | `Suspended` | Admin action | Cache invalidated, sessions revoked |
| `Active` | `Deactivated` | Admin action | Cache invalidated, sessions revoked |
| `Active` | `PasswordResetRequired` | Admin/security trigger | — |
| `Active` | `Deleted` | Admin action | Cache invalidated |
| `Suspended` | `Active` | Admin action (reactivate) | — |
| `Suspended` | `Deactivated` | Admin action | — |
| `Suspended` | `Deleted` | Admin action | — |
| `Deactivated` | `Active` | Admin action (reactivate) | — |
| `Deactivated` | `Deleted` | Admin action | — |
| `PasswordResetRequired` | `Active` | Password reset completed | — |
| `Deleted` | `Active` | Admin action (restore) | Within retention period |

### Lifecycle Triggers

* **API Only** — No time-based or event-based automatic transitions
* All state changes require explicit API calls
* Admin authorization required for most transitions

### De-Provisioning Behavior

| Action | Effect |
|--------|--------|
| Suspend | Immediate access revocation, cache invalidation |
| Deactivate | Immediate access revocation, cache invalidation |
| Delete (Soft) | Logical removal, data retained indefinitely |

**Soft Delete Policy:**
* No eventual hard deletion
* Data retained for audit and recovery purposes
* Deleted users can be restored by admin

---

## 7. Data & Persistence

### Database

**Choice:** Amazon DynamoDB

**Rationale:**
* Read-heavy workload alignment
* Serverless scaling
* Single-digit millisecond latency
* AWS-native integration

### Data Model

**Users Table:**

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| `PK` | String | Partition Key | `USER#<user_id>` |
| `SK` | String | Sort Key | `PROFILE` |
| `user_id` | String | — | UUID |
| `email` | String | GSI-PK | Unique email |
| `user_type` | String | — | `end_user` / `admin` |
| `state` | String | GSI | User state |
| `cognito_sub` | String | — | Cognito user sub |
| `created_at` | String | — | ISO timestamp |
| `updated_at` | String | — | ISO timestamp |
| `created_by` | String | — | Creator user ID |
| `state_changed_at` | String | — | Last state change |
| `state_changed_by` | String | — | Who changed state |
| `tenant_id` | String | — | Future: tenant isolation |

**Global Secondary Indexes:**

| GSI Name | Partition Key | Sort Key | Purpose |
|----------|---------------|----------|---------|
| `GSI-Email` | `email` | — | Lookup by email |
| `GSI-State` | `state` | `created_at` | List users by state |
| `GSI-Tenant` | `tenant_id` | `created_at` | Future: tenant queries |

### Read/Write Patterns

| Pattern | Frequency | Optimization |
|---------|-----------|--------------|
| Authorization check | Very High | Redis cache (60s TTL) |
| User state lookup | High | Redis cache (30s TTL) |
| User profile read | Medium | DynamoDB direct |
| User profile update | Low | DynamoDB direct |
| User creation | Low | DynamoDB direct |
| User listing | Low | DynamoDB GSI with pagination |

---

## 8. Service-to-Service Authentication

### Approach

**AWS IAM Roles** — Services assume IAM roles, requests signed with AWS Signature V4.

```
┌────────────────────────┐         ┌─────────────────────────┐
│ Order Service          │         │  User Management        │
│ (ECS Task)             │────────▶│  Service (API Gateway)  │
│                        │         │                         │
│ IAM Role:              │         │  IAM Policy:            │
│ order-service-role     │         │  Allow order-service    │
└────────────────────────┘         └─────────────────────────┘
```

### IAM Roles per Service

| Service | IAM Role | Allowed Actions |
|---------|----------|-----------------|
| Order Service | `order-service-role` | `User:read`, authorization checks |
| Notification Service | `notification-service-role` | `User:read` |
| Admin Dashboard | `admin-dashboard-role` | All `User:*` and `AdminUser:*` actions |

### Request Flow

```python
# Downstream service calling User Management
import boto3
from aws_requests_auth.boto_utils import BotoAWSRequestsAuth

auth = BotoAWSRequestsAuth(
    aws_host="api.usermanagement.internal",
    aws_region="us-east-1",
    aws_service="execute-api"
)

response = requests.post(
    "https://api.usermanagement.internal/v1/authorize",
    json={"user_id": "user-123", "action": "orders:create", "resource": "..."},
    auth=auth
)
```

---

## 9. API Design

### API Style

* **REST**
* **Versioning:** URL path versioning (`/v1/...`)

### Endpoints

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/auth/register` | Self-registration |
| `POST` | `/v1/auth/verify-email` | Verify email OTP |
| `POST` | `/v1/auth/login` | User login |
| `POST` | `/v1/auth/mfa/verify` | Verify MFA code |
| `POST` | `/v1/auth/token/refresh` | Refresh access token |
| `POST` | `/v1/auth/logout` | Logout (revoke refresh token) |
| `POST` | `/v1/auth/password/forgot` | Initiate password reset |
| `POST` | `/v1/auth/password/reset` | Complete password reset |

#### Authorization

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/authorize` | Check authorization |
| `POST` | `/v1/authorize/batch` | Batch authorization check |

#### User Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/users` | Create user (admin) |
| `GET` | `/v1/users` | List users (admin) |
| `GET` | `/v1/users/{id}` | Get user |
| `PUT` | `/v1/users/{id}` | Update user |
| `DELETE` | `/v1/users/{id}` | Soft delete user |
| `POST` | `/v1/users/{id}/suspend` | Suspend user |
| `POST` | `/v1/users/{id}/activate` | Activate user |
| `POST` | `/v1/users/{id}/deactivate` | Deactivate user |
| `POST` | `/v1/users/{id}/restore` | Restore deleted user |

#### Profile (Self-Service)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/me` | Get own profile |
| `PUT` | `/v1/me` | Update own profile |
| `PUT` | `/v1/me/password` | Change own password |
| `GET` | `/v1/me/mfa` | Get MFA status |
| `POST` | `/v1/me/mfa/enable` | Enable MFA |
| `POST` | `/v1/me/mfa/disable` | Disable MFA |

---

## 10. Rate Limiting

### Implementation

**Approach:** Redis-based sliding window with API Gateway as first line of defense

```
Request → API Gateway (throttle) → User Management Service (fine-grained limits)
```

### Rate Limits

#### Authentication Endpoints

| Endpoint | Limit | Window | Dimension |
|----------|-------|--------|-----------|
| `POST /auth/login` | 5 | 1 min | IP |
| `POST /auth/login` | 10 | 1 min | Email |
| `POST /auth/mfa/verify` | 5 | 1 min | User |
| `POST /auth/password/forgot` | 3 | 1 hour | Email |
| `POST /auth/password/reset` | 5 | 1 hour | IP |
| `POST /auth/register` | 10 | 1 hour | IP |
| `POST /auth/verify-email` | 5 | 1 min | Email |

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
| `DELETE /users/{id}` | 10 | 1 min | User |

### Progressive Lockout (Authentication)

| Consecutive Failures | Lockout Duration |
|----------------------|------------------|
| 3 | 30 seconds |
| 5 | 5 minutes |
| 10 | 1 hour |
| 20 | 24 hours |

---

## 11. Error Handling

### Response Format

All errors return a standard JSON structure:

```json
{
  "error": {
    "code": "AUTHORIZATION_DENIED",
    "message": "You do not have permission to perform this action.",
    "details": {
      "action": "users:delete",
      "resource": "user-456"
    },
    "request_id": "req-abc-123",
    "timestamp": "2024-01-15T10:23:45.123Z"
  },
  "retry": {
    "retryable": false
  }
}
```

### Error Codes

| Category | HTTP Status | Codes | Retryable |
|----------|-------------|-------|-----------|
| Authentication | 401 | `TOKEN_EXPIRED`, `TOKEN_INVALID`, `MFA_REQUIRED` | No |
| Authorization | 403 | `AUTHORIZATION_DENIED`, `USER_SUSPENDED`, `USER_DEACTIVATED` | No |
| Validation | 422 | `VALIDATION_FAILED`, `INVALID_EMAIL_FORMAT` | No |
| Resource | 404/409 | `USER_NOT_FOUND`, `USER_ALREADY_EXISTS`, `STATE_CONFLICT` | No |
| Rate Limit | 429 | `RATE_LIMIT_EXCEEDED`, `ACCOUNT_LOCKED` | Yes |
| Service | 5xx | `INTERNAL_ERROR`, `DEPENDENCY_UNAVAILABLE` | Yes |

### Downstream Consumer Guidelines

| Error Type | Action |
|------------|--------|
| 401 | Re-authenticate |
| 403 | Do not retry, show error |
| 422 | Fix input, do not retry |
| 429 | Wait `retry_after` seconds, then retry |
| 5xx | Retry with exponential backoff (max 3 attempts) |

---

## 12. Scale & Non-Functional Expectations

### Expected Scale (POC Assumptions)

| Metric | Target |
|--------|--------|
| Total users | ~1,000,000 |
| Concurrent sessions | ~10,000 |
| Tenants | Single |
| Authorization checks/second | ~1,000 |

### Performance

| Operation | Latency Target |
|-----------|----------------|
| Authorization check (cached) | < 10ms |
| Authorization check (uncached) | < 100ms |
| Token validation | < 20ms |
| User profile read | < 50ms |
| User profile update | < 200ms |

### Availability

* High availability required
* Single AWS region (acceptable for POC)

---

## 13. Security & Compliance

### Security Posture

| Control | Implementation |
|---------|----------------|
| Authentication | Cognito with MFA |
| Authorization | AVP (ABAC) |
| Transport | TLS 1.2+ |
| Service-to-service | IAM roles |
| Secrets | AWS Secrets Manager |
| Rate limiting | Redis + API Gateway |

### Immediate Revocation

User state checked on every request:

```
JWT Valid + User State Active → Allow
JWT Valid + User State Suspended → Deny (403)
JWT Valid + User State Deactivated → Deny (403)
```

### Audit & Compliance

* Explicit audit logging out of scope for POC
* Data retention supported at lifecycle level
* Design allows audit features without architectural changes

---

## 14. Observability

### Tooling

| Tool | Purpose |
|------|---------|
| Amazon CloudWatch | Metrics and logs |
| AWS CloudTrail | API audit trail |
| AWS X-Ray | Distributed tracing |

### Key Metrics

* Authentication success/failure rates
* Authorization latency (p50, p95, p99)
* Cache hit rates
* Error rates by category

---

## 15. Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python (Django) |
| Database | Amazon DynamoDB |
| Cache | Amazon ElastiCache (Redis) |
| Authentication | Amazon Cognito |
| Authorization | Amazon Verified Permissions |
| API Gateway | Amazon API Gateway |
| Compute | AWS Lambda or ECS |
| Secrets | AWS Secrets Manager |

---

## 16. POC Success Criteria

This POC is considered successful if it:

* ✓ Demonstrates scalable design thinking
* ✓ Shows security-conscious decision making
* ✓ Maintains clean service boundaries
* ✓ Abstracts managed services behind unified interface
* ✓ Is easy to evolve into a production system

---

## 17. Future Considerations (Not Implemented)

| Feature | Notes |
|---------|-------|
| Multi-tenancy | Schema supports `tenant_id` |
| Event-driven lifecycle | SNS/EventBridge integration |
| Advanced audit logging | Dedicated audit service |
| Cross-region deployment | DynamoDB Global Tables |
| Hard deletion / GDPR | Compliance workflows |
| Federated identity | SAML/OIDC providers |

---