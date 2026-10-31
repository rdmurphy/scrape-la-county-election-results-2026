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

fetch() {
    local url="$1"
    local filter="$2"
    local check="$3"
    local output_file="$4"

    local name raw formatted
    name="$(basename "$output_file")"
    raw="$tmp_directory/$name.raw"
    formatted="$tmp_directory/$name.formatted"

    # fail on HTTP errors and retry instead of saving an error page
    curl --fail --silent --show-error --location \
      --retry 3 --retry-delay 5 --retry-all-errors \
      "$url" > "$raw"

    # make sure the response looks like real stuff
    if ! jq --exit-status "$check" "$raw" > /dev/null; then
        echo "Response from $url failed sanity check: $check" >&2
        return 1
    fi

    jq "$filter" "$raw" > "$formatted"
    mv "$formatted" "$output_file"
}

# write a main method that accepts two parameters called output_directory and election_id
main() {
    local output_directory="$1"
    local election_id="$2"

    # create the output directory if it does not exist
    mkdir -p "$output_directory"

    # scratch space for downloads, cleaned up no matter how we exit
    tmp_directory="$(mktemp -d)"
    trap 'rm -rf "$tmp_directory"' EXIT

    # grab the results and output
    fetch "https://results.lavote.gov/electionresults/json?electionid=$election_id" \
      "." \
      ".Election != null" \
      "$output_directory/results.json"

    # grab the counter_data and output
    fetch "https://results.lavote.gov/ElectionResults/GetCounterData?electionID=$election_id" \
      ".Data |= map(.Value |= floor) | .Data |= sort_by(.Number)" \
      ".Data | type == \"array\" and length > 0" \
      "$output_directory/counter_data.json"

    # grab the election_data and output
    fetch "https://results.lavote.gov/ElectionResults/GetElectionData?electionID=$election_id" \
      "del(.TimeStamp)" \
      ".Data.ContestGroups | type == \"array\" and length > 0" \
      "$output_directory/election_data.json"
}

main "$@"
