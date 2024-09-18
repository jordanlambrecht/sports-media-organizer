# Sports Media Organizer

## Organizing your torrent downloader

It's highly recommended that you use sub-categories with your torrent downloader and enable automatic file management. The parent category should be 'sports' and the sub-category should be the sport flavor i.e 'wrestling'

## Naming Conventions

**Folders:** /{[league_name]}/Season {[air_year]} or Season 01/

**Files:** {[event_name]}-{[episode_title]}{-[part_number]}{.[air_year]}{.[air_month]}{.[air_day]}{.[codec]}{.[resolution]}{.[release_group]}.{[extension_name]}

**Example Folder + Filename (No Event Name):** /root/WWE Raw/Season 2012/WWE.Hall-of-Fame-Induction-Ceremony-2012.04.02.x264.720p-VANiLLA.mp4

**Example Folder + Filename (With Event Name):** /root/WWE Raw/Season 2012/Hell-in-a-Cell-2012.04.02.x264.720p-VANiLLA.mp4

**Example with Unknown Information:** /root/WWE Raw/Season 2012/[UNKNOWN-EVENT]-[UNKNOWN-TITLE]-2012.04.02.x264.720p.mp4

## Logic Flows

### League Matching Logic

```text
+---------------------------------------------+
|         infer_league (Controller)           |
+---------------------------------------------+
                    |
       +-----------------------------+
       |  Step 1: Match Using Regex  |
       +-----------------------------+
                     |
                Match Found?
            /                  \
         Yes                    No
         /                        \
+----------------------------+     +-------------------------------+
| High Confidence (90%)      |     | Step 2: Match Using Overrides |
| League Matched Using Regex |     +-------------------------------+
+----------------------------+                 |
              |                          Match Found?
         Return League                      /      \
                                       Yes          No
                                       /              \
                 +--------------------------------+    +--------------------------------+
                 | Medium Confidence (70%)        |    |  Step 3: Infer League from     |
                 | League Matched Using Overrides |    |  Directory Structure           |
                 +--------------------------------+    +--------------------------------+
                              |                                           |
                         Return League                               Match Found?
                                                                         / \
                                                                      Yes   No
                                                                      /       \
                                 +---------------------------------------+    +-------------------------+
                                 | Low Confidence (50%)                  |    | Step 4: Fallback        |
                                 | League Inferred from Directory        |    | Default to "Unknown"    |
                                 +---------------------------------------+    +-------------------------+
                                              |                                   |
                                        Return League                         Return "Unknown"

```

### Date, Seasons, Part Numbers

1. Controller: extract_date_and_season
   • Calls multiple sub-methods to extract date and season information.
   • Confidence is calculated based on how the date is extracted.
2. Stage 1: Extract Date from String
   Tries to extract the date directly from the string using known formats.
   - If a match is found:
     - Return the result.
     - High confidence (90%).
   - If no match:
     - Proceed to Stage 2.
3. Stage 2: Handle Incomplete Dates
   Handles incomplete or special date formats (e.g., 87.04.22A -> 1987, Part A).
   - If a match is found:
     - Medium confidence (70%).
     - Return the result.
   - If no match:
     - Proceed to Stage 3.
4. Stage 3: Infer Year from Directory
   Attempts to infer the year from the directory structure (e.g., /WWE/1987/...).
   - If a match is found:
     - Low confidence (50%).
     - Return the result.
   - If no match:
     - Proceed to Stage 4.
5. Stage 4: Fallback to “Unknown”
   - If no date can be extracted or inferred:
     - Return "Unknown" for date and season.
     - Confidence: 0.

```text
┌--------------------------------------------+
|  extract_date_and_season (Controller)      |
+--------------------------------------------+
                     |
              ┌------------------+
              |  Stage 1:        |
              |  Extract Date    |
              |  from String     |
              +------------------+
                            |
                      Match Found?
                          / \
                       Yes   No
                       /       \
┌-------------------------+       ┌---------------------+
| High Confidence (90%)   |       |  Stage 2: Handle    |
| Date Extracted Directly |       |  Incomplete Dates   |
+-------------------------+       +---------------------+
           |                                |
      Return Results                  Match Found?
                                           / \
                                        Yes   No
                                        /       \
               ┌--------------------------+    ┌-----------------------+
               | Medium Confidence (70%)   |    | Stage 3: Infer Year   |
               | Handled Incomplete Date   |    | from Directory        |
               +--------------------------+    +-----------------------+
                                                   |
                                              Match Found?
                                                  / \
                                               Yes   No
                                               /       \
                         ┌---------------------------------+    ┌--------------------+
                         | Low Confidence (50%)            |    | Stage 4: Fallback  |
                         | Year Inferred from Directory    |    | Default to "Unknown"|
                         +---------------------------------+    +--------------------+
                                      |                                |
                                 Return Results                  Return "Unknown"

```

### Codec Extraction

```text

  ┌----------------------------------------------+
  |   codec_extract_from_filename (Controller)   |
  +----------------------------------------------+
                         |
        ┌----------------------------------+
        |   Step 1: Match from Filename    |
        +----------------------------------+
                         |
               ┌----------------------+
               |  Extract Codec       |
               |  from Filename using |
               |  YAML (codecs.yaml)  |
               +----------------------+
                         |
             ┌--------------------------+
             |  Extract Resolution      |
             |  from Filename using     |
             |  YAML (resolutions.yaml) |
             +--------------------------+
                         |
              ┌------------------------+
              |  Extract Release       |
              |  Format from Filename  |
              |  using YAML            |
              |  (release-types.yaml)  |
              +------------------------+
                         |
            Are both Codec & Resolution found?
                     /       \
                  Yes         No
                 /             \
 ┌---------------------+    ┌---------------------------+
 |  High Confidence    |    | Step 2: Fallback to       |
 |  Return Codec &     |    | ffprobe for Missing Data  |
 |  Resolution         |    |                           |
 +---------------------+    +---------------------------+
                                         |
                               ┌---------------------+
                               |  Use ffprobe to     |
                               |  Extract Codec,     |
                               |  Resolution, Width, |
                               |  Height from file   |
                               +---------------------+
                                         |
                             ┌────────────────────────+
                             │  Return Codec,          │
                             │  Resolution (if         │
                             │  extracted by ffprobe)  │
                             +────────────────────────+

```

### Release Groups

```text
     ┌────────────────────────────────────────────────────────────────┐
     │                  release_group_extract_from_filename           │
     │                          (filename)                            │
     └────────────────────────────────────────────────────────────────┘
                                     │
                ┌────────────────────┴─────────────────────────┐
                │                                              │
                ▼                                              ▼
  ┌────────────────────────────────┐     ┌────────────────────────────────────┐
  │  release_group_match_from_yaml │     │  release_group_match_using_regex   │
  │          (filename)            │     │           (filename)               │
  └────────────────────────────────┘     └────────────────────────────────────┘
            │                                                  │
            ▼                                                  ▼
  ┌───────────────────────────────┐         ┌──────────────────────────────┐
  │       Match found in YAML?    │         │    Match found via Regex?    │
  │             (Yes/No)          │         │           (Yes/No)           │
  └───────────────────────────────┘         └──────────────────────────────┘
            │                                                  │
            │              ┌─────────────────────┐             │
            ├─── Yes ───▶  │     Return group    │  ◀─── Yes ──┤
            │              └─────────────────────┘             │
           Nah                                                Nah
            │                                                  │
            ▼                                                  ▼
   ┌─────────────────────────────┐                  ┌─────────────────────────┐
   │      Check if               │                  │  check if release_group │
   │  is_release_group_in_yaml?  │                  │        = "Unknown"      │
   └─────────────────────────────┘                  └─────────────────────────┘
            │                                                  │
            ▼                                                  ▼
  ┌───────────────────────────────┐             ┌──────────────────────────────┐
  │   Found in YAML? (Yes/No)     │             │   Config: append_unknown_    │
  │                               │             │  release_group is True?      │
  └───────────────────────────────┘             └──────────────────────────────┘
            │                                                  │
            │          ┌─────────────────────────┐             │         ┌───────────────┐
            ├─ No ──▶  │  add_release_group      │             ├─ No ──▶ │   Return " "  │
            │          │  to release-groups.yaml │             │         └───────────────┘
           Yes         └─────────────────────────┘            Yes
            │                                                  │
            │                                                  ▼
            ▼                                          ┌────────────────────────────────┐
  ┌────────────────────────┐                           │     release_group = "UnKn0wn"  │
  │  Return release_group  │                           │       Return release_group     │
  └────────────────────────┘                           └────────────────────────────────┘
```

### Title, Part Numbers

```text
     ┌──────────────────────────────────────────────────────────────────────┐
     │                episode_title_extract_from_filename                   │
     │                            (filename, slots)                         │
     └──────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────────────────────────────┐
  │          Apply Global Substitutions (from YAML)           │
  │       (from YAML: pre_run_filename_substitutions)         │
  │                        (filename)                         │
  └───────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────────────────────────────┐
  │             Extract Part Number (if exists)               │
  │             (e.g., 2012-04-02a -> part-01)                │
  │                (filename, episode_part)                   │
  └───────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────────────────────────────┐
  │          Set episode_part in slots                        │
  │  (slots["episode_part"] = part_number)                    │
  └───────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────────────────────────────┐
  │          Apply Global Filters (from YAML)                 │
  │  (Removes unwanted text: pre_run_filter_out)              │
  │             (filename)                                    │
  └───────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────┐
  │           Extract Event Name from Filename                 │
  │   (Use regex or YAML wildcards to pull event name)         │
  │           (filename, slots["event_name"])                  │
  └────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────┐
  │       Apply Sport-Specific Overrides (from YAML)           │
  │  (Wildcard Matches for league/event in YAML)               │
  │            (slots, filename)                               │
  └────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────┐
  │      Remove Known Components from Filename                 │
  │  (Remove league_name, event_name, date, codec, resolution, │
  │  release group)                                            │
  │                     (slots, filename)                      │
  └────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────┐
  │              Clean Episode Title                           │
  │  (Replaces spaces/periods with dashes, removes unwanted    │
  │   characters)                                              │
  │            (title)                                         │
  └────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────┐
  │            Return Cleaned Episode Title (title)            │
  └────────────────────────────────────────────────────────────┘
```

### Special Event Flows

```text
 ┌─────────────────────────────────────────────────────────────────┐
 │                  event_name_extract_from_filename               │
 │                          (filename, slots)                      │
 └─────────────────────────────────────────────────────────────────┘
                                 │
                ┌────────────────┴──────────────────────┐
                │                                       │
                ▼                                       ▼
 ┌────────────────────────────────────┐   ┌──────────────────────────────────────┐
 │  event_name_match_from_overrides   │   │   event_name_infer_from_filename     │
 │        (filename, slots)           │   │            (filename)                │
 └────────────────────────────────────┘   └──────────────────────────────────────┘
                │                                       │
                ▼                                       ▼
 ┌───────────────────────────────────┐     ┌───────────────────────────────────┐
 │     Match found in overrides?     │     │   Match found in filename using   │
 │            (Yes/No)               │     │          regex patterns?          │
 └───────────────────────────────────┘     └───────────────────────────────────┘
                │                                       │
               Yes                                      No
                │                                       │
                ▼                                       ▼
 ┌──────────────────────────┐             ┌────────────────────────────┐
 │  Return matched event    │             │  Event name set as ""      │
 └──────────────────────────┘             └────────────────────────────┘
                │
                ▼
 ┌───────────────────────────────────────────────┐
 │  event_name_cleanup (clean up unwanted text)  │
 └───────────────────────────────────────────────┘
                │
                ▼
 ┌───────────────────────────────────────────────────────────┐
 │  Return cleaned event, or remove event_name slot if None  │
 └───────────────────────────────────────────────────────────┘
```

### File Extension Flows

```text
         ┌──────────────────────────────────────────────────────────┐
         │                  extension_extract_controller            │
         │                          (filename)                      │
         └──────────────────────────────────────────────────────────┘
                                     │
                ┌────────────────────┴─────────────────────┐
                │                                          │
                ▼                                          ▼
 ┌──────────────────────────────────────┐   ┌──────────────────────────────────────┐
 │    extension_extract_from_filename   │   │         extension_validate           │
 │               (filename)             │   │            (extension)               │
 └──────────────────────────────────────┘   └──────────────────────────────────────┘
                │                                          │
                ▼                                          ▼
      ┌───────────────────────────┐             ┌─────────────────────────────────┐
      │    Return file extension  │             │    Validate extension against   │
      │                           │             │  allowed and blocked extensions │
      └───────────────────────────┘             └─────────────────────────────────┘
```

## To-Do

- [ ] Add additional sports categories beyond wrestling.
- [ ] Hunt down more poorly-named wrestling files to expand outlier matching
