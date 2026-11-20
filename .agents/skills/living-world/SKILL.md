---
name: living-world
description: >-
  Manages campaign factions, progress clocks, and off-screen world events. Use after
  sessions or during downtime to make the world react dynamically to player choices
  and surface observable fallout across the setting.
---

# Living World: Faction Clocks & Off-Screen Events (`living-world`)

The player characters are not the only active agents in the setting: factions documented in `<Vault>/Campaign/Factions/` and `<Vault>/Campaign/Story Arcs.md` pursue their own agendas whenever the party explores, rests, or prioritizes one threat over another.

---

## 1. Read Active State
Before proposing updates:
1. Read `<Vault>/Campaign/World State.md` (in-game date, party location, active clocks).
2. Read all faction notes in `<Vault>/Campaign/Factions/`.
3. Check the Faction Reaction Matrix in `<Vault>/Campaign/Story Arcs.md`.

Standard Markdown progress-clock notation:
- 4-segment clock: `[X] [ ] [ ] [ ]` (`1/4`)
- 6-segment clock: `[X] [X] [ ] [ ] [ ] [ ]` (`2/6`)
- 8-segment clock: `[X] [X] [X] [ ] [ ] [ ] [ ] [ ]` (`3/8`)

---

## 2. Reactive Evaluation Procedure (Post-Session / Downtime)
Evaluate each active faction:
1. **Did the PCs directly disrupt its plan?** Hold, roll back, or pivot the faction's clock and tactics.
2. **Did the PCs ignore that front to pursue something else?** Propose advancing by `1` segment (or `2` if completely unopposed).
3. **Did significant travel or downtime pass?** Propose proportional advancement across all unopposed factions.

> [!IMPORTANT] DM Approval Required
> Present proposed clock changes to the DM for review before committing irreversible world shifts (`dm-reviewer-narrative-authority.md`).

---

## 3. Observable World Consequences (Living World Fallout)
For every filled clock segment, generate at least **1 tangible signal** the players can perceive:
- **Rumors & News:** Tavern talk, town criers, intercepted dispatches, anxious travelers.
- **Environmental & Economic Shifts:** Price spikes, tightened gate patrols, closed roads, nervous merchants.
- **Clock Completion:** Filling the final segment triggers an irreversible turning point (an outpost falls, an ally vanishes, a regional crisis erupts) that reshapes the next story arc.

---

## 4. Persist Updates
After DM sign-off:
- Update clock segments in `<Vault>/Campaign/World State.md`.
- Update each affected note under `<Vault>/Campaign/Factions/`.
- Feed observable fallout into the *Living World Fallout* section of the next `session-prep`.
