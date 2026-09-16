# Public development signing key

This is an intentionally public, non-production Android development key.

It exists only so successive RPGPUBLIC APKs have the same signature and can be
installed as upgrades during physical testing. It must never sign a production
PocketPVP release. The keystore password and key password are both `android`;
the alias is `androiddebugkey`.
