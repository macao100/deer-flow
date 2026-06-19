#!/usr/bin/env bash
# DeerFlow — visualiseur de logs unifié
# Usage: ./scripts/logs.sh [--errors] [--gateway] [--frontend] [--filter PATTERN] [--last N]
#
# Sans arguments : suit logs/deerflow.log en temps réel avec colorisation
# --errors    : n'affiche que WARNING/ERROR/CRITICAL
# --gateway   : suit uniquement gateway.log
# --frontend  : suit uniquement frontend.log
# --filter P  : filtre grep (regex)
# --last N    : affiche les N dernières lignes avant de suivre (défaut: 100)

set -e
REPO_ROOT="$(builtin cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P)"
LOGS="$REPO_ROOT/logs"

# ── Couleurs ─────────────────────────────────────────────────────────────────
RED='\033[0;31m';  YELLOW='\033[1;33m'; GREEN='\033[0;32m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';   GRAY='\033[0;37m'
BOLD='\033[1m';    NC='\033[0m'

# ── Paramètres ───────────────────────────────────────────────────────────────
ERRORS_ONLY=false
SOURCE="deerflow"      # deerflow | gateway | frontend | nginx
FILTER=""
LAST=100

while [[ $# -gt 0 ]]; do
    case "$1" in
        --errors)           ERRORS_ONLY=true ;;
        --gateway)          SOURCE="gateway" ;;
        --frontend)         SOURCE="frontend" ;;
        --nginx)            SOURCE="nginx" ;;
        --filter)           FILTER="$2"; shift ;;
        --last)             LAST="$2"; shift ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# //'
            exit 0 ;;
        *) echo "Option inconnue : $1"; exit 1 ;;
    esac
    shift
done

# ── Fichier cible ─────────────────────────────────────────────────────────────
case "$SOURCE" in
    deerflow) LOG_FILE="$LOGS/deerflow.log" ;;
    gateway)  LOG_FILE="$LOGS/gateway.log"  ;;
    frontend) LOG_FILE="$LOGS/frontend.log" ;;
    nginx)    LOG_FILE="$LOGS/nginx.log"    ;;
esac

if [[ ! -f "$LOG_FILE" ]]; then
    echo -e "${YELLOW}⚠ $LOG_FILE n'existe pas encore.${NC}"
    echo "  Lancez DeerFlow avec  make dev  puis relancez cette commande."
    exit 1
fi

# ── Coloriser une ligne ───────────────────────────────────────────────────────
colorize() {
    while IFS= read -r line; do
        case "$line" in
            *CRITICAL*|*ERROR*|*Exception*|*Traceback*|*error:*)
                printf "${RED}%s${NC}\n" "$line" ;;
            *WARNING*|*WARN*|*warn*)
                printf "${YELLOW}%s${NC}\n" "$line" ;;
            *"→ 2"*|*"→ 3"*|*INFO*)
                printf "${GREEN}%s${NC}\n" "$line" ;;
            *"[GATEWAY]"*)
                printf "${BLUE}%s${NC}\n" "$line" ;;
            *"[FRONTEND]"*)
                printf "${CYAN}%s${NC}\n" "$line" ;;
            *"[NGINX]"*)
                printf "${GRAY}%s${NC}\n" "$line" ;;
            *)
                printf "%s\n" "$line" ;;
        esac
    done
}

# ── Filtrage ─────────────────────────────────────────────────────────────────
apply_filter() {
    if $ERRORS_ONLY; then
        grep -E "ERROR|WARNING|WARN|CRITICAL|Exception|Traceback" || true
    elif [[ -n "$FILTER" ]]; then
        grep -E "$FILTER" || true
    else
        cat
    fi
}

# ── En-tête ──────────────────────────────────────────────────────────────────
echo -e "${BOLD}DeerFlow logs — $LOG_FILE${NC}"
$ERRORS_ONLY && echo -e "${YELLOW}  Mode : erreurs uniquement${NC}"
[[ -n "$FILTER"  ]] && echo -e "${CYAN}  Filtre : $FILTER${NC}"
echo -e "${GRAY}  Ctrl+C pour quitter${NC}"
echo "────────────────────────────────────────────────────────────"

# ── Tail ─────────────────────────────────────────────────────────────────────
tail -n "$LAST" -f "$LOG_FILE" | apply_filter | colorize
