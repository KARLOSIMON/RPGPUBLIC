# PP-MAP-001 Public Canvas Contract

This branch is the disposable OpenTibia/OTSP proving canvas for PP-MAP-001.

## Allowed here

- generic OTSP terrain/border/wall/door/stair laboratories;
- labeled test maps and visual regression fixtures;
- generic RME/OTBM compatibility probes;
- public-client rendering checks;
- movement/collision/container/light tests needed to validate generic map grammar;
- sanitized generated maps that contain no PocketPVP proprietary world design.

## Forbidden here

- PocketPVP production town/world layouts;
- private quests, progression, economy, role systems, secrets or proprietary composition rules;
- the private certified grammar registry;
- private generator heuristics or district/encounter plans;
- any proprietary art/assets.

## Test philosophy

RPGPUBLIC is a renderer/proving surface, not the source of truth.

A public lab result may prove that a generic OTSP combination renders and behaves correctly. The corresponding evidence is then recorded in the PRIVATE PP-MAP-001 registry in RPGNEWGAME.

No public experiment is automatically a production rule.

## Physical gate

Phone testing is reserved for mature checkpoints. Basic border, wall-direction, palette and reachability defects must be caught before asking for an Android test.
