#!/usr/bin/env bash

if ! curl -fsSL -o /tmp/webmin-setup-repo.sh https://raw.githubusercontent.com/webmin/webmin/master/webmin-setup-repo.sh; then
    die "Failed to download Webmin repository setup script."
fi

if ! sudo sh /tmp/webmin-setup-repo.sh -f; then
    rm -f /tmp/webmin-setup-repo.sh
    die "Failed to setup Webmin repository."
fi