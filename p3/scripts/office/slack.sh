#!/bin/bash
# NAME: Slack
# VERSION: 1.0
# DESCRIPTION: slack_desc

# --- Start of the script code ---
flatpak_in_lib
flatpak install --or-update --user --noninteractive com.slack.Slack
