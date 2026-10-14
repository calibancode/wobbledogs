# Code map

Namespaces and types in the reconstructed assemblies. Generated from the
decompiled source; regenerate after re-decompiling.

For how the game behaves, see [GAME_MECHANICS.md](GAME_MECHANICS.md) and
[SAVE_FORMAT.md](SAVE_FORMAT.md).

## Assembly-CSharp

1121 source files, 1302 type declarations across 16 namespaces.

| Namespace | Types | Kinds |
|---|---:|---|
| `<global>` | 994 | 747 class, 146 enum, 71 delegate, 29 struct, 1 interface |
| `I2.Loc` | 109 | 82 class, 14 enum, 6 delegate, 4 struct, 3 interface |
| `Poly2Tri` | 47 | 37 class, 7 enum, 2 struct, 1 interface |
| `SimplySVG` | 41 | 32 class, 3 delegate, 3 enum, 3 interface |
| `ClipperLib` | 26 | 14 class, 8 enum, 4 struct |
| `ClockStone` | 23 | 17 class, 3 enum, 2 interface, 1 delegate |
| `XNode` | 16 | 12 class, 4 enum |
| `Technie.PhysicsCreator.QHull` | 11 | 11 class |
| `Technie.PhysicsCreator` | 10 | 9 class, 1 enum |
| `I2.Loc.SimpleJSON` | 7 | 6 class, 1 enum |
| `Moments` | 5 | 4 class, 1 enum |
| `UnityEngine.AI` | 5 | 4 class, 1 enum |
| `Moments.Encoder` | 4 | 4 class |
| `InControl` | 2 | 2 class |
| `Assets.Scripts.Core` | 1 | 1 class |
| `MessengerExtensions` | 1 | 1 class |

## Assembly-CSharp-firstpass

506 source files, 568 type declarations across 6 namespaces.

| Namespace | Types | Kinds |
|---|---:|---|
| `Steamworks` | 485 | 283 struct, 104 enum, 68 class, 30 delegate |
| `UnityStandardAssets.ImageEffects` | 55 | 35 class, 20 enum |
| `HighlightingSystem` | 21 | 11 class, 6 enum, 2 delegate, 2 struct |
| `DevConsole` | 3 | 2 class, 1 struct |
| `RelationsInspector.Backend.AutoBackend` | 3 | 3 class |
| `<global>` | 1 | 1 class |

## Largest reconstructed types

By decompiled source size; a rough guide to where the game's logic sits.

| Type | Bytes | File |
|---|---:|---|
| `DogLooks` | 115,627 | `DogLooks.cs` |
| `ObjectPlacementManager` | 91,624 | `ObjectPlacementManager.cs` |
| `ConstructionManager` | 90,691 | `ConstructionManager.cs` |
| `ScriptLocalization` | 79,815 | `I2/Loc/ScriptLocalization.cs` |
| `Clipper` | 75,713 | `ClipperLib/Clipper.cs` |
| `PenFocus` | 62,817 | `PenFocus.cs` |
| `DoggyBrain` | 61,736 | `DoggyBrain.cs` |
| `DogRegistration` | 60,636 | `DogRegistration.cs` |
| `ObjectGrabber` | 60,039 | `ObjectGrabber.cs` |
| `DogAI` | 57,537 | `DogAI.cs` |
| `DogStorageGUIManager` | 57,105 | `DogStorageGUIManager.cs` |
| `GutFloraMutations` | 53,899 | `GutFloraMutations.cs` |
| `ScriptTerms` | 53,474 | `I2/Loc/ScriptTerms.cs` |
| `AudioController` | 52,566 | `AudioController.cs` |
| `RoomBase` | 48,840 | `RoomBase.cs` |
| `LanguageSourceData` | 46,333 | `I2/Loc/LanguageSourceData.cs` |
| `LegController` | 45,588 | `LegController.cs` |
| `ControlManager` | 44,525 | `ControlManager.cs` |
| `GoogleLanguages` | 44,391 | `I2/Loc/GoogleLanguages.cs` |
| `SaveLoadManager` | 42,093 | `SaveLoadManager.cs` |
| `MasterDogGene` | 38,858 | `MasterDogGene.cs` |
| `GeneticInspectionGUIManager` | 33,719 | `GeneticInspectionGUIManager.cs` |
| `BreedingGUI` | 33,462 | `BreedingGUI.cs` |
| `GUIManagerPens` | 33,074 | `GUIManagerPens.cs` |
| `FaceController` | 32,964 | `FaceController.cs` |
