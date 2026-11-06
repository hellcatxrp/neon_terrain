# Music visualiser

A TouchDesigner music visualiser. It plays a folder of audio files, or a Discord voice channel through VB-Audio Virtual Cable, and draws a neon spectrum terrain that scrolls with the music.

![Neon spectrum terrain](_preview/kick_moment.png)

The front line is the live spectrum, with bass in the middle. Older moments recede toward the horizon. Loud sections rush forward and quiet sections nearly freeze. Kicks flare the front line. Colour follows the section.

The network is built by `build_music_rack.py` inside TouchDesigner. The `.toe` files in this folder are project shells. Run the script, then save, and the rack is in the project.

This copy was built and run on **TouchDesigner 2023.12480** (product version `0.99.2023.12480`) on Windows. The picture is 1280×720.

## What you need

- Windows 10 or Windows 11, and an Administrator account for the installer.
- A GPU and driver that support Vulkan 1.1. Derivative asks for at least 4 GB of GPU memory, with 8 GB recommended, and a current driver from Nvidia, AMD, or Intel. [System requirements](https://derivative.ca/UserGuide/System_Requirements).
- A three-button mouse. TouchDesigner uses the middle button.
- A free [Derivative account](https://derivative.ca/download) so you can create a license key.
- Audio files. The track menu lists `.wav` and `.flac`. This TouchDesigner build's Audio File In documents wav, mp3, and aif. If a flac file errors, use a wav.
- Optional, for a Discord voice channel: [VB-Audio Virtual Cable](https://vb-audio.com/Cable/).

You do not install Python yourself. The scripts run in TouchDesigner's textport. System Python has no TouchDesigner operators and will refuse to build the rack.

## Install TouchDesigner

These steps follow Derivative's [install guide](https://derivative.ca/UserGuide/Install_TouchDesigner). Use **2023.12480** if you want the build this project was made on. Newer Official builds may open the scripts, and they were not the build used here.

1. Create an account and download the installer from [derivative.ca/download](https://derivative.ca/download).
2. For this build, open [Official Downloads](https://derivative.ca/download/archive) and get **2023.12480**.
3. Run `TouchDesigner.2023.12480.exe` from an Administrator account. The Web installer is enough. Leave the destination at `C:\Program Files\Derivative\TouchDesigner` unless you have a reason to move it.
4. If Windows already has another TouchDesigner build, choose **Install Parallel Build** so this one stays beside it. A custom tag such as `2023.12480` makes the shortcut easy to find.
5. Start TouchDesigner. The Key Manager opens on the first launch.
6. Create a key for the license you are allowed to use. [Licensing](https://derivative.ca/UserGuide/Licensing):
   - **Non-Commercial** is free for personal and learning use when you are not paid for the work. Output resolution is limited to 1280×1280, which covers this picture. Each account starts with 10 keys, and a Non-Commercial key is tied to one computer.
   - **Educational**, **Commercial**, or **Pro** is required when you are paid for work in TouchDesigner, or when you need the higher resolution and the operators those licenses unlock.
7. On Windows N or Windows KN, install the [Media Feature Pack](https://support.microsoft.com/en-us/windows/media-feature-pack-for-windows-n-8622b390-4ce6-43c9-9b42-549e5328e407). Those editions ship without the media libraries TouchDesigner needs.

If the installer quits with no useful message, run it from an Administrator command prompt with a log, as the install guide describes, and send that log to Derivative. A **Key Retrieval Error** on startup is covered in the same guide.

## Install VB-Audio Virtual Cable

Skip this section if you only play files from a folder.

1. Download the cable from [vb-audio.com/Cable](https://vb-audio.com/Cable/) and run the installer.
2. Reboot if **CABLE Input** and **CABLE Output** do not show up in Windows sound settings.
3. Leave the Windows output device on your headset or speakers. Leave the microphone on your real mic.

The names matter:

| Device | Role |
| --- | --- |
| CABLE Input (VB-Audio Virtual Cable) | Playback end. Discord sends the voice channel here. |
| CABLE Output (VB-Audio Virtual Cable) | Recording end. TouchDesigner listens here. |

## Get the project

Copy this folder, or clone it once a remote exists. There is no remote configured yet.

The scripts were written for this path:

`C:\Users\James\Desktop\TOUCH`

If your folder is somewhere else, change that path in these files before you run them:

- `build_music_rack.py` (the textport example in the header, and the save reminder at the end of `build`)
- `upgrade_visual.py` (both `open(...)` paths)
- `listen_cable.py` (the textport example and the `open(...)` path)

Set your music library in `build_music_rack.py`:

```python
MUSIC_DIR = r'C:\Users\James\Desktop\MUSIC_SUNO'
```

Point that at a folder of wav or flac files. Subfolders are ignored. Spreadsheets, images, and peak-cache folders in the same directory are ignored. After the rack exists you can also change **Music Folder** on the Music page and pulse **Reload Tracks**.

## Build the rack

1. Open TouchDesigner 2023.12480.
2. Open `NewProject.toe` in this folder, or use File, New.
3. Open the textport with **Alt+T**.
4. Paste this line. Change the path if you moved the folder.

```python
exec(open(r'C:\Users\James\Desktop\TOUCH\build_music_rack.py', encoding='utf-8').read())
```

That creates `/project1/music_rack`: the player, the track menu, the analysis, and the picture. **Play stays off.** Running it again destroys the previous `/project1/music_rack` and builds a new one.

5. Click the purple `music_rack` component so its parameters show. The path bar should read `/project1`, with `music_rack` selected. If the path bar says `/project1/music_rack`, you are inside the component. Press **u**, or click `project1` in the path bar, then select `music_rack`.
6. Open the **Music** page on the right.
7. Pick a **Track**, set **Volume** (the default is 0.25), then turn **Play** on.
8. Click the blue `preview` operator inside the component and press **v**. Fit the viewer if the picture is cropped. The timeline transport at the bottom of TouchDesigner does not start the song. The Music page **Play** switch does.

Save with **Ctrl+S** into this folder when the picture looks right. Next time, open that `.toe` and skip the textport line.

### Refresh only the picture

If `music_rack` is already there and you only want the current terrain again:

```python
exec(open(r'C:\Users\James\Desktop\TOUCH\upgrade_visual.py', encoding='utf-8').read())
```

That leaves the player, the track, and Play as they are. If the viewer does not open, click `preview` and press **v**.

## Music page

| Control | What it does |
| --- | --- |
| Track | File from the music folder. The menu stores row numbers. The path lives in the `track_menu` table. |
| Play | Starts and stops playback. Off after a fresh build. |
| Source | **File** plays the track. **Voice channel** listens to CABLE Output. |
| Volume | File playback level. Default 0.25. |
| Low / Mid / High / RMS Gain | How hard each band drives the analysis. |
| Kick Threshold | How easily the low band counts as a kick. |
| Motion | How fast the terrain scrolls with the music. |
| Kick Punch | How hard the front line flares on a kick. |
| Onset Threshold | Lower values catch more kicks. |
| Reload Tracks | Reads Music Folder again. |
| Music Folder | Folder scanned for `.wav` and `.flac`. |

`audio_out` channels, all 0 to 1 after their gains and limits:

| Channel | Source |
| --- | --- |
| `low` | Lowpass around 140 Hz |
| `mid` | Band from about 180 Hz to 2200 Hz |
| `high` | Highpass around 4000 Hz |
| `rms` | Loudness of the mono mix |
| `kick` | Trigger on the low band |

Drive another picture from:

```python
op('/project1/music_rack/audio_out')
```

The spectrum curve is the `spectrum` CHOP. The terrain reads band levels through `vis_features` and the shaped spectrum through `spec_shape`.

## Play a Discord voice channel

Use this when the song is already playing in a Discord voice channel. File playback and the voice channel are separate. Switch back when you want games, Spotify, YouTube, and ordinary listening on the headset with TouchDesigner silent.

`HOW_TO_RUN.txt` is the same procedure written for the machine this project was built on, with that headset named in the steps. The device names below are the ones that matter on any PC.

### Everyday listening

1. Windows Settings, System, Sound. Output device is your headset or speakers.
2. Discord, User Settings, Voice & Video. Output device is the same headset or speakers. Input device stays your real microphone.
3. Press **Win+R**, run `mmsys.cpl`, open **Recording**, and double-click **CABLE Output**. On the **Listen** tab, clear **Listen to this device**. Apply. This is the small Sound window with Playback and Recording tabs.
4. In TouchDesigner, on `music_rack`, set **Source** to **File**.

### Voice channel into the visualiser and the headset

1. Leave the Windows output device on your headset or speakers. Do not set the system output to CABLE Input. That would send the whole PC into the cable.
2. Discord, User Settings, Voice & Video. Set Output Device to **CABLE Input (VB-Audio Virtual Cable)**. Leave the input device as your real microphone. Never set the mic to CABLE Output or CABLE Input.
3. Press **Win+R**, run `mmsys.cpl`, Recording, **CABLE Output**, **Listen**. Tick **Listen to this device**. Set playback through your headset or speakers. Apply.
4. In the textport, the first time:

```python
exec(open(r'C:\Users\James\Desktop\TOUCH\listen_cable.py', encoding='utf-8').read())
```

That adds `cable_in`, points it at CABLE Output, switches **Source** to **Voice channel**, and opens `preview` in its own window. After that, the Music page menu is enough.

5. Screen-share the preview window with its audio off, so the call is not sent twice.

TouchDesigner does not play the cable back out of its speakers in Voice channel mode. Doing that would loop the voice channel into CABLE Input. You hear the call because Windows Listen sends CABLE Output to the headset.

If the picture moves and the headset stays silent, check the Listen tab, then re-pair the headset in its own app and confirm Windows is still outputting to it.

### Switch back

From a call to a normal PC: Discord output back to the headset, Listen off on CABLE Output, and **Source** set to **File**.

From a normal PC to a call: Discord output to CABLE Input, Listen on through the headset, and **Source** set to **Voice channel**.

Save the project after the first cable setup so `cable_in` is still there next time.

## Files

| File | Role |
| --- | --- |
| `build_music_rack.py` | Current builder. Neon spectrum terrain. |
| `upgrade_visual.py` | Replaces the picture on an existing rack. |
| `listen_cable.py` | Points an existing rack at VB-Cable and opens the preview window. |
| `HOW_TO_RUN.txt` | The same run steps, with this PC's headset named. |
| `NewProject.toe`, `NewProject.2.toe` | Project shells. Save into one of them after a build. |
| `Backup/` | An older project shell. |
| `_preview/` | Still frames of the terrain, plus an unused light-cycle experiment. |
| `build_music_rack.v3_terrain.py` | Earlier copy of the terrain builder. |
| `build_music_rack.v2_cloud.py` | Older colour-cloud picture. |
| `build_music_rack.before_visual_rework.py` | Original picture. |
| `build_music_rack.v4_cycle.py` | Light-cycle experiment. Unused. |

Run `build_music_rack.py` for a new rack. The other `build_music_rack.*` files are earlier pictures kept beside it.

`_preview/tools/` can draw the unused cycle experiment outside TouchDesigner. That path needs system Python with NumPy and Pillow. It is not part of running the visualiser.

## Troubleshooting

- **Textport says to run this inside TouchDesigner.** The line was pasted into system Python. Use Alt+T inside TouchDesigner.
- **`/project1` is missing.** Open a project, or File, New, then run the line again.
- **Track menu says `name1`, or the player looks for a file called `name1`.** The Track menu must not use `menuSource`. The script stores paths in `track_menu` and uses row numbers as the menu values. Run the build line again.
- **No audio files.** Music Folder is wrong, or the folder has no wav or flac. Fix the folder and pulse Reload Tracks.
- **A flac errors.** Pick a wav of the same track.
- **The viewer is black, cropped, or still the old picture.** Click `preview` and press **v**. Then run `upgrade_visual.py`.
- **CABLE Output is not in the device menu.** Install VB-Cable, reboot, and run `listen_cable.py` again. The script stays on File until that device is visible.
- **Parameter Execute type not found.** The script looks up `parameterexecuteDAT`, `parexecDAT`, and `parexecuteDAT` because the operator type name is injected by TouchDesigner. Use 2023.12480, which is the build this lookup was written against.

## License

MIT. See [LICENSE](LICENSE). Copyright (c) 2026 Hellcatxrp.

Source: [https://github.com/hellcatxrp/neon_terrain](https://github.com/hellcatxrp/neon_terrain)

Audio in the music folder stays outside this repository. The older experiment scripts and `_preview/` stills are part of the tree.
