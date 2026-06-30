#!/bin/bash
# name: Skills Seeker
# version: 1.0
# description: skills_seeker_desc
# icon: skills-seeker.svg
# compat: debian, ubuntu, fedora, arch, cachy, ostree, rhel, suse, solus
# noconfirm: yes
# nocontainer:

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_

FETCHER="$SCRIPT_DIR/../../app/skills_fetcher.py"
PYTHON=$(command -v python3)

_zen_fallback() {
    "$@" 2>/dev/null
    return $?
}

show_main_menu() {
    choice=$(zenity --list --title="Skills Seeker" \
        --column="Option" --column="Description" \
        "search" "$_skills_search_label" \
        "trending" "$_skills_trending_label" \
        "hot" "$_skills_hot_label" \
        "official" "$_skills_official_label" \
        "installed" "$_skills_installed_label" \
        "clear_cache" "$_skills_clear_cache_label" \
        --height=320 --width=450 2>/dev/null) || return 1
    echo "$choice"
}

run_search() {
    query=$(zenity --entry --title="$_skills_search_title" \
        --text="$_skills_search_text" --width=400 2>/dev/null) || return 1
    [ -z "$query" ] && return 0
    _do_search "$query"
}

_do_search() {
    local query="$1"
    local json
    json=$("$PYTHON" "$FETCHER" search "$query" 30 2>/dev/null) || {
        zeninf "$_skills_error_fetch" 2>/dev/null || echo "$_skills_error_fetch"
        return 1
    }
    _show_results "$json" "$query"
}

_show_results() {
    local json="$1"
    local query="$2"
    local list_items
    list_items=$(echo "$json" | "$PYTHON" -c "
import json,sys
data=json.load(sys.stdin)
for s in data.get('skills',[]):
    name=s.get('name','')
    inst=s.get('installs',0)
    src=s.get('source','')
    if inst>=1_000_000: inst_str=f'{inst/1_000_000:.1f}M'
    elif inst>=1_000: inst_str=f'{inst/1_000:.1f}K'
    else: inst_str=str(inst)
    print(f'{name}\t{inst_str}\t{src}')
" 2>/dev/null) || {
        zeninf "$_skills_error_parse" 2>/dev/null || echo "$_skills_error_parse"
        return 1
    }
    [ -z "$list_items" ] && {
        zeninf "$_skills_no_results" 2>/dev/null || echo "$_skills_no_results"
        return 0
    }
    local selected
    selected=$(zenity --list --title="$_skills_results_title" \
        --column="$_skills_col_name" --column="$_skills_col_installs" --column="$_skills_col_source" \
        --width=600 --height=400 $list_items 2>/dev/null) || return 1
    [ -z "$selected" ] && return 0
    _handle_skill_selection "$selected"
}

_handle_skill_selection() {
    local selected_name="$1"
    local skill_id source slug
    skill_id=$(echo "$selected_name" | awk '{print $1}')
    if [[ "$skill_id" == */* ]]; then
        source="${skill_id%/*}"
        slug="${skill_id##*/}"
    else
        source=""
        slug="$skill_id"
    fi
    local detail_json
    detail_json=$("$PYTHON" "$FETCHER" search "$slug" 5 2>/dev/null) || {
        zeninf "$_skills_error_fetch" 2>/dev/null
        return 1
    }
    local matched_id matched_source matched_name
    matched_id=$(echo "$detail_json" | "$PYTHON" -c "
import json,sys
data=json.load(sys.stdin)
for s in data.get('skills',[]):
    if s.get('skillId','').lower()=='$slug' or s.get('name','').lower()=='$slug':
        print(s['id'])
        break
" 2>/dev/null) || matched_id=""
    if [ -n "$matched_id" ]; then
        source="${matched_id%/*}"
        slug="${matched_id##*/}"
    fi
    local action
    action=$(zenity --list --title="$_skills_action_title" \
        --column="Action" --column="Description" \
        "install" "$_skills_install_label" \
        "detail" "$_skills_detail_label" \
        "back" "$_skills_back_label" \
        --width=400 --height=250 2>/dev/null) || return 0
    case "$action" in
        install) _install_skill "$source" "$slug" ;;
        detail)  _show_detail "$source" "$slug" ;;
        *) return 0 ;;
    esac
}

_show_detail() {
    local source="$1" slug="$2"
    local detail_json
    detail_json=$("$PYTHON" "$FETCHER" detail "$source" "$slug" 2>/dev/null) || {
        zeninf "$_skills_error_fetch" 2>/dev/null
        return 1
    }
    local name desc installs files_str
    name=$(echo "$detail_json" | "$PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('name',''))" 2>/dev/null) || name=""
    desc=$(echo "$detail_json" | "$PYTHON" -c "import json,sys; print(json.load(sys.stdin).get('description',''))" 2>/dev/null) || desc=""
    installs=$(echo "$detail_json" | "$PYTHON" -c "
import json,sys
d=json.load(sys.stdin)
i=d.get('installs',0)
print(f'{i:,}' if i<1000 else (f'{i/1000:.1f}K' if i<1_000_000 else f'{i/1_000_000:.1f}M'))
" 2>/dev/null) || installs=""
    files_str=$(echo "$detail_json" | "$PYTHON" -c "
import json,sys
d=json.load(sys.stdin)
files=d.get('files',[])
print('\n'.join(files) if files else '$_skills_no_files')
" 2>/dev/null) || files_str=""
    zenity --info --title="$_skills_detail_title" \
        --text="<b>$name</b>\n\n$desc\n\n<b>$_skills_col_installs:</b> $installs\n<b>$_skills_files_label:</b>\n$files_str" \
        --width=500 2>/dev/null || {
            echo "=== $name ==="
            echo "$desc"
            echo "Installs: $installs"
            echo "Files:"
            echo "$files_str"
        }
}

_install_skill() {
    local source="$1" slug="$2"
    [ -z "$source" ] && {
        zeninf "$_skills_error_no_source" 2>/dev/null || echo "$_skills_error_no_source"
        return 1
    }
    local agents=()
    [[ -d "$HOME/.claude" ]] && agents+=("claude-code")
    [[ -d "$HOME/.codex" ]] && agents+=("codex")
    [[ -d "$HOME/.config/opencode" ]] && agents+=("opencode")
    [[ -d "$HOME/.cursor" ]] && agents+=("cursor")
    [[ -d "$HOME/.windsurf" ]] && agents+=("windsurf")
    [[ -d "$HOME/.gemini" ]] && agents+=("gemini-cli")
    [[ -d "$HOME/.agents" ]] && agents+=("cline")
    [[ -d "$HOME/.roo" ]] && agents+=("roo")
    [[ -d "$HOME/.trae" ]] && agents+=("trae")
    [[ -d "$HOME/.kilocode" ]] && agents+=("kilo")
    [[ -d "$HOME/.factory" ]] && agents+=("droid")
    [[ -d "$HOME/.copilot" ]] && agents+=("github-copilot")
    if [ ${#agents[@]} -eq 0 ]; then
        zeninf "$_skills_no_agents" 2>/dev/null || echo "$_skills_no_agents"
        return 1
    fi
    local agent_list=""
    for a in "${agents[@]}"; do
        agent_list+="$a\n"
    done
    local chosen_agent
    chosen_agent=$(echo -e "$agent_list" | \
        zenity --list --title="$_skills_choose_agent_title" \
        --column="Agent" --height=300 --width=300 2>/dev/null) || return 1
    [ -z "$chosen_agent" ] && return 0
    local skill_ref="${source}/${slug}"
    if ! zenask "$_skills_confirm_title" \
        "$_skills_confirm_msg\n\n$skill_ref\n$_skills_agent_label: $chosen_agent" 400 200 2>/dev/null; then
        return 0
    fi
    pkg_npm npm
    local install_log
    install_log=$(mktemp)
    npx skills add "$source" -a "$chosen_agent" -g -y --skill "$slug" > "$install_log" 2>&1
    local rc=$?
    if [ $rc -eq 0 ]; then
        zeninf "$_skills_success_msg\n\n$skill_ref" 2>/dev/null || echo "$_skills_success_msg"
    else
        local error_tail
        error_tail=$(tail -5 "$install_log" | tr '\n' ' ')
        zeninf "$_skills_error_install\n\n$error_tail" 2>/dev/null || {
            echo "$_skills_error_install"
            cat "$install_log"
        }
    fi
    rm -f "$install_log"
}

_run_trending() {
    local json
    json=$("$PYTHON" "$FETCHER" trending 30 2>/dev/null) || {
        zeninf "$_skills_error_fetch" 2>/dev/null
        return 1
    }
    _show_results "$json" "trending"
}

_run_hot() {
    local json
    json=$("$PYTHON" "$FETCHER" hot 30 2>/dev/null) || {
        zeninf "$_skills_error_fetch" 2>/dev/null
        return 1
    }
    _show_results "$json" "hot"
}

_run_official() {
    local json
    json=$("$PYTHON" "$FETCHER" all-time 50 2>/dev/null) || {
        zeninf "$_skills_error_fetch" 2>/dev/null
        return 1
    }
    _show_results "$json" "official"
}

_run_installed() {
    local list_json
    list_json=$(npx skills list 2>/dev/null) || {
        zeninf "$_skills_error_list" 2>/dev/null
        return 1
    }
    local formatted
    formatted=$(echo "$list_json" | "$PYTHON" -c "
import json,sys
try:
    data=json.load(sys.stdin)
    for s in data:
        print(f\"{s.get('name','')}\t{s.get('scope','')}\t{', '.join(s.get('agents',[]))}\")
except: pass
" 2>/dev/null) || formatted=""
    if [ -z "$formatted" ]; then
        zeninf "$_skills_no_installed" 2>/dev/null || echo "$_skills_no_installed"
        return 0
    fi
    zenity --text-info --title="$_skills_installed_title" \
        --width=600 --height=400 --filename=/dev/stdin <<< "$formatted" 2>/dev/null || echo "$formatted"
}

while true; do
    choice=$(show_main_menu) || break
    case "$choice" in
        search)     run_search ;;
        trending)   _run_trending ;;
        hot)        _run_hot ;;
        official)   _run_official ;;
        installed)  _run_installed ;;
        clear_cache)
            "$PYTHON" "$FETCHER" clear_cache 2>/dev/null
            zeninf "$_skills_cache_cleared" 2>/dev/null || echo "$_skills_cache_cleared"
            ;;
        *) break ;;
    esac
done
