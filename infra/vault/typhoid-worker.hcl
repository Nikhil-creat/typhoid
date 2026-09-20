# Workers get read-only access to per-run dynamic credentials. Nothing else.
path "database/creds/typhoid-test-{{identity.entity.metadata.org}}" { capabilities = ["read"] }
path "oauth/token/typhoid-test"                                   { capabilities = ["read"] }
path "sys/wrapping/unwrap"                                        { capabilities = ["update"] }
# Explicitly deny everything else
path "secret/*" { capabilities = ["deny"] }
