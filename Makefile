REPO_NAME    := huachicol
COMPOSE_PROD := -f compose.yaml

UP_GUARDS     = ensure_network
DEPLOY_GUARDS = ensure_network

include make/common.mk
