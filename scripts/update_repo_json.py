#!/usr/bin/env python3
"""
Update repo.json with RELEASE_TAG and CATBOX_URL environment variables or CLI args.
This script is safe to run from the repository root (workflow does this).
It sets the app's top-level "version" to RELEASE_TAG and prepends a new entry in
apps[0].versions with updated downloadURL, size, date, and localizedDescription.

Usage examples:
  python3 scripts/update_repo_json.py --release-tag 1.2.3 --catbox-url https://... --release-notes "Notes" --size 123456
Or use environment variables RELEASE_TAG, CATBOX_URL, RELEASE_NOTES when not passing CLI args.
"""
import os
import json
import datetime
import urllib.request
import urllib.error
import argparse


def parse_args():
    p = argparse.ArgumentParser(description='Update repo.json with new version info')
    p.add_argument('--release-tag', '-t', help='Release tag / version string')
    p.add_argument('--catbox-url', '-u', help='Download URL (Catbox)')
    p.add_argument('--release-notes', '-n', help='Release notes to include in localizedDescription')
    p.add_argument('--size', '-s', type=int, help='Size in bytes (optional). If omitted, the script will try to probe or fallback to existing size')
    return p.parse_args()


def main():
    args = parse_args()

    # Prefer CLI args, fallback to environment variables
    release = args.release_tag or os.environ.get('RELEASE_TAG')
    catbox = args.catbox_url or os.environ.get('CATBOX_URL')
    release_notes = args.release_notes or os.environ.get('RELEASE_NOTES')
    provided_size = args.size if args.size is not None else None

    p = 'repo.json'
    if not os.path.exists(p):
        print(f"repo.json not found at {p}")
        return 1

    with open(p, 'r', encoding='utf8') as f:
        data = json.load(f)

    if not release:
        print('RELEASE_TAG not provided; nothing to do')
        return 0

    # Choose the app to update: prefer matching bundleIdentifier if provided, else first app
    apps = data.get('apps') or []
    if not apps:
        print('No apps array found in repo.json')
        return 1

    app = apps[0]

    # Prepare new version entry values
    new_download = catbox if catbox else app.get('downloadURL') or ''

    # Determine size: use provided_size if given, else try probing, else fallback to existing
    new_size = None
    if provided_size is not None:
        new_size = provided_size
    else:
        printf("Size not provided, failed to update repo...")
        return 1

    # date in ISO8601 with timezone UTC offset
    date_iso = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    # Construct localized description: include a header with tweak version, optional release notes, then base localized
    parts = [f"This version includes the ApolloICA tweak version: {release} patched with Liquid Glass support."]
    if release_notes:
        # keep release notes as provided; if multi-line it's preserved
        parts.append(release_notes)

    new_localized = "\n\n".join(parts).strip()

    # Prepare new version object (keep some fields from previous first version)
    prev = None
    if app.get('versions') and len(app['versions']) > 0:
        prev = app['versions'][0]

    new_version_obj = {
        'downloadURL': new_download,
        'size': new_size,
        'version': release,
        'buildVersion': '1',
        'date': date_iso,
        'localizedDescription': new_localized,
    }

    # copy minOSVersion if present in prev
    if prev and prev.get('minOSVersion'):
        new_version_obj['minOSVersion'] = prev.get('minOSVersion')

    changed = False

    # Update app top-level fields
    if app.get('version') != release:
        app['version'] = release
        changed = True

    if app.get('versionDate') != date_iso:
        app['versionDate'] = date_iso
        changed = True

    if app.get('downloadURL') != new_download:
        app['downloadURL'] = new_download
        changed = True

    if app.get('size') != new_size:
        app['size'] = new_size
        changed = True

    # Prepend new version to versions array if the topmost version is not the same
    versions = app.get('versions')
    if versions is None:
        app['versions'] = [new_version_obj]
        changed = True
    else:
        top_version = versions[0].get('version') if versions and len(versions) > 0 else None
        if top_version != release:
            app['versions'].insert(0, new_version_obj)
            changed = True
        else:
            # If top version equals release, replace it
            app['versions'][0] = new_version_obj
            changed = True

    if changed:
        with open(p, 'w', encoding='utf8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print('repo.json updated')
    else:
        print('No changes required for repo.json')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())

