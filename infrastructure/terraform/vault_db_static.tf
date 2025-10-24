# Vault KV Storage for Database Credentials
# This approach stores static database credentials in Vault KV v2
# Use this instead of the Database Secrets Engine when RDS is not publicly accessible

# Store database credentials in Vault KV
# Note: This needs to be done manually or via a null_resource since we can't
# write secrets directly with Terraform (security best practice)

# Create a script to store DB credentials in Vault
resource "null_resource" "store_db_credentials" {
  triggers = {
    db_password = random_password.db_password.result
    db_endpoint = aws_db_instance.postgresql.address
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Store database credentials in Vault KV
      vault kv put \
        -address="${var.vault_address}" \
        -namespace="${var.vault_namespace}" \
        kv/database/qnt9-srs \
        username="${aws_db_instance.postgresql.username}" \
        password="${random_password.db_password.result}" \
        host="${aws_db_instance.postgresql.address}" \
        port="${aws_db_instance.postgresql.port}" \
        database="${aws_db_instance.postgresql.db_name}" \
        connection_string="postgresql://${aws_db_instance.postgresql.username}:${random_password.db_password.result}@${aws_db_instance.postgresql.address}:${aws_db_instance.postgresql.port}/${aws_db_instance.postgresql.db_name}?sslmode=require"
    EOT

    environment = {
      VAULT_TOKEN = var.vault_token
    }
  }

  depends_on = [
    aws_db_instance.postgresql
  ]
}

# Data source to read the stored credentials (for verification)
data "vault_kv_secret_v2" "database" {
  mount = "kv"
  name  = "database/qnt9-srs"

  depends_on = [null_resource.store_db_credentials]
}

# Create policy for FastAPI to read database credentials
resource "vault_policy" "fastapi_db_static" {
  name = "qnt9-srs-fastapi-db-static-policy"

  policy = <<EOT
# Allow reading database credentials from KV
path "kv/data/database/qnt9-srs" {
  capabilities = ["read"]
}

path "kv/metadata/database/qnt9-srs" {
  capabilities = ["read"]
}

# Allow renewing own token
path "auth/token/renew-self" {
  capabilities = ["update"]
}

# Allow looking up own token
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
EOT
}

# Outputs for application configuration
output "vault_db_static_config" {
  description = "Vault KV configuration for static database credentials"
  value = {
    kv_path     = "kv/data/database/qnt9-srs"
    policy_name = vault_policy.fastapi_db_static.name
  }
}

output "vault_fastapi_env_vars_static" {
  description = "Environment variables for FastAPI application (using static credentials)"
  value = {
    VAULT_ADDR      = var.vault_address
    VAULT_NAMESPACE = var.vault_namespace
    VAULT_KV_PATH   = "kv/data/database/qnt9-srs"
    DB_HOST         = aws_db_instance.postgresql.address
    DB_PORT         = aws_db_instance.postgresql.port
    DB_NAME         = aws_db_instance.postgresql.db_name
  }
}

# Output the credentials for verification (sensitive)
output "db_credentials_stored" {
  description = "Confirmation that DB credentials are stored in Vault"
  value = {
    vault_path = "kv/database/qnt9-srs"
    username   = aws_db_instance.postgresql.username
    host       = aws_db_instance.postgresql.address
    port       = aws_db_instance.postgresql.port
    database   = aws_db_instance.postgresql.db_name
  }
}
