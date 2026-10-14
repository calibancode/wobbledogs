# Game mechanics

A description of how Wobbledogs works, reconstructed from the decompiled
assemblies. The original source is not published here (it is copyrighted); this
document is the substitute for reading it. Everything below is derived from
`Assembly-CSharp.dll` unless stated otherwise, and every claim is traceable to a
class or file name you can find by decompiling the assembly yourself.

Class names are given in `code`, and file names as `File.cs`, relative to the
root of the decompiled `Assembly-CSharp` project. Where the evidence is
ambiguous that is called out explicitly.

---

## Boot and core architecture

The game is a Unity 2019.4.23f1 Mono title with three scenes, registered in
build order: `00_title`, `01_home` and `02_breedingCenter` (names hard-coded in
`SceneManagerBase.cs`; the same list is embedded in the shipped
`globalgamemanagers`). Unity therefore starts in `level0`, the title scene.

There is no custom launcher and no central game loop. Boot is ordinary Unity
scene loading plus one bootstrap component, `SceneCreator`, whose `Awake` runs
`GlobalProperties.UpdateGravity()`, `UpdateTargetFramerate()` and then
`SetUpObjects()`. Target framerate is **60** and gravity is a fixed
`-29.43 m/s²` scaled by a gravity modifier (`GlobalProperties.cs`).

*Caveat:* the decompiled source contains no `[DefaultExecutionOrder]` attribute,
so "`SceneCreator` runs first" must come from the project's Script Execution
Order setting, which is not recoverable from the assembly. Other title-scene
scripts assume the registry already exists, which is consistent with it.

### The global registry

Rather than a `GameManager`, the game uses a service-locator registry.
`ObjectRegistration` keeps a `Dictionary<GlobalObject, GameObject>` and stores
itself in a static field; anything can fetch a system with
`ObjectRegistration.GetRegistrationScript().GetGlobalComponent<T>(GlobalObject.X)`.
`SceneCreator.SetUpObjects()` instantiates the persistent objects, the scene
manager, the save-file holder, the per-scene objects and the GUI, then loads
saved data — in that order.

`GlobalObject` is an enum of **50** slots. About 30 are actually referenced in
code; the notable systems are:

| Slot | Component | Purpose |
|---|---|---|
| `DOG_REGISTRATION` | `DogRegistration` | dog lifecycle, spawning, thumbnails |
| `GUI` | `GUIManagerPens` / `GUIManagerTitleScreen` | UI hub |
| `SCENE_MANAGER` | `SceneManagerBase` | scene + game-mode machine |
| `INVENTORY_MANAGER` | `InventoryManager` | item catalogue and inventory |
| `CONSTRUCTION_MANAGER` | `ConstructionManager` | building and placement |
| `OBJECT_GRABBER` | `ObjectGrabber` | drag/throw of objects and dogs |
| `DOG_GUT_MANAGER` | `DogGutsManager` | the gut simulation |
| `FLORA_MANAGER` | `FloraManager` | field guide and discovery |
| `RESEARCH_MANAGER` | `ResearchManager` | unlock progression |
| `CONTROL_MANAGER` | `ControlManager` | input bindings |
| `GLOBAL_CLOCK` | `GlobalClock` | in-game time |
| `SAVE_FILE_HOLDER` | `ActiveSaveFile` | active save slot |
| `GHOST_MANAGER` | `GhostManager` | dead-dog ghosts |
| `ADVENTURE_MANAGER` | `AdventureManager` | timed off-screen expeditions |
| `TUTORIAL` | `TutorialObjects` | tutorial state machine |
| `TEXTURE_LOADER`, `MODEL_LOADER` | | lazily load dog part assets |
| `PAUSE_MENU`, `EVENT_SYSTEM`, `RACE_*`, `ARENA`, `SHOP_MANAGER` | | declared but never referenced in code |

The last row is interesting: those slots exist but nothing reads them, so their
objects are presumably wired up in the scene or prefab assets rather than code.

### Simulation

Simulation is decentralised: 236 classes define `Update`, 45 `FixedUpdate`. The
load-bearing ones are `DogRegistration.Update` (drains the spawn queue and steps
a private `PhysicsScene` manually), `DogAI.Update`/`DoggyBrain.Update` (per-dog
thinking), `GlobalClock.Update` (advances in-game time from unscaled time),
`GUIManagerBase.Update` and `DogHome.Update` (input). Unity's default fixed
timestep is used — nothing in game code assigns `Time.fixedDeltaTime`. Pausing
is `Time.timeScale = 0` driven by a lock-reason set in `PauseController`,
so several systems can request a pause independently.

The game has a `GameMode` of `HOME`, `BREEDING` or `TITLE`, tracked by
`SceneManagerBase` and inferred from the loaded scene.

---

## Dogs

### The genome

A dog carries **two parallel genomes** on its `MasterDogGene` component:

* a quantitative genome: a string of `0`/`1` digits broken by `|` separators;
* a dominant/recessive genome: an `A`/`a` string.

`GeneticProperty` enumerates **120** quantitative traits (mostly Plus/Minus
pairs — body scale on each axis, leg-pair counts front and back, head count and
size, tail and wing size, nose/ear/horn modifiers, per-part RGB, and emission
colour). `GeneticDomRecProperty` enumerates **73** discrete traits (eyes, mouth,
ears, tails, wings, nose, horns, missing limbs, voice, pattern, alignment).

Each gene declares a bit `length` (default 10), a `loopCount` (default 2), and a
`geneType` of `STANDARD`, `SUPER` or `LOOPED`. Continuous traits are decoded as
a binary fraction scaled into a `[min, max]` range by
`MathUtil.GetFloatFromGeneSequence` (at most 20 significant bits); discrete ones
are rounded. `SUPER` genes gain an extended maximum when they are longer than
their base length, which is how unusual specimens occur.

The concrete gene definitions — the values of the ranges and lengths — live in
prefab data, not in code, so an exact per-gene parameter table cannot be read
out of the assembly alone.

### Appearance

`DogLooks.UpdateLooks()` is the single funnel from genome to geometry. It
composes gene readings, an age ratio (puppies are not proportioned like adults)
and per-dog randomness. Highlights:

* **Body** — per-axis scale genes plus a global scale, clamped and additionally
  capped when the player enables `GameSettings.AreGeneticsCapped()`.
* **Legs** — front and back leg-pair counts, soft-capped at 6 and hard-capped at
  30; dominant/recessive "missing limb" traits delete specific legs.
* **Head** — size modifiers plus a head count, soft cap 4 and hard cap 10, with
  extra heads laid out in a ring. Big-head and tiny-head states trigger at
  0.625 and 0.25 of the size range.
* **Tail / wing / nose / ears / horns** — continuous size genes choose a
  magnitude, while the dominant/recessive genes choose the *type* from small
  enumerations (15 tail types, 10 ear types, 9 nose types, 6 wing types, 5 horn
  types).
* **Colour and emission** — per-part RGB and pattern RGB genes are combined
  against per-material min/max ranges; pattern type is one of none, splotches,
  stripes or repeating, baked into a texture by `TextureGeneration`.

### Behaviour and needs

`DogAI` loads behaviour scripts from a `"DogBehaviors"` template. Each
behaviour derives from `DogBehaviorBase` and declares a priority, target
conditions and a list of actions. There is **no classic state machine**:
`DogState` is unrelated (a short-range face raycast sensor).

Selection is utility-based. `DogAI.ChooseBehavior()` gathers candidate
behaviours per target, scores each, squares and scales the weights, then picks a
weighted random valid target. Scoring is dominated by **need relief**
(current minus potential need score, doubled), then target, room/reservation and
personality multipliers. Above that sit fixations (31 `FixationType` values) and
transient distractions. Dogs also learn by praise and scolding and keep an
opinion of other dogs, which feeds into breeding choices.

`DoggyBrain` holds five needs as separate components: **Hunger, Stress, Energy,
Anger, Boredom** (`Need` enum). Each has min/max/ideal and a decay rate, and is
scored as the squared distance from its ideal. Per-second constants:

| Need | Rate | Note |
|---|---|---|
| Hunger | `-0.0018` … `-0.001` | worsens as the dog becomes Ancient |
| Energy | `-0.0017` / `-0.0034` | |
| Boredom | `-0.0015` | |
| Stress | `+0.0005` | decays toward calm |
| Anger | `+0.0005` | |

Happiness is "all five needs inside tolerance bands" (0.5 and 0.8); the displayed
happy percentage averages hunger and energy. There is **no temperature, health
or mood stat** — those do not exist in the code.

### Ageing and death

Age runs through `PUPPY`, `CHILD`, `TEEN`, `YOUNG_ADULT`, `ADULT`, `ANCIENT`
and only advances while in the home pens and unpaused. Pre-adult stages last
300, 600, 600 and 600 seconds; adulthood lasts 2100 s. At the end of a stage a
dog becomes cocoon-ready and pupates in a cocoon, which is also when mutations
apply.

There are exactly **two** death causes, `OLD_AGE` and `HUNGER`:

* Old age adds a random end-of-life modifier (−300 … +900 s) to the adult
  timer; a dog with any life extension becomes `ANCIENT` first, otherwise it
  dies. The ancient stage caps at 10 800 s.
* Starvation kills after **480 s** at zero hunger, with a warning at 360 s.

Death is suppressed during the tutorial and when `GameSettings.IsDogDeathEnabled()`
is off. On death the dog's legs, head, tail and wings are scattered as food and
its body becomes food plus a `DogCore`, which can be memorialised into a
gravestone. Banished dead dogs become ghosts in `GhostManager`, with hunger and
energy frozen.

### Breeding

There is **no gender system** — any two adult, non-cocooned living dogs can
breed. Breeding consumes one unfertilised egg, which is the real currency of the
system. Selecting parents transitions to the breeding-centre scene, where
`BreedingController` produces a litter of **5** by default (range 1–8).

Inheritance combines both genomes:

* The quantitative genome either copies one parent wholesale or performs a
  crossover with probability `crossoverRate = 0.7`, splicing at the `|`
  separators (so genes stay intact).
* The dominant/recessive genome takes one allele from each parent per locus, then
  may flip an allele with a probability that grows as "stability" falls.
* Each pup then runs `MutateGenome`, which flips individual bits at
  `mutationRate = 0.0075` and can apply a `superMutationRate = 0.05`
  super-mutation that changes a gene's length.

"Stability" starts at 1.0 and drops roughly 0.10–0.15 per generation
(`expectedMaxGenerations = 10`). Lower stability means smaller litters and more
dominant/recessive mutation — the game's built-in incentive against repeatedly
inbreeding the same pair.

There is also passive egg laying: `DogEggLayingController` fills a timer over
**300 s** (half rate if the dog is unhappy) and lays an egg with a 1 % chance of
a second. It picks a mate weighted by the dog's opinion of others and uses a
fixed stability of 0.75, with mutation scaled by the `PassiveEggMutationRate`
setting. Separately, a happy adult lays a **capsule** every 180 s (50 % chance)
containing a dog core that extends lifespan.

### Mutation and gut flora

The headline mechanic. Every dog has a gut simulated in a separate 2D scene by
`DogGutsManager`, holding up to **35** `GutFloraBase` organisms. A new dog starts
with **10** flora drawn from its egg's flora pool.

Food is a vector for flora: each `Eatable` lists the flora types it introduces,
and eating spawns them into the gut. Flora have collision behaviours — they can
duplicate, boost, kill or transform one another, and undergo mitosis.

Mutations happen at pupation. `MasterDogGene.AdvanceDogGenes` scans the dog's
living flora, rolls each flora's mutation effects against their rarity, scales
the intensity by flora count (0.15 … 1.0), and dispatches through
`GutFloraMutations.MutateGeneFromEffect`, which maps roughly **70** effects onto
genetic properties. A single generation's change to any one property is capped
at `0.33`. Petting the cocoon for 2 s grants an extra mutation.

Dirt is a hazard: above **10** dirt flora a dog starts barfing (10 % chance per
check). Ancient dogs passively produce the *Bacillus Vitus* flora every 120 s.
Unfertilised "dud" eggs are produced when a dog accumulates 15 of the `scaph`
flora, laying 2–15 of them at once.

---

## World, construction and content

The world is a set of rectangular **rooms** connected by pipes. `RoomBase` owns
its walls, placed objects and their grids, carpet and wallpaper, spookiness,
gravity modifiers and sound players, plus a `focusTransform` the camera follows.
A "pen" is the player-facing name for a room: build categories are `PEN`, `PIPE`
and `MISC`, and `DogHome` tracks how many pens are unlocked.

`ConstructionManager` is a mode machine (`STANDARD`, `CONSTRUCTION`, `PLACEMENT`
plus sub-modes for new room, new pipe and destroy). Rooms and pipes are tracked
by unique IDs; `RoomPathfinder` does a breadth-first search over linked rooms to
decide what is reachable, and expansion nodes compute where a pipe can attach on
each wall. `ObjectPlacementManager` handles object, plant and puddle placement on
grids of 1.0, 0.25 and 1.0 units respectively, with a mode set of select, place,
move, edit, destroy and prune. `BuildableManager` loads buildable assets from
`Resources/BuildObjects/...`, each with an ID, footprint, price and build
category.

`PenFocus` is the camera brain: it drives several Cinemachine rigs (pen focus,
dog focus, tutorial, orthographic construction camera) and switches priority
between them, including a den interior/exterior mode.

Flora and the field guide connect the world to genetics: `FloraManager` records
which flora have been discovered, which food introduces them and their effects,
and reports field-guide completion. (`FloraManager.DoesNewDiscoveryExist()` is
hard-coded to return `false` — apparently stubbed.)

Progression runs through `GoalsController` (assets under `Resources/Goals/`),
`ResearchManager` (assets under `Resources/Researchables/`) and eight adventure
destinations. Goals track ~60 distinct `GoalCondition` counters and grant typed
rewards — items, researchables, dogs, food, rooms, eggs or gameplay flags — and
forward completion to Steam achievements. Adventures have a 180-second cooldown
and return flavour text plus a random researchable unlock.

**Uncertain:** no class in the code stores or spends a cash balance, even though
`BuildableObject.price`, a "Not enough money!" string in `BuildPrice` and a
`+$/-$` price indicator all exist. The economy appears to be vestigial or
disabled in this build.

UI is split between `GUIManagerBase`, `GUIManagerPens` (play/build/placement)
and `GUIManagerTitleScreen`, with a `GUIMode` of `PLAY`, `CONSTRUCT`,
`OBJECT_INFO` and `PLACEMENT`. Around two dozen screen controllers exist
(goals, dog storage, breeding selection, gut view, genetic inspection, flora,
research, photo mode, passive mode, inventory, building, adventure, mutation,
and per-object panels for incubators, feeders, gardens and so on).

Audio uses the third-party **ClockStone Audio Toolkit** wrapped by
`AudioController`, with sounds triggered by string keys (`AudioController.Play("pen_focus")`).
`SFXOverlord` locks and mutes categories, and `MusicPlaylistController` picks
music per location. Localisation uses **I2 Localization**, with generated
`ScriptTerms`/`ScriptLocalization` key classes.

## The cheat console

The debug console is vendor code in `Assembly-CSharp-firstpass/DevConsole`,
built on the `SickDev.CommandSystem` library. On first use it scans
`Assembly-CSharp.dll` and itself for methods marked `[Command]`: **38** in
`CheatEngine`, **54** in `CheatLookConsoleCommands`, plus a handful of console
utilities (clear, help, key remapping, log). It opens when Tab is held and `/`
or `\` is pressed, and closes with Escape — matching the game's shipped
`readme.txt`.

Most of these behaviours are gated by the `passive_*` settings stored in the
save file (over thirty of them), which is how the "passive mode" variations are
implemented.
