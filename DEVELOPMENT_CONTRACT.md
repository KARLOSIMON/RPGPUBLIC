# Public / private development contract

## RPGPUBLIC

Purpose: free, reproducible OpenTibia proving ground.

RPGPUBLIC may contain:
- pinned open-source engine/client build instructions;
- OTSP CC BY 4.0 graphics and attribution;
- generic test maps/accounts/items required to exercise upstream mechanics;
- Android packaging, signing and physical-test instrumentation;
- fixes that are generic to the client/server integration.

RPGPUBLIC must not contain:
- private PocketPVP art;
- unreleased PocketPVP maps or quests;
- proprietary progression/economy/role designs;
- production credentials or secrets;
- private workbook exports.

## RPGNEWGAME

Purpose: the private PocketPVP product.

PocketPVP-specific mechanics and art are developed here after the relevant
engine behavior is proven in RPGPUBLIC.

## Promotion rule

Do not solve a generic engine defect by adding PocketPVP-specific complexity.

For movement, attack/chase, lighting, inventory, containers, equipment,
death/loot and other baseline mechanics:

1. reproduce against RPGPUBLIC;
2. fix/prove the generic behavior there;
3. physically verify the Android build;
4. only then port the known-good integration into RPGNEWGAME.

This keeps public CI inexpensive and makes private builds integration gates
rather than basic-engine debugging sessions.
