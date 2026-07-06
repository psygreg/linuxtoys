#!/bin/bash

echo "=================================================="
echo "    Restaurador de Fontes Padrao do Sistema        "
echo "=================================================="

# --- VERIFICAÇÃO DE DEPENDÊNCIAS ---
echo "Verificando dependencias no Ubuntu..."
for cmd in "fc-cache" "gsettings"; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "[ERRO] Ambiente incompativel. Ferramenta essencial '$cmd' nao encontrada."
        exit 1
    fi
done

echo "Tudo certo! Iniciando a restauracao..."
echo "--------------------------------------------------"
echo "Resetando configuracoes para o padrao de fabrica..."

safe_gsettings() {
    env -u PYTHONHOME -u PYTHONPATH PATH="/usr/bin:/bin:$PATH" XDG_DATA_DIRS="/usr/share:/usr/local/share" gsettings "$@"
}

# 1. Reseta as fontes da interface
safe_gsettings reset org.gnome.desktop.interface font-name
safe_gsettings reset org.gnome.desktop.interface document-font-name
safe_gsettings reset org.gnome.desktop.interface monospace-font-name

# 2. Remove os ficheiros fisicos
echo "Removendo ficheiros da fonte Atkinson..."
rm -rf "$HOME/.local/share/fonts/truetype/atkinson_hyperlegible"

# 3. Atualiza o cache focado apenas na pasta do usuário (silencioso)
echo "Atualizando cache de fontes do sistema..."
fc-cache -f "$HOME/.local/share/fonts" 2>/dev/null

echo "=================================================="
echo " Sucesso! O sistema foi totalmente restaurado."
echo " Fontes apagadas e interface revertida para o padrao."
echo "=================================================="