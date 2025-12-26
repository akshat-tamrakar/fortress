# User Management Service – POC Analysis

## Overview

This document describes the **design analysis and architectural decisions** for a **User Management Service** intended as a **Proof of Concept (POC)** for a large-scale enterprise application.

The goal of this POC is to demonstrate **scalability thinking, security-first design, and clean service boundaries**, while keeping implementation complexity appropriate for a POC.

### Design Philosophy

This POC adopts a **Cognito-only approach** for user data storage, leveraging AWS managed services to minimize custom infrastructure while maintaining clean service abstractions.

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Consumers & Boundaries](#2-consumers--boundaries)
3. [User Model & Identity](#3-user-model--identity)
4. [Authentication Strategy](#4-authentication-strategy)
5. [Authorization Model](#5-authorization-model)
6. [User Lifecycle Management](#6-user-lifecycle-management)
7. [Service-to-Service Authentication](#7-service-to-service-authentication)
8. [API Design](#8-api-design)
9. [Rate Limiting](#9-rate-limiting)
10. [Error Handling](#10-error-handling)
11. [Scale & Non-Functional Expectations](#11-scale--non-functional-expectations)
12. [Security & Compliance](#12-security--compliance)
13. [Observability](#13-observability)
14. [Technology Stack](#14-technology-stack)
15. [POC Success Criteria](#15-poc-success-criteria)
16. [Future Considerations](#16-future-considerations)
17. [Appendices](#appendices)

---

## 1. Purpose & Scope

### Primary Purpose

The service is responsible for:

- User authentication
- Authorization
- User lifecycle management

### Scope

- Application-specific user management
- Single-tenant system
- Internal-facing service consumed by other microservices

### Out of Scope (for POC)

- Cross-tenant access
- External consumers
- Advanced compliance workflows
- Full audit pipelines
- Graceful degradation patterns
- Soft delete / user recovery
- Custom user state tracking

---

## 2. Consumers & Boundaries

### Consumers

- Internal microservices only

### Responsibility Boundaries

| Concern | Owner |
|---------|-------|
| Identity, credentials & user data | Amazon Cognito |
| Business authorization | Amazon Verified Permissions |
| Orchestration & abstraction | User Management Service |

### Service Abstraction

All Cognito and AVP interactions are **abstracted behind the User Management Service interface**. Downstream services:

- Do not call Cognito directly
- Do not call AVP directly
- Interact only with User Management Service APIs

```
┌─────────────────┐      ┌─────────────────────────────────────────┐
│ Order Service   │─────▶│        User Management Service          │
│ Report Service  │      │                                         │
│ Admin Service   │      │  ┌─────────────┐  ┌──────────────────┐  │
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

---

## 3. User Model & Identity

### User Types

| Type | Description | Cognito Pool |
|------|-------------|--------------|
| End Users | Application users | End User Pool |
| Admin Users | Platform administrators | Admin User Pool |

### Identity Uniqueness

- Users are uniquely identified by **email**
- Email uniqueness is enforced by Cognito
- **Email is immutable** — changing email creates a new user

### User Creation Flow

| Method | Flow | Initiator |
|--------|------|-----------|
| Self-Registration | User signs up → Email OTP verification → Active | User |
| Admin-Initiated | Admin creates user → Email OTP sent → User verifies → Active | Admin |

### Verification Mechanism

| Configuration | Value |
|---------------|-------|
| Method | Email OTP |
| OTP Expiry | 15 minutes (Cognito default) |
| Max Attempts | Managed by Cognito |

### User Data Storage

**All user data is stored in Cognito:**

| Attribute | Cognito Attribute | Mutable |
|-----------|-------------------|---------|
| User ID | `sub` (auto-generated) | No |
| Email | `email` | No |
| First Name | `given_name` | Yes |
| Last Name | `family_name` | Yes |
| Phone | `phone_number` | Yes |
| User Type | `custom:user_type` | No |
| Account Status | `Enabled/Disabled` | Yes (Admin) |
| Email Verified | `email_verified` | Yes |
| MFA Enabled | MFA settings | Yes |
| Created At | `UserCreateDate` | No |
| Updated At | `UserLastModifiedDate` | No |

### No Custom Database

This POC intentionally **does not use DynamoDB or any custom database** for user data:

| Trade-off | Accepted Limitation |
|-----------|---------------------|
| Custom states | Use Cognito's enabled/disabled only |
| Soft delete | Users are permanently deleted |
| State change tracking | No audit of who changed what |
| Rich queries | Limited to Cognito's capabilities |
| Restore deleted users | Not possible |

---

## 4. Authentication Strategy

### Authentication Model

- Username (email) & password
- Multi-factor authentication (TOTP app-based)

### Identity Provider

- Delegated to **Amazon Cognito**
- **Separate user pools** for End Users and Admin Users
- Cognito handles:
  - Credential storage
  - MFA enforcement
  - Token issuance
  - Password policies
  - Email verification
  - Account status

### Token Lifecycle

| Token Type | Expiry | Purpose |
|------------|--------|---------|
| Access Token | 15 minutes | API authorization |
| ID Token | 15 minutes | User identity claims |
| Refresh Token | 7 days | Obtain new access tokens |

**Refresh Strategy:**

- Client refreshes access token before expiry
- Refresh tokens are rotated on use
- Refresh token reuse detected and rejected

### JWT Claims Strategy

**Approach:** Minimal claims (Cognito defaults + user_type)

| Claim | Source | Description |
|-------|--------|-------------|
| `sub` | Cognito | User identifier (UUID) |
| `email` | Cognito | User email |
| `email_verified` | Cognito | Email verification status |
| `token_use` | Cognito | Token type (access/id) |
| `custom:user_type` | Cognito | `end_user` or `admin` |
| `cognito:groups` | Cognito | User groups (optional) |

### Session Strategy

- Stateless authentication using JWTs
- Tokens validated by User Management Service
- No server-side session storage

### Immediate Revocation Strategy

For disabled users, revocation is handled via:

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
│ 2. Check User Status    │ ← From cache (30s TTL) or Cognito
│    (Cognito lookup)     │
└─────────────────────────┘
    │
    ├── Enabled = true  → Proceed
    │
    └── Enabled = false → 403 Forbidden
```

**Implementation:**

- User enabled status cached in Redis (30-second TTL)
- Disabling user immediately invalidates cache entry
- Every request validates user is still enabled

---

## 5. Authorization Model

### Authorization Style

- **ABAC-first model**
- Authorization decisions are made using:
  - User attributes (from Cognito)
  - Resource attributes
  - Action context

### Policy Engine

- **Amazon Verified Permissions (AVP)**
- Cedar policies evaluate:
  - Principal (user)
  - Action
  - Resource
  - Context

### Core Resources & Actions

| Resource | Actions | Description |
|----------|---------|-------------|
| `User` | `create`, `read`, `update`, `delete`, `list` | User CRUD operations |
| `User` | `disable`, `enable` | Account status management |
| `User` | `reset-password` | Password management |
| `AdminUser` | `create`, `read`, `update`, `delete`, `list` | Admin user management |
| `Policy` | `read`, `list` | Policy viewing |

### Action Matrix by User Type

| Action | End User (Self) | End User (Others) | Admin |
|--------|-----------------|-------------------|-------|
| `User:read` | ✓ | ✗ | ✓ |
| `User:update` | ✓ (limited) | ✗ | ✓ |
| `User:delete` | ✗ | ✗ | ✓ |
| `User:disable` | ✗ | ✗ | ✓ |
| `User:enable` | ✗ | ✗ | ✓ |
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
| User disabled/enabled | All entries for user |
| User attribute change | All entries for user |
| Policy update | Full cache flush |

### Failure Mode

**Policy:** Fail-Closed

If AVP is unavailable:

- Authorization requests return **denied**
- Cached decisions (within TTL) may be used
- Error logged with high severity
- Alert triggered

---

## 6. User Lifecycle Management

### User States (Cognito-Based)

| State | Cognito Status | Description |
|-------|----------------|-------------|
| `UNCONFIRMED` | User created, not verified | Awaiting email verification |
| `CONFIRMED` | Email verified | User confirmed but may need password change |
| `FORCE_CHANGE_PASSWORD` | Admin-created user | Must change temporary password |
| `ENABLED` | Account active | Can authenticate |
| `DISABLED` | Account disabled | Cannot authenticate |
| `DELETED` | User deleted | Permanently removed |

### Simplified State Model

For API responses, we abstract Cognito states:

| API State | Cognito States | Can Authenticate |
|-----------|----------------|------------------|
| `Unverified` | `UNCONFIRMED` | No |
| `PasswordChangeRequired` | `FORCE_CHANGE_PASSWORD` | Limited |
| `Active` | `CONFIRMED` + `Enabled=true` | Yes |
| `Disabled` | `Enabled=false` | No |

### State Transitions

```
┌─────────────┐     verify      ┌─────────┐
│ Unverified  │────────────────▶│ Active  │
└─────────────┘                 └─────────┘
                                    │  ▲
                              disable│  │enable
                                    ▼  │
                                ┌─────────┐
                                │Disabled │
                                └─────────┘
                                    │
                                    │ delete
                                    ▼
                                ┌─────────┐
                                │ Deleted │ (permanent)
                                └─────────┘
```

### Valid State Transitions

| From | To | Action | Who Can Perform |
|------|----|--------|-----------------|
| `Unverified` | `Active` | Email verification | User |
| `PasswordChangeRequired` | `Active` | Password change | User |
| `Active` | `Disabled` | Disable account | Admin |
| `Disabled` | `Active` | Enable account | Admin |
| `Active` | `Deleted` | Delete user | Admin |
| `Disabled` | `Deleted` | Delete user | Admin |

### Lifecycle Triggers

- **API Only** — No time-based automatic transitions
- All state changes require explicit API calls
- Admin authorization required for disable/enable/delete

### Deletion Behavior

| Aspect | Behavior |
|--------|----------|
| Delete type | **Hard delete** (permanent) |
| Data retention | None (user data removed from Cognito) |
| Recovery | **Not possible** |
| Tokens | Immediately invalid |

> ⚠️ **POC Limitation:** Deleted users cannot be recovered. For production, consider adding DynamoDB for soft delete capability.

---

## 7. Service-to-Service Authentication

### Approach

**AWS IAM Roles** — Services assume IAM roles, requests signed with AWS Signature V4.

```
┌────────────────────────┐         ┌─────────────────────────┐
│ Order Service          │         │  User Management        │
│ (ECS Task)             │────────▶│  Service (Django/Nginx) │
│                        │         │                         │
│ IAM Role:              │         │  IAM Auth:              │
│ order-service-role     │         │  Verify IAM signature   │
└────────────────────────┘         └─────────────────────────┘
```

### IAM Roles per Service

| Service | IAM Role | Allowed Actions |
|---------|----------|-----------------|
| Order Service | `order-service-role` | `User:read`, authorization checks |
| Notification Service | `notification-service-role` | `User:read` |
| Admin Dashboard | `admin-dashboard-role` | All `User:*` and `AdminUser:*` |

---

## 8. API Design

**REST API** with URL path versioning (`/v1/...`) providing authentication, authorization, and user management endpoints.

**Key endpoints:**
- Authentication: `/auth/register`, `/auth/login`, `/auth/mfa/verify`
- Authorization: `/authorize`, `/authorize/batch` (IAM-authenticated)
- User Management: `/users` (CRUD operations, admin-only)
- Self-Service: `/me` (profile management)

**See:** [api-specifications.md](./api-specifications.md)

---

## 9. Rate Limiting

**Nginx-based rate limiting** with progressive lockout for authentication failures (3 failures = 30s lockout, escalating to 24 hours).

**Key limits:**
- Authentication: 20 requests/min per IP (5 req/min for password reset)
- Authorization: 1000 checks/min per IP
- User management: 100 requests/min per IP

**Implementation:**
- Nginx limit_req zones with burst capacity
- Per-IP rate limiting enforced at reverse proxy layer
- Connection limiting (10 concurrent connections per IP)

**See:** [api-specifications.md](./api-specifications.md)

---

## 10. Error Handling

**Standardized JSON error format** with error codes, human-readable messages, and retry guidance.

**Error categories:**
- 401: Authentication errors (TOKEN_EXPIRED, INVALID_CREDENTIALS)
- 403: Authorization errors (USER_DISABLED, AUTHORIZATION_DENIED)
- 400/422: Validation errors (INVALID_EMAIL_FORMAT, PASSWORD_TOO_WEAK)
- 429: Rate limiting (RATE_LIMIT_EXCEEDED, ACCOUNT_LOCKED)
- 5xx: Service errors (INTERNAL_ERROR, DEPENDENCY_UNAVAILABLE)

**See:** [api-specifications.md](./api-specifications.md)

---

## 11. Scale & Non-Functional Expectations

### Expected Scale (POC Assumptions)

| Metric | Target |
|--------|--------|
| Total users | ~1,000,000 |
| Concurrent sessions | ~10,000 |
| Tenants | Single |
| Authorization checks/second | ~1,000 |

### Cognito Limits

| Limit | Default | Notes |
|-------|---------|-------|
| User pools per account | 1,000 | Sufficient |
| Users per pool | 40,000,000 | Sufficient |
| API rate limits | Varies | May need to request increase |

### Performance Targets

| Operation | Latency Target (p99) |
|-----------|---------------------|
| Authorization check (cached) | < 10ms |
| Authorization check (uncached) | < 100ms |
| Token validation | < 20ms |
| User profile read | < 100ms |
| User profile update | < 200ms |
| Login (no MFA) | < 500ms |
| Login (with MFA) | < 1000ms |

### Availability

- High availability provided by AWS managed services
- Single AWS region (acceptable for POC)
- Target: 99.9% uptime

---

## 12. Security & Compliance

### Security Controls

| Control | Implementation |
|---------|----------------|
| Authentication | Amazon Cognito with MFA |
| Authorization | Amazon Verified Permissions (ABAC) |
| Transport Security | TLS 1.2+ |
| Service-to-Service Auth | AWS IAM Roles |
| Rate Limiting | Nginx |
| Input Validation | Schema validation on all inputs |
| Password Storage | Cognito (bcrypt) |

### Password Policy (Cognito)

| Requirement | Value |
|-------------|-------|
| Minimum length | 12 characters |
| Require uppercase | Yes |
| Require lowercase | Yes |
| Require numbers | Yes |
| Require special characters | Yes |
| Temporary password expiry | 7 days |

### MFA Configuration

| Setting | Value |
|---------|-------|
| MFA Type | TOTP (app-based) |
| Enforcement - End Users | Optional |
| Enforcement - Admins | Required |

### Immediate Revocation

User enabled status checked on every authenticated request:

```
JWT Valid + User Enabled → Allow
JWT Valid + User Disabled → Deny (403 USER_DISABLED)
```

---

## 13. Observability

### Tooling

| Tool | Purpose |
|------|---------|
| Amazon CloudWatch | Metrics and logs |
| AWS CloudTrail | API audit trail |
| AWS X-Ray | Distributed tracing |

### Key Metrics

| Category | Metrics |
|----------|---------|
| Authentication | Login success/failure rates, MFA usage |
| Authorization | Latency (p50, p95, p99), cache hit rate |
| Cognito | API call counts, throttling |
| System | Error rates, request latency |

---

## 14. Technology Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | Python (Django) |
| User Data Store | Amazon Cognito |
| Authorization | Amazon Verified Permissions |
| Cache | Amazon ElastiCache (Redis) |
| Reverse Proxy | Nginx |
| Compute | AWS Lambda or Amazon ECS |
| Monitoring | Amazon CloudWatch, AWS X-Ray |

### What We Don't Need

| Component | Reason |
|-----------|--------|
| DynamoDB | User data in Cognito |
| RDS | No relational data |
| Custom user database | Cognito handles everything |

---

## 15. POC Success Criteria

This POC is considered successful if it demonstrates:

- [ ] **Scalable Design** — Architecture supports 1M users, 10K concurrent sessions
- [ ] **Security-First Approach** — MFA, ABAC, fail-closed authorization
- [ ] **Clean Service Boundaries** — Cognito/AVP abstracted behind unified API
- [ ] **Operational Readiness** — Error handling, rate limiting, observability
- [ ] **Simplicity** — Minimal infrastructure using managed services

---

## 16. Future Considerations

Features **not implemented** in POC but may be needed for production:

| Feature | Limitation | Future Solution |
|---------|------------|-----------------|
| Soft delete | Users permanently deleted | Add DynamoDB for state tracking |
| User recovery | Cannot restore deleted users | Add DynamoDB for soft delete |
| State audit | No tracking of who disabled whom | Add DynamoDB or audit service |
| Multi-tenancy | Single tenant only | Add tenant_id to schema |
| Custom states | Only enabled/disabled | Add DynamoDB for custom states |
| Rich queries | Limited Cognito queries | Add DynamoDB or search service |
| Federated identity | Not configured | Add SAML/OIDC to Cognito |

---
