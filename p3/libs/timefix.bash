# --- Time Synchronization Guard ---
# Debian 13+ (and Ubuntu 25.10+ and Kali rolling) verify repository signatures
# with Sequoia's sqv instead of gpgv, which is far stricter about signature
# validity windows. A system clock that runs behind real time turns freshly
# signed repository metadata into "future-dated" content and apt reports:
#
#   Sub-process /usr/bin/sqv returned an error code (1), error message is:
#   Verifying signature: Not live until ...
#
# which reads like a key or repository problem but is a pure clock-skew
# symptom. The same skew also breaks TLS and any other signed package layer
# once it grows past minutes.
#
# timefix_bootguard enforces, silently and once per boot, that the system
# clock agrees with an external reference before any script code runs:
#
#  - Fast path: systemd already reports an NTP-synchronized clock. The boot
#    gets stamped and later runs return in milliseconds.
#  - The reference is a CDN Date header fetched over HTTP, because that is
#    the exact transport package managers already rely on: it keeps working
#    where NTP (UDP 123) is firewalled.
#  - Corrective order: enable the system's NTP service (systemd timedated),
#    then one-shot NTP utilities (chronyd -q, ntpdate, sntp, ntpd -q), then
#    a hard step against the reference itself. A hard step needs existing
#    privilege (root, a cached sudo ticket, or a run0-sudo session): with no
#    privilege available the boot is stamped "pending" and askpass's success
#    hook completes the correction right after the first authorization.
#  - Stamp states: "synced", "pending" (privilege owed - completed by
#    timefix_afterauth), "soft:<epoch>" (no reachable reference; retried
#    after _TIMEFIX_SOFT_RETRY seconds) and "failed" (corrective attempts
#    exhausted for this boot). Boot-scoped through /proc/sys/kernel/random/
#    boot_id, so a reboot always re-runs the check.
#
# It never shows a dialog, never installs packages, and only steps the clock
# further than the tolerance below when absolutely justified. Call it as
# `timefix_bootguard || true` (set -e hardening). Set LINUXTOYS_TIMEFIX=0 to
# skip enforcement entirely.

_TIMEFIX_TOLERANCE=60
_TIMEFIX_SOFT_RETRY=600
LINUXTOYS_TIMEFIX_BUSY=0

# Stamp file location. Per-user runtime dirs are tmpfs on boot-aware inits,
# and the boot_id check keeps the guard honest on distros with a persistent
# /tmp or a root service that shares /run.
_timefix_stamp_path () {
    if [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -d "$XDG_RUNTIME_DIR" ]; then
        printf '%s/linuxtoys-timefix.stamp\n' "$XDG_RUNTIME_DIR"
        return 0
    fi
    if [ "$(id -u 2>/dev/null)" = "0" ]; then
        printf '/run/linuxtoys-timefix.stamp\n'
    else
        printf '%s/linuxtoys-timefix.stamp\n' "${TMPDIR:-/tmp}"
    fi
    return 0
}

_timefix_boot_id () {
    local boot
    boot="$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)" || return 1
    [ -n "$boot" ] || return 1
    printf '%s\n' "$boot"
}

_timefix_stamp_write () {
    local stamp boot
    stamp=$(_timefix_stamp_path) || return 1
    boot=$(_timefix_boot_id) || return 1
    printf '%s\n%s\n' "$1" "$boot" > "$stamp" 2>/dev/null
    return 0
}

# Current boot stamp token on stdout: synced | pending | failed | soft:<epoch>.
# Stamps from a previous boot (boot_id mismatch) read as none.
_timefix_stamp_state () {
    local stamp boot token
    stamp=$(_timefix_stamp_path) || { printf 'none\n'; return 0; }
    boot=$(_timefix_boot_id) || { printf 'none\n'; return 0; }
    if [ -r "$stamp" ]; then
        token="$(head -n 1 "$stamp" 2>/dev/null)"
        if [ "$(tail -n 1 "$stamp" 2>/dev/null)" = "$boot" ]; then
            case "$token" in
                synced|pending|failed)
                    printf '%s\n' "$token"
                    return 0
                    ;;
                soft:*)
                    printf '%s\n' "$token"
                    return 0
                    ;;
            esac
        fi
    fi
    printf 'none\n'
    return 0
}

# Parse an RFC 2822 (HTTP Date) timestamp into a Unix epoch.
_timefix_parse_date () {
    local epoch
    epoch=$(LC_ALL=C date -u -d "$1" +%s 2>/dev/null) || return 1
    case "$epoch" in
        ''|*[!0-9]*) return 1 ;;
    esac
    printf '%s\n' "$epoch"
    return 0
}

# Reference clock: the mirror/CDN's own HTTP Date header, as a Unix epoch.
# Debian's CDN answers globally; google.com only backs it up for restrictive
# networks. curl is preferred (scripts install it all the time); wget does
# "spider" requests just as silent. Fails only when nothing is reachable.
_TIMEFIX_HTTP_HOSTS="deb.debian.org security.debian.org www.google.com"

_timefix_http_epoch () {
    local host hdr epoch
    for host in $_TIMEFIX_HTTP_HOSTS; do
        if command -v curl >/dev/null 2>&1; then
            hdr=$(curl -fsSI --max-time 5 "http://$host/" 2>/dev/null) || hdr=""
        elif command -v wget >/dev/null 2>&1; then
            hdr=$(wget -q -S --spider --timeout=5 -O /dev/null "http://$host/" 2>&1) || hdr=""
        else
            return 1
        fi
        hdr=$(printf '%s\n' "${hdr:-}" | tr -d '\r' | sed -n 's/^[[:space:]]*[Dd]ate:[[:space:]]*//p' | tail -n 1)
        [ -n "$hdr" ] || continue
        epoch=$(_timefix_parse_date "$hdr") || continue
        printf '%s\n' "$epoch"
        return 0
    done
    return 1
}

# Local clock minus reference, in seconds. Negative means behind real time,
# the direction apt's "Not live until" reports; ahead counts too (certs and
# sqv both reject the other direction once it grows).
_timefix_skew () {
    local reference
    reference=$(_timefix_http_epoch) || return 1
    printf '%s\n' $(( $(date -u +%s) - reference ))
    return 0
}

_timefix_skew_ok () {
    local skew
    skew=$(_timefix_skew) || return 1
    if [ "$skew" -le "$_TIMEFIX_TOLERANCE" ] && [ "$skew" -ge "-$_TIMEFIX_TOLERANCE" ]; then
        return 0
    fi
    return 1
}

# Whether a "soft:<epoch>" stamp is still inside its retry window.
_timefix_soft_fresh () {
    local epoch now
    epoch="${1#soft:}"
    case "$epoch" in
        ''|*[!0-9]*) return 1 ;;
    esac
    now=$(date -u +%s 2>/dev/null) || return 1
    if [ $((now - epoch)) -lt "$_TIMEFIX_SOFT_RETRY" ]; then
        return 0
    fi
    return 1
}

# Poll the NTP path for up to ~10s before moving on to one-shots.
_timefix_ntp_poll () {
    local attempt
    for attempt in 1 2 3 4 5; do
        if _timefix_skew_ok; then
            return 0
        fi
        sleep 2
    done
    return 1
}

# Privilege-confirmed correction ladder. $1 is the skew observed by the
# caller (used only for reporting context). Returns 0 when the clock reads
# real time within tolerance, 1 when the boot is beyond repair here.
_timefix_apply () {
    local skew="$1" reference attempt

    # 1) systemd time management: let the always-running service take over,
    #    and give it a few poll cycles to reach a server.
    if command -v timedatectl >/dev/null 2>&1; then
        sudo_ timedatectl set-ntp true || true
        if _timefix_ntp_poll; then
            return 0
        fi
    fi

    # 2) one-shot NTP clients, common across the distro families this app
    #    supports and init-independent. Each one is best-effort; a recheck
    #    after each keeps later attempts off healthy clocks.
    if command -v chronyd >/dev/null 2>&1; then
        sudo_ chronyd -q || true
        if _timefix_skew_ok; then
            return 0
        fi
    fi
    if command -v ntpdate >/dev/null 2>&1; then
        sudo_ ntpdate pool.ntp.org || true
        if _timefix_skew_ok; then
            return 0
        fi
    fi
    if command -v sntp >/dev/null 2>&1; then
        sudo_ sntp -s pool.ntp.org || true
        if _timefix_skew_ok; then
            return 0
        fi
    fi
    if command -v ntpd >/dev/null 2>&1; then
        sudo_ ntpd -q -p pool.ntp.org || true
        if _timefix_skew_ok; then
            return 0
        fi
    fi

    # 3) hard step against the reference itself: works wherever the package
    #    manager already reached the network, even with NTP filtered out.
    if reference=$(_timefix_http_epoch); then
        if command -v timedatectl >/dev/null 2>&1; then
            # set-time refuses while an NTP service is running, and parses
            # its argument in the machine's local timezone: disable NTP and
            # render the epoch in local wall-clock form.
            sudo_ timedatectl set-ntp false || true
            if sudo_ timedatectl set-time "$(LC_ALL=C date -d "@$reference" +'%Y-%m-%d %H:%M:%S')"; then
                sudo_ timedatectl set-ntp true || true
                if _timefix_skew_ok; then
                    return 0
                fi
            fi
        else
            if sudo_ date -u -s "@$reference"; then
                sudo_ hwclock --systohc || true
                if _timefix_skew_ok; then
                    return 0
                fi
            fi
        fi
    fi

    return 1
}

_timefix_abs () {
    if [ "$1" -lt 0 ]; then
        echo "$(( -1 * $1 ))"
    else
        echo "$1"
    fi
}

# Orchestrator. Outcomes:
#   0 healthy (within tolerance, nothing to do)
#   1 no reachable reference right now
#   2 skew confirmed but no privilege available right now
#   3 skewed and the correction ladder could not fix it
#   4 skewed and corrected
_timefix_try () {
    # systemd already synchronized the clock: instantaneous fast path that
    # keeps healthy boots clear of any network probe at all.
    if command -v timedatectl >/dev/null 2>&1; then
        if [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" = "yes" ]; then
            return 0
        fi
    fi

    local skew
    if ! skew=$(_timefix_skew); then
        return 1
    fi
    if [ "$skew" -le "$_TIMEFIX_TOLERANCE" ] && [ "$skew" -ge "-$_TIMEFIX_TOLERANCE" ]; then
        return 0
    fi

    local marker="${TMPDIR:-/tmp}/linuxtoys_sudo_validated-${UID}"
    local sudo_cmd=""
    if [ "$(id -u)" -eq 0 ]; then
        :
    elif [ -f "$marker" ] || \
        { sudo_cmd=$(_sudo_command_path 2>/dev/null) && "$sudo_cmd" -n true 2>/dev/null; }; then
        :
    else
        return 2
    fi

    local direction="behind real time"
    if [ "$skew" -gt 0 ]; then
        direction="ahead of real time"
    fi
    if _timefix_apply "$skew"; then
        _timefix_note "System clock was $(_timefix_abs "$skew") second(s) $direction; synchronized."
        return 4
    fi
    _timefix_note "System clock is $(_timefix_abs "$skew") second(s) $direction and automatic correction failed. apt signature verification ('Not live until') and other signed operations may misbehave until the clock is fixed."
    return 3
}

# Terminal-buffer-only notes: the guard stays dialog-free by design.
_timefix_note () {
    printf '[linuxtoys] %s\n' "$1" >&2
}

# Silent boot-scoped enforcement. `timefix_bootguard afterauth` (used by the
# askpass hook) is allowed to seal a pending boot since privilege exists then.
# Source-time callers (linuxtoys.bash) intentionally skip "pending" so the
# correction lands right after the first successful authorization instead.
timefix_bootguard () {
    if [ "${LINUXTOYS_TIMEFIX:-1}" = "0" ]; then
        return 0
    fi
    if [ "${LINUXTOYS_TIMEFIX_BUSY:-0}" = "1" ]; then
        return 0
    fi

    local mode="${1:-}"
    local state
    state=$(_timefix_stamp_state)
    case "$state" in
        synced|failed)
            return 0
            ;;
        pending)
            [ -n "$mode" ] || return 0
            ;;
        soft:*)
            if _timefix_soft_fresh "$state" && [ -z "$mode" ]; then
                return 0
            fi
            ;;
    esac

    LINUXTOYS_TIMEFIX_BUSY=1
    local outcome_rc
    _timefix_try
    outcome_rc=$?
    LINUXTOYS_TIMEFIX_BUSY=0

    case "$outcome_rc" in
        0)
            _timefix_stamp_write synced || true
            ;;
        1)
            _timefix_stamp_write "soft:$(date -u +%s)" || true
            ;;
        2)
            # Privilege owed, wherever the guard ran from: askpass's success
            # hook retries pending boots right after the first authorization.
            _timefix_stamp_write pending || true
            ;;
        3)
            _timefix_stamp_write failed || true
            ;;
        4)
            _timefix_stamp_write synced || true
            ;;
    esac
    return 0
}

# askpass success hook: authorization just succeeded anywhere in the app, so
# finish a pending correction right now, silently.
timefix_afterauth () {
    if [ "${LINUXTOYS_TIMEFIX:-1}" = "0" ]; then
        return 0
    fi
    if [ "${LINUXTOYS_TIMEFIX_BUSY:-0}" = "1" ]; then
        return 0
    fi
    timefix_bootguard afterauth || true
    return 0
}
