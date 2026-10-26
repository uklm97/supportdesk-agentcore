from pathlib import Path

import deploy_web


def test_dry_run_never_invalidates_and_marks_every_sync_as_dryrun():
    commands = deploy_web.build_commands("bkt", "DIST1", Path("dist"), dry_run=True)
    assert len(commands) == 2
    assert all("--dryrun" in c for c in commands)
    assert not any("cloudfront" in c for c in commands)


def test_real_run_syncs_both_groups_then_invalidates():
    commands = deploy_web.build_commands("bkt", "DIST1", Path("dist"), dry_run=False)
    assert [c[1] for c in commands] == ["s3", "s3", "cloudfront"]
    assert all("--dryrun" not in c for c in commands)
    assert commands[2][-4:] == ["--distribution-id", "DIST1", "--paths", "/*"][-4:]
    assert all("s3://bkt" in c for c in commands[:2])


def test_hashed_assets_are_cached_long_and_pages_are_not_cached():
    assets, pages = deploy_web.build_commands("bkt", "D", Path("dist"), dry_run=True)
    assert deploy_web.LONG_CACHE in assets and "assets/*" in assets
    assert deploy_web.NO_CACHE in pages and pages[pages.index("--exclude") + 1] == "assets/*"
