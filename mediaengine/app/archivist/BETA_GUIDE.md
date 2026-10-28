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
length, "A reel for every day") analyses nothing again. Big videos (4K) are analysed several at once. DJI videos
(drones, Osmo): when the camera's small copy `.LRF` lies next to a video, the AI finds the moments in it - much
faster - and the reel is still cut from the original 4K. "Check this PC"
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

**Colours** (new reel or a variant): "As filmed" (nothing changed), "Brighter and richer" (pale drone or phone videos
come out livelier), "Warm" (golden light) or "Cinematic" (softer contrast, cooler shadows). Only the reel is coloured;
the videos stay as they are. Another colour later is a new version made in about the time of a variant.

## Clips from a long video

Auto Edit → **Clips from a long video**: choose a podcast, a stream or an interview and the length of a clip (15–30,
30–60 or 45–90 s), press "Find clips". MediaEngine listens to the speech once (the voice add-on's Whisper: about 5–15
minutes for an hour of video) and lists the parts that make good short clips - whole sentences, the likeliest first,
with their words. Read, press ▶ Play to watch a part, change the start or end if you like, tick the ones you want and
press "Make the ticked clips". Each becomes a vertical 9:16 clip (or square, or as filmed): the face kept in the
frame (someone walking: the frame goes with them; two people apart, as in a podcast: each in its own half, one above
the other, the captions between them; people side by side or three and more: all of them, as big as they fit, on
blurred edges - or, with "The one speaking, close up", whoever is talking, switching when another one talks; a
streamer's camera in a corner of a game: the camera above, the game below), the video's own sound
evened out, captions with the words in the look you choose, optionally the first sentence as a title. They are saved next to the saved reels in a folder
"<video> - clips", named by their first words. Use only videos you may cut (your own, or footage a clipping campaign
gives you).

## Cartoon Studio

Auto Edit → **Cartoon Studio**: a short 2D cartoon made by MediaEngine itself - its own characters (drawn the same in
every scene and episode), backgrounds (a street, an office, the city hall, a road, a bank, night, a board for schemes),
schemes of money with arrows, contracts with a stamp, charts, a road with potholes; the characters' voices (the voice
add-on: the narrator in the program's own voice, the others in voices from a description, kept for the next
episode), mouths moving with the words, captions, short sounds. Choose the example story (How a City Loses Millions
on a Simple Road Contract) or paste a script, vertical 9:16 or wide 16:9, press "Make the cartoon". On the film's page
change any line, who says it, the feeling, the gesture or a scene's background and press "Make it again" - a new
version, the old one stays. Without the voice add-on: a quick preview without voices. Saved in "Cartoons" next to the
saved reels. The story is plain text: change the example or write your own (the help on the page shows how).

**Write a story** (a free model on this PC): install the story writer once - Qwen3-14B (Alibaba, Apache-2.0, about 9 GB:
writes better, Russian and Romanian too; for a graphics card with 12 GB) or Qwen3-4B (about 4.3 GB, any PC), with
llama.cpp (MIT), into the data folder; it runs on the graphics card (or the processor) and sends nothing anywhere;
"Another model" changes it later. Then write a topic in a few words - or paste a text (an article, notes, what is said in a video) -
choose the language (English, Russian, Romanian), the viewers' country if it matters, the length and the format, and
press "Write the story": about a minute on a graphics card, several minutes on the processor. Read the story, change
what you like and press "Make the cartoon". "Write another version" asks again; "Another language or country" retells
a story (also a finished cartoon's) with the country's own names, money and offices. Nothing the model writes is a
fact check: read it before you publish.

**Characters** (the button at the top of Cartoon Studio): everyone your cartoons have used, with a picture. A
character keeps its look and voice in every new film whose story names it; change the skin, hair, hairstyle, beard,
clothes and their colour, glasses, a hard hat, the role and the voice's description (a new description makes a new
voice, kept again). Characters walk into a scene they were not in; a scene only the narrator speaks in shows the
narrator presenting it.

## Converting videos

**Media → Convert** (or "Convert" on videos chosen in the Library, or "Choose videos on this PC"). The copies go into
the "Converted" folder in MediaEngine's data folder (or a folder you choose - "Change…"); your videos are only read,
nothing is written to cards or source folders.

- **Preset**: Share 1080p (messengers and sharing), Small 720p, High Quality 1080p or Original Resolution (the same
  size). All H.264 + AAC - plays everywhere. "Fit under … MB" picks the quality for a size (for a messenger, say).
- **Join into one video**: the parts of one GoPro recording in their order; several recordings - one video each.
- **Cut…**: start and end to the frame; "Save this picture" - a JPG; "Turn the picture"; "Without sound".
- **More**: faster 2/4/8x or slow motion ½x / ¼x, vertical 9:16, your logo in a corner, less wind, even out the sound,
  the date and time of filming in a corner (by the camera's or the phone's clock), brighter.
- **Pictures every 5/10/30/60 seconds** - pictures and one PDF for a report (with your own title).
- Conversions run one at a time: the next waits in line ("Take out of the line"). When ready: "Show in folder", "Open
  video", "Copy file" (Ctrl+V pastes it into a messenger or a folder), "Earlier conversions".
- **NVIDIA graphics card**: "Check this PC → Test converting on the graphics card" (about two minutes, your videos are
  not used; the first conversion runs it by itself). The card is used only if it is faster with the same picture; after this test also for the More options
  and turned videos.

## Orders from other programs

Another program on this PC can order a video (**Auto Edit → Orders**). It puts a folder with `order.json` into
`MediaEngine Data\Orders\Inbox`; MediaEngine makes the video and puts it into `Orders\Done\<order>` (`video.mp4` +
`result.json`, a receipt with checks), or explains in `Orders\Failed` why it could not. Two kinds: a reel from videos
(MediaEngine chooses the moments; it is also a normal project) and a video exactly by plan (pictures, pieces of videos
and a narration with their times). New orders start at once or wait for your OK. MediaEngine publishes nothing.
The format for whoever writes the other program: `Orders\ORDERS.md`.

## Voice-over and captions

**Auto Edit → Voice-over and text.** A text read by a voice, with captions timed to the words; and captions for your own
videos. It is an add-on: the first time press "Install the voice add-on". It downloads about 13 GB once into the data
folder (MediaEngine goes online for it only then; free open models, nothing is sent anywhere). An add-on installed
before 21 October offers "Download the new voice engine" (Qwen3-TTS, about 4.7 GB): the voice 9_2 and the voices from
a recording are then said by it - livelier (your pick 14_5); a voice from a description stays on VoxCPM2. With an NVIDIA graphics
card the voice is made on it (seconds per sentence); without one, on the processor (about a minute per sentence).

- **New voice-over**: write the text the way it is said (short sentences; commas and dots where the pauses are) and
  choose a voice: "Host - the voice of 9_2" (your pick from the voice test; always the same voice, each piece at its own pitch), a voice from a description,
  or a voice from a recording of a person who agreed to it. "Pace": a bit slower or faster, shorter or longer pauses
  between sentences (the voice keeps its pitch). Every piece is listened to; a piece with missing words is
  made again. Then listen, download the WAV and the captions (SRT), or **Put it on a video**: the video's own sound gets
  quieter while the voice speaks and the captions are burned in.
- **Captions for a video**: the speech in your video becomes captions burned into a copy.
- **Look of the captions**: bold capitals with the word being said in color (like Reels), on a dark box, classic,
  calm (business), one word at a time (like TikTok), or the word being said on a color block; a color, a size, a place. A title at the top for the first 3 seconds and a text at the end can be
  added at once. The font (Montserrat, with Cyrillic) ships with the program.
- **Text on a video** (no add-on needed): titles and lines of text on any video at the seconds you choose - on a
  colored stripe, a dark box or in big letters. "Preview" shows a picture in a second, before the video is made.
- **Finish a video** (a saved reel → "Text, captions, voice-over"): everything for one video on one page - a voice
  (none, one made already or a new one), captions (the voice's words or the video's speech), the look, texts,
  music under it (quieter while the voice speaks), a preview, one button. "More videos, finished the same way": several
  videos at once (paths, Choose… for several, or saved reels ticked) - one new video each, with the same voice
  (a new voice-over is made once), captions, look, texts and music.
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
themselves changed, it says that the full installer is needed this time. Old versions pile up next to it: "Check this PC" →
"Remove the older versions" removes them and keeps the two newest (projects and reels are not touched).

Closing the window does not stop MediaEngine (a reel being made goes on): its icon is in the tray next to the clock
(maybe under the ^ arrow). Click it to open the window, right-click → Quit to stop the program. Settings can start it
in the background when you sign in to Windows (off by default). A reel that was being made when the PC restarted is
made again by itself at the next start (once).

## Recovery and support

Diagnostics stay local by default. Use Activity > Jobs & errors to inspect durable job history. Failed jobs can be retried and running jobs can be cancelled safely.

Update health checks can restore the previous build if a new release fails to start. Recovery never silently weakens privacy settings and never deletes source originals.

Support export/upload is explicit opt-in only. This beta does not auto-upload support data. Raw media and tokens are excluded by default.
