# One Piece chapter alerts (GitHub Actions + ntfy + email)

Every 5 minutes, a free GitHub Actions job checks the TCB Scans One Piece page.
When a chapter newer than the one it last saw appears, it sends you an iPhone
push notification (via ntfy) and an email (via Gmail). Total cost: $0.

## Files

- `check_chapter.py` - the checker (Python standard library only, nothing to install)
- `.github/workflows/check.yml` - the schedule and the run steps
- `last_chapter.txt` - created automatically on the first run; remembers the last chapter you were told about

## Setup (about 10 minutes)

### 1. Put the files in a new public GitHub repo
1. On github.com, click **New repository**, name it (for example `onepiece-alerts`), choose **Public**, and create it.
2. Click **uploading an existing file** and upload `check_chapter.py` and `README.md`.
3. The workflow file has to live in a folder. Click **Add file > Create new file**, type
   `.github/workflows/check.yml` as the name (typing the slashes creates the folders), paste in the contents of `check.yml`, and commit.

### 2. Set up iPhone push (ntfy)
1. Install the free **ntfy** app from the App Store.
2. Open it, tap **+**, and subscribe to a topic name that nobody could guess, such as
   `onepiece-yourname-7391x`. Anyone who knows the name can read or send to it, so treat it like a password.
3. Allow notifications when iOS asks. Leave "Use another server" off (the default ntfy.sh server is what the script uses).

### 3. Set up email (Gmail app password)
The script sends mail through Gmail. You need an app password, not your normal password.
1. Turn on 2-Step Verification for the Gmail account you want to send from (Google Account > Security).
2. Go to https://myaccount.google.com/apppasswords, create an app password named "onepiece", and copy the 16 characters.

If you would rather not use Gmail, say so and the script can be switched to another provider.

### 4. Add your secrets to GitHub
In your repo: **Settings > Secrets and variables > Actions > New repository secret**. Add:

| Name | Value |
| --- | --- |
| `NTFY_TOPIC` | the topic name from step 2 |
| `EMAIL_ADDRESS` | the Gmail address that sends the mail |
| `EMAIL_APP_PASSWORD` | the 16-character app password |
| `EMAIL_TO` | where alerts should go (optional; defaults to `EMAIL_ADDRESS`) |

Secrets are encrypted and are not visible in a public repo or in the logs.

### 5. Test it
1. Go to the **Actions** tab. If GitHub asks, click to enable workflows.
2. Choose **Check for new One Piece chapter > Run workflow**, tick **send_test**, and run it.
3. Within about a minute you should get a `[TEST]` push on your iPhone and an email. This test does not change the saved chapter.
4. Run it once more with send_test unticked. The first normal run saves the current latest chapter as the starting point and sends nothing. From then on you are alerted only for chapters newer than that.

## Good to know

- **Timing:** GitHub's scheduler is "about every 5 minutes", and runs are sometimes delayed by a few minutes at busy times. To check every 10 minutes instead, change `*/5` to `*/10` in `check.yml`.
- **Public repo and the 60-day rule:** GitHub disables scheduled workflows in a repo with no activity for 60 days. The script commits `last_chapter.txt` whenever a new chapter appears, and One Piece releases weekly, so this should not trigger. If you ever get an email from GitHub about disabled workflows, just click re-enable.
- **If the site changes:** if TCB Scans moves to a new domain, edit the `PAGE_URL` line near the top of `check_chapter.py`. If the page layout changes or the site blocks GitHub's servers, the run fails with a clear message and GitHub emails you about the failed run, so you will not go silent without knowing.
- **Decimal chapters** such as 1053.1 are handled; it alerts on whichever chapter number is highest.
- **Failures:** if only one channel (push or email) fails, you still get the other and the chapter is not re-sent. If both fail, it retries on the next run.
