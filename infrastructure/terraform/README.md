# PostgreSQL Database Setup für FastAPI

## Übersicht
Die Terraform-Konfiguration erstellt eine AWS RDS PostgreSQL-Datenbank für die SRS FastAPI-Anwendung.

## Database Features

- **Engine**: PostgreSQL 15.4
- **Instance Class**: db.t3.micro (anpassbar via Variable)
- **Storage**: 20 GB (autoscaling bis 100 GB)
- **Encryption**: Aktiviert
- **Backups**: 7 Tage Retention (Production), 1 Tag (Dev/Staging)
- **Multi-AZ**: Aktiviert für Production
- **Enhanced Monitoring**: CloudWatch Logs und Performance Insights
- **Secrets Management**: Credentials in AWS Secrets Manager

## Terraform Outputs

Nach dem Deployment erhalten Sie folgende Outputs:

```bash
terraform output db_instance_endpoint  # Full endpoint (host:port)
terraform output db_instance_address   # Database host
terraform output db_instance_port      # Database port
terraform output db_instance_name      # Database name
terraform output db_secret_arn         # ARN des Secrets mit Credentials
```

## FastAPI Integration

### 1. Dependencies installieren

```bash
pip install sqlalchemy psycopg2-binary asyncpg alembic
```

### 2. Database Connection String abrufen

```bash
# Aus Terraform outputs
DB_HOST=$(terraform output -raw db_instance_address)
DB_PORT=$(terraform output -raw db_instance_port)
DB_NAME=$(terraform output -raw db_instance_name)

# Password aus AWS Secrets Manager
SECRET_ARN=$(terraform output -raw db_secret_arn)
aws secretsmanager get-secret-value --secret-id $SECRET_ARN --query SecretString --output text
```

### 3. FastAPI Beispiel-Code

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Umgebungsvariablen
DB_USERNAME = os.getenv("DB_USERNAME", "srs_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "srs_db")

# Connection String
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from database import Base

class StockRecommendation(Base):
    __tablename__ = "stock_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    recommendation = Column(String)
    price = Column(Float)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# app.py
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import engine, get_db, Base
from models import StockRecommendation

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.post("/recommendations/")
def create_recommendation(
    symbol: str,
    recommendation: str,
    price: float,
    confidence_score: float,
    db: Session = Depends(get_db)
):
    db_recommendation = StockRecommendation(
        symbol=symbol,
        recommendation=recommendation,
        price=price,
        confidence_score=confidence_score
    )
    db.add(db_recommendation)
    db.commit()
    db.refresh(db_recommendation)
    return db_recommendation

@app.get("/recommendations/")
def read_recommendations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    recommendations = db.query(StockRecommendation).offset(skip).limit(limit).all()
    return recommendations
```

### 4. Async Version (empfohlen für Performance)

```python
# database_async.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DB_USERNAME = os.getenv("DB_USERNAME", "srs_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "srs_db")

ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(ASYNC_DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
```

## Environment Variables für Kubernetes

Erstellen Sie ein Kubernetes Secret für die Database Credentials:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: postgres-credentials
type: Opaque
stringData:
  DB_USERNAME: srs_admin
  DB_PASSWORD: <aus AWS Secrets Manager>
  DB_HOST: <aus terraform output>
  DB_PORT: "5432"
  DB_NAME: srs_db
```

Oder verwenden Sie External Secrets Operator für automatische Synchronisation mit AWS Secrets Manager:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: postgres-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: postgres-credentials
  data:
  - secretKey: DB_USERNAME
    remoteRef:
      key: srs-db-credentials
      property: username
  - secretKey: DB_PASSWORD
    remoteRef:
      key: srs-db-credentials
      property: password
  - secretKey: DB_HOST
    remoteRef:
      key: srs-db-credentials
      property: host
  - secretKey: DB_PORT
    remoteRef:
      key: srs-db-credentials
      property: port
  - secretKey: DB_NAME
    remoteRef:
      key: srs-db-credentials
      property: dbname
```

## Alembic für Database Migrations

```bash
# Alembic initialisieren
alembic init alembic

# In alembic.ini die connection string anpassen
# In alembic/env.py:
from database import Base
from models import StockRecommendation  # Import your models
target_metadata = Base.metadata

# Migration erstellen
alembic revision --autogenerate -m "Initial migration"

# Migration ausführen
alembic upgrade head
```

## Troubleshooting

### Connection Timeout
- Stellen Sie sicher, dass Ihre FastAPI-App im gleichen VPC wie die RDS-Instanz läuft
- Überprüfen Sie die Security Group Rules
- Testen Sie die Verbindung mit: `psql -h <DB_HOST> -U <DB_USERNAME> -d <DB_NAME>`

### Secrets abrufen
```bash
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw db_secret_arn) \
  --query SecretString \
  --output text | jq .
```

## Kosten-Optimierung

- Für Dev/Test: Nutzen Sie `db.t3.micro` oder `db.t4g.micro`
- Für Production: Erwägen Sie Reserved Instances für 30-70% Ersparnis
- Aktivieren Sie Storage Autoscaling nur wenn nötig
- Nutzen Sie Multi-AZ nur für Production

## Sicherheit

- ✅ Verschlüsselung at rest aktiviert
- ✅ Passwörter in AWS Secrets Manager
- ✅ Security Groups beschränken Zugriff auf VPC
- ✅ Enhanced Monitoring aktiviert
- ✅ Deletion Protection für Production
- ⚠️ Erwägen Sie SSL/TLS für Verbindungen: `?sslmode=require`

## Nächste Schritte

1. Terraform apply durchführen
2. Database Credentials aus Secrets Manager abrufen
3. Kubernetes Secret erstellen
4. FastAPI App mit SQLAlchemy konfigurieren
5. Alembic Migrations einrichten
6. Tests durchführen
