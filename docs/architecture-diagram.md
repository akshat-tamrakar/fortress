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
│                            Nginx Reverse Proxy                                   │
│                   Rate Limiting • SSL/TLS • Security Headers                     │
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

## Component Diagram

### Service Boundaries & AWS Integrations

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          Fortress Service Boundary                               │
│                                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                        API Layer (Django REST Framework)                  │  │
│  │                                                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │  │
│  │  │ Authentication│  │Authorization │  │     Users    │  │   /me Self   │ │  │
│  │  │    Module    │  │    Module    │  │   Module     │  │   Service    │ │  │
│  │  │              │  │              │  │              │  │              │ │  │
│  │  │ • Register   │  │ • Authorize  │  │ • List Users │  │ • Get Profile│ │  │
│  │  │ • Login      │  │ • Batch      │  │ • Create     │  │ • Update Me  │ │  │
│  │  │ • MFA        │  │ • Cache Mgmt │  │ • Update     │  │ • MFA Setup  │ │  │
│  │  │ • Tokens     │  │              │  │ • Delete     │  │              │ │  │
│  │  │ • Logout     │  │              │  │ • Enable     │  │              │ │  │
│  │  │              │  │              │  │ • Disable    │  │              │ │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │  │
│  └─────────┼──────────────────┼──────────────────┼──────────────────┼─────────┘  │
│            │                  │                  │                  │            │
│  ┌─────────▼──────────────────▼──────────────────▼──────────────────▼─────────┐  │
│  │                            Middleware Layer                                 │  │
│  │                                                                              │  │
│  │  ┌──────────────────────────┐      ┌────────────────────────────────────┐  │  │
│  │  │ UserStatusMiddleware     │      │ AuthorizationMiddleware            │  │  │
│  │  │ ─────────────────────    │      │ ───────────────────────            │  │  │
│  │  │ • Validate JWT tokens    │      │ • Check AVP permissions            │  │  │
│  │  │ • Extract user context   │      │ • Cache authorization decisions    │  │  │
│  │  │ • Check user enabled     │      │ • Enforce access control           │  │  │
│  │  │ • Cache user status      │      │ • Fail-closed on errors            │  │  │
│  │  └──────────────────────────┘      └────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│            │                  │                  │                  │            │
│  ┌─────────▼──────────────────▼──────────────────▼──────────────────▼─────────┐  │
│  │                          Service Layer (Business Logic)                     │  │
│  │                                                                              │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐│  │
│  │  │  AuthService    │  │  AuthzService   │  │     UserService             ││  │
│  │  │  ────────────   │  │  ─────────────  │  │     ────────────            ││  │
│  │  │ • register()    │  │ • authorize()   │  │ • create_user()             ││  │
│  │  │ • login()       │  │ • batch_auth()  │  │ • get_user()                ││  │
│  │  │ • verify_mfa()  │  │ • check_cache() │  │ • list_users()              ││  │
│  │  │ • refresh()     │  │ • save_cache()  │  │ • update_user()             ││  │
│  │  │ • logout()      │  │ • invalidate()  │  │ • delete_user()             ││  │
│  │  │ • reset_pwd()   │  │                 │  │ • enable/disable_user()     ││  │
│  │  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────────────┘│  │
│  └───────────┼─────────────────────┼───────────────────────┼────────────────────┘  │
│              │                     │                       │                       │
│  ┌───────────▼─────────────────────▼───────────────────────▼────────────────────┐  │
│  │                        Client Integration Layer                              │  │
│  │                                                                               │  │
│  │  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────────────┐│  │
│  │  │ CognitoClient    │   │   AVPClient      │   │   CacheService           ││  │
│  │  │ ──────────────   │   │   ──────────     │   │   ────────────           ││  │
│  │  │ • sign_up()      │   │ • is_authorized()│   │ • get(key)               ││  │
│  │  │ • initiate_auth()│   │ • batch_auth()   │   │ • set(key, val, ttl)     ││  │
│  │  │ • verify_code()  │   │ • create_policy()│   │ • delete(key)            ││  │
│  │  │ • mfa_setup()    │   │ • get_policy()   │   │ • scan_pattern(pattern)  ││  │
│  │  │ • refresh_token()│   │ • put_entity()   │   │ • exists(key)            ││  │
│  │  │ • global_signout│   │                  │   │ • ttl(key)               ││  │
│  │  │ • admin_ops()    │   │                  │   │ • compress/decompress    ││  │
│  │  └────────┬─────────┘   └────────┬─────────┘   └──────────┬───────────────┘│  │
│  └───────────┼──────────────────────┼──────────────────────────┼────────────────┘  │
│              │                      │                          │                   │
└──────────────┼──────────────────────┼──────────────────────────┼───────────────────┘
               │                      │                          │
               │                      │                          │
    ┌──────────▼──────────┐  ┌────────▼─────────┐   ┌───────────▼──────────┐
    │                     │  │                  │   │                      │
    │  AWS Cognito        │  │  Amazon Verified │   │  Amazon ElastiCache  │
    │  User Pools         │  │  Permissions     │   │  (Redis)             │
    │                     │  │                  │   │                      │
    │ ┌─────────────────┐ │  │ ┌──────────────┐ │   │ ┌──────────────────┐ │
    │ │ User Directory  │ │  │ │ Policy Store │ │   │ │ Authorization    │ │
    │ │ • Authentication│ │  │ │ • Cedar      │ │   │ │ Cache            │ │
    │ │ • MFA Storage   │ │  │ │   Policies   │ │   │ │ TTL: 60s         │ │
    │ │ • Password Hash │ │  │ │ • ABAC Rules │ │   │ ├──────────────────┤ │
    │ │ • User Attrs    │ │  │ │ • Entities   │ │   │ │ User Status      │ │
    │ └─────────────────┘ │  │ │ • Contexts   │ │   │ │ Cache            │ │
    │                     │  │ └──────────────┘ │   │ │ TTL: 30s         │ │
    │ ┌─────────────────┐ │  │                  │   │ ├──────────────────┤ │
    │ │ Token Service   │ │  │ ┌──────────────┐ │   │ │ JWKS Keys        │ │
    │ │ • JWT Issuance  │ │  │ │ Evaluation   │ │   │ │ Cache            │ │
    │ │ • Refresh       │ │  │ │ Engine       │ │   │ │ TTL: 24h         │ │
    │ │ • Validation    │ │  │ │ • Real-time  │ │   │ └──────────────────┘ │
    │ │ • Revocation    │ │  │ │ • <100ms     │ │   │                      │
    │ └─────────────────┘ │  │ │ • Scalable   │ │   │ Connection Pool:     │
    │                     │  │ └──────────────┘ │   │ • Max: 50            │
    │ Regional Service    │  │ Regional Service │   │ • Cluster Mode       │
    │ Multi-AZ Replicated │  │ Multi-AZ         │   │ • Multi-AZ           │
    └─────────────────────┘  └──────────────────┘   └──────────────────────┘
```

### Service Integration Points

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      AWS Service Integration Details                      │
└──────────────────────────────────────────────────────────────────────────┘

Authentication Flow Integration:
┌─────────────────────────────────────────────────────────────────────────┐
│ Fortress ←→ AWS Cognito                                                 │
├─────────────────────────────────────────────────────────────────────────┤
│ Operations:                                                             │
│ • sign_up()              → Creates user in Cognito User Pool           │
│ • confirm_sign_up()      → Verifies email with confirmation code       │
│ • initiate_auth()        → Authenticates user, returns JWT tokens      │
│ • respond_to_auth()      → Handles MFA challenges (TOTP)               │
│ • refresh_token()        → Issues new access/id tokens                 │
│ • global_sign_out()      → Revokes all tokens for user                 │
│ • admin_get_user()       → Retrieves user attributes                   │
│ • admin_update_user()    → Updates user attributes                     │
│ • admin_enable_user()    → Enables user account                        │
│ • admin_disable_user()   → Disables user account                       │
│                                                                         │
│ Data Exchange:                                                          │
│ → UserPoolId, ClientId, Username, Password                             │
│ ← AccessToken, IdToken, RefreshToken, Session                          │
│                                                                         │
│ Error Handling:                                                         │
│ • NotAuthorizedException → Invalid credentials                         │
│ • UserNotFoundException  → User doesn't exist                          │
│ • TooManyRequestsException → Rate limited                              │
│ • CodeMismatchException → Invalid MFA/verification code                │
└─────────────────────────────────────────────────────────────────────────┘

Authorization Flow Integration:
┌─────────────────────────────────────────────────────────────────────────┐
│ Fortress ←→ Amazon Verified Permissions                                │
├─────────────────────────────────────────────────────────────────────────┤
│ Operations:                                                             │
│ • is_authorized()        → Evaluates single authorization request      │
│ • batch_is_authorized()  → Evaluates multiple requests in batch        │
│ • put_schema()           → Defines Cedar schema                        │
│ • create_policy()        → Creates new Cedar policy                    │
│ • get_policy()           → Retrieves policy details                    │
│ • list_policies()        → Lists all policies                          │
│                                                                         │
│ Request Format:                                                         │
│ → PolicyStoreId                                                         │
│ → Principal: { entityType, entityId, attributes }                      │
│ → Action: { actionType, actionId }                                     │
│ → Resource: { entityType, entityId, attributes }                       │
│ → Context: { additional_attributes }                                   │
│                                                                         │
│ Response:                                                               │
│ ← Decision: ALLOW | DENY                                               │
│ ← DeterminingPolicies: [policy_ids]                                    │
│ ← Errors: [evaluation_errors]                                          │
│                                                                         │
│ Performance:                                                            │
│ • Latency: <100ms (p99)                                                │
│ • Cache: 60s TTL on decisions                                          │
│ • Batch: Up to 30 requests per call                                    │
└─────────────────────────────────────────────────────────────────────────┘

Caching Integration:
┌─────────────────────────────────────────────────────────────────────────┐
│ Fortress ←→ Amazon ElastiCache (Redis)                                 │
├─────────────────────────────────────────────────────────────────────────┤
│ Operations:                                                             │
│ • get(key)               → Retrieves cached value                      │
│ • set(key, val, ttl)     → Stores value with expiration               │
│ • delete(key)            → Removes cached value                        │
│ • scan(pattern)          → Pattern-based key search                    │
│ • exists(key)            → Checks key existence                        │
│ • expire(key, ttl)       → Updates TTL                                 │
│                                                                         │
│ Key Patterns:                                                           │
│ • authz:{principal}:{action}:{resource}  (60s TTL)                     │
│ • user_status:{user_id}                  (30s TTL)                     │
│ • jwks:{pool_id}                         (24h TTL)                     │
│                                                                         │
│ Data Format:                                                            │
│ • Serialization: JSON with zlib compression                            │
│ • Encoding: UTF-8                                                      │
│                                                                         │
│ Connection Management:                                                  │
│ • Pool Size: 50 connections                                            │
│ • Timeout: 5 seconds                                                   │
│ • Retry: 3 attempts with exponential backoff                           │
│ • Health Check: 30s interval                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Diagram

### AWS Infrastructure Layout

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud (Region: us-east-1)                       │
│                                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                              Public Zone                                    │  │
│  │                                                                             │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                         Route 53 (DNS)                                │  │  │
│  │  │  • Hosted Zone: fortress.example.com                                 │  │  │
│  │  │  • Health Checks: Multi-region failover                              │  │  │
│  │  │  • Routing Policy: Weighted/Latency-based                            │  │  │
│  │  └───────────────────────────────┬──────────────────────────────────────┘  │  │
│  │                                  │                                          │  │
│  │                                  ▼                                          │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                  AWS WAF (Web Application Firewall)                  │  │  │
│  │  │  • SQL Injection Protection                                          │  │  │
│  │  │  • XSS Protection                                                    │  │  │
│  │  │  • Rate Limiting Rules                                               │  │  │
│  │  │  • IP Allowlist/Blocklist                                            │  │  │
│  │  └───────────────────────────────┬──────────────────────────────────────┘  │  │
│  │                                  │                                          │  │
│  │                                  ▼                                          │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                Application Load Balancer (ALB)                       │  │  │
│  │  │  • SSL/TLS Termination (ACM Certificate)                             │  │  │
│  │  │  • TLS 1.2+ Only                                                     │  │  │
│  │  │  • Multi-AZ Deployment (us-east-1a, us-east-1b, us-east-1c)         │  │  │
│  │  │  • Health Checks: /health endpoint (30s interval)                    │  │  │
│  │  │  • Connection Draining: 60s                                          │  │  │
│  │  └───────────────────────────────┬──────────────────────────────────────┘  │  │
│  └──────────────────────────────────┼─────────────────────────────────────────┘  │
│                                     │                                            │
│                                     ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                       Nginx Reverse Proxy Layer                             │  │
│  │                                                                             │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │  │
│  │  │ Configuration: /etc/nginx/conf.d/fortress.conf                      │   │  │
│  │  │ • Rate Limiting:                                                     │   │  │
│  │  │   - /auth/*: 20 requests/min per IP                                 │   │  │
│  │  │   - /forgot-password: 5 requests/min per IP                         │   │  │
│  │  │   - /v1/*: 100 requests/min per IP                                  │   │  │
│  │  │ • Security Headers: HSTS, CSP, X-Frame-Options, etc.               │   │  │
│  │  │ • SSL/TLS: TLS 1.2+ with modern ciphers                             │   │  │
│  │  │ • Connection Limiting: 10 connections per IP                        │   │  │
│  │  │ • Static/Media File Serving                                         │   │  │
│  │  └────────────────────────────────┬────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                            │
│                                     ▼                                            │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                              VPC (10.0.0.0/16)                              │  │
│  │                                                                             │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    Public Subnets (10.0.1.0/24)                      │  │  │
│  │  │  • NAT Gateway (Multi-AZ)                                            │  │  │
│  │  │  • Internet Gateway                                                  │  │  │
│  │  └──────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                             │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │              Private Subnet - AZ A (10.0.10.0/24)                    │  │  │
│  │  │                                                                       │  │  │
│  │  │  ┌────────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │     Compute Option 1: AWS Lambda                               │  │  │  │
│  │  │  │                                                                 │  │  │  │
│  │  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │  │  │  │
│  │  │  │  │   Lambda     │  │   Lambda     │  │   Lambda     │        │  │  │  │
│  │  │  │  │  Function    │  │  Function    │  │  Function    │        │  │  │  │
│  │  │  │  │              │  │              │  │              │        │  │  │  │
│  │  │  │  │ Django App   │  │ Django App   │  │ Django App   │        │  │  │  │
│  │  │  │  │ Runtime:     │  │ (Auto-scaled │  │ (Auto-scaled │        │  │  │  │
│  │  │  │  │ Python 3.11  │  │  instances)  │  │  instances)  │        │  │  │  │
│  │  │  │  │ Memory: 1024MB│ │              │  │              │        │  │  │  │
│  │  │  │  │ Timeout: 30s │  │              │  │              │        │  │  │  │
│  │  │  │  │ Concurrency: │  │              │  │              │        │  │  │  │
│  │  │  │  │   100        │  │              │  │              │        │  │  │  │
│  │  │  │  └──────────────┘  └──────────────┘  └──────────────┘        │  │  │  │
│  │  │  └────────────────────────────────────────────────────────────────┘  │  │  │
│  │  │                                OR                                     │  │  │
│  │  │  ┌────────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │     Compute Option 2: Amazon ECS (Fargate)                     │  │  │  │
│  │  │  │                                                                 │  │  │  │
│  │  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │  │  │  │
│  │  │  │  │  ECS Task    │  │  ECS Task    │  │  ECS Task    │        │  │  │  │
│  │  │  │  │              │  │              │  │              │        │  │  │  │
│  │  │  │  │ Django App   │  │ Django App   │  │ Django App   │        │  │  │  │
│  │  │  │  │ Container    │  │ Container    │  │ Container    │        │  │  │  │
│  │  │  │  │              │  │              │  │              │        │  │  │  │
│  │  │  │  │ CPU: 0.5 vCPU│  │ CPU: 0.5 vCPU│  │ CPU: 0.5 vCPU│        │  │  │  │
│  │  │  │  │ Memory: 1GB  │  │ Memory: 1GB  │  │ Memory: 1GB  │        │  │  │  │
│  │  │  │  │              │  │              │  │              │        │  │  │  │
│  │  │  │  │ Auto-scaling:│  │              │  │              │        │  │  │  │
│  │  │  │  │ Min: 3       │  │              │  │              │        │  │  │  │
│  │  │  │  │ Max: 50      │  │              │  │              │        │  │  │  │
│  │  │  │  │ Target: 70%  │  │              │  │              │        │  │  │  │
│  │  │  │  │    CPU       │  │              │  │              │        │  │  │  │
│  │  │  │  └──────────────┘  └──────────────┘  └──────────────┘        │  │  │  │
│  │  │  └────────────────────────────────────────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                             │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │              Private Subnet - AZ B (10.0.20.0/24)                    │  │  │
│  │  │              (Same compute deployment as AZ A)                        │  │  │
│  │  └──────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                             │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │              Private Subnet - AZ C (10.0.30.0/24)                    │  │  │
│  │  │              (Same compute deployment as AZ A)                        │  │  │
│  │  └──────────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                             │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                  Security Groups & Network ACLs                       │  │  │
│  │  │                                                                       │  │  │
│  │  │  SG-ALB: Allow 443 from 0.0.0.0/0                                    │  │  │
│  │  │  SG-Compute: Allow traffic from SG-ALB only                          │  │  │
│  │  │  SG-Redis: Allow 6379 from SG-Compute                                │  │  │
│  │  │  NACL: Stateless firewall rules                                      │  │  │
│  │  └──────────────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                          AWS Managed Services                               │  │
│  │                                                                             │  │
│  │  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐  │  │
│  │  │   AWS Cognito        │  │  Amazon Verified     │  │ ElastiCache     │  │  │
│  │  │   User Pools         │  │  Permissions (AVP)   │  │ (Redis)         │  │  │
│  │  │                      │  │                      │  │                 │  │  │
│  │  │ User Pool ID:        │  │ Policy Store:        │  │ Cluster:        │  │  │
│  │  │   us-east-1_xxxxx    │  │   Cedar Policies     │  │   Multi-AZ      │  │  │
│  │  │                      │  │                      │  │                 │  │  │
│  │  │ MFA: TOTP Enabled    │  │ Entities:            │  │ Node Type:      │  │  │
│  │  │ Password Policy:     │  │   Users, Resources   │  │   cache.t3.medium│ │  │
│  │  │   Min 12 chars       │  │                      │  │

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Request Flow Overview                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

Client Request
      │
      ▼
┌──────────────────────────────────────┐
│   Nginx Reverse Proxy (Port 443)    │  ← 20 req/min (auth), 100 req/min (users)
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
                            │   - Multi-AZ             │
                            └──────────┬───────────────┘
                                       │
                                       ▼
                         ┌──────────────────────────────┐
                         │   Nginx Reverse Proxy        │
                         │   - Rate Limiting            │
                         │   - Request Validation       │
                         │   - SSL/TLS Re-encryption    │
                         │   - Security Headers         │
                         │   - Static File Serving      │
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

Layer 2: Nginx Reverse Proxy Security
┌────────────────────────────────────────────────────────────────┐
│  • TLS 1.2+ only (modern cipher suites)                        │
│  • Request size limits (10MB)                                  │
│  • Rate limiting per IP (20-100 req/min)                       │
│  • Connection limiting (10 per IP)                             │
│  • Security headers (HSTS, CSP, X-Frame-Options, etc.)         │
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
│ Reverse Proxy     │ Nginx                     │ Rate limiting, SSL │
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
