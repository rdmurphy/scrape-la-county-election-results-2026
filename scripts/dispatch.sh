#!/usr/bin/env bash

# Exit on error
set -o errexit
# Exit on use of an uninitialised variable
set -o nounset
# Exit if any statement returns a non-true return value
set -o pipefail
# Set the trace option for the entire script if the TRACE environment variable is set to 1
if [[ "${TRACE-0}" == "1" ]]; then
    set -o xtrace
fi

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

main() {
    local interval="${1:-600}"

    # fail fast if gh can't talk to GitHub
    gh auth status > /dev/null

    # keep the machine from sleeping for as long as this script runs
    if command -v caffeinate > /dev/null; then
        caffeinate -i -w $$ &
    fi

    log "Dispatching collect.yaml every ${interval}s. Ctrl-C to stop."

    while true; do
        # a failed run shouldn't end the loop
        if gh workflow run collect.yaml --ref main; then
            log "Dispatched."
        else
            log "Dispatch failed, will try again next round."
        fi

        sleep "$interval"
    done
}

main "$@"
