#!/bin/bash

# Define caminhos e URLs estruturadas
DOWNLOAD_DIR="$HOME/Downloads/Atkinson_Hyperlegible"
FONT_DIR="$HOME/.local/share/fonts/truetype/atkinson_hyperlegible"
GITHUB_URL="https://raw.githubusercontent.com/google/fonts/main/ofl/atkinsonhyperlegible"

echo "=================================================="
echo "   Instalador da Fonte Atkinson Hyperlegible      "
echo "=================================================="

# 1. Cria e limpa o diretório de downloads temporários
echo "Preparando diretorios..."
mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$FONT_DIR"
cd "$DOWNLOAD_DIR" || exit 1

# Limpa instalações parciais anteriores na pasta de download
rm -f *.ttf OFL.txt

# 2. Baixa as fontes diretamente do GitHub oficial
echo "Baixando arquivos de fonte (.ttf)..."
FONT_FILES=(
    "AtkinsonHyperlegible-Regular.ttf"
    "AtkinsonHyperlegible-Italic.ttf"
    "AtkinsonHyperlegible-Bold.ttf"
    "AtkinsonHyperlegible-BoldItalic.ttf"
    "OFL.txt"
)

for file in "${FONT_FILES[@]}"; do
    echo "  Baixando $file..."
    if ! curl -L -f -sS -O "$GITHUB_URL/$file"; then
        echo "Erro ao baixar o arquivo $file. Verifique sua conexao."
        exit 1
    fi
done

# 3. Instala no sistema
echo "Instalando fontes em: $FONT_DIR"
cp *.ttf "$FONT_DIR/"

# 4. Atualiza o cache focado apenas na pasta do usuário (silencioso)
echo "Atualizando cache de fontes do sistema..."
fc-cache -f "$HOME/.local/share/fonts" 2>/dev/null

# 5. Aplica as fontes no GNOME com segurança
echo "Aplicando novas configuracoes no GNOME Ajustes..."

safe_gsettings() {
    env -u PYTHONHOME -u PYTHONPATH PATH="/usr/bin:/bin:$PATH" XDG_DATA_DIRS="/usr/share:/usr/local/share" gsettings "$@"
}

safe_gsettings set org.gnome.desktop.interface font-name "Atkinson Hyperlegible 12"
safe_gsettings set org.gnome.desktop.interface document-font-name "Atkinson Hyperlegible 12"
safe_gsettings set org.gnome.desktop.interface monospace-font-name "Ubuntu Sans Mono 12"

echo "=================================================="
echo " Sucesso! Fonte instalada e aplicada no sistema!"
echo " Seus menus e documentos ja mudaram automaticamente."
echo " Pasta de backup: $DOWNLOAD_DIR"
echo "=================================================="