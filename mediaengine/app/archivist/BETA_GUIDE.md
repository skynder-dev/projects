# MediaEngine Beta Guide

MediaEngine is local-first. Your media stays on this PC unless you explicitly connect a provider or enable an optional cloud workflow.

No external account or billing is required for local use.

## Making a reel (Auto Edit)

1. Auto Edit -> "Choose folder..." (a folder of videos on this computer) or "Choose videos..." (single files).
   Phone videos: copy them to the computer first.
2. Pick Length, Format and Sound -> "Create reel". Analysis of new videos takes a while; later builds reuse it.
3. Review: remove, replace, trim or reorder moments; every change is a new version, older ones stay.
4. "Save MP4" (or "Save to another folder...") on any finished version, one click. Next to it, "Small copy for
   messengers" (about 720p, a much smaller file). "Exported reels" at the top of the Auto Edit page opens the folder
   with the finished reels.

A reel is 5 seconds to 2 minutes long. While a reel is being made, its progress is shown at the top of every page.
To go back to an earlier version of the program: "Check this PC" -> "Use this version" (projects stay the same).

A new reel starts with the last reel's format, sound and mode. A vertical reel from horizontal videos can "Fill the
screen" (cropped to the interesting part) or show the "Whole picture, blurred edges". When Auto muted a reel, "The
same reel with the original sound" builds it with the sound.

One reel takes up to 64 videos. A folder with more (a whole phone, say) shows its shooting days (from the file name
or the recording time in the video) and a tick list; "A reel for every day" makes one reel for each day of a trip.
A camera card can be chosen at its root: the video folders inside it are listed. In the Library, select videos and
press "Make a reel".

A project you no longer need: "Archive", then "Delete" in the archive frees its space; saved MP4 files and the
original videos stay. The database and settings are copied automatically (once a day and before a new build first
runs) to "MediaEngine Data\data\backups".

Your original files are only read, never changed. "Check this PC" (Home, Settings, Auto Edit) shows whether the
AI model and video tools are found and builds a 5-second test reel. The language switch is at the top right.

**AI+** is a stronger, optional model. Download it once on "Check this PC" (about 650 MB, free), then choose "AI+"
when you make a reel or a variant. The first analysis of new videos takes longer. It understands people and what
they do much better than AI (on public test photos it finds the right photo for a description in 86 of 100 cases,
AI in 60); for plain landscapes the difference is small. Use "Compare blind" to see which mode is better for your
videos.

With AI+ you can also pick a **theme** (sea and beach, mountains, children, family, celebration, animals, sunset,
nature, snow, city, food, sport, road trip): the reel is then made of the moments that match it, from all the videos.
A new theme for videos already analysed takes seconds. In the **Library**, "Find by theme (AI+)" shows which videos
match a theme. "Prepare AI+ for the whole Library" looks at each video once (Private and rejected videos are never
included): then every search is instant (a video opens at its best moment) and AI+ reels from these videos are built
much faster. It can run overnight: it waits while a reel is being built and continues where it stopped.

**Music and title** (optional, under "Music and title" when you make a reel or a variant): a title and a second line
for the first 3 seconds, and your own song under the reel (with the videos' quieter sound or only the music). The
cuts fall on the beat of the music ("Cuts on the beat of the music"; a song without a clear beat leaves the cuts as
they were). Changing them later makes a new version quickly.

## What can leave this PC

Nothing leaves this PC by default. If you explicitly connect a provider or start an optional upload, authentication data, selected uploads, and provider analytics can be sent to that service.

Provider credentials belong in Windows Credential Manager, not MediaEngine SQLite or Supabase.

Cloud Vault is off by default. Its upload modes are exports only, selected media, or full archive mirror. Enabling cloud never deletes local or source originals.

Provider analytics retain source provenance and are descriptive. MediaEngine does not automatically choose a cross-provider winner or create an opaque ranking.

## Recovery and support

Diagnostics stay local by default. Use Activity > Jobs & errors to inspect durable job history. Failed jobs can be retried and running jobs can be cancelled safely.

Update health checks can restore the previous build if a new release fails to start. Recovery never silently weakens privacy settings and never deletes source originals.

Support export/upload is explicit opt-in only. This beta does not auto-upload support data. Raw media and tokens are excluded by default.
