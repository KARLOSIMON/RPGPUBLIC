# RPGPUBLIC

Public OpenTibia runtime proving ground for the PocketPVP project.

This repository exists to prove standard RPG mechanics on free public GitHub
Actions before the private game layer is applied.

## Public baseline

- The Forgotten Server 10.41-era pinned engine
- OTClient Redemption pinned Android client
- OpenTibia Sprite Pack (OTSP) graphics, CC BY 4.0
- Generic test world only
- Native server-authoritative movement, collision and combat
- Native item/container/equipment semantics
- Native item light and transform action

No private PocketPVP art, maps, progression design, economy design, role systems
or production secrets belong in this repository.

## Physical gate

A baseline build is useful only when an Android phone proves:

1. login and reconnect work;
2. movement and collision work;
3. tapping/selecting a Goblin starts native attack;
4. Chase mode continues attacking a moving Goblin;
5. the equipped sword deals native TFS damage;
6. the test lamp visibly changes world lighting when toggled;
7. backpack/container open and item movement work;
8. death/corpse/loot work.

After this baseline is stable, PocketPVP-specific development stays private.

## Licensing

OTSP graphics are sourced at build time from
`peonso/opentibia_sprite_pack` and are licensed CC BY 4.0. See the upstream
repository and AUTHORS.md for attribution.
