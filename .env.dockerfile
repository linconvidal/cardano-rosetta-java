LOG=INFO
NETWORK="preprod"  # mainnet, preprod, testnet, devkit
PROTOCOL_MAGIC=1 # mainnet 764824073, preprod 1, testnet 2, devkit 42

#common env
DB_ADMIN_USER_NAME="rosetta_db_admin"
DB_ADMIN_USER_SECRET="weakpwd#123_d"

# Postgres variables
DB_IMAGE_NAME="postgres"
DB_IMAGE_TAG="14.11-bullseye"
DB_NAME="rosetta-java-preprod"
DB_HOST="db" # Service name in docker-compose or local db
DB_PORT="5432"
DB_SCHEMA=${NETWORK}
DB_PATH="data"

# Cardano Node variables
CARDANO_NODE_HOST="cardano-node" # Service name in docker-compose or local cardano node
CARDANO_NODE_PORT="3001" # Uncomment if you are using local cardano node
CARDANO_NODE_VERSION="8.9.0"
CARDANO_NODE_SUBMIT_HOST="cardano-submit-api"
NODE_SUBMIT_API_PORT=8090
CARDANO_NODE_SOCKET="./node-ipc"
CARDANO_NODE_DB="./node/db"
CARDANO_CONFIG="./config/${NETWORK}"

#api env
API_SPRING_PROFILES_ACTIVE_API="dev" # staging. Additional profiles: mempool (if mempool should be activated)
API_PORT=8081
TRANSACTION_TTL=3000

DB_CONNECTION_PARAMS_PROVIDER_TYPE="ENVIRONMENT"
DB_DRIVER_CLASS_NAME="org.postgresql.Driver"

ROSETTA_VERSION=1.4.13
TOPOLOGY_FILEPATH=/config/${NETWORK}/topology.json
GENESIS_SHELLEY_PATH=/config/${NETWORK}/shelley-genesis.json
GENESIS_BYRON_PATH=/config/${NETWORK}/byron-genesis.json
GENESIS_ALONZO_PATH=/config/${NETWORK}/alonzo-genesis.json
GENESIS_CONWAY_PATH=/config/${NETWORK}/conway-genesis.json
API_NODE_SOCKET_PATH=./node/node.socket
PRINT_EXCEPTION=true

#api env
YACI_SPRING_PROFILES="postgres" # database profiles: h2, postgres
INDEXER_NODE_PORT=3001
MEMPOOL_ENABLED=true