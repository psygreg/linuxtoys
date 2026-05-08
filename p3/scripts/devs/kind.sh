#!/bin/bash
# name: Kind (Kubernetes)
# version: 1.0
# description: kind_desc
# icon: kind.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy, ostree, ublue
# repo: https://kind.sigs.k8s.io/

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

DEFAULT_CLUSTER_NAME="linuxtoys"
CLUSTER_NAME="$DEFAULT_CLUSTER_NAME"
INGRESS_MANIFEST_URL="https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml"

sudo_rq
# kind requires a container runtime provider.
if ! command -v docker >/dev/null 2>&1 && \
   ! command -v podman >/dev/null 2>&1 && \
   ! command -v nerdctl >/dev/null 2>&1; then
    fatal "No container runtime found (docker/podman/nerdctl). Install Docker or Podman first, then run Kind installation again."
fi

if is_arch || is_cachy; then
    pkg_install kind-bin kubectl
else
    arch="$(uname -m)"
    case "$arch" in
        x86_64) kind_arch="amd64" ;;
        aarch64|arm64) kind_arch="arm64" ;;
        *)
            fatal "Unsupported architecture for Kind binary: $arch"
            ;;
    esac

    kind_url="https://kind.sigs.k8s.io/dl/latest/kind-linux-${kind_arch}"

    if ! curl -fsSL "$kind_url" -o /tmp/kind; then
        fatal "Failed to download Kind binary."
    fi

    chmod +x /tmp/kind
    prep_create /usr/local/bin/kind
    if ! sudo install -Dm755 /tmp/kind /usr/local/bin/kind; then
        fatal "Failed to install Kind to /usr/local/bin."
    fi

    kubectl_version="$(curl -fsSL https://dl.k8s.io/release/stable.txt)"
    [ -n "$kubectl_version" ] || fatal "Failed to get latest kubectl version."
    kubectl_url="https://dl.k8s.io/release/${kubectl_version}/bin/linux/${kind_arch}/kubectl"

    if ! curl -fsSL "$kubectl_url" -o /tmp/kubectl; then
        fatal "Failed to download kubectl binary."
    fi

    chmod +x /tmp/kubectl
    prep_create /usr/local/bin/kubectl
    if ! sudo install -Dm755 /tmp/kubectl /usr/local/bin/kubectl; then
        fatal "Failed to install kubectl to /usr/local/bin."
    fi
fi

if command -v kind >/dev/null 2>&1 && command -v kubectl >/dev/null 2>&1; then
    :
else
    fatal "kind and/or kubectl command was not found after installation."
fi

is_valid_cluster_name() {
    local name="$1"
    [[ "$name" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ ]]
}

prompt_cluster_name() {
    local input=""
    if [[ "$DISABLE_ZENITY" == "1" ]]; then
        read -r -p "Cluster name [$DEFAULT_CLUSTER_NAME]: " input
    else
        input="$(zenity --entry \
            --title="Kind (Kubernetes)" \
            --text="Enter the cluster name (lowercase letters, numbers, and '-')." \
            --entry-text="$DEFAULT_CLUSTER_NAME" \
            --width=460 --height=260)"
        [ $? -ne 0 ] && return 1
    fi

    input="${input:-$DEFAULT_CLUSTER_NAME}"
    if ! is_valid_cluster_name "$input"; then
        zenwrn "Invalid cluster name: '$input'. Using default '$DEFAULT_CLUSTER_NAME'."
        input="$DEFAULT_CLUSTER_NAME"
    fi

    CLUSTER_NAME="$input"
    return 0
}

setup_kind_ingress_demo() {
    local kind_cfg
    if kind get clusters 2>/dev/null | grep -Fxq "$CLUSTER_NAME"; then
        return 10
    fi

    kind_cfg="$(mktemp)"
    cat > "$kind_cfg" <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF

    if ! kind create cluster --name "$CLUSTER_NAME" --config "$kind_cfg"; then
        rm -f "$kind_cfg"
        return 1
    fi
    rm -f "$kind_cfg"

    kubectl apply -f "$INGRESS_MANIFEST_URL" >/dev/null 2>&1 || return 20
    kubectl wait --namespace ingress-nginx \
        --for=condition=ready pod \
        --selector=app.kubernetes.io/component=controller \
        --timeout=180s >/dev/null 2>&1 || return 21

    return 0
}

if [[ "$DISABLE_ZENITY" == "1" ]]; then
    read -r -p "kind and kubectl installed. Create demo cluster with ingress controller now? [y/N]: " _create_demo
    if [[ "$_create_demo" =~ ^[Yy]$ ]]; then
        prompt_cluster_name || { zeninf "kind and kubectl installed successfully."; exit 0; }
        setup_kind_ingress_demo
        case $? in
            0)
                zeninf "Demo cluster '$CLUSTER_NAME' with ingress-nginx is ready."
                ;;
            10)
                zeninf "Cluster '$CLUSTER_NAME' already exists. Keeping current setup."
                ;;
            20|21)
                zenwrn "Cluster '$CLUSTER_NAME' was created, but ingress-nginx is not fully ready yet."
                ;;
            *)
                zenwrn "Could not create cluster '$CLUSTER_NAME' automatically."
                ;;
        esac
    else
        zeninf "kind and kubectl installed successfully."
    fi
else
    if zenity --question --title "Kind (Kubernetes)" --text "kind and kubectl were installed.\n\nDo you want to create a demo cluster with ingress-nginx now?" --ok-label="Create cluster" --cancel-label="Skip" --width=480 --height=280; then
        prompt_cluster_name || { zeninf "kind and kubectl installed successfully."; exit 0; }
        setup_kind_ingress_demo
        case $? in
            0)
                zeninf "Demo cluster '$CLUSTER_NAME' with ingress-nginx is ready."
                ;;
            10)
                zeninf "Cluster '$CLUSTER_NAME' already exists. Keeping current setup."
                ;;
            20|21)
                zenwrn "Cluster '$CLUSTER_NAME' was created, but ingress-nginx is not fully ready yet."
                ;;
            *)
                zenwrn "Could not create cluster '$CLUSTER_NAME' automatically."
                ;;
        esac
    else
        zeninf "kind and kubectl installed successfully."
    fi
fi
