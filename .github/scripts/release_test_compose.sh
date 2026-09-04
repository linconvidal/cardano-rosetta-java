#!/usr/bin/env bash
# Compose's original files remain authoritative; only runtime env and local tags change.

release_compose() (
  cd "$DEPLOY_DIR" || exit
  docker compose --project-name "$PROJECT_NAME" \
    --env-file "$COMPOSE_BASE_ENV" --env-file .env.docker-compose-profile-mid-level \
    --env-file "$COMPOSE_ENV_FILE" --file docker-compose.yaml "$@"
)

prepare_compose_images() {
  local image immutable_id
  for image in "$API_IMAGE" "$INDEXER_IMAGE" "$CARDANO_NODE_IMAGE" "$POSTGRES_IMAGE" "$MITHRIL_IMAGE"; do
    docker pull "$image"
    immutable_id=$(docker image inspect "$image" --format '{{.Id}}')
    docker tag "$immutable_id" "${image%@*}"
  done
}

compose_candidate_services() {
  printf '%s\n' "api|$API_IMAGE" "yaci-indexer|$INDEXER_IMAGE" "db|$POSTGRES_IMAGE" \
    "cardano-node|$CARDANO_NODE_IMAGE" "cardano-submit-api|$CARDANO_NODE_IMAGE" \
    "mithril|$MITHRIL_IMAGE" "cardano-sync-waiter|$CARDANO_NODE_IMAGE"
}

verify_compose_config() {
  local config service image
  config=$(release_compose config --format json)
  while IFS='|' read -r service image; do
    [[ "$(jq -r --arg service "$service" '.services[$service].image' <<< "$config")" == "${image%@*}" ]]
  done < <(compose_candidate_services)
}

verify_compose_container() {
  local service=$1 expected_image=$2 configured_image running_id expected_id containers
  local -a all=()
  case "$service" in mithril|cardano-sync-waiter) all=(--all) ;; esac
  containers=$(docker ps "${all[@]}" \
    --filter "label=com.docker.compose.project=${PROJECT_NAME}" \
    --filter "label=com.docker.compose.service=${service}" --format '{{.ID}}')
  [[ -n "$containers" && "$containers" != *$'\n'* ]] || {
    echo "Expected exactly one $service container for $PROJECT_NAME." >&2; exit 1;
  }
  if [[ "$service" == api || "$service" == yaci-indexer ]]; then
    verify_compose_history "$containers"
  fi
  configured_image=$(docker inspect "$containers" --format '{{.Config.Image}}')
  running_id=$(docker inspect "$containers" --format '{{.Image}}')
  expected_id=$(docker image inspect "$expected_image" --format '{{.Id}}')
  [[ "$configured_image" == "${expected_image%@*}" && "$running_id" == "$expected_id" ]] || {
    echo "Compose $service image mismatch: configured=$configured_image running=$running_id expected=$expected_image ($expected_id)." >&2
    exit 1
  }
}

verify_compose_history() {
  local history
  history=$(docker inspect "$1" | jq -r \
    '.[0].Config.Env[] | select(startswith("REMOVE_SPENT_UTXOS=")) | sub("^REMOVE_SPENT_UTXOS="; "")')
  [[ "$history" == false ]] || { echo "Compose $1 is not in full-history mode." >&2; exit 1; }
}

verify_compose_candidate() {
  local service image
  while IFS='|' read -r service image; do
    verify_compose_container "$service" "$image"
  done < <(compose_candidate_services)
}

# Before stopping: require ownership. After stopping: no container may retain a
# path, its parent, or its descendants. Docker errors must never look like no mounts.
verify_compose_mounts() {
  local policy=$1 containers container mounts mount data_path project service
  containers=$(docker ps --all --quiet)
  for container in $containers; do
    mounts=$(docker inspect "$container" --format '{{range .Mounts}}{{println .Source}}{{end}}')
    while IFS= read -r mount; do
      [[ -n "$mount" ]] || continue
      for data_path in "$DB_PATH" "$CARDANO_NODE_DIR"; do
        if [[ "$mount" != "$data_path" && "$data_path" != "$mount"/* && "$mount" != "$data_path"/* ]]; then
          continue
        fi
        [[ "$policy" != unmounted ]] || {
          echo "Refusing deletion: $container still references $data_path via $mount." >&2; exit 1;
        }
        project=$(docker inspect "$container" --format '{{index .Config.Labels "com.docker.compose.project"}}')
        [[ "$project" == "$PROJECT_NAME" ]] || {
          echo "Data path $mount belongs to foreign project $project." >&2; exit 1;
        }
        if [[ "$policy" == services ]]; then
          service=$(docker inspect "$container" --format '{{index .Config.Labels "com.docker.compose.service"}}')
          if [[ "$data_path" == "$DB_PATH" ]]; then
            [[ "$service" == db ]] || { echo "Unexpected database service $service." >&2; exit 1; }
          else
            case "$service" in
              api|cardano-node|cardano-submit-api|cardano-sync-waiter|mithril|yaci-indexer) ;;
              *) echo "Unexpected node-data service $service." >&2; exit 1 ;;
            esac
          fi
        fi
      done
    done <<< "$mounts"
  done
}
