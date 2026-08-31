# Forge Remote Table

Forge Remote Table is a separate, freeform single-player Commander tabletop made for long-distance games over Discord, FaceTime, Zoom, etc. One player can use real cards on camera while the other screen-shares this digital table.

## What is different from The Commander Forge?

- No rules engine, legality checks, timing restrictions, mana enforcement, or automatic opponent.
- Any card can be moved to any zone manually.
- Cards can be added even if they were not in the original deck.
- Built around screen sharing and manual communication with a real opponent.
- Saves only in the player's browser by default; no game server or account is required.

## Features

- Paste almost any normal Commander decklist and load card data/art through Scryfall.
- Auto-detect a commander from a `Commander` section, or type a commander manually.
- Optional official-precon browser (reads the public Commander Forge precon catalog when available).
- Drag cards between hand, battlefield, graveyard, exile, command zone, and library.
- Free placement on the battlefield; double-click to tap/untap.
- Draw, draw N, shuffle, search library, look at top N, mill N, exile top N, and redraw hand.
- Add any Magic card at any time (useful for theft/copy/wish effects).
- Custom tokens, emblems, markers, and reminder objects.
- Arbitrary named counters on any card, +1/+1 and -1/-1 shortcuts, face-down state, transform/flip, and duplicate/copy.
- Life, poison, energy, commander tax, turn, and commander-damage trackers.
- Dice and coin tools.
- Undo/redo, browser autosave, JSON export/import, and table notes.

## Run it

This is a static site. Open `index.html` from a simple local web server, or publish the repository with GitHub Pages.

For GitHub Pages in a new repository: **Settings → Pages → Deploy from a branch → main / root**.

## Card data

Card data and card images are requested from [Scryfall](https://scryfall.com/) in the player's browser. Magic: The Gathering is a trademark of Wizards of the Coast LLC. This project is not affiliated with Wizards of the Coast.
