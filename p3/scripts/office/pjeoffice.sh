#!/bin/bash
# name: PJeOffice Pro
# version: 1.0
# description: Um software disponibilizado gratuitamente pelo Conselho Nacional de Justiça (CNJ) do Brasil para acesso ao PJE via certificado digital e assinatura eletrônica de documentos.
# icon: pjeoffice-pro.png
# compat: debian, ubuntu
# localize: pt

# --- Start of the script code ---
cd $HOME
tag=$(curl -s "https://api.github.com/repos/psygreg/pje-installer/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
wget https://github.com/psygreg/pje-installer/releases/download/${tag}/pje-installer_${tag}-1_amd64.deb
sudo apt install -y ./pje-installer_${tag}-1_amd64.deb
rm ./pje-installer_${tag}-1_amd64.deb