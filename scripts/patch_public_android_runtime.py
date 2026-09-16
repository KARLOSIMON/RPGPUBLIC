#!/usr/bin/env python3
"""Generic Android runtime fixes for the RPGPUBLIC OpenTibia proving ground.

This file must remain PocketPVP-agnostic. It only fixes baseline mobile behavior:
- normal left tap on a hostile creature starts native offensive chase/attack;
- fat-finger taps may resolve a hostile creature one tile around the release tile;
- mobile autowalk no longer silently changes ChaseOpponent to DontChase;
- tapping a corpse/container opens it when no hostile creature was selected;
- the oversized outfit/customisation UI is suppressed on mobile;
- character-list appearance preview is suppressed on mobile.

Combat legality, timing, damage, pathing, collision, loot and item authority stay
inside the stock OTClient/TFS runtime.
"""
from __future__ import annotations

import argparse
from pathlib import Path

MARKER = "-- RPGPUBLIC_MOBILE_BASELINE_V1"
OUTFIT_MARKER = "-- RPGPUBLIC_HIDE_MOBILE_OUTFIT_V1"
CHARLIST_MARKER = "-- RPGPUBLIC_HIDE_MOBILE_CHARACTER_APPEARANCE_V1"


def patch_gameinterface(root: Path) -> None:
    path = root / "modules" / "game_interface" / "gameinterface.lua"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return

    mobile_anchor = """    if g_platform.isMobile() then
        if mouseButton == MouseRightButton then
            createThingMenu(menuPosition, lookThing, useThing, creatureThing)
            return true
        end
"""
    mobile_replacement = """    if g_platform.isMobile() then
        local player = g_game.getLocalPlayer()

        if mouseButton == MouseRightButton then
            createThingMenu(menuPosition, lookThing, useThing, creatureThing)
            return true
        end

        -- RPGPUBLIC_MOBILE_BASELINE_V1
        -- A normal phone tap on a non-NPC creature is combat. Upstream mobile
        -- otherwise requires the separate attack shortcut to be armed first.
        if mouseButton == MouseLeftButton then
            local target = attackCreature
            if (not target or target:isNpc()) and creatureThing and not creatureThing:isNpc() then
                target = creatureThing
            end

            if target and target ~= player and not target:isNpc() and target:getHealthPercent() > 0 then
                if player then player:stopAutoWalk() end
                g_game.setFightMode(FightOffensive)
                g_game.setChaseMode(ChaseOpponent)
                modules.game_textmessage.displayStatusMessage(
                    'RPGPUBLIC target -> ' .. target:getName()
                )
                g_game.attack(target)
                return true
            end

            -- Make the generic mobile baseline capable of opening corpses and
            -- containers without forcing the user to arm the "use" shortcut.
            if useThing and (useThing:isContainer() or useThing:isLyingCorpse()) then
                if useThing:getParentContainer() then
                    g_game.open(useThing, useThing:getParentContainer())
                else
                    g_game.open(useThing)
                end
                return true
            end
        end
"""
    if mobile_anchor not in text:
        raise SystemExit("gameinterface mobile anchor changed")
    text = text.replace(mobile_anchor, mobile_replacement, 1)

    chase = """if g_game.isAttacking() and g_game.getChaseMode() == ChaseOpponent then
                    g_game.setChaseMode(DontChase)
                end"""
    chase_mobile_safe = """if (not g_platform.isMobile()) and g_game.isAttacking() and g_game.getChaseMode() == ChaseOpponent then
                    g_game.setChaseMode(DontChase)
                end"""
    count = text.count(chase)
    if count < 1:
        raise SystemExit("mobile chase-cancel anchor missing")
    text = text.replace(chase, chase_mobile_safe)

    path.write_text(text, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    assert MARKER in verify
    assert "RPGPUBLIC target -> " in verify
    assert verify.count("(not g_platform.isMobile()) and g_game.isAttacking()") >= 1
    assert "useThing:isLyingCorpse()" in verify


def patch_uigamemap(root: Path) -> None:
    path = root / "modules" / "game_interface" / "widgets" / "uigamemap.lua"
    text = path.read_text(encoding="utf-8")
    marker = "-- RPGPUBLIC_FAT_FINGER_TARGET_V1"
    if marker in text:
        return

    anchor = """    local autoWalkTile = g_map.getTile(autoWalkPos)
    if autoWalkTile then
        attackCreature = autoWalkTile:getTopCreature()
    end

    local ret = modules.game_interface.processMouseAction"""
    replacement = """    local autoWalkTile = g_map.getTile(autoWalkPos)
    if autoWalkTile then
        attackCreature = autoWalkTile:getTopCreature()
    end

    -- RPGPUBLIC_FAT_FINGER_TARGET_V1
    -- Visible creature sprites can extend beyond their logical 32px tile.
    -- On mobile, resolve the nearest living non-NPC creature within one tile
    -- of the release position when the exact tile has no valid target.
    if g_platform.isMobile() and
        (not attackCreature or attackCreature:isNpc() or attackCreature:getHealthPercent() <= 0) then
        local player = g_game.getLocalPlayer()
        local best = nil
        local bestDistance = 999
        for _, creature in ipairs(g_map.getSpectatorsInRange(autoWalkPos, false, 1, 1) or {}) do
            if creature and creature ~= player and not creature:isNpc() and creature:getHealthPercent() > 0 then
                local pos = creature:getPosition()
                if pos.z == autoWalkPos.z then
                    local distance = math.max(
                        math.abs(pos.x - autoWalkPos.x),
                        math.abs(pos.y - autoWalkPos.y)
                    )
                    if distance < bestDistance then
                        best = creature
                        bestDistance = distance
                    end
                end
            end
        end
        attackCreature = best or attackCreature
    end

    local ret = modules.game_interface.processMouseAction"""
    if anchor not in text:
        raise SystemExit("uigamemap target-resolution anchor changed")
    text = text.replace(anchor, replacement, 1)
    path.write_text(text, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    assert marker in verify
    assert "getSpectatorsInRange(autoWalkPos, false, 1, 1)" in verify


def patch_outfit(root: Path) -> None:
    path = root / "modules" / "game_outfit" / "outfit.lua"
    text = path.read_text(encoding="utf-8")
    if OUTFIT_MARKER in text:
        return

    anchor = """function create(player, outfitList, creatureMount, mountList, familiarList, wingsList, auraList, effectsList, shaderList)
    if ignoreNextOutfitWindow and g_clock.millis() < ignoreNextOutfitWindow + 1000 then
        return
    end
"""
    replacement = """function create(player, outfitList, creatureMount, mountList, familiarList, wingsList, auraList, effectsList, shaderList)
    -- RPGPUBLIC_HIDE_MOBILE_OUTFIT_V1
    -- The upstream desktop outfit/customisation window is wider than the
    -- portrait phone viewport. For the public mechanics baseline we keep the
    -- current outfit and suppress this UI entirely on mobile.
    if g_platform.isMobile() then
        if window then
            destroy()
        end
        local currentOutfit = player and player:getOutfit() or nil
        if currentOutfit then
            scheduleEvent(function()
                if g_game.isOnline() then
                    g_game.changeOutfit(currentOutfit)
                end
            end, 1)
        end
        return
    end

    if ignoreNextOutfitWindow and g_clock.millis() < ignoreNextOutfitWindow + 1000 then
        return
    end
"""
    if anchor not in text:
        raise SystemExit("outfit create anchor changed")
    text = text.replace(anchor, replacement, 1)
    path.write_text(text, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    assert OUTFIT_MARKER in verify
    assert "g_platform.isMobile()" in verify
    assert "g_game.changeOutfit(currentOutfit)" in verify


def patch_character_list(root: Path) -> None:
    path = root / "modules" / "client_entergame" / "characterlist.lua"
    text = path.read_text(encoding="utf-8")
    if CHARLIST_MARKER in text:
        return

    anchor = """local function shouldShowAppearance()
    return g_game.getFeature(GameEnterGameShowAppearance)
end
"""
    replacement = """local function shouldShowAppearance()
    -- RPGPUBLIC_HIDE_MOBILE_CHARACTER_APPEARANCE_V1
    return (not g_platform.isMobile()) and g_game.getFeature(GameEnterGameShowAppearance)
end
"""
    if anchor not in text:
        raise SystemExit("character-list appearance anchor changed")
    text = text.replace(anchor, replacement, 1)
    path.write_text(text, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    assert CHARLIST_MARKER in verify


def patch(root: Path) -> None:
    patch_gameinterface(root)
    patch_uigamemap(root)
    patch_outfit(root)
    patch_character_list(root)
    print("RPGPUBLIC Android baseline runtime patch: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("client_root", type=Path)
    args = parser.parse_args()
    patch(args.client_root)


if __name__ == "__main__":
    main()
