# Save data

Wobbledogs persists to `%USERPROFILE%\AppData\LocalLow\Animal Uprising\Wobbledogs\`
(Unity's `Application.persistentDataPath`). On Linux/Proton that resolves inside
the prefix at
`pfx/drive_c/users/<user>/AppData/LocalLow/Animal Uprising/Wobbledogs/`.

Documenting the format is useful because it is data, not source: a save is
readable without decompiling anything.

## Files

| File | Contents |
|---|---|
| `wobbledogsData_<slot>.dat` | A save slot. `_0` is the *slot index*, not a literal |
| `backup_wobbledogsData_<slot>_<n>.dat` | Rotating backup of a slot |
| `controlsData.dat` | Input rebindings, independent of any slot |

The names come from `SaveLoadManager.cs`: `"/wobbledogsData_"` plus the slot
number plus `".dat"`. A new slot is created as the highest existing index plus
one, so the first save is exactly `wobbledogsData_0.dat`; on load the game
defaults to the *lowest*-numbered existing file (`ActiveSaveFile.cs`).

## Serializer

The format is .NET **`BinaryFormatter`**. Every read and write in
`SaveLoadManager.cs` goes through `new BinaryFormatter().Serialize(...)` /
`.Deserialize(...)`; no JSON, XML or custom binary format appears anywhere in
the path.

The first bytes of a real save confirm it (record type 0 = `SerializedStreamHeader`,
root id 1, header id −1), followed immediately by the length-prefixed
`BinaryLibrary` name for the root type's assembly:

```
00000000: 0001 0000 00ff ffff ff01 0000 0000 0000
00000010: 000c 0200 0000 4641 7373 656d 626c 792d   ....FAssembly-
00000020: 4353 6861 7270 2c20 5665 7273 696f 6e3d   CSharp, Version=
...
```

`0c 02 00 00 00` is a `BinaryLibrary` record whose length-prefixed string is
`Assembly-CSharp, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null`. The
root object's type name follows in the object records (`SaveFile`, then
`PlayerData`, then its fields by name). Byte order is little-endian, the .NET
default.

## Structure

The root is `SaveFile` (`SaveFile.cs`), marked `[Serializable] internal`:

* `string fileName` — the slot's display name;
* `PlayerData mainData` — everything else.

`PlayerData` (`PlayerData.cs`) is the real payload. Grouped:

* **Progression** — `newSave`, `initialEggCollected`, `hasGeneratedCorePortraits`,
  `tutorialState`, `currentGameMode`, `IDCounter`;
* **Owned things** — `SaveableDogs dogs`, `SaveableInventory inventory`,
  `SaveableGoals goals`, `SaveableResearchStatus research`,
  `List<SaveableFloraUnlock> floraUnlocks`;
* **World** — `SaveableTaggedObjects worldTaggedObjectsHome` (placed objects and
  cocoons), `SaveableDogHome dogPenHome` and `dogPenBreedingCenter` (rooms,
  pipes and per-home ID counters), `SaveableDogDenManager dogDenManager`;
* **Breeding** — `dogToBreedA` / `dogToBreedB` slots;
* **Play time** — `SaveableDateTime dateTime`;
* **Settings** — `cappedGenetics`, `dogDeathEnabled`, `customAverageAdultDogLifespanInMinutes`
  and over thirty `passive_*` flags that gate the passive-mode behaviours.

A `SaveableDog` (`SaveableDog.cs`) embeds the dog's genome, brain, gut contents,
thumbnail textures, profile, position and age state. There is **no cash or
currency field** — consistent with the economy appearing vestigial elsewhere.

## Backups

Two distinct mechanisms exist, and they are easy to confuse:

1. **Write-time temp copy.** Before every write, `CreateBackupFile` copies the
   live file to `<name>_tempCopy.dat`. It is deleted after a successful write;
   on failure it is promoted to `<name>_tempCopy_backup.bak`.
2. **Rotating load-time backup.** When a slot is loaded outside the main menu,
   `MakeBackupsIfNeeded` copies the current file to `backup_<slot>_0.dat`, or
   `_1.dat` if a `_0` already exists. At most one prior backup is kept — the
   oldest is deleted — and it fires at most once per file per session.

`RestoreFileFromMostRecentValidBackup` loads the newest file that still
deserializes, which is the recovery path if a save is corrupted.

## controlsData.dat

`SavedControlsFile` (`SavedControlsFile.cs`) holds a default `ControlMapping`
plus a dictionary of Steam user id → `ControlMapping`. A `ControlMapping` is a
stick-toggle flag and a list of `CommandMapping` entries, each storing an
InControl command plus keyboard, mouse and controller rebindings. It is written
by `ControlManager.SaveControlMapping()` when the controls menu closes, and a
default file is created if none exists. Note the save opens with
`FileMode.Open`, so the file must already be present to be written.

## Versioning and integrity

There is **no top-level save version field, no migration path, no checksum and
no obfuscation**. Specifically absent: `ISerializable`,
`OnSerializing`/`OnDeserialized`, `[OptionalField]`, `SerializationBinder`,
`GZipStream`/`DeflateStream`, and any encryption (`Aes`, `Rijndael`,
`CryptoStream`). The only version marker anywhere is
`SaveableGoals.goalsVersion`, whose sole migration resets one goal when the
value is 0.

That means a save can be edited by hand, but also that there is nothing to
detect or repair a bad edit.

## Notes for a parser

If you want to read saves without the game:

* You must implement the .NET `BinaryFormatter` wire format — record types,
  the object table with back-references, length-prefixed assembly-qualified type
  names, little-endian. The root type is `Assembly-CSharp`'s `SaveFile`.
* Dictionaries are **not** native `Dictionary<,>`; they are a
  `SerializableDictionary<T,T2>` with parallel `keys` and `values` lists.
* `[NonSerialized]` fields exist and are simply absent on disk.
* Expect engine wrapper structs (`SerializableVector3`, `SerializableColor`) and
  enums serialized numerically.
* No delegate or event *fields* are stored, so that classic hazard does not
  apply here.
* The graph is large and field-order sensitive; there is no checksum, so a
  mismatched field set surfaces as a deserialization failure rather than a
  clear error.

Reading arbitrary saves reliably is easiest by loading the type graph with
`BinaryFormatter` itself against a compatible `Assembly-CSharp`, which is what
this project can rebuild.
