#!/usr/bin/env python3

import os
import sys
from .parser import get_categories, get_all_scripts_recursive
from .update_helper import get_current_version
from .cli_helper import run_manifest_mode
from .cli_helper import run_update_check_cli
from .cli_helper import find_script_by_name
from .cli_helper import run_script


def easy_cli_run_script(script_info):

    # Disable zenity for CLI execution
    # This prevents GUI dialogs from appearing during script execution
    # We handle user prompts via CLI instead
    os.environ['DISABLE_ZENITY'] = '1'

    
    try:
        run_script(script_info)
    except KeyboardInterrupt:
        print("\n⚠️  Programa encerrado pelo usuário.")
        return 130  # código padrão de interrupção Ctrl+C
    except Exception as e:
        print(f"✗ Erro ao executar o script: {e}")
        return 1
    return 0


def confirm_action(action_to_confirm_message):
    """Pergunta ao usuário se deseja continuar após falha."""
    try:
        response = input(f"{action_to_confirm_message} [y/N]: ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Operação cancelada.")
            return False
    except KeyboardInterrupt:
        print("\n⚠️  Operação cancelada pelo usuário.")
        return False
    return True


def execute_scripts_with_feedback(scripts_found):
    total = len(scripts_found)
    
    for index, script_info in enumerate(scripts_found, 1):
        name = script_info.get("name", os.path.basename(script_info["path"]))
        print(f"\n[{index}/{total}] 🚀 Executando: {name}")
        print("=" * 60)

        exit_code = easy_cli_run_script(script_info)

        if exit_code == 0:
            print(f"✓ {name} concluído com sucesso.")
        elif exit_code == 130:
            print("⚠️  Execução interrompida pelo usuário.")
            break
        else:
            print(f"✗ {name} falhou com código {exit_code}.")
            # Pergunta se o usuário quer continuar com os itens restantes
            if not confirm_action("Deseja continuar com os scripts restantes?"):
                break



def scripts_install(args:list, skip_confirmation, translations):

    # Filtra a lista de scripts removendo os flags de confirmação
    install_list = [arg for arg in args if arg not in ("-y", "--yes")]

    # Verifica se algum script foi especificado
    if not install_list:
        print("✗ Nenhum item especificado para instalação.\n")
        print("Use: ")
        print("   EASY_CLI=1 python3 run.py --install [option] <item1> <item2> ...")
        return 0  # Interrompe o fluxo normal do programa

    print("🧰 EASY CLI INSTALL MODE")
    print("=" * 60)
    print(f"📜 Scripts solicitados: {', '.join(install_list)}\n")

    scripts_found_list = []
    scripts_missing = []

    # Busca scripts com find_script_by_name()
    for script_name in install_list:
        script_info = find_script_by_name(script_name, translations)

        if script_info:
            scripts_found_list.append(script_info)
        else:
            scripts_missing.append(script_name)

    # Relatório de scripts não encontrados
    if scripts_missing:
        print("⚠️  Scripts não encontrados:")
        for name in scripts_missing:
            print(f" - {name}")
        print()

    if not scripts_found_list:
        print("✗ Nenhum script válido encontrado. Abortando.")
        return True

    # Relatório dos scripts encontrados
    print(f"✅ {len(scripts_found_list)} script(s) encontrados e prontos para execução:\n")
    for script_info in scripts_found_list:
        print(f" - {script_info['name']} | {os.path.basename (script_info['path'])}")
    print()

    # Pergunta ao usuário se deseja continuar
    if skip_confirmation or confirm_action("Deseja continuar com a execução dos scripts?"):
        execute_scripts_with_feedback(scripts_found_list)

def print_script_list(translations):
    scripts = get_all_scripts(translations)

    # Calcula larguras para alinhar colunas
    max_file_len = max(len(os.path.splitext(os.path.basename(s["path"]))[0]) for s in scripts)
    max_name_len = max(len(s["name"]) for s in scripts)

    print(f"\nScripts encontrados: {len(scripts)}\n")

    print(f"   {'SCRIPT':<{max_file_len}}     {'NAME':<{max_name_len}}")
    print("=" * (max_file_len + max_name_len + 4))

    for script in sorted(scripts, key=lambda s: s["name"].lower()):
        filename = os.path.splitext(os.path.basename(script["path"]))[0]
        print(f" - {filename:<{max_file_len}} --> {script['name']:<{max_name_len}}")

def get_all_scripts(translations=None):
    """
    Return a sorted list of all scripts as objects with 'name' and 'path' keys.
    Includes nested categories and root scripts.
    """
    scripts = []
    categories = get_categories(translations) or []

    def add_script(name, path):
        if not name or not path:
            return
        scripts.append({"name": name, "path": path})

    for category in categories:
        path = category.get('path')
        name = category.get('name')
        if not path or not name:
            continue

        if category.get('is_script'):
            add_script(name, path)
        else:
            for script in (get_all_scripts_recursive(path, translations) or []):
                add_script(script.get('name'), script.get('path'))

    # Remove duplicados e ordena por nome
    unique_scripts = { (s["name"], s["path"]) : s for s in scripts }.values()
    return sorted(unique_scripts, key=lambda s: s["name"])

    
def easy_cli_help_mansage():
    """
    Print usage information for EASY CLI mode.

    To use it with the source code, run the following command:
    #### EASY_CLI=1 SCRIPT_DIR=[path/to/lunuxtoys/p3] python3 run.py --install [option] <item1> <item2> ...

    """
    print("LinuxToys EASY CLI Usage:")
    print("=" * 60)
    print("Usage:")
    print("  EASY_CLI=1 python3 run.py --install [option] <item1> <item2> ...")
    print()
    print("Funcions:")
    print("  -i, --install              Install selected options")
    print()
    print("Install options:")
    print("  -s, --script       Install specified LinuxToys scripts")
    print("  -p, --package      Install specified system packages")
    print("  -f, --flatpak      Install specified Flatpak packages")
    print("  -l, --list         List all available scripts")
    print()
    print("Examples:")
    print("  EASY_CLI=1 python3 run.py --install -s script1 script2")
    print("  EASY_CLI=1 python3 run.py --install -p package1 package2")
    print("  EASY_CLI=1 python3 run.py --install -f flatpak1 flatpak2")
    print()
    print("Other options:")
    print("  -h, --help         Show this help message")
    print("  -m, --manifest     Enable manifest mode features")
    print("  -v, --version      Show version information")
    print("  -y, --yes          Skip confirmation prompts (recommended to use as the last argument)")
    print()

    
        
def easy_cli_handler(translations=None):
    """
    Handles the EASY CLI mode for LinuxToys.

    This function parses command-line arguments when EASY_CLI mode is active 
    (EASY_CLI=1) and executes the corresponding actions such as:

    - Installing scripts (--install -s <script1> <script2> ...)
    - Listing available scripts (--install -l)
    - Checking for updates (update, upgrade, --check-updates)
    - Running in manifest mode (--manifest, -m)
    - Displaying version (-v, --version)
    - Displaying help (-h, --help)

    It also supports developer mode (-D, --DEV_MODE) and optional automatic 
    confirmation flags (-y, --yes) to skip prompts.
    """

    # --- DEVELOPER MODE ---
    def dev_check(args):
        dev_flags = ("-D", "--DEV_MODE")
        found = False

        for flag in dev_flags:
            while flag in args:
                args.remove(flag)
                found = True

        if found and not os.environ.get("DEV_MODE"):
            # Set DEV_MODE environment variable
            os.environ["DEV_MODE"] = "1"

                    # --- DEVELOPER MODE BANNER ---
            try:
                from app.dev_mode import print_dev_mode_banner
                print_dev_mode_banner()
            except ImportError:
                pass  # dev_mode not available

    # --- SKIP CONFIRMATION ---
    def skip_confirmation(args):
        if os.environ.get("DEV_MODE") == "1":
            return True
        
        skip_flags = ("-y", "--yes")
        found = False

        for flag in skip_flags:
            while flag in args:
                args.remove(flag)
                found = True

        return found


    args = sys.argv[1:]

    dev_check(args)


    if not args:
        print("✗ Nenhum argumento fornecido.\n")
        easy_cli_help_mansage()
        return 0
    
    if args[0] in ("-i", "--install"):
        if args[1] in ("-l", "--list"):
            print_script_list(translations)
            return 0
        
        if args[1] in ("-s", "--script"): # Para instalação de scripts
            scripts_install(args[2:], skip_confirmation(args), translations)
            return 0
        
        # TODO : Implementar instalação de pacotes e flatpaks
        # elif args[1] in ("-p", "--package"): # Para instalação de pacotes
        #     packages_install(args[2:], skip_confirmation(args), translations)
        #     return 0

        # elif args[1] in ("-f", "--flatpak"): # Para instalação de flatpaks
        #     flatpaks_install(args[2:], skip_confirmation(args), translations)
        #     return 0

        else:
            print("✗ Parâmetro inválido após '--install'. \n ")
            print("Use:")
            print("  [-s | --script]    for scripts")
            print("  [-p | --package]   for pacotes")
            print("  [-f | --flatpak]   for flatpaks")
            print("  [-l | --list]      to list all available scripts")
            return 0
        

    elif args[0] in ("-h", "--help", "help"):
        easy_cli_help_mansage()
        return 0
    
    elif args[0] in ("update", "upgrade", "check-updates", "update-check", "--check-updates"):
        return 1 if run_update_check_cli(translations) else 0
    
    elif args[0] in ("--manifest", "-m"):
        # Run in CLI mode using manifest.txt
        return run_manifest_mode(translations)
    
    elif args[0] in ("-v", "--version"):
        print(f"LinuxToys {get_current_version()}")
        return 0

    else:
        print(f"\n✗ Ação desconhecida: {args[0]} \n")
        easy_cli_help_mansage()
        return 0
    
