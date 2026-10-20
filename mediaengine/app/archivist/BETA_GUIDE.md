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

A reel is 5 seconds to 2 minutes long. While a reel is being made, its progress is shown at the top of every page, and
about how long is left once that can be estimated. When a long build (over a minute) has finished, Windows shows a notification - a click opens
the reel (can be turned off in Settings).

The AI analyses each video once and keeps it for every reel: a new reel from the same videos (another project, another
length, "A reel for every day") analyses nothing again. Big videos (4K) are analysed several at once. "Check this PC"
shows how much space this takes ("Free").
**"Prepare in advance"** (next to "Create reel"): MediaEngine only analyses the videos - for example overnight - and
the reel is then made from them in minutes ("Build" in the project). Videos added to the folder later are analysed
during the build.
To go back to an earlier version of the program: "Check this PC" -> "Use this version" (projects stay the same).
Only versions in the same folder whose folder holds just the program are listed; a version older than 11 October 2026
has no button: start it from its own folder.

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
"Test the graphics card" is on "Check this PC" too: if the graphics card decodes 4K faster than the processor with exactly the same
picture, MediaEngine cuts the videos with it (noticeable with big 4K folders); otherwise everything stays on the processor.

**AI+** is a stronger, optional model. Download it once on "Check this PC" (about 650 MB, free), then choose "AI+"
when you make a reel or a variant. The first analysis of new videos takes longer. It understands people and what
they do much better than AI (on public test photos it finds the right photo for a description in 86 of 100 cases,
AI in 60); for plain landscapes the difference is small. Use "Compare blind" to see which mode is better for your
videos.

With AI+ you can also pick a **theme** (sea and beach, mountains, children, family, celebration, animals, sunset,
nature, snow, city, food, sport, road trip, aerial view (drone) - without take-off and landing): the reel is then made of the moments that match it, from all the videos.
A new theme for videos already analysed takes seconds. In the **Library**, "Find by theme (AI+)" shows which videos
match a theme. "Prepare AI+ for the whole Library" looks at each video once (Private and rejected videos are never
included): then every search is instant (a video opens at its best moment) and AI+ reels from these videos are built
much faster. It can run overnight: it waits while a reel is being built and continues where it stopped.

**Music and title** (optional, under "Music and title" when you make a reel or a variant): a title and a second line
for the first 3 seconds, and your own song under the reel (with the videos' quieter sound or only the music). The
cuts fall on the beat of the music ("Cuts on the beat of the music"; a song without a clear beat leaves the cuts as
they were). Changing them later makes a new version quickly.

## Orders from other programs

Another program on this PC can order a video (**Auto Edit → Orders**). It puts a folder with `order.json` into
`MediaEngine Data\Orders\Inbox`; MediaEngine makes the video and puts it into `Orders\Done\<order>` (`video.mp4` +
`result.json`, a receipt with checks), or explains in `Orders\Failed` why it could not. Two kinds: a reel from videos
(MediaEngine chooses the moments; it is also a normal project) and a video exactly by plan (pictures, pieces of videos
and a narration with their times). New orders start at once or wait for your OK. MediaEngine publishes nothing.
The format for whoever writes the other program: `Orders\ORDERS.md`.

## Voice-over and captions

**Auto Edit → Voice-over.** A text read by a voice, with captions timed to the words; and captions for your own
videos. It is an add-on: the first time press "Install the voice add-on". It downloads about 8 GB once into the data
folder (MediaEngine goes online for it only then; free open models, nothing is sent anywhere). With an NVIDIA graphics
card the voice is made on it (seconds per sentence); without one, on the processor (about a minute per sentence).

- **New voice-over**: write the text the way it is said (short sentences; commas and dots where the pauses are) and
  choose a voice: "Host - the voice of 4_4" or "4_2" (your picks from the voice test; always the same voice), a voice from a description,
  or a voice from a recording of a person who agreed to it. Every piece is listened to; a piece with missing words is
  made again. Then listen, download the WAV and the captions (SRT), or **Put it on a video**: the video's own sound gets
  quieter while the voice speaks and the captions are burned in.
- **Captions for a video**: the speech in your video becomes captions burned into a copy.
- **Look of the captions**: bold capitals with the word being said in color (like Reels), on a dark box, classic, or
  calm (business); a color, a size, a place. A title at the top for the first 3 seconds and a text at the end can be
  added at once. The font (Montserrat, with Cyrillic) ships with the program.
- **Text on a video** (no add-on needed): titles and lines of text on any video at the seconds you choose - on a
  colored stripe, a dark box or in big letters. "Preview" shows a picture in a second, before the video is made.
- **Edit text and captions** (on a finished video): fix a word right in its line, change the look, add a text - a new
  video is made, the old one stays.

The new videos are saved next to your reels; your files are only read. "Remove the add-on" frees the space.

## What can leave this PC

Nothing leaves this PC by default. If you explicitly connect a provider or start an optional upload, authentication data, selected uploads, and provider analytics can be sent to that service.

Provider credentials belong in Windows Credential Manager, not MediaEngine SQLite or Supabase.

Cloud Vault is off by default. Its upload modes are exports only, selected media, or full archive mirror. Enabling cloud never deletes local or source originals.

Provider analytics retain source provenance and are descriptive. MediaEngine does not automatically choose a cross-provider winner or create an opaque ranking.

## New versions, tray, start

**Update** is a button at the top. Only when you press it does MediaEngine look on GitHub for a newer version; it shows
what is new, and "Update now" puts it into a new folder next to this one and switches to it (a few MB; the same
projects). The previous version stays: to go back, "Check this PC" → "Use this version". When the libraries
themselves changed, it says that the full installer is needed this time.

Closing the window does not stop MediaEngine (a reel being made goes on): its icon is in the tray next to the clock
(maybe under the ^ arrow). Click it to open the window, right-click → Quit to stop the program. Settings can start it
in the background when you sign in to Windows (off by default). A reel that was being made when the PC restarted is
made again by itself at the next start (once).

## Recovery and support

Diagnostics stay local by default. Use Activity > Jobs & errors to inspect durable job history. Failed jobs can be retried and running jobs can be cancelled safely.

Update health checks can restore the previous build if a new release fails to start. Recovery never silently weakens privacy settings and never deletes source originals.

Support export/upload is explicit opt-in only. This beta does not auto-upload support data. Raw media and tokens are excluded by default.
