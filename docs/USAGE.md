# Usage guide

How FollowLens talks to Instagram, what that costs, and how to use it without getting your account limited.

Türkçe: [KULLANIM.md](KULLANIM.md)

## The short version

- Scan **once or twice a day**. More often tells you nothing new and only adds risk.
- Track **a handful of accounts**, not dozens.
- Leave the cooldown alone. Do not make a habit of `?force=1`.
- If Instagram shows you a warning, or a scan reports a rate limit, **stop for at least a day**.
- If you can, use the session of a **secondary account** rather than your main one.

## What a scan actually sends

FollowLens has no API key and no special access. It sends the same web requests your browser sends when you open someone's followers list, using the session cookie you gave it. Nothing else is contacted.

For each tracked account, one scan does this:

| Step | Requests |
| --- | --- |
| Look up the account id | 1 the first time, then 0 (the id is remembered in `known_ids`) |
| Read **following** | 1 request per 200 accounts, per pass |
| Read **followers** | 1 request per 100 accounts, per pass |

Each list is read in **2 to 4 passes**. Instagram's lists are unreliable: a single pass regularly leaves accounts out. FollowLens repeats the read and merges the results, and stops as soon as a pass adds nobody new, so a stable list costs two passes and an unstable one up to `followers_max_passes`.

What that adds up to, per account, per scan:

| Account size (following / followers) | Requests | Time |
| --- | --- | --- |
| about 180 / 180 | 6 – 12 | under a minute |
| 500 / 500 | 16 – 32 | 1 – 3 minutes |
| 1,000 / 2,000 | 50 – 100 | 3 – 9 minutes |
| 800 / 5,000 | not supported, see [Limits](#limits) | |

Multiply by the number of accounts you track. Three small accounts are roughly 20 – 35 requests per scan.

## How the requests are paced

| Setting | Default | What it does |
| --- | --- | --- |
| `delay_seconds` | 3.0 | Pause after every request |
| `delay_jitter_seconds` | 2.5 | Extra random pause on top, so requests are 3.0 – 5.5 s apart rather than on a fixed beat |
| `min_scan_interval_seconds` | 600 | Minimum time between two scans |
| `followers_max_passes` | 4 | Upper bound on passes per list |

If Instagram answers `429 Too Many Requests`, FollowLens waits about 15 seconds, then about 30, and then gives up on the whole scan rather than pushing on.

Two rules keep the cooldown honest:

- A scan that read **nothing** (expired session, no connection) does not start the cooldown, so you can retry as soon as you have fixed the cause.
- The **first read of a newly added account** is let through the cooldown, once. Every later scan waits.

## The risk, plainly

Reading these lists automatically is against Instagram's Terms of Service. Instagram does not publish its limits and changes them without notice, so **nobody can promise you a safe number**, including this guide. What follows is how to keep the volume low, not a guarantee.

What Instagram may do, roughly in order of severity:

1. **Refuse one account's lists** for a while. The scan reports *"The session itself works … Instagram is refusing this account for now."*
2. **Rate-limit the session**, with a 429 or a quiet *"Please wait a few minutes."*
3. **Log the session out.** Every account fails and you need a fresh cookie.
4. **Show a warning in the app** about automated behaviour, or ask you to confirm your identity.
5. **Restrict or disable the account.** This is rare at these volumes, but it is the reason for everything above.

What raises the risk:

- Scanning many times a day, or looping `?force=1`
- Tracking many accounts, or very large ones
- Lowering the delays
- Running a scan while you are also very active in the app with the same account
- Carrying on after a warning

## When something goes wrong

| You see | Do this |
| --- | --- |
| One account refused, others fine | Wait a few hours. Do **not** fetch a new cookie; the session is fine. |
| 429 or *"Please wait a few minutes"* | Stop for at least 30 minutes. If it happens again the same day, stop until tomorrow. |
| Every account fails with 401 | The session expired. Copy a fresh `sessionid` into `config.json`. |
| A warning inside Instagram | Stop scanning for 24 – 48 hours. Come back at half the frequency. |
| Asked to confirm your identity | Complete it in the app, then wait a few days before scanning again. |

The full list of messages is in the [README](../README.md#troubleshooting).

## The session cookie

The `sessionid` cookie **is** your login. Anyone who has it can use your account without your password.

- It lives only in `config.json`, which is git-ignored. Never commit it, paste it in a chat or put it in a screenshot.
- It is sent only to `instagram.com`.
- It lasts from a few days to a few weeks. When it expires, copy a new one from your browser.
- To revoke one immediately, log out of that browser session in Instagram. Changing your password revokes all of them.

Using a secondary account's session keeps your main account out of it entirely. The trade-off is that it can only read what that secondary account is allowed to see.

## What FollowLens can read

- **Public accounts**: yes.
- **Private accounts**: only if the account behind the session follows them. Otherwise FollowLens says so and saves nothing.
- **Your own account** (the `self` target): always.

Instagram answers with an *empty list*, not an error, for an account it will not show you. FollowLens checks the profile's own counts first, and never saves an empty list for an account that clearly has followers.

## Limits

- **About 4,000 followers and 8,000 following per account.** A read stops after 40 pages, so larger lists come back incomplete and the diff is not trustworthy. FollowLens is built for personal-sized accounts.
- **No timestamps.** Instagram does not say when someone followed or unfollowed. "Recent" always means "since the previous scan".
- **No background scanning.** A scan runs when you press Refresh or call `/scan`. Nothing runs on its own.

## Reading the result

Because the lists are unreliable, not every change is real. Only the plain green and plain red rows are activity:

| Row | Meaning |
| --- | --- |
| `+` green, *new follower* | Someone genuinely new |
| `+` muted, *returned* | Was reported leaving earlier and is back; not new |
| `-` red, *unfollowed* | Left, and stayed gone |
| `-` struck through, *back since* | A later scan found them again; never left |
| `~` muted, *account gone* | Vanished from both lists at once: deactivated, renamed or gone private |

If the same names keep leaving and returning, raise `followers_max_passes` by one. It costs a few more requests per scan and makes the lists more complete.
