#!/bin/bash
# name: Postgres + pgAdmin
# version: 1.0
# description: Postgres + pgAdmin
# icon: docker.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

sudo_rq
_docker_up "$SCRIPT_DIR/../resources/docker/postgres.yaml"
