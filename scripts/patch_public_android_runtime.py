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
BATTLE_MARKER = "-- RPGPUBLIC_STICKY_MOBILE_BATTLE_TARGET_V1"
INVENTORY_MARKER = "-- RPGPUBLIC_STICKY_MOBILE_CHASE_V1"
LOCALE_MARKER = "-- RPGPUBLIC_SKIP_FIRST_LOCALE_PROMPT_V1"
LOGIN_MARKER = "-- RPGPUBLIC_TEST_LOGIN_PREFILL_V1"
EQUIPMENT_MARKER = "-- RPGPUBLIC_OPEN_EQUIPMENT_ON_LOGIN_V1"
PUBLIC_TEST_ID = "a"


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

            if target and rpgPublicEnsureAttack(target) then
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

    helper_anchor = "function processMouseAction(menuPosition, mouseButton, autoWalkPos, lookThing, useThing, creatureThing, attackCreature)\n"
    helper = """local function rpgPublicEnsureAttack(creature)
    if not creature then return false end
    local player = g_game.getLocalPlayer()
    if creature == player or creature:isNpc() or creature:getHealthPercent() <= 0 then
        return false
    end

    local current = g_game.getAttackingCreature()
    if current and current:getId() == creature:getId() then
        modules.game_textmessage.displayStatusMessage(
            'RPGPUBLIC already targeting -> ' .. creature:getName()
        )
        return true
    end

    if player then player:stopAutoWalk() end
    g_game.setFightMode(FightOffensive)
    g_game.setChaseMode(ChaseOpponent)
    modules.game_textmessage.displayStatusMessage(
        'RPGPUBLIC target -> ' .. creature:getName()
    )
    g_game.attack(creature)
    return true
end

"""
    if helper_anchor not in text:
        raise SystemExit("processMouseAction anchor changed")
    text = text.replace(helper_anchor, helper + helper_anchor, 1)
    text = text.replace(mobile_anchor, mobile_replacement, 1)

    shortcut_old = """        elseif shortcut == "attack" then
            if attackCreature and attackCreature ~= player then
                modules.game_shortcuts.resetShortcuts()
                g_game.attack(attackCreature)
                return true
            elseif creatureThing and creatureThing ~= player and autoWalkPos and creatureThing:getPosition().z == autoWalkPos.z then
                modules.game_shortcuts.resetShortcuts()
                g_game.attack(creatureThing)
                return true
            end
            return true
"""
    shortcut_new = """        elseif shortcut == "attack" then
            if attackCreature and attackCreature ~= player then
                modules.game_shortcuts.resetShortcuts()
                rpgPublicEnsureAttack(attackCreature)
                return true
            elseif creatureThing and creatureThing ~= player and autoWalkPos and creatureThing:getPosition().z == autoWalkPos.z then
                modules.game_shortcuts.resetShortcuts()
                rpgPublicEnsureAttack(creatureThing)
                return true
            end
            return true
"""
    if shortcut_old not in text:
        raise SystemExit("mobile attack-shortcut anchor changed")
    text = text.replace(shortcut_old, shortcut_new, 1)

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
    assert "RPGPUBLIC already targeting -> " in verify
    assert verify.count("rpgPublicEnsureAttack(") >= 4
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


def patch_battle(root: Path) -> None:
    path = root / "modules" / "game_battle" / "battle.lua"
    text = path.read_text(encoding="utf-8")
    if BATTLE_MARKER in text:
        return

    old = """    elseif mouseButton == MouseLeftButton and not g_mouse.isPressed(MouseRightButton) then
        if self.isTarget then
            g_game.cancelAttack()
        else
            g_game.attack(self.creature)
        end
        return true
"""
    new = """    elseif mouseButton == MouseLeftButton and not g_mouse.isPressed(MouseRightButton) then
        -- RPGPUBLIC_STICKY_MOBILE_BATTLE_TARGET_V1
        if g_platform.isMobile() then
            if self.creature and not self.creature:isNpc() and self.creature:getHealthPercent() > 0 then
                local current = g_game.getAttackingCreature()
                g_game.setFightMode(FightOffensive)
                g_game.setChaseMode(ChaseOpponent)
                if not current or current:getId() ~= self.creature:getId() then
                    g_game.attack(self.creature)
                end
            end
        elseif self.isTarget then
            g_game.cancelAttack()
        else
            g_game.attack(self.creature)
        end
        return true
"""
    if old not in text:
        raise SystemExit("battle-list target toggle anchor changed")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    verify = path.read_text(encoding="utf-8")
    assert BATTLE_MARKER in verify
    assert "g_game.setChaseMode(ChaseOpponent)" in verify


def patch_inventory(root: Path) -> None:
    path = root / "modules" / "game_inventory" / "inventory.lua"
    text = path.read_text(encoding="utf-8")
    if INVENTORY_MARKER in text:
        return

    safe_old = """    g_game.setSafeFight(not checked)
    if not checked then
        g_game.cancelAttack()
    end
"""
    safe_new = """    g_game.setSafeFight(not checked)
    if not checked then
        -- RPGPUBLIC_STICKY_MOBILE_CHASE_V1
        -- Safe-fight is a PvP control; on mobile it must not cancel a monster.
        local target = g_game.getAttackingCreature()
        if not g_platform.isMobile() or not target or target:isPlayer() then
            g_game.cancelAttack()
        end
    end
"""
    if safe_old not in text:
        raise SystemExit("safe-fight attack-cancel anchor changed")
    text = text.replace(safe_old, safe_new, 1)

    stand_old = """        if not ignoreUpdate then
            g_game.setChaseMode(DontChase)
        end
"""
    stand_new = """        if not ignoreUpdate then
            if g_platform.isMobile() and g_game.isAttacking() then
                -- Active mobile combat is sticky; Stop/Cancel ends it explicitly.
                ui.standPosture:setEnabled(true)
                ui.followPosture:setEnabled(false)
                g_game.setChaseMode(ChaseOpponent)
                return
            end
            g_game.setChaseMode(DontChase)
        end
"""
    if stand_old not in text:
        raise SystemExit("stand-posture chase anchor changed")
    text = text.replace(stand_old, stand_new, 1)

    walk_old = """local function walkEvent()
    if modules.client_options.getOption('autoChaseOverride') then
        if g_game.isAttacking() and g_game.getChaseMode() == ChaseOpponent then
            selectPosture('stand', false)
        end
    end
end
"""
    walk_new = """local function walkEvent()
    if g_platform.isMobile() and g_game.isAttacking() then
        -- Never let ordinary walking or autoChaseOverride drop active chase.
        if g_game.getChaseMode() ~= ChaseOpponent then
            g_game.setChaseMode(ChaseOpponent)
        end
        return
    end

    if modules.client_options.getOption('autoChaseOverride') then
        if g_game.isAttacking() and g_game.getChaseMode() == ChaseOpponent then
            selectPosture('stand', false)
        end
    end
end
"""
    if walk_old not in text:
        raise SystemExit("inventory walkEvent anchor changed")
    text = text.replace(walk_old, walk_new, 1)

    start_old = """    inventoryShrink = g_settings.getBoolean('mainpanel_shrink_inventory')
    refreshInventorySizes()
    refreshInventory_panel()
"""
    start_new = """    -- RPGPUBLIC_OPEN_EQUIPMENT_ON_LOGIN_V1
    -- Keep equipment expanded/visible on every login for physical gear tests.
    inventoryShrink = false
    g_settings.set('mainpanel_shrink_inventory', false)
    inventoryController.ui:show()
    refreshInventorySizes()
    refreshInventory_panel()
"""
    if start_old not in text:
        raise SystemExit("inventory onGameStart visibility anchor changed")
    text = text.replace(start_old, start_new, 1)

    path.write_text(text, encoding="utf-8")
    verify = path.read_text(encoding="utf-8")
    assert INVENTORY_MARKER in verify
    assert "Never let ordinary walking or autoChaseOverride drop active chase." in verify
    assert "target:isPlayer()" in verify
    assert EQUIPMENT_MARKER in verify
    assert "inventoryShrink = false" in verify
    assert "inventoryController.ui:show()" in verify


def patch_locales(root: Path) -> None:
    path = root / "modules" / "client_locales" / "locales.lua"
    text = path.read_text(encoding="utf-8")
    if LOCALE_MARKER in text:
        return

    old = """    local userLocaleName = g_settings.get('locale', 'false')
    if userLocaleName ~= 'false' and setLocale(userLocaleName) then
        pdebug('Using configured locale: ' .. userLocaleName)
    else
        setLocale(defaultLocaleName)
        if g_app.hasUpdater() then
            connect(g_app, {
                onUpdateFinished = createWindow,
            })
        else
            connect(g_app, {
                onRun = createWindow,
            })
        end
    end
"""
    new = """    local userLocaleName = g_settings.get('locale', 'false')
    if userLocaleName ~= 'false' and setLocale(userLocaleName) then
        pdebug('Using configured locale: ' .. userLocaleName)
    else
        -- RPGPUBLIC_SKIP_FIRST_LOCALE_PROMPT_V1
        -- First launch uses the normal English default immediately.
        setLocale(defaultLocaleName)
        g_settings.set('locale', defaultLocaleName)
    end
"""
    if old not in text:
        raise SystemExit("locale first-run anchor changed")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    assert LOCALE_MARKER in verify


def patch_entergame(root: Path) -> None:
    path = root / "modules" / "client_entergame" / "entergame.lua"
    text = path.read_text(encoding="utf-8")
    if LOGIN_MARKER in text:
        return

    old = """    if serverData and serverData.account then
        EnterGame.setAccountName(serverData.account)
        EnterGame.setPassword(serverData.password)
        enterGame:getChildById('rememberEmailBox'):setChecked(true)
    else
        EnterGame.setAccountName('')
        EnterGame.setPassword('')
        enterGame:getChildById('rememberEmailBox'):setChecked(false)
    end
"""
    new = f"""    if serverData and serverData.account then
        EnterGame.setAccountName(serverData.account)
        EnterGame.setPassword(serverData.password)
        enterGame:getChildById('rememberEmailBox'):setChecked(true)
    else
        -- RPGPUBLIC_TEST_LOGIN_PREFILL_V1
        -- Disposable public proving-ground login. Keep the final Login tap manual.
        local publicTestId = '{PUBLIC_TEST_ID}'
        EnterGame.setAccountName(g_crypt.encrypt(publicTestId))
        EnterGame.setPassword(g_crypt.encrypt(publicTestId))
        enterGame:getChildById('rememberEmailBox'):setChecked(true)
        enterGame:getChildById('autoLoginBox'):setChecked(false)
    end
"""
    if old not in text:
        raise SystemExit("enter-game prefill anchor changed")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    assert LOGIN_MARKER in verify
    assert "local publicTestId" in verify
    assert "rememberEmailBox'):setChecked(true)" in verify


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
    patch_battle(root)
    patch_inventory(root)
    patch_locales(root)
    patch_entergame(root)
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
