"""Upload the built front end (web/dist) to the site bucket and refresh CloudFront.

This CHANGES AWS (writes files to S3, creates a CloudFront invalidation), so run it only
after the supportdesk-app stack is deployed and you have approved it. Order of work:
  1. python scripts/write_web_config.py      (writes web/public/config.json)
  2. cd web && npm run build                 (copies config.json into web/dist)
  3. python scripts/deploy_web.py --dry-run  (shows what would be uploaded, changes nothing)
  4. python scripts/deploy_web.py            (uploads for real)

`--dry-run` only runs `aws s3 sync --dryrun`; it never creates the invalidation.
Hashed files in dist/assets are cached for a year; index.html and config.json are never cached.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import boto3

from stack_outputs import read_stack_outputs, require_outputs

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "web" / "dist"
APP_STACK = "supportdesk-app"
LONG_CACHE = "public, max-age=31536000, immutable"
NO_CACHE = "no-cache"


def build_commands(bucket: str, distribution_id: str, dist: Path, dry_run: bool) -> list[list[str]]:
    """The aws CLI commands, in order. Pure function so it can be tested without AWS."""
    target = f"s3://{bucket}"
    dry = ["--dryrun"] if dry_run else []
    assets = ["aws", "s3", "sync", str(dist), target, "--delete", "--cache-control", LONG_CACHE,
              "--exclude", "*", "--include", "assets/*", *dry]
    pages = ["aws", "s3", "sync", str(dist), target, "--delete", "--cache-control", NO_CACHE,
             "--exclude", "assets/*", *dry]
    commands = [assets, pages]
    if not dry_run:
        commands.append(["aws", "cloudfront", "create-invalidation", "--distribution-id", distribution_id, "--paths", "/*"])
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="show what would be uploaded; change nothing")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    if not (DIST / "index.html").exists():
        print("web/dist/index.html is missing. Run `npm run build` in web/ first.", file=sys.stderr)
        return 1
    if not (DIST / "config.json").exists():
        print("web/dist/config.json is missing. Run scripts/write_web_config.py, then build again.", file=sys.stderr)
        return 1

    outputs = read_stack_outputs(boto3.client("cloudformation", region_name=args.region), APP_STACK)
    bucket, distribution_id = require_outputs(outputs, APP_STACK, "SiteBucketName", "DistributionId")
    for command in build_commands(bucket, distribution_id, DIST, args.dry_run):
        print("+", " ".join(command[:5]), "...")
        if subprocess.run(command, check=False).returncode != 0:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
