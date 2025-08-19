#!/bin/bash
# NAME: Slack
# VERSION: 1.0
# DESCRIPTION: slack_desc
# icon: slack

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.slack.Slack
