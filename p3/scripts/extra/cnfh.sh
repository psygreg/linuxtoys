#!/bin/bash
# name: Distrobox Command Handler
# version: 1.0
# description: dch_desc
# icon: cnfh.svg
# nocontainer: invert

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# Create the command-not-found handler
create_cnf_handler() {
    local handler_dir="$HOME/.local/distrobox-handler"
    local cnf_script="$handler_dir/command_not_found_handle"
    mkdir -p "$handler_dir"
    tee "$cnf_script" > /dev/null << 'EOF'
#!/bin/bash
# Distrobox Command-Not-Found Handler
# Automatically executes commands on host if not found in container
command_not_found_handle() {
    local cmd="$1"
    shift
    local args="$@"
    
    # Skip if distrobox-host-exec is not available
    if ! command -v distrobox-host-exec >/dev/null 2>&1; then
        echo "bash: $cmd: command not found" >&2
        return 127
    fi
    
    # Check if command exists on host
    if distrobox-host-exec which "$cmd" >/dev/null 2>&1; then
        echo "Command '$cmd' not found in container, executing on host..." >&2
        exec distrobox-host-exec "$cmd" "$@"
    else
        # Fallback to traditional command not found message
        echo "bash: $cmd: command not found" >&2
        return 127
    fi
}
EOF
    chmod +x "$cnf_script"
}
# Create zsh command-not-found handler
create_zsh_cnf_handler() {
    local handler_dir="$HOME/.local/distrobox-handler"
    local zsh_cnf_script="$handler_dir/zsh_command_not_found_handler"
    
    mkdir -p "$handler_dir"
    
    tee "$zsh_cnf_script" > /dev/null << 'EOF'
#!/bin/bash
# Distrobox ZSH Command-Not-Found Handler

zsh_command_not_found_handler() {
    local cmd="$1"
    shift
    local args="$@"
    
    # Skip if distrobox-host-exec is not available
    if ! command -v distrobox-host-exec >/dev/null 2>&1; then
        echo "zsh: command not found: $cmd" >&2
        return 127
    fi
    
    # Check if command exists on host
    if distrobox-host-exec which "$cmd" >/dev/null 2>&1; then
        echo "Command '$cmd' not found in container, executing on host..." >&2
        exec distrobox-host-exec "$cmd" "$@"
    else
        # Fallback to traditional command not found message
        echo "zsh: command not found: $cmd" >&2
        return 127
    fi
}
EOF
}
# Set up bash integration
setup_bash_integration() {
    local bashrc_addition="/etc/bash.bashrc.d/99-distrobox-cnf"
    
    sudo mkdir -p /etc/bash.bashrc.d
    
    sudo tee "$bashrc_addition" > /dev/null << EOF
# Distrobox Command-Not-Found Handler Integration
if [ -f "\$HOME/.local/distrobox-handler/command_not_found_handle" ]; then
    source "\$HOME/.local/distrobox-handler/command_not_found_handle"
fi
EOF

    # Also add to global bashrc if the directory approach doesn't work
    if ! grep -q "distrobox-handler/command_not_found_handle" /etc/bash.bashrc 2>/dev/null; then
        sudo tee -a /etc/bash.bashrc > /dev/null << 'EOF'

# Distrobox Command-Not-Found Handler Integration
if [ -f "$HOME/.local/distrobox-handler/command_not_found_handle" ]; then
    source "$HOME/.local/distrobox-handler/command_not_found_handle"
fi
EOF
    fi
}

# Set up zsh integration
setup_zsh_integration() {
    local zshrc_addition="/etc/zsh/zshrc.d/99-distrobox-cnf.zsh"
    sudo mkdir -p /etc/zsh/zshrc.d
    sudo tee "$zshrc_addition" > /dev/null << EOF

# Distrobox Command-Not-Found Handler Integration for ZSH
if [ -f "\$HOME/.local/distrobox-handler/zsh_command_not_found_handler" ]; then
    source "\$HOME/.local/distrobox-handler/zsh_command_not_found_handler"
fi
EOF
    # Also add to global zshrc
    if [ -f /etc/zsh/zshrc ] && ! grep -q "distrobox-handler/zsh_command_not_found_handler" /etc/zsh/zshrc; then
        sudo tee -a /etc/zsh/zshrc > /dev/null << 'EOF'

# Distrobox Command-Not-Found Handler Integration
if [ -f "$HOME/.local/distrobox-handler/zsh_command_not_found_handler" ]; then
    source "$HOME/.local/distrobox-handler/zsh_command_not_found_handler"
fi
EOF
    fi
}

# Create user-specific integration for immediate effect
setup_user_integration() {
    # Bash integration for current user
    if [ -f "$HOME/.bashrc" ]; then
        if ! grep -q "distrobox-handler/command_not_found_handle" "$HOME/.bashrc"; then
            tee -a "$HOME/.bashrc" > /dev/null << 'EOF'

# Distrobox Command-Not-Found Handler Integration
if [ -f "$HOME/.local/distrobox-handler/command_not_found_handle" ]; then
    source "$HOME/.local/distrobox-handler/command_not_found_handle"
fi
EOF
        fi
    fi
    
    # Zsh integration for current user
    if [ -f "$HOME/.zshrc" ]; then
        if ! grep -q "distrobox-handler/zsh_command_not_found_handler" "$HOME/.zshrc"; then
            tee -a "$HOME/.zshrc" > /dev/null << 'EOF'

# Distrobox Command-Not-Found Handler Integration
if [ -f "$HOME/.local/distrobox-handler/zsh_command_not_found_handler" ]; then
    source "$HOME/.local/distrobox-handler/zsh_command_not_found_handler"
fi
EOF
        fi
    fi
}

# Create commonly used host command aliases
create_host_aliases() {
    local alias_file="/etc/profile.d/distrobox-host-aliases.sh"
    sudo tee "$alias_file" > /dev/null << 'EOF'
# Common host command aliases for distrobox containers
# These commands are typically better run on the host

# File management and system tools
alias xdg-open='distrobox-host-exec xdg-open'
alias nautilus='distrobox-host-exec nautilus'
alias dolphin='distrobox-host-exec dolphin'
alias thunar='distrobox-host-exec thunar'

# System monitoring and hardware
alias htop='distrobox-host-exec htop'
alias lscpu='distrobox-host-exec lscpu'
alias lsusb='distrobox-host-exec lsusb'
alias lspci='distrobox-host-exec lspci'

# Network tools
alias nmcli='distrobox-host-exec nmcli'
alias nmtui='distrobox-host-exec nmtui'

# Package managers (host)
alias flatpak='distrobox-host-exec flatpak'
alias snap='distrobox-host-exec snap'

# Text editors that work better on host
alias gedit='distrobox-host-exec gedit'
alias kate='distrobox-host-exec kate'

# Media tools
alias firefox='distrobox-host-exec firefox'
alias chromium='distrobox-host-exec chromium'
alias google-chrome='distrobox-host-exec google-chrome'
EOF

    sudo chmod +x "$alias_file"
}
# Remove user integration
remove_user_integration() {
    # Remove from user's bashrc
    if [ -f "$HOME/.bashrc" ]; then
        # Create a temporary file without the distrobox integration
        grep -v "distrobox-handler/command_not_found_handle" "$HOME/.bashrc" > "$HOME/.bashrc.tmp"
        # Remove the comment line as well if it exists alone
        sed -i '/^# Distrobox Command-Not-Found Handler Integration$/d' "$HOME/.bashrc.tmp"
        # Remove empty lines that might be left behind
        sed -i '/^$/N;/^\n$/d' "$HOME/.bashrc.tmp"
        mv "$HOME/.bashrc.tmp" "$HOME/.bashrc"
    fi
    # Remove from user's zshrc
    if [ -f "$HOME/.zshrc" ]; then
        grep -v "distrobox-handler/zsh_command_not_found_handler" "$HOME/.zshrc" > "$HOME/.zshrc.tmp"
        sed -i '/^# Distrobox Command-Not-Found Handler Integration$/d' "$HOME/.zshrc.tmp"
        sed -i '/^$/N;/^\n$/d' "$HOME/.zshrc.tmp"
        mv "$HOME/.zshrc.tmp" "$HOME/.zshrc"
    fi
}

# Remove system integration
remove_system_integration() {
    # Remove bash integration files
    sudo rm -f /etc/bash.bashrc.d/99-distrobox-cnf
    # Remove from global bashrc
    if [ -f /etc/bash.bashrc ]; then
        sudo sed -i '/# Distrobox Command-Not-Found Handler Integration/,+3d' /etc/bash.bashrc
    fi
    # Remove zsh integration files
    sudo rm -f /etc/zsh/zshrc.d/99-distrobox-cnf.zsh
    # Remove from global zshrc
    if [ -f /etc/zsh/zshrc ]; then
        sudo sed -i '/# Distrobox Command-Not-Found Handler Integration/,+3d' /etc/zsh/zshrc
    fi
    # Remove host aliases
    sudo rm -f /etc/profile.d/distrobox-host-aliases.sh
}
# Check if the handler is installed
is_handler_installed() {
    local handler_dir="$HOME/.local/distrobox-handler"
    local cnf_script="$handler_dir/command_not_found_handle"
    local zsh_cnf_script="$handler_dir/zsh_command_not_found_handler"
    # Check if handler files exist
    if [ -f "$cnf_script" ] || [ -f "$zsh_cnf_script" ]; then
        return 0  # Installed
    fi
    # Check if integration exists in user configs
    if [ -f "$HOME/.bashrc" ] && grep -q "distrobox-handler" "$HOME/.bashrc"; then
        return 0  # Installed
    fi
    if [ -f "$HOME/.zshrc" ] && grep -q "distrobox-handler" "$HOME/.zshrc"; then
        return 0  # Installed
    fi
    # Check if system-wide integration exists
    if [ -f "/etc/bash.bashrc.d/99-distrobox-cnf" ] || [ -f "/etc/zsh/zshrc.d/99-distrobox-cnf.zsh" ]; then
        return 0  # Installed
    fi
    if [ -f "/etc/profile.d/distrobox-host-aliases.sh" ]; then
        return 0  # Installed
    fi
    return 1  # Not installed
}
# Remove handler files
remove_handler_files() {
    local handler_dir="$HOME/.local/distrobox-handler"
    if [ -d "$handler_dir" ]; then
        rm -rf "$handler_dir"
        echo "Removed handler directory: $handler_dir"
    fi
}
# Complete removal function
remove_cnf_handler() {
    echo "=== Removing Distrobox Command-Not-Found Handler ==="
    echo ""
    remove_user_integration
    remove_system_integration
    remove_handler_files
    echo ""
    echo "=== Removal completed successfully! ==="
    echo ""
    echo "To complete the removal:"
    echo "  • Restart your terminal sessions, or"
    echo "  • Source your shell config:"
    echo "    source ~/.bashrc    (for bash)"
    echo "    source ~/.zshrc     (for zsh)"
    echo ""
}
# Show usage examples
show_examples() {
    echo ""
    echo "=== Distrobox Command-Not-Found Handler Installed ==="
    echo ""
    echo "Examples of what this enables:"
    echo "  • Type 'firefox' in container → automatically runs on host"
    echo "  • Type 'xdg-open document.pdf' → opens with host's default app"
    echo "  • Type 'htop' → shows host system monitoring"
    echo ""
    echo "To test immediately, source your shell config:"
    echo "  source ~/.bashrc    (for bash)"
    echo "  source ~/.zshrc     (for zsh)"
    echo ""
    echo "Or simply open a new terminal session."
    echo ""
}
# Main installation function
install_cnf_handler() {
    echo "=== Installing Distrobox Command-Not-Found Handler ==="
    echo ""
    create_cnf_handler
    create_zsh_cnf_handler
    setup_bash_integration
    setup_zsh_integration
    setup_user_integration
    create_host_aliases
    echo ""
    echo "Installation completed successfully!"
    show_examples
}
sudo_rq
if is_handler_installed; then
    echo "Distrobox command-not-found handler is currently installed."
    echo "Running removal mode..."
    echo ""
    remove_cnf_handler
else
    echo "Distrobox command-not-found handler is not installed."
    echo "Running installation mode..."
    echo ""
    install_cnf_handler
fi