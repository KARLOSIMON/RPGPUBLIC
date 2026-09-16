#!/usr/bin/env python3
"""Inspect OTSP items.otb records relevant to TFS combat splashes."""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

START=0xFE
END=0xFF
ESCAPE=0xFD
ITEM_ATTR_SERVERID=0x10
ITEM_ATTR_CLIENTID=0x11
ITEM_GROUP_SPLASH=11

@dataclass
class Node:
    node_type:int
    props:bytes
    children:list["Node"]

def parse_node(data:bytes, offset:int)->tuple[Node,int]:
    if data[offset] != START:
        raise ValueError(f"expected node at {offset}")
    node_type=data[offset+1]
    offset += 2
    props=bytearray()
    children=[]
    while offset < len(data):
        b=data[offset]
        if b == ESCAPE:
            props.append(data[offset+1]); offset += 2; continue
        if b == START:
            child,offset=parse_node(data,offset); children.append(child); continue
        if b == END:
            return Node(node_type,bytes(props),children),offset+1
        props.append(b); offset += 1
    raise ValueError("unterminated OTB node")

def record(node:Node):
    if len(node.props) < 4:
        return None
    flags=struct.unpack_from("<I",node.props,0)[0]
    off=4
    sid=cid=None
    while off < len(node.props):
        attr=node.props[off]
        length=struct.unpack_from("<H",node.props,off+1)[0]
        off += 3
        payload=node.props[off:off+length]
        off += length
        if attr == ITEM_ATTR_SERVERID and length == 2:
            sid=struct.unpack("<H",payload)[0]
        elif attr == ITEM_ATTR_CLIENTID and length == 2:
            cid=struct.unpack("<H",payload)[0]
    if sid is None or cid is None:
        return None
    return {"server_id":sid,"client_id":cid,"group":node.node_type,"flags":flags}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("otb",type=Path)
    args=ap.parse_args()
    data=args.otb.read_bytes()
    if data[:4] not in (b"OTBI",bytes(4)):
        raise SystemExit(f"unexpected OTB header {data[:4]!r}")
    root,end=parse_node(data,4)
    if end != len(data) and any(data[end:]):
        raise SystemExit("unexpected OTB trailing bytes")
    records=[]
    for child in root.children:
        r=record(child)
        if r: records.append(r)

    by_id={r["server_id"]:r for r in records}
    print("TFS hardcoded splash IDs:")
    for sid in (2016,2019):
        print(f"  {sid}: {by_id.get(sid)}")

    splash=[r for r in records if r["group"] == ITEM_GROUP_SPLASH]
    print(f"OTSP splash-group records ({len(splash)}):")
    for r in splash:
        print(f"  server={r['server_id']} client={r['client_id']} flags={r['flags']}")

    if not splash:
        raise SystemExit("OTSP has no ITEM_GROUP_SPLASH records")
    if by_id.get(2019,{}).get("group") != ITEM_GROUP_SPLASH:
        print("DIAGNOSIS: TFS ITEM_SMALLSPLASH=2019 is NOT a splash in pinned OTSP.")
    else:
        print("DIAGNOSIS: server 2019 is a splash; investigate fluid subtype/client DAT mapping next.")

    FLAG_PICKUPABLE = 1 << 5
    FLAG_MOVEABLE = 1 << 6
    FLAG_STACKABLE = 1 << 7
    stackables = [
        r for r in records
        if (r["flags"] & FLAG_STACKABLE)
        and (r["flags"] & FLAG_PICKUPABLE)
        and (r["flags"] & FLAG_MOVEABLE)
    ]
    print(f"Pickupable+moveable+stackable candidates ({len(stackables)}):")
    for r in stackables[:160]:
        print(f"  server={r['server_id']} client={r['client_id']} group={r['group']} flags={r['flags']}")

    print("Sword-range OTB candidates:")
    for sid in list(range(1677, 1800)) + list(range(2264, 2273)) + list(range(2586, 2602)):
        r = by_id.get(sid)
        if r:
            print(f"  server={sid} client={r['client_id']} group={r['group']} flags={r['flags']}")

if __name__ == "__main__":
    main()
