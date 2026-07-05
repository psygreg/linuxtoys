#!/bin/bash

echo "=================================================="
echo "   Restaurador de Fontes Padrao do Sistema        "
echo "=================================================="

echo "Resetando configuracoes para o padrao de fabrica..."

# Forca a saida de qualquer ambiente virtual ativo apenas dentro deste script
if [ -n "$CONDA_DEFAULT_ENV" ]; then
    conda deactivate 2>/dev/null
fi

if [ -n "$VIRTUAL_ENV" ]; then
    deactivate 2>/dev/null
fi

# 1. Reseta as fontes da interface no banco de dados do GNOME
gsettings reset org.gnome.desktop.interface font-name
gsettings reset org.gnome.desktop.interface document-font-name
gsettings reset org.gnome.desktop.interface monospace-font-name

# 2. Remove os ficheiros fisicos para garantir lixo zero absoluto
echo "Removendo ficheiros da fonte Atkinson..."
rm -rf "$HOME/.local/share/fonts/truetype/atkinson_hyperlegible"

# 3. Atualiza o cache do sistema para consolidar a remocao
echo "Atualizando cache de fontes do sistema..."
fc-cache -f

echo "=================================================="
echo " Sucesso! O sistema foi totalmente restaurado."
echo " Fontes apagadas e interface revertida para o padrao."
echo "=================================================="