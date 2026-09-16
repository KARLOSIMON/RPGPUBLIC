#!/usr/bin/env python3
"""Prepare a stock OTClient Redemption Android tree for RPGPUBLIC.

This is deliberately a baseline, not PocketPVP customization:
- protocol 10.41;
- pinned OTSP DAT/SPR graphics;
- stock OTClient combat, follow, targeting, inventory and lighting;
- portrait Android shell;
- separate Android package id so it can coexist with private PocketPVP.
"""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

LOGIN_HOST = "thomas.proxy.rlwy.net"
LOGIN_PORT = 58136
PROTOCOL = 1041
PACKAGE_ID = "com.karlosimon.rpgpublic"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing anchor for {label}")
    return text.replace(old, new, 1)


def prepare(client: Path, otsp: Path) -> None:
    init = client / "init.lua"
    gradle = client / "android" / "app" / "build.gradle.kts"
    manifest = client / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    strings = client / "android" / "app" / "src" / "main" / "res" / "values" / "strings.xml"

    for path in (init, gradle, manifest, strings):
        if not path.is_file():
            raise SystemExit(f"missing pinned OTClient file: {path}")

    source_dat = otsp / "client_files" / "otsp.dat"
    source_spr = otsp / "client_files" / "otsp.spr"
    if not source_dat.is_file() or not source_spr.is_file():
        raise SystemExit("missing pinned OTSP client_files/otsp.dat or otsp.spr")

    things = client / "data" / "things" / str(PROTOCOL)
    things.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_dat, things / "Tibia.dat")
    shutil.copy2(source_spr, things / "Tibia.spr")

    text = init.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "clientAssets = {\n        enabled = true,",
        "clientAssets = {\n        enabled = false,",
        "disable dynamic client asset downloads",
    )

    start_marker = "Servers_init = {}\n\nif ENABLE_SERVERS then\n"
    end_marker = "\nend\n\ng_app.setName("
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise SystemExit("pinned OTClient server block changed")

    server_block = f'''Servers_init = {{
    ["{LOGIN_HOST}"] = {{
        port = {LOGIN_PORT},
        protocol = {PROTOCOL},
        httpLogin = false,
        useAuthenticator = false
    }}
}}
'''
    text = text[:start] + server_block + text[end + len("\nend\n"):]
    text = replace_once(
        text,
        'g_app.setName("OTClient - Redemption");',
        'g_app.setName("RPGPUBLIC");',
        "app name",
    )
    text = replace_once(
        text,
        'g_app.setCompactName("otclient");',
        'g_app.setCompactName("rpgpublic");',
        "compact app name",
    )
    text = replace_once(
        text,
        'g_app.setOrganizationName("otcr");',
        'g_app.setOrganizationName("karlosimon");',
        "organization name",
    )
    init.write_text(text, encoding="utf-8")

    g = gradle.read_text(encoding="utf-8")
    g = replace_once(
        g,
        'applicationId = "com.github.otclient"',
        f'applicationId = "{PACKAGE_ID}"',
        "Android package id",
    )
    version_code = int(os.environ.get("RPGPUBLIC_VERSION_CODE", "1"))
    g = replace_once(g, "versionCode = 1", f"versionCode = {version_code}", "version code")
    gradle.write_text(g, encoding="utf-8")

    m = manifest.read_text(encoding="utf-8")
    m = replace_once(
        m,
        'android:screenOrientation="landscape"',
        'android:screenOrientation="portrait"',
        "portrait orientation",
    )
    manifest.write_text(m, encoding="utf-8")

    s = strings.read_text(encoding="utf-8")
    s = replace_once(s, "<string name=\"app_name\">otclient</string>",
                     "<string name=\"app_name\">RPGPUBLIC</string>",
                     "launcher label")
    strings.write_text(s, encoding="utf-8")

    checks = {
        "server": f'["{LOGIN_HOST}"]' in text,
        "protocol": f"protocol = {PROTOCOL}" in text,
        "dynamic_assets_disabled": "clientAssets = {\n        enabled = false," in text,
        "dat": (things / "Tibia.dat").stat().st_size > 0,
        "spr": (things / "Tibia.spr").stat().st_size > 0,
        "package": PACKAGE_ID in g,
        "portrait": 'android:screenOrientation="portrait"' in m,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise SystemExit(f"RPGPUBLIC client preparation failed: {failed}")

    print("RPGPUBLIC stock client preparation: PASS")
    print(f"login={LOGIN_HOST}:{LOGIN_PORT} protocol={PROTOCOL}")
    print(f"package={PACKAGE_ID} versionCode={version_code}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("client", type=Path)
    parser.add_argument("otsp", type=Path)
    args = parser.parse_args()
    prepare(args.client, args.otsp)


if __name__ == "__main__":
    main()
