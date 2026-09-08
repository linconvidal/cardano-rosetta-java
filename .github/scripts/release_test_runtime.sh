#!/usr/bin/env bash
# Runtime evidence shared by the dedicated Compose and Kubernetes test deployments.

wait_for_release_live() {
  local endpoint=$1 network=$2 expected_version=$3
  local payload sync_state version attempt=0 deadline=$((SECONDS + SYNC_TIMEOUT_SECONDS))
  payload=$(jq -nc --arg network "$network" \
    '{network_identifier: {blockchain: "cardano", network: $network}}')
  until sync_state=$(curl -fs --header 'Content-Type: application/json' --data "$payload" \
      "$endpoint/network/status" | jq -r '.sync_status.synced and .sync_status.stage == "LIVE"') \
      && [[ "$sync_state" == true ]]; do
    (( SECONDS < deadline )) || { echo "$PHASE did not reach LIVE in time." >&2; exit 1; }
    (( ++attempt % 20 )) || echo "$PHASE: still waiting after $((SECONDS / 60))m."
    sleep "${POLL_INTERVAL_SECONDS:-60}"
  done
  version=$(curl -fsS --header 'Content-Type: application/json' --data "$payload" \
    "$endpoint/network/options" | jq -r '.version.middleware_version')
  [[ "$version" == "$expected_version" ]] || {
    echo "$PHASE reports middleware $version, expected $expected_version." >&2; exit 1;
  }
  echo "$PHASE is LIVE on $version."
}

report_release_cleanup_space() {
  local storage_root=$1 free_bytes reclaimable_bytes=0 data_path du_output used_bytes
  shift
  free_bytes=$(df --output=avail -B1 "$storage_root" | awk 'NR == 2 {print $1}')
  for data_path in "$@"; do
    # Live files may vanish during du. Accept its total only if it is numeric.
    du_output=$(sudo du -sB1 "$data_path") || true
    used_bytes=$(awk '{print $1}' <<< "$du_output")
    [[ "$used_bytes" =~ ^[0-9]+$ ]] || {
      echo "Could not measure $data_path." >&2; exit 1;
    }
    reclaimable_bytes=$((reclaimable_bytes + used_bytes))
  done
  printf 'Disk space at %s: available=%s bytes; deployment data=%s bytes; estimated available after cleanup=%s bytes.\n' \
    "$storage_root" "$free_bytes" "$reclaimable_bytes" "$((free_bytes + reclaimable_bytes))"
}

capture_release_machine() {
  local disk_path=$1 deployment=$2 environment=$3
  local cpu_json cpu_model cores_per_socket sockets threads physical_cores
  local key value visible_ram_gib disk_total_gib disk_free_gib machine_specs
  local -a disk_stats
  cpu_json=$(lscpu --json)
  cpu_model=$(jq -r '.lscpu[] | select(.field == "Model name:") | .data' <<< "$cpu_json")
  cores_per_socket=$(jq -r '.lscpu[] | select(.field == "Core(s) per socket:") | .data' <<< "$cpu_json")
  sockets=$(jq -r '.lscpu[] | select(.field == "Socket(s):") | .data' <<< "$cpu_json")
  physical_cores=$((cores_per_socket * sockets))
  threads=$(nproc)
  while read -r key value _; do
    if [[ "$key" == "MemTotal:" ]]; then
      visible_ram_gib=$(((value + 524288) / 1048576))
      break
    fi
  done < /proc/meminfo
  mapfile -t disk_stats < <(df -BG --output=size,avail "$disk_path")
  read -r disk_total_gib disk_free_gib <<< "${disk_stats[1]}"
  disk_total_gib=${disk_total_gib%G}
  disk_free_gib=${disk_free_gib%G}
  machine_specs="${threads} vCPUs, ${visible_ram_gib}GB RAM; CPU=${cpu_model}; cores=${physical_cores}; threads=${threads}; visible RAM=${visible_ram_gib}GiB; disk=${disk_total_gib}GiB; free=${disk_free_gib}GiB; environment=${environment}; kernel=$(uname -sr)"
  echo "machine_specs=$machine_specs" >> "$GITHUB_OUTPUT"
  printf '### %s runner\n\n%s\n' "$deployment" "$machine_specs" >> "$GITHUB_STEP_SUMMARY"
}
