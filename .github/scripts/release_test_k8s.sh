#!/usr/bin/env bash
# Cluster/storage identity and the supported Helm deployment contract.

verify_release_cluster() {
  local uid
  uid=$(kubectl get namespace kube-system -o json | jq -r '.metadata.uid')
  [[ "$uid" == "$EXPECTED_KUBE_SYSTEM_UID" ]] || {
    echo "Unexpected K8s cluster identity: $uid" >&2; exit 1;
  }
}

# Emits PV name, PV UID and canonical data path as TSV. Call through an assignment,
# not a process substitution: API/filesystem failures must abort the caller.
verify_release_volume() (
  set -euo pipefail
  local pvc=$1 expected_uid=$2 pvc_json pv_json pv pv_uid data_path root_device path_device
  pvc_json=$(kubectl get pvc "$pvc" --namespace "$NAMESPACE" -o json)
  pv=$(jq -er --arg release "$HELM_RELEASE" --arg size "$VOLUME_SIZE" --arg uid "$expected_uid" '
    if .metadata.labels["app.kubernetes.io/instance"] == $release and
       .metadata.uid == $uid and .spec.resources.requests.storage == $size and
       .spec.storageClassName == "local-path" and .status.phase == "Bound"
    then .spec.volumeName else error("Unexpected release PVC contract") end
  ' <<< "$pvc_json")
  pv_json=$(kubectl get pv "$pv" -o json)
  pv_uid=$(jq -r '.metadata.uid' <<< "$pv_json")
  data_path=$(jq -er --arg pvc "$pvc" --arg uid "$expected_uid" --arg namespace "$NAMESPACE" '
    if .spec.claimRef.uid == $uid and .spec.claimRef.name == $pvc and
       .spec.claimRef.namespace == $namespace and .spec.persistentVolumeReclaimPolicy == "Delete"
    then .spec.local.path else error("Unexpected release PV binding or reclaim policy") end
  ' <<< "$pv_json")
  root_device=$(stat -c '%d' "$K8S_STORAGE_ROOT")
  path_device=$(sudo stat -c '%d' "$data_path")
  if [[ "$data_path" != "$K8S_STORAGE_ROOT"/* ]] ||
     ! sudo test -d "$data_path" || sudo test -L "$data_path" ||
     [[ "$(sudo realpath -e "$data_path")" != "$data_path" ]] ||
     [[ "$path_device" != "$root_device" ]]; then
    echo "Unsafe local-path storage target for $pvc: $data_path" >&2
    exit 1
  fi
  printf '%s\t%s\t%s\n' "$pv" "$pv_uid" "$data_path"
)

# One snapshot per workload in the current step, never cached across phases.
# Populates workload_json/pods_json; container verification selects pod_json.
load_release_workload() {
  local kind=$1 name=$2
  kubectl rollout status "$kind/$HELM_RELEASE-$name" --namespace "$NAMESPACE" --timeout=10m
  workload_json=$(kubectl get "$kind" "$HELM_RELEASE-$name" --namespace "$NAMESPACE" -o json)
  pods_json=$(kubectl get pods --namespace "$NAMESPACE" \
    --selector "app=${HELM_RELEASE}-${name},component=${name}" --output json)
}

verify_release_container() {
  local container=$1 expected_image=$2 image
  image=$(jq -r --arg container "$container" \
    '.spec.template.spec.containers[] | select(.name == $container) | .image' <<< "$workload_json")
  [[ "$image" == "$expected_image" ]] || {
    echo "K8s $container template does not use $expected_image." >&2; exit 1;
  }
  pod_json=$(jq -cer --arg container "$container" --arg image "$expected_image" \
    --arg digest "${expected_image##*@}" '
      [.items[] | select(
        any(.spec.containers[]; .name == $container and .image == $image) and
        any(.status.containerStatuses[]?; .name == $container and .ready == true and (.imageID | endswith("@" + $digest)))
      )] | if length == 1 then .[0] else error("Expected one ready pod, found \(length)") end
    ' <<< "$pods_json")
}

verify_release_init_container() {
  local container=$1 expected_image=$2 image
  image=$(jq -r --arg container "$container" \
    '.spec.template.spec.initContainers[] | select(.name == $container) | .image' <<< "$workload_json")
  if [[ "$image" != "$expected_image" ]] || ! jq -e \
    --arg container "$container" --arg image "$expected_image" --arg digest "${expected_image##*@}" '
      [.items[] | select(
        any(.spec.initContainers[]; .name == $container and .image == $image) and
        any(.status.initContainerStatuses[]?; .name == $container and
          .state.terminated.exitCode == 0 and (.imageID | endswith("@" + $digest)))
      )] | length == 1
    ' <<< "$pods_json"; then
    echo "K8s $container did not complete from $expected_image." >&2
    exit 1
  fi
}

verify_release_deployment() {
  local deployment=$1 expected_image=$2 history init_container
  local workload_json pods_json pod_json
  shift 2
  load_release_workload deployment "$deployment"
  history=$(jq -r --arg container "$deployment" \
    '.spec.template.spec.containers[] | select(.name == $container) | .env[] |
     select(.name == "REMOVE_SPENT_UTXOS") | .value' <<< "$workload_json")
  [[ "$history" == false ]] || { echo "K8s $deployment is not full-history." >&2; exit 1; }
  pods_json=$(jq --arg container "$deployment" '
    .items |= map(select([.spec.containers[] | select(.name == $container) | .env[]? |
      select(.name == "REMOVE_SPENT_UTXOS") | .value] == ["false"]))
  ' <<< "$pods_json")
  verify_release_container "$deployment" "$expected_image"
  # Deployment init evidence must belong to that same ready, full-history pod.
  pods_json=$(jq -nc --argjson pod "$pod_json" '{items: [$pod]}')
  for init_container in "$@"; do
    verify_release_init_container "$init_container" "$CARDANO_NODE_IMAGE"
  done
}

release_helm() {
  local postgres_version_ref=${POSTGRES_IMAGE#cardanofoundation/cardano-rosetta-java-postgres:}
  helm "$@" "$HELM_RELEASE" "$chart" \
    --namespace "$NAMESPACE" \
    --values "$chart/values-k3s.yaml" \
    --set-string global.network=mainnet \
    --set-string global.profile=mid \
    --set-string global.releaseVersion="$PRERELEASE_TAG" \
    --set-string global.apiImage="$API_IMAGE" \
    --set-string global.indexerImage="$INDEXER_IMAGE" \
    --set-string global.cardanoNodeImage="$CARDANO_NODE_IMAGE" \
    --set-string global.mithrilImage="$MITHRIL_IMAGE" \
    --set-string global.pgVersionTag="$postgres_version_ref" \
    --set-string global.db.existingSecret="$DB_SECRET_NAME" \
    --set-string global.storage.cardanoNode.size="$VOLUME_SIZE" \
    --set-string global.storage.postgresql.size="$VOLUME_SIZE" \
    --set-string rosetta-api.env.removeSpentUtxos=false \
    --set-string yaci-indexer.env.removeSpentUtxos=false
}
