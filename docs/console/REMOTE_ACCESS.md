# Console on your phone, from anywhere (Tailscale) — one-time setup

The laptop is the hub. It runs the console and the Studio watcher all the time. Your phone reaches it through **Tailscale**, a private encrypted network made of your own devices.

- Nothing is exposed to the internet.
- Nothing is exposed on the Wi‑Fi you're on.
- Only your Tailscale login can open the console.

```
phone (Tailscale app) ──private tunnel──► laptop: tailscale serve (HTTPS) ──► 127.0.0.1:8878 /console
Drive "hack.CCM Inbox" ──Drive for desktop──► laptop folder ──► studio.py watch ──► drafts in /console/studio
```

## 1. Tailscale (about 10 minutes)
1. Install Tailscale on the **laptop** (Windows) and the **phone** (App Store / Play Store). Sign in with the **same account** on both.
2. On the laptop, open the Tailscale tray menu → **Preferences** → enable **Run unattended**. It then stays connected after a restart, even before you log in.
3. In a laptop terminal, run:
   ```
   tailscale serve --bg 8878
   ```
   - If it prints a link asking you to enable HTTPS certificates for your tailnet, open the link, enable it, and run the command again.
   - `--bg` keeps the setting across reboots.
   - `tailscale serve status` shows the address, e.g. `https://my-laptop.tail1234.ts.net`.
4. On the phone, open `https://<that address>/console/studio` and add it to the home screen.
   - The Tailscale app must be switched on.
   - You can leave it on all the time; it only routes traffic for your own devices.

**To stop sharing:** `tailscale serve reset`.

## 2. Tell the console who you are
In `.env` (in the repo folder on the laptop):
```
CONSOLE_OWNER=the-email-you-use-for-tailscale@example.com
```
How the console decides who gets in:
- **The laptop itself:** works with no login, as before.
- **Your phone, through Tailscale:** allowed. Tailscale tells the console who you are, and approvals are recorded under your Tailscale name.
- **Any other Tailscale user:** refused.
- **Another device on the same Wi‑Fi:** refused. The console now listens on `127.0.0.1` only.
- If `CONSOLE_OWNER` is not set, all remote access is refused, and the console prints a warning when it starts.

## 3. The inbox: Google Drive for desktop
1. Install **Google Drive for desktop** on the laptop.
2. In Drive, create `hack.CCM Inbox` with the subfolders `CCM`, `Medicine` and `Microbiology`. Inside any of them, add a `Questions` subfolder for question lists.
3. Right-click `hack.CCM Inbox` in Explorer → **Offline access → Available offline**.
4. In `.env`, set (use your own drive letter):
   ```
   STUDIO_INPUT_DIR=G:/My Drive/hack.CCM Inbox
   ```

**What happens to your files:**
- **A note** you save from claude.ai (`.md` or `.docx`) into `CCM/` becomes one Studio item: your theory note, plus derived Q&A, flashcards and MCQs.
- **A question list** in `CCM/Questions/` (or any `.csv`) is split into one item per question.
- **After pickup**, the file is moved to `hack.CCM Inbox/Processed/…`. You'll see that on your phone's Drive app too.
- **Editing a note** and saving it again with the same name creates a new version of the same item.

## 4. Keep the laptop awake and running
- **Settings → System → Power → Screen and sleep:** "When plugged in, put my device to sleep after" → **Never**.
- **Lid:** Control Panel → Power Options → "Choose what closing the lid does" → **Do nothing** (when plugged in).
- **Autostart** the console and the watcher with `scripts\start_hackccm.ps1`. Setup steps are in the script's header (Task Scheduler, "At log on").
  - It restarts either process if it stops.
  - Logs go to `logs\`.

## 5. Daily use
1. Make a note with Claude and save it to `hack.CCM Inbox/CCM/` from your phone or laptop.
2. Within about 5 minutes (`STUDIO_WATCH_INTERVAL`), the watcher picks it up, generates the material and checks it.
3. On your phone, open the Studio, open the item, review it tab by tab, then **Approve selected** → **Publish**.
4. To deploy, tap **Push changes** at the top of the console. It pushes from the laptop using its git login, and Vercel redeploys.

**Costs:** each note uses about 4–6 OpenRouter calls. The daily and per-run caps (`STUDIO_MAX_CALLS_PER_DAY`, `STUDIO_MAX_CALLS_PER_RUN`) are shown in the Studio header. Set a credit limit on the OpenRouter key as a hard ceiling.

## Troubleshooting
| Symptom | Check |
|---|---|
| Phone can't load the page | Tailscale switched on on the phone? `tailscale serve status` on the laptop? Laptop awake? |
| "403 — Set CONSOLE_OWNER" | Add `CONSOLE_OWNER` to `.env`, then restart the console |
| "403 — x@y is not allowed" | `CONSOLE_OWNER` must be exactly your Tailscale login |
| Note not picked up | Is the file inside a subject folder (`CCM/`, …)? Files are left for 60 s while Drive finishes syncing. See `logs\studio-watch.log` |
| "CAPPED" in the log | The daily call cap was reached. Items stay queued until tomorrow, or raise the cap |
