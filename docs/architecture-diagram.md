# Fortress Architecture Diagram

## System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          External Systems & Clients                              │
│                                                                                   │
│  ┌──────────────────┐         ┌──────────────────┐      ┌──────────────────┐   │
│  │  End User Apps   │         │  Microservices   │      │  Admin Portal    │   │
│  │  (Web/Mobile)    │         │  (IAM Auth)      │      │  (Admin Users)   │   │
│  └────────┬─────────┘         └────────┬─────────┘      └────────┬─────────┘   │
│           │                            │                          │              │
│           │ JWT Auth                   │ IAM SigV4               │ JWT Auth     │
│           │                            │                          │              │
└───────────┼────────────────────────────┼──────────────────────────┼──────────────┘
            │                            │                          │
            └────────────────────────────┼──────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│                         API Gateway (Amazon API Gateway)                         │
│                        Rate Limiting • Request Validation                        │
│                                                                                   │
└───────────────────────────────────────┬───────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│                         Fortress User Management Service                         │
│                              (Django REST Framework)                             │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      Fortress User Management Service                             │
│                                                                                    │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                           API Layer (Django REST)                          │  │
│  │                                                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │
│  │  │ Authentication│  │Authorization │  │     Users    │  │     /me      │ │  │
│  │  │   Endpoints  │  │  Endpoints   │  │  Endpoints   │  │  Endpoints   │ │  │
│  │  │              │  │              │  │              │  │              │ │  │
│  │  │ • /register  │  │ • /authorize │  │ • GET /users │  │ • GET /me    │ │  │
│  │  │ • /login     │  │ • /batch     │  │ • POST /users│  │ • PUT /me    │ │  │
│  │  │ • /logout    │  │              │  │ • PUT /users │  │ • /mfa/setup │ │  │
│  │  │ • /mfa/*     │  │              │  │ • DELETE     │  │              │ │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │  │
│  └─────────┼──────────────────┼──────────────────┼──────────────────┼─────────┘  │
│            │                  │                  │                  │            │
│  ┌─────────▼──────────────────▼──────────────────▼──────────────────▼─────────┐  │
│  │                         Middleware Layer                                    │  │
│  │                                                                              │  │
│  │  ┌──────────────────────┐         ┌─────────────────────────────────────┐  │  │
│  │  │ UserStatusMiddleware │         │   AuthorizationMiddleware           │  │  │
│  │  │ - Validate JWT       │         │   - Check permissions via AVP       │  │  │
│  │  │ - Check user enabled │         │   - Cache authorization decisions   │  │  │
│  │  │ - Cache user status  │         │   - Fail-closed model               │  │  │
│  │  └──────────────────────┘         └─────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│            │                  │                  │                  │            │
│  ┌─────────▼──────────────────▼──────────────────▼──────────────────▼─────────┐  │
│  │                         Service Layer                                        │  │
│  │                                                                              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │  AuthService │  │ AuthzService │  │ UserService  │  │ CacheService │   │  │
│  │  │              │  │              │  │              │  │              │   │  │
│  │  │ - register() │  │ - authorize()│  │ - create()   │  │ - get()      │   │  │
│  │  │ - login()    │  │ - batch()    │  │ - list()     │  │ - set()      │   │  │
│  │  │ - logout()   │  │ - cache()    │  │ - update()   │  │ - delete()   │   │  │
│  │  │ - mfa()      │  │              │  │ - delete()   │  │ - pattern()  │   │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │  │
│  └─────────┼──────────────────┼──────────────────┼──────────────────┼─────────┘  │
│            │                  │                  │                  │            │
│  ┌─────────▼──────────────────▼──────────────────▼──────────────────▼─────────┐  │
│  │                      AWS SDK Client Layer                                   │  │
│  │                                                                              │  │
│  │  ┌──────────────┐       ┌──────────────┐              ┌──────────────┐     │  │
│  │  │CognitoClient │       │  AVPClient   │              │ Redis Client │     │  │
│  │  │              │       │              │              │              │     │  │
│  │  │ - sign_up()  │       │ - authorize()│              │ - get/set    │     │  │
│  │  │ - login()    │       │ - context    │              │ - del/scan   │     │  │
│  │  │ - mfa()      │       │ - entities   │              │ - ttl config │     │  │
│  │  │ - tokens()   │       │              │              │              │     │  │
│  │  └──────┬───────┘       └──────┬───────┘              └──────┬───────┘     │  │
│  └─────────┼──────────────────────┼─────────────────────────────┼─────────────┘  │
│            │                      │                              │                │
└────────────┼──────────────────────┼──────────────────────────────┼────────────────┘
             │                      │                              │
             ▼                      ▼                              ▼
┌──────────────────┐   ┌──────────────────────┐      ┌──────────────────────┐
│  AWS Cognito     │   │  Amazon Verified     │      │  Amazon ElastiCache  │
│  User Pools      │   │  Permissions (AVP)   │      │  (Redis)             │
│                  │   │                      │      │                      │
│ • User Store     │   │ • Cedar Policies     │      │ • Authorization      │
│ • Authentication │   │ • ABAC Evaluation    │      │ • User Status        │
│ • MFA            │   │ • Policy Store       │      │ • JWKS Keys          │
│ • JWT Tokens     │   │ • Context-based      │      │ • TTL: 30-60s        │
└──────────────────┘   └──────────────────────┘      └──────────────────────┘
```

---

## Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Request Flow Overview                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

Client Request
      │
      ▼
┌──────────────────────────────────────┐
│     API Gateway (Rate Limiting)      │  ← 5 req/min (auth), 100 req/min (users)
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│      Django URL Router (urls.py)     │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│    Middleware Chain                  │
│  1. UserStatusMiddleware             │  ← Validate JWT & check user status
│  2. AuthorizationMiddleware          │  ← Check AVP permissions (if needed)
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│    View Layer (DRF ViewSets)         │  ← Request handling & serialization
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│    Service Layer                     │  ← Business logic
│  - AuthService                       │
│  - AuthzService                      │
│  - UserService                       │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│    AWS Client Layer                  │  ← AWS SDK calls
│  - CognitoClient                     │
│  - AVPClient                         │
│  - Redis Client                      │
└──────────────┬───────────────────────┘
               │
               ▼
         AWS Services
```

---

## Authentication Flow

```
┌────────────┐                                                    ┌──────────────┐
│   Client   │                                                    │   Cognito    │
└─────┬──────┘                                                    └──────┬───────┘
      │                                                                  │
      │ 1. POST /auth/register                                          │
      │    { email, password, name }                                    │
      ├──────────────────────────────────────────────────────────┐      │
      │                                                           │      │
      │                                                           ▼      │
      │                                              ┌────────────────────┴─────┐
      │                                              │  CognitoClient.sign_up() │
      │                                              │  - Create user           │
      │                                              │  - Send verification     │
      │                                              └────────────┬─────────────┘
      │                                                           │      ▲
      │ 2. Email sent to user                                    │      │
      │◄──────────────────────────────────────────────────────────┘      │
      │                                                                  │
      │ 3. POST /auth/verify-email                                      │
      │    { email, code }                                              │
      ├──────────────────────────────────────────────────────────────────┤
      │                                              confirm_sign_up()   │
      │                                                                  │
      │ 4. POST /auth/login                                             │
      │    { email, password }                                          │
      ├──────────────────────────────────────────────────────────────────┤
      │                                              initiate_auth()     │
      │                                                                  │
      │ 5a. MFA Required → { session, mfa_required }                    │
      │◄─────────────────────────────────────────────────────────────────┤
      │                                                                  │
      │ 5b. POST /auth/mfa/verify                                       │
      │     { session, mfa_code }                                       │
      ├──────────────────────────────────────────────────────────────────┤
      │                                      respond_to_auth_challenge() │
      │                                                                  │
      │ 6. { access_token, id_token, refresh_token }                    │
      │◄─────────────────────────────────────────────────────────────────┤
      │                                                                  │
      │ 7. Authenticated requests with JWT in header                    │
      │    Authorization: Bearer <access_token>                         │
      ├──────────────────────────────────────────────────────────────────┤
      │                                              validate JWT        │
      │                                                                  │
      │ 8. POST /auth/token/refresh                                     │
      │    { refresh_token }                                            │
      ├──────────────────────────────────────────────────────────────────┤
      │                                              refresh_tokens()    │
      │                                                                  │
      │ 9. { access_token, id_token }                                   │
      │◄─────────────────────────────────────────────────────────────────┤
      │                                                                  │
      │ 10. POST /auth/logout                                           │
      │     { access_token }                                            │
      ├──────────────────────────────────────────────────────────────────┤
      │                                              global_sign_out()   │
      │                                                                  │
      │ 11. { success: true }                                           │
      │◄─────────────────────────────────────────────────────────────────┤
      │                                                                  │
```

---

## Authorization Flow (ABAC with Amazon Verified Permissions)

```
┌────────────┐                                ┌────────────┐              ┌─────────┐
│   Client   │                                │  Fortress  │              │   AVP   │
└─────┬──────┘                                └──────┬─────┘              └────┬────┘
      │                                              │                         │
      │ 1. Authenticated request                     │                         │
      │    Authorization: Bearer <jwt>               │                         │
      ├──────────────────────────────────────────────▶                         │
      │                                              │                         │
      │                              2. Middleware extracts user context       │
      │                                 - principal_id (user_id)                │
      │                                 - user_type (admin/end_user)            │
      │                                 - action (update_user)                  │
      │                                 - resource (user:{id})                  │
      │                                              │                         │
      │                              3. Check cache                            │
      │                                 key: authz:{principal}:{action}:...    │
      │                                              │                         │
      │                              ┌───────────────▼─────────────┐           │
      │                              │  Cache Hit?                 │           │
      │                              │  - Yes → Return decision    │           │
      │                              │  - No  → Query AVP          │           │
      │                              └───────────────┬─────────────┘           │
      │                                              │                         │
      │                              4. Query AVP (if cache miss)              │
      │                                              ├─────────────────────────▶
      │                                              │  is_authorized(         │
      │                                              │    principal={          │
      │                                              │      entityType: "User" │
      │                                              │      entityId: "123"    │
      │                                              │    },                   │
      │                                              │    action={             │
      │                                              │      actionType: "..."  │
      │                                              │      actionId: "update" │
      │                                              │    },                   │
      │                                              │    resource={...},      │
      │                                              │    context={...}        │
      │                                              │  )                      │
      │                                              │                         │
      │                                              │                    5. Evaluate │
      │                                              │                       Cedar    │
      │                                              │                       Policies │
      │                                              │                         │
      │                              6. Decision     │◄─────────────────────────
      │                                 { decision: "ALLOW" }                  │
      │                                              │                         │
      │                              7. Cache decision (60s TTL)               │
      │                                              │                         │
      │                              8. Process request or deny                │
      │                                              │                         │
      │ 9. Response                                  │                         │
      │◄──────────────────────────────────────────────                         │
      │                                                                        │
```

### Cedar Policy Example

```cedar
// Allow admins to manage all users
permit (
  principal is User,
  action in [User::Action::"create_user", User::Action::"update_user", 
             User::Action::"delete_user"],
  resource is User
)
when {
  principal.user_type == "admin"
};

// Allow users to update their own profile
permit (
  principal is User,
  action == User::Action::"update_user",
  resource is User
)
when {
  principal.id == resource.id &&
  principal.user_type == "end_user"
};
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Data Storage & Flow                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          AWS Cognito User Pool                                │
│                          (Primary User Store)                                 │
│                                                                               │
│  User Attributes:                                                             │
│  • sub (UUID) - Primary ID                                                    │
│  • email (unique) - User identifier                                           │
│  • email_verified - Verification status                                       │
│  • given_name - First name                                                    │
│  • family_name - Last name                                                    │
│  • phone_number - Contact (E.164)                                             │
│  • custom:user_type - "admin" or "end_user"                                   │
│  • enabled - Account status (true/false)                                      │
│                                                                               │
│  Authentication Data:                                                         │
│  • Password hash (bcrypt)                                                     │
│  • MFA settings (TOTP secret)                                                 │
│  • Token metadata (issued, revoked)                                           │
└─────────────────────────────────────┬─────────────────────────────────────────┘
                                      │
                                      │ User CRUD operations
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │   CognitoClient          │
                        │   - AdminCreateUser      │
                        │   - AdminGetUser         │
                        │   - AdminUpdateUser      │
                        │   - AdminDeleteUser      │
                        │   - AdminEnableUser      │
                        │   - AdminDisableUser     │
                        └──────────────────────────┘
                                      │
                                      │
┌─────────────────────────────────────┼─────────────────────────────────────────┐
│                                     │                                          │
│                      Redis Cache (ElastiCache)                                │
│                                                                                │
│  Cache Keys:                                           TTL                    │
│  • authz:{principal}:{action}:{resource}  ────────────  60s                   │
│  • user_status:{user_id}                  ────────────  30s                   │
│  • jwks:{cognito_pool}                    ────────────  24h                   │
│                                                                                │
│  Data Format: JSON                                                            │
│  Compression: zlib                                                            │
│  Max Connections: 50                                                          │
│                                                                                │
└────────────────────────────────────────────────────────────────────────────────┘


┌────────────────────────────────────────────────────────────────────────────────┐
│                  Amazon Verified Permissions (AVP)                             │
│                       Policy Store                                             │
│                                                                                 │
│  Cedar Policies:                                                                │
│  • Admin access policies                                                        │
│  • User self-service policies                                                   │
│  • Role-based access control                                                    │
│  • Attribute-based conditions                                                   │
│                                                                                 │
│  Entities:                                                                      │
│  • Users (principal)                                                            │
│  • Resources (user records)                                                     │
│  • Actions (CRUD operations)                                                    │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Production Deployment                               │
└─────────────────────────────────────────────────────────────────────────────────┘

                                   ┌──────────────┐
                                   │   Route 53   │
                                   │     DNS      │
                                   └──────┬───────┘
                                          │
                                          ▼
                            ┌──────────────────────────┐
                            │   Application Load       │
                            │   Balancer (ALB)         │
                            │   - SSL/TLS Termination  │
                            │   - Health Checks        │
                            └──────────┬───────────────┘
                                       │
                                       ▼
                         ┌──────────────────────────────┐
                         │   Amazon API Gateway         │
                         │   - Rate Limiting            │
                         │   - Request Validation       │
                         │   - API Keys                 │
                         │   - CloudWatch Logs          │
                         └──────────┬───────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │ AWS Lambda   │      │ AWS Lambda   │      │ AWS Lambda   │
    │ or           │      │ or           │      │ or           │
    │ ECS Fargate  │      │ ECS Fargate  │      │ ECS Fargate  │
    │              │      │              │      │              │
    │ Django App   │      │ Django App   │      │ Django App   │
    │ Instance 1   │      │ Instance 2   │      │ Instance N   │
    └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
           │                     │                     │
           └─────────────────────┼─────────────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 │               │               │
                 ▼               ▼               ▼
        ┌────────────┐  ┌────────────┐  ┌────────────┐
        │  Cognito   │  │    AVP     │  │ElastiCache │
        │ User Pools │  │   Policy   │  │  (Redis)   │
        │            │  │   Store    │  │            │
        │ Multi-AZ   │  │  Regional  │  │ Multi-AZ   │
        └────────────┘  └────────────┘  └────────────┘
                 │               │               │
                 └───────────────┼───────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  CloudWatch     │
                        │  - Logs         │
                        │  - Metrics      │
                        │  - Alarms       │
                        └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  X-Ray          │
                        │  (Distributed   │
                        │   Tracing)      │
                        └─────────────────┘
```

### Deployment Options

**Option 1: AWS Lambda (Serverless)**
- Auto-scaling based on demand
- Pay per request
- Cold start considerations
- Max 15-minute execution time
- Best for variable traffic

**Option 2: Amazon ECS Fargate**
- Container-based deployment
- Predictable performance
- Long-running processes
- Easier debugging
- Best for consistent traffic

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Security Layers                                       │
└─────────────────────────────────────────────────────────────────────────────────┘

Layer 1: Network Security
┌────────────────────────────────────────────────────────────────┐
│  • VPC with private subnets                                    │
│  • Security Groups (least privilege)                           │
│  • NACLs for network-level filtering                           │
│  • No public internet access for app servers                   │
└────────────────────────────────────────────────────────────────┘

Layer 2: API Gateway Security
┌────────────────────────────────────────────────────────────────┐
│  • TLS 1.2+ only                                               │
│  • API Keys for service-to-service                             │
│  • Request size limits (1MB)                                   │
│  • Rate limiting per IP/API key                                │
│  • CloudWatch logging (all requests)                           │
└────────────────────────────────────────────────────────────────┘

Layer 3: Authentication
┌────────────────────────────────────────────────────────────────┐
│  • JWT validation (RS256)                                      │
│  • Token expiry checks (15 min access, 7 day refresh)          │
│  • MFA enforcement (TOTP)                                      │
│  • Password policy (12+ chars, complexity)                     │
│  • Email verification required                                 │
└────────────────────────────────────────────────────────────────┘

Layer 4: Authorization
┌────────────────────────────────────────────────────────────────┐
│  • ABAC via Amazon Verified Permissions                        │
│  • Fail-closed model (deny on error)                           │
│  • Context-aware decisions                                     │
│  • Cached for performance (60s TTL)                            │
│  • Audit logging for all decisions                             │
└────────────────────────────────────────────────────────────────┘

Layer 5: Data Protection
┌────────────────────────────────────────────────────────────────┐
│  • Encryption at rest (AWS managed keys)                       │
│  • Encryption in transit (TLS)                                 │
│  • No sensitive data in logs                                   │
│  • PII in Cognito only (not in Django DB)                      │
│  • Token revocation on logout/disable                          │
└────────────────────────────────────────────────────────────────┘

Layer 6: Application Security
┌────────────────────────────────────────────────────────────────┐
│  • Input validation (DRF serializers)                          │
│  • SQL injection protection (ORM)                              │
│  • XSS protection (CSP headers)                                │
│  • CSRF protection (Django middleware)                         │
│  • Rate limiting (progressive lockout)                         │
└────────────────────────────────────────────────────────────────┘

Layer 7: Monitoring & Incident Response
┌────────────────────────────────────────────────────────────────┐
│  • CloudWatch alarms (failed auth, high latency)               │
│  • X-Ray tracing (request flow)                                │
│  • Audit logs (all operations)                                 │
│  • Automated alerts (PagerDuty/SNS)                            │
│  • Runbooks for common incidents                               │
└────────────────────────────────────────────────────────────────┘
```

---

## Scalability Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         Horizontal Scaling Strategy                              │
└─────────────────────────────────────────────────────────────────────────────────┘

Target: 1M users, 10K concurrent sessions

Component Scaling:

┌──────────────────────────────────────────────────────────────────────┐
│ Django Application Servers (Compute)                                 │
│ • Lambda: Auto-scale 0-1000 concurrent executions                    │
│ • ECS Fargate: Auto-scale 10-100 tasks based on CPU/memory          │
│ • Metric: Target 70% CPU, 80% memory utilization                    │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ AWS Cognito (Managed - Auto-scales)                                  │
│ • No instance management required                                    │
│ • Handles millions of users automatically                            │
│ • Regional service with multi-AZ replication                         │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ Amazon Verified Permissions (Managed - Auto-scales)                  │
│ • Policy store replicated across AZs                                 │
│ • Automatic scaling for evaluation requests                          │
│ • Sub-100ms latency for most evaluations                             │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ ElastiCache Redis (Caching Layer)                                    │
│ • Single node: 5GB (dev/test)                                        │
│ • Production: Multi-AZ with read replicas                            │
│ • Cluster mode: 3-5 shards for >50K ops/sec                          │
│ • Automatic failover enabled                                         │
└──────────────────────────────────────────────────────────────────────┘

Performance Characteristics:

Authentication Endpoints:
- Throughput: 100 TPS per instance
- Latency: p50=200ms, p99=500ms
- Bottleneck: Cognito API calls

Authorization Endpoints:
- Throughput: 1000 TPS per instance (cached)
- Latency: p50=10ms (cache hit), p99=100ms (AVP call)
- Bottleneck: AVP evaluation (uncached)

User Management Endpoints:
- Throughput: 50 TPS per instance
- Latency: p50=150ms, p99=400ms
- Bottleneck: Cognito list operations
```

---

## Component Breakdown

### Django Apps

```
fortress/
├── apps/authentication/       # Authentication Module
│   ├── views.py              # Register, login, MFA, logout endpoints
│   ├── backends.py           # JWT authentication backend
│   ├── middleware.py         # User status & authorization middleware
│   ├── serializers.py        # Request/response serializers
│   └── services/
│       ├── auth_service.py   # Authentication business logic
│       └── cognito_client.py # AWS Cognito SDK wrapper
│
├── apps/authorization/        # Authorization Module
│   ├── views.py              # Authorization check endpoints
│   ├── serializers.py        # Authorization request/response
│   └── services/
│       ├── authz_service.py  # Authorization business logic
│       ├── avp_client.py     # Amazon VP SDK wrapper
│       └── cache_service.py  # Redis caching layer
│
└── apps/users/               # User Management Module
    ├── views.py              # User CRUD & profile endpoints
    ├── serializers.py        # User data serializers
    └── services/
        └── user_service.py   # User management business logic
```

### Key Files & Responsibilities

**Settings & Configuration**
- `fortress/settings.py` - Django settings, AWS config, cache config
- `.env` - Environment variables (secrets, endpoints)

**URL Routing**
- `fortress/urls.py` - Main URL configuration
- `apps/*/urls.py` - App-specific URL patterns

**Middleware**
- `UserStatusMiddleware` - Validates JWT, checks user enabled status
- `AuthorizationMiddleware` - Enforces AVP permissions

**Services**
- `CognitoClient` - AWS Cognito operations
- `AVPClient` - Amazon Verified Permissions operations
- `CacheService` - Redis caching operations
- `AuthService` - Authentication business logic
- `AuthzService` - Authorization business logic
- `UserService` - User management business logic

---

## Technology Stack Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                      Technology Choices                         │
├─────────────────────────────────────────────────────────────────┤
│ Category          │ Technology                │ Rationale        │
├───────────────────┼───────────────────────────┼─────────────────┤
│ Web Framework     │ Django 5.x + DRF          │ Rapid dev, ORM  │
│ Language          │ Python 3.11+              │ Ecosystem       │
│ Package Manager   │ uv                        │ Fast, modern    │
│ User Store        │ AWS Cognito               │ Managed, secure │
│ Authorization     │ Amazon VP (Cedar)         │ ABAC, scalable  │
│ Cache             │ ElastiCache (Redis)       │ Low latency     │
│ API Gateway       │ Amazon API Gateway        │ Rate limiting   │
│ Compute           │ Lambda / ECS Fargate      │ Serverless/containers │
│ Monitoring        │ CloudWatch + X-Ray        │ AWS native      │
│ Code Quality      │ Ruff                      │ Fast linting    │
│ Testing           │ pytest + hypothesis       │ Property tests  │
└───────────────────┴───────────────────────────┴─────────────────┘
```

---

## API Endpoints Reference

### Authentication APIs
```
POST   /v1/auth/register              - Self-registration
POST   /v1/auth/verify-email          - Email verification
POST   /v1/auth/login                 - User login
POST   /v1/auth/mfa/verify            - MFA verification
POST   /v1/auth/token/refresh         - Refresh access token
POST   /v1/auth/logout                - Logout & revoke tokens
POST   /v1/auth/password/forgot       - Initiate password reset
POST   /v1/auth/password/reset        - Complete password reset
```

### Authorization APIs
```
POST   /v1/authorize                  - Single authorization check
POST   /v1/authorize/batch            - Batch authorization checks
```

### User Management APIs
```
GET    /v1/users                      - List users (admin)
POST   /v1/users                      - Create user (admin)
GET    /v1/users/{id}                 - Get user by ID
PUT    /v1/users/{id}                 - Update user
DELETE /v1/users/{id}                 - Delete user (hard delete)
POST   /v1/users/{id}/disable         - Disable user account
POST   /v1/users/{id}/enable          - Enable user account
```

### Self-Service APIs
```
GET    /v1/me                         - Get own profile
PUT    /v1/me                         - Update own profile
POST   /v1/me/mfa/setup               - Setup/verify MFA
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Handling Strategy                       │
└─────────────────────────────────────────────────────────────────┘

Application Error
      │
      ▼
┌─────────────────────────┐
│ Exception Raised        │
│ (AuthError, UsersError, │
│  AuthzError)            │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Custom Exception Handler│
│ - Map to HTTP status    │
│ - Format error response │
│ - Log error details     │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ Standardized Response   │
│ {                       │
│   "error": {            │
│     "code": "...",      │
│     "message": "...",   │
│     "details": {}       │
│   },                    │
│   "retry": {            │
│     "retryable": bool,  │
│     "retry_after": sec  │
│   }                     │
│ }                       │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│ CloudWatch Logs         │
│ - Request ID            │
│ - Error details         │
│ - Stack trace           │
│ - User context          │
└─────────────────────────┘
```

---

## Cache Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                        Redis Cache Keys                          │
└─────────────────────────────────────────────────────────────────┘

Authorization Decisions:
Key: authz:{principal_id}:{action}:{resource_type}:{resource_id}
TTL: 60 seconds
Value: { "decision": "ALLOW|DENY", "timestamp": epoch }

User Status:
Key: user_status:{user_id}
TTL: 30 seconds
Value: { "enabled": true|false, "timestamp": epoch }

JWKS Keys:
Key: jwks:{cognito_pool_id}
TTL: 86400 seconds (24 hours)
Value: { "keys": [...], "timestamp": epoch }

Cache Invalidation:
- User disabled → Delete user_status:{user_id}
- User deleted → Delete user_status:{user_id} AND authz:{user_id}:*
- Policy update → Delete authz:* (pattern-based)
```

---

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────────┐
│                    Key Metrics to Monitor                        │
└─────────────────────────────────────────────────────────────────┘

Application Metrics:
• Request rate (TPS)
• Response time (p50, p95, p99)
• Error rate (5xx, 4xx)
• Authentication success rate
• Authorization cache hit rate
• Active user sessions

AWS Service Metrics:
• Cognito API throttles
• AVP evaluation latency
• Redis CPU/memory utilization
• Lambda cold starts
• ECS task CPU/memory

Business Metrics:
• Daily/monthly active users
• Registration rate
• MFA adoption rate
• Failed login attempts (security)

Alarms:
• Error rate > 1%
• p99 latency > 1s
• Cognito throttles
• Redis connection failures
• Authorization cache miss rate > 50%
```

---

## Summary

The **Fortress User Management Service** architecture demonstrates:

1. **Separation of Concerns**
   - Clear boundaries between authentication, authorization, and user management
   - Service layer abstracts AWS SDK calls
   - Middleware handles cross-cutting concerns

2. **Security-First Design**
   - Multi-layered security (network, API gateway, authentication, authorization)
   - Fail-closed authorization model
   - MFA support with TOTP
   - JWT-based stateless authentication

3. **Scalability**
   - Horizontal scaling via AWS managed services
   - Caching for performance (Redis)
   - Stateless application servers
   - Target: 1M users, 10K concurrent sessions

4. **Operational Excellence**
   - Comprehensive monitoring and alerting
   - Standardized error handling
   - Distributed tracing with X-Ray
   - CloudWatch logs for debugging

5. **Cost Optimization**
   - Managed services minimize infrastructure overhead
   - Serverless options (Lambda) for variable traffic
   - Efficient caching reduces API calls

---

**Document Version**: 1.0  
**Last Updated**: December 26, 2024  
**Author**: Akshat Tamrakar
