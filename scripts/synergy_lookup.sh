#!/bin/bash

##############################################################################
# MTG Card Synergy Lookup Tool
#
# Usage:
#   ./synergy_lookup.sh "Lightning Bolt"
#   ./synergy_lookup.sh "Counterspell" 20 Modern
#   ./synergy_lookup.sh "Goblin Electromancer" 15 "" aggro
#
##############################################################################

set -euo pipefail

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
ENDPOINT="/api/v1/synergy"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
usage() {
    cat << EOF
Usage: $0 <card_name> [max_results] [format] [archetype]

Arguments:
  card_name       (required) Name of the card to find synergies for
  max_results     (optional) Number of results (1-100, default: 10)
  format          (optional) Format filter (Standard, Modern, Commander, etc.)
  archetype       (optional) Archetype (aggro, control, midrange, combo, tempo, ramp)

Examples:
  $0 "Lightning Bolt"
  $0 "Counterspell" 20 Modern
  $0 "Goblin Electromancer" 15 "" aggro
  $0 "Omnath Locus of Creation" 25 Commander ramp

EOF
    exit 1
}

check_prerequisites() {
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: curl is not installed${NC}"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        echo -e "${YELLOW}Warning: jq is not installed. Install it for prettier output.${NC}"
        echo "  macOS: brew install jq"
        echo "  Linux: sudo apt-get install jq"
        NO_JQ=true
    else
        NO_JQ=false
    fi
}

url_encode() {
    local string="$1"
    echo "${string// /%20}"
}

check_api_running() {
    if ! curl -s "${API_URL}/health" > /dev/null 2>&1; then
        echo -e "${RED}Error: Cannot connect to API at ${API_URL}${NC}"
        echo "Make sure your MTG CAG system is running:"
        echo "  cd /home/shea/Documents/GitHub/agentic-cag-system"
        echo "  source venv/bin/activate"
        echo "  python -m uvicorn mtg_cag_system.main:app --reload"
        exit 1
    fi
}

lookup_synergies() {
    local card_name="$1"
    local max_results="${2:-10}"
    local format_filter="${3:-}"
    local archetype="${4:-}"

    # Validate max_results
    if ! [[ "$max_results" =~ ^[0-9]+$ ]] || [ "$max_results" -lt 1 ] || [ "$max_results" -gt 100 ]; then
        echo -e "${RED}Error: max_results must be between 1 and 100${NC}"
        exit 1
    fi

    # Build URL
    local encoded_card=$(url_encode "$card_name")
    local url="${API_URL}${ENDPOINT}/${encoded_card}?max_results=${max_results}"

    if [ -n "$format_filter" ] && [ "$format_filter" != "none" ]; then
        url="${url}&format_filter=${format_filter}"
    fi

    if [ -n "$archetype" ] && [ "$archetype" != "none" ]; then
        url="${url}&archetype=${archetype}"
    fi

    # Make request
    echo -e "${BLUE}📋 Looking up synergies for: ${YELLOW}${card_name}${NC}"
    echo -e "${BLUE}🔗 URL: ${url}${NC}"
    echo ""

    local response=$(curl -s -w "\n%{http_code}" "$url")
    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n-1)

    # Handle errors
    if [ "$http_code" != "200" ]; then
        if [ "$http_code" = "404" ]; then
            echo -e "${RED}❌ Card not found or no synergies available${NC}"
        elif [ "$http_code" = "400" ]; then
            echo -e "${RED}❌ Invalid request: $(echo "$body" | jq -r '.detail' 2>/dev/null || echo "$body")${NC}"
        else
            echo -e "${RED}❌ HTTP Error ${http_code}${NC}"
        fi
        exit 1
    fi

    # Display results
    if [ "$NO_JQ" = true ]; then
        # Fallback: simple output without jq
        echo -e "${GREEN}✅ Found synergies:${NC}"
        echo "$body"
    else
        # Pretty output with jq
        local total=$(echo "$body" | jq '.total_found')
        local exec_time=$(echo "$body" | jq '.execution_time')

        echo -e "${GREEN}✅ Found ${total} synergies (${exec_time}s)${NC}"
        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

        # Display synergies
        echo "$body" | jq -r '.synergies[] |
            "  \u001b[32m✓\u001b[0m \(.name)\n    └─ Similarity: \(.similarity_score * 100 | round)%"'

        echo ""
        echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}⏱️  Query time: ${exec_time}s${NC}"
        echo ""
    fi
}

# Main
main() {
    check_prerequisites

    if [ $# -lt 1 ]; then
        usage
    fi

    check_api_running

    lookup_synergies "$@"
}

main "$@"
