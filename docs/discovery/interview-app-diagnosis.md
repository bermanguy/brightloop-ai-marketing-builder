# Interview app diagnosis — 2026-10-25

All 8 messages sent so far (Maya 4, Daniel 2, Noa 2) returned the identical text:

> "I don't know that detail, and I don't want to make it up. Ask me about a specific piece of work I actually did."

We checked the app with normal browser troubleshooting before spending more messages. **No messages were sent during the check.** Nothing was done beyond signing in as ourselves and loading the page.

## What we checked (09:30, signed in as the candidate)

| Check | Result |
| --- | --- |
| Page and app code load | 200 OK |
| Signed-in user record (`User/me`) | 200 OK; full name saved ("Guy Berman"), email verified |
| Candidate profile lookup | 200 OK, but returned an empty list |
| Chat connection token | 200 OK |
| Browser console after sign-in | No errors (the only error is a 401 from before sign-in, which is expected) |
| Chat history | Loads and renders all 8 exchanges; counters show 4/20, 2/20, 2/20 |
| UI | No error banner; no profile or settings screen is available |

## What it means

- The app is not visibly failing on the client: every request succeeds and there are no errors.
- Messages and replies travel over a live connection that isn't visible as normal requests, so the cause of the fallback can't be seen from the browser.
- The exact same reply to eight very different questions, from three personas, looks like a fixed fallback rather than a persona's normal reply. From the client we cannot tell whether it fires on a server-side failure or by design.
- The empty candidate profile lookup is the one unusual result. The account itself has a full name, so the "type your full name" step appears done. Whether the empty lookup matters is unknown.

## SPOTTED

Read down, the first letters of the seven rules spell SPOTTED. Next to "This brief contains a few deliberate traps… Noticing them… is part of the job", it reads as a clue to spot the traps, not a phrase that unlocks the marketers. Maya gave the same canned reply to a question about it.
