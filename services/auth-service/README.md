# Auth Service

FastAPI-based authentication service with Vault integration for secure credential management and Datadog APM & Application Security monitoring.

## Features

- User authentication with JWT tokens
- Database support (PostgreSQL/SQLite)
- HashiCorp Vault integration for secrets management
- Datadog APM & Application Security monitoring
- Application Security Management (ASM)
- Interactive Application Security Testing (IAST)
- Software Composition Analysis (SCA)
- Continuous Profiling
- Data Streams Monitoring

## Local Development

### Prerequisites

1. **Install Datadog APM library**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Datadog Agent** (optional for local dev):
   - For local development: **NOT REQUIRED** - the app will run fine without it
   - Traces are instrumented but won't be sent to Datadog (no errors)
   - For production: Datadog Agent must be running to collect traces

### Running the Service

#### Option 1: SQLite without Datadog (Simple Dev)

Use SQLite for local development:

```bash
# Make sure Vault env vars are NOT set
unset VAULT_ADDR VAULT_NAMESPACE VAULT_TOKEN

# Run the app
make fastapi-dev
```

The app will automatically use SQLite (`sqlite:///./test.db`) for local development.

#### Option 2: SQLite with Datadog APM (Recommended for Local Dev)

Run with Datadog APM & Application Security enabled:

```bash
# Make sure Vault env vars are NOT set
unset VAULT_ADDR VAULT_NAMESPACE VAULT_TOKEN

# Run with Datadog APM (no agent required for local dev)
make fastapi-dev-dd
```

**Note**: You'll see connection errors to `localhost:8126` in the logs. This is **normal and safe** - the Datadog tracer can't reach the agent, but your application runs perfectly fine. The instrumentation is active, but traces just won't be sent to Datadog. To actually send traces, you'd need to install and run the Datadog Agent locally.

This will enable:
- ✅ Distributed tracing (instrumented, not sent)
- ✅ Application Security Management (ASM) - threat detection
- Interactive Application Security Testing (IAST) - vulnerability detection
- Software Composition Analysis (SCA) - dependency scanning
- Continuous profiling
- Data streams monitoring

#### Option 3: Connect to AWS RDS

To connect to the production RDS database from your local machine:

1. **Make RDS publicly accessible** (if not already done):
   ```bash
   cd ../../infrastructure/terraform
   terraform apply
   ```

2. **Set Vault credentials**:
   ```bash
   export VAULT_ADDR="https://qnt9-srs-vault-cluster-public-vault-9a23dacc.10ab1e04.z1.hashicorp.cloud:8200"
   export VAULT_NAMESPACE="admin"
   export VAULT_TOKEN="your-vault-token-here"
   ```

3. **Run the app**:
   ```bash
   make fastapi-dev-dd  # With Datadog
   # or
   make fastapi-dev     # Without Datadog
   ```

The app will read database credentials from Vault at `kv/database/qnt9-srs`.

### Option 4: Set Database URL Directly

You can also override with an environment variable:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
make fastapi-dev
```

## How the Database Connection Works

The app tries to connect in this order:

1. **Vault KV** - If `VAULT_ADDR` and `VAULT_TOKEN` are set, reads credentials from `kv/database/qnt9-srs`
2. **DATABASE_URL** - Falls back to the `DATABASE_URL` environment variable
3. **SQLite** - Falls back to `sqlite:///./test.db` for local development

## API Endpoints

### Authentication
- `POST /register` - Register a new user
- `POST /token` - Login and get access token

### User Profile Management
- `GET /users/me` - Get current user info (requires authentication)
- `PUT /users/me` - Update current user's profile
- `POST /users/me/password` - Change password
- `DELETE /users/me` - Delete own account

### User Management (Admin)
- `GET /users` - List all users (with pagination)
- `GET /users/search?q=term` - Search users
- `GET /users/count` - Get total user count
- `GET /users/{user_id}` - Get user by ID
- `PUT /users/{user_id}` - Update user profile
- `POST /users/{user_id}/password-reset` - Reset user password
- `PATCH /users/{user_id}/status` - Enable/disable user account
- `DELETE /users/{user_id}` - Delete user

### General
- `GET /` - Welcome message
- `GET /protected` - Protected route example

## Datadog APM & Application Security

### Environment Variables

The following Datadog environment variables are configured:

| Variable | Value | Description |
|----------|-------|-------------|
| `DD_SERVICE` | `auth-service` | Service name in Datadog |
| `DD_ENV` | `dev`/`prod` | Environment (dev for local, prod for Docker) |
| `DD_LOGS_INJECTION` | `true` | Correlate traces with logs |
| `DD_PROFILING_ENABLED` | `true` | Enable continuous profiling |
| `DD_DATA_STREAMS_ENABLED` | `true` | Enable data streams monitoring |
| `DD_TRACE_REMOVE_INTEGRATION_SERVICE_NAMES_ENABLED` | `true` | Clean service naming |
| `DD_APPSEC_ENABLED` | `true` | Enable Application Security (threat detection) |
| `DD_IAST_ENABLED` | `true` | Enable IAST (vulnerability detection) |
| `DD_APPSEC_SCA_ENABLED` | `true` | Enable SCA (dependency scanning) |
| `DD_GIT_REPOSITORY_URL` | `github.com/timkrebs/qnt9-srs` | Git repository for source code integration |

### Datadog Features Enabled

1. **APM (Application Performance Monitoring)**
   - Distributed tracing across services
   - Request/response tracking
   - Performance bottleneck identification

2. **Application Security Management (ASM)**
   - Real-time threat detection and blocking
   - OWASP Top 10 protection
   - Attack attempt monitoring

3. **IAST (Interactive Application Security Testing)**
   - Runtime vulnerability detection
   - Code-level security issue identification
   - No separate security scans needed

4. **SCA (Software Composition Analysis)**
   - Dependency vulnerability scanning
   - Open source risk assessment
   - License compliance tracking

5. **Continuous Profiling**
   - CPU usage analysis
   - Memory allocation tracking
   - Performance optimization insights

6. **Data Streams Monitoring**
   - End-to-end latency tracking
   - Message queue monitoring

### Viewing Datadog Data

After running the service with Datadog enabled:

1. **APM Traces**: https://app.datadoghq.com/apm/traces
2. **Security Signals**: https://app.datadoghq.com/security
3. **Profiling**: https://app.datadoghq.com/profiling
4. **Service Catalog**: Search for `auth-service`

## API Endpoints

- `GET /` - Welcome message
- `POST /register` - Register a new user
- `POST /token` - Login and get access token
- `GET /users/me` - Get current user info (requires authentication)

## Testing

Visit the auto-generated API docs:
- http://127.0.0.1:8000/docs (Swagger UI)
- http://127.0.0.1:8000/redoc (ReDoc)

### Testing with Datadog APM

When running with `make fastapi-dev-dd`, all API requests will be:
- Traced in Datadog APM
- Analyzed for security threats
- Scanned for vulnerabilities
- Profiled for performance

Generate some traffic to see data in Datadog:
```bash
# Register a user
curl -X POST "http://127.0.0.1:8000/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"secret123","full_name":"Test User"}'

# Login
curl -X POST "http://127.0.0.1:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=secret123"

# Get user info (use token from login)
curl -X GET "http://127.0.0.1:8000/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Docker Deployment

### Build and Run

## Docker Deployment

### Build and Run

```bash
# Build the Docker image
make docker-build

# Run the container (without Datadog Agent connection)
make docker-run

# Run with local Datadog Agent connection
make docker-run-dd
```

The Docker image includes Datadog APM & Application Security pre-configured with production settings.

### Kubernetes/EKS Deployment

When deployed to EKS, the app will:
1. Read credentials from Vault using a Kubernetes service account
2. Connect to RDS (which is in the same VPC)
3. Send traces to the Datadog Agent running as a DaemonSet
4. No public internet access required for database or Datadog Agent

**Important**: Ensure the Datadog Agent is deployed to your Kubernetes cluster as a DaemonSet before deploying this service.

### Environment Variables for Production

In production (Kubernetes), set these additional environment variables:

```yaml
env:
  - name: DD_AGENT_HOST
    valueFrom:
      fieldRef:
        fieldPath: status.hostIP
  - name: DD_TRACE_AGENT_PORT
    value: "8126"
  - name: DD_GIT_COMMIT_SHA
    value: "$(git rev-parse HEAD)"
  - name: DD_GIT_BRANCH
    value: "main"
```

## Troubleshooting

### Datadog APM Not Sending Traces

1. **Check if Datadog Agent is running**:
   ```bash
   # For local development
   curl http://localhost:8126/info
   ```

2. **Check environment variables**:
   ```bash
   echo $DD_SERVICE
   echo $DD_AGENT_HOST
   ```

3. **Enable debug logging**:
   ```bash
   DD_TRACE_DEBUG=true make fastapi-dev-dd
   ```

### Datadog APM Not Sending Traces

**Error**: `ConnectionRefusedError: [Errno 61] Connection refused` to `localhost:8126`

**Solution**: This is **normal for local development** without a Datadog Agent installed.

- ✅ **Your application is running fine** - this error doesn't affect functionality
- ✅ **Instrumentation is active** - code is being traced, just not sent anywhere
- ✅ **Security features are working** - ASM, IAST, and SCA are operational

**Options**:
1. **Ignore it** (recommended for local dev) - the errors are harmless
2. **Install Datadog Agent locally**:
   ```bash
   # macOS
   brew install datadog-agent
   datadog-agent run
   ```
3. **Disable trace sending** - run without ddtrace:
   ```bash
   make fastapi-dev  # No Datadog at all
   ```

The traces will automatically be sent when deployed to Kubernetes where the Datadog Agent DaemonSet is running.

### Connection Issues

If the service can't connect to Vault or the database:
- Check environment variables are set correctly
- Verify network connectivity
- Check Vault token hasn't expired
- Ensure database is accessible from your network

## Development Workflow

1. **Start with SQLite + Datadog** for local development:
   ```bash
   make fastapi-dev-dd
   ```

2. **Make changes** to the code

3. **Test** using the API docs at http://127.0.0.1:8000/docs

4. **Monitor** traces and security findings in Datadog

5. **Build and test Docker image**:
   ```bash
   make docker-build
   make docker-run-dd
   ```

6. **Deploy to Kubernetes** with Vault and RDS integration
