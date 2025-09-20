#!/bin/bash
# name: Mongo + Mongo Express
# version: 1.0
# description: Mongo + Mongo Express
# icon: docker.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

sudo_rq
_docker_up "$SCRIPT_DIR/../resources/docker/mongo.yaml"