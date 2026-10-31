from datetime import datetime
from json import load, loads
from pathlib import Path

from prepare_timeframes import prepare

# The key each feed uses for the county's own timestamp
TIMESTAMP_KEYS = {
    'counter_data': 'TimeStamp',
    'results': 'Timestamp',
}

ARCHIVE_FORMAT = '%Y-%m-%dT%H%M%S'


def parse_timestamp(value):
    # counter_data: "6/2/2026 8:15:15 PM", results: "2026-06-02T20:15:15.75"
    for fmt in ('%m/%d/%Y %I:%M:%S %p', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).replace(microsecond=0)
        except ValueError:
            pass

    raise ValueError(f'Could not parse timestamp: "{value}"')


def archive(directory, name):
    """
    Saves a copy of the current feed under the county's timestamp.

    The feeds flicker between cached versions, so a timestamp we've already
    seen is ignored.
    """
    text = (directory / f'{name}.json').read_text()
    timestamp = parse_timestamp(loads(text)[TIMESTAMP_KEYS[name]])

    archive_dir = directory / 'archive' / name
    archive_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(archive_dir.glob('*.json'))
    newest = existing[-1].stem if existing else None

    path = archive_dir / f'{timestamp.strftime(ARCHIVE_FORMAT)}.json'

    if path.exists() and (path.stem != newest or path.read_text() == text):
        return

    path.write_text(text)


def build_snapshots(directory):
    """
    Turns every archived counter_data that changed the vote counts into a
    snapshot named <date>-<n>, numbered per day.
    """
    archive_dir = directory / 'archive'

    snapshots = []
    previous = None
    archived = sorted((archive_dir / 'counter_data').glob('*.json'))

    for path in archived:
        with open(path) as infile:
            data = load(infile)['Data']

        # skip timestamps that didn't move any numbers, including an all-zero
        # pre-election file
        if data == previous or not any(d['Value'] for d in data):
            continue

        previous = data
        snapshots.append(path.stem)

    # until real numbers arrive, use the newest zeroed-out file as a placeholder
    if not snapshots and archived:
        snapshots.append(archived[-1].stem)

    names = {}
    per_day = {}

    for stamp in snapshots:
        date = datetime.strptime(stamp, ARCHIVE_FORMAT).strftime('%Y-%m-%d')
        per_day[date] = per_day.get(date, 0) + 1
        names[stamp] = f'{date}-{per_day[date]}'

    for name in TIMESTAMP_KEYS:
        output_dir = directory / name
        output_dir.mkdir(parents=True, exist_ok=True)

        wanted = set()

        for stamp, snapshot in names.items():
            source = archive_dir / name / f'{stamp}.json'

            # results.json can lag behind counter_data.json; it'll be filled in
            # on a later run once it shows up
            if not source.exists():
                continue

            wanted.add(f'{snapshot}.json')
            target = output_dir / f'{snapshot}.json'
            text = source.read_text()

            if not target.exists() or target.read_text() != text:
                target.write_text(text)

        # these directories are fully generated, so clear out anything stale
        for path in output_dir.glob('*.json'):
            if path.name not in wanted:
                path.unlink()


def update(directory):
    directory = Path(directory)

    for name in TIMESTAMP_KEYS:
        archive(directory, name)

    build_snapshots(directory)
    prepare(directory)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python update_snapshots.py <directory>")
        sys.exit(1)

    directory = sys.argv[1]
    update(directory)
