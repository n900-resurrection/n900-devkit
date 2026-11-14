"""Quick notes: the data side. A list of short notes kept in a JSON file; no GUI here, so it is tested on the PC with plain unittest."""
import json
import os
import time

PATH = os.environ.get("QUICKNOTES_FILE") or os.path.join(os.environ.get("HOME", "/home/user"), ".quick-notes.json")


def load(path=None):
    """The notes (newest first) as a list of {"text", "ts"}; a missing or broken file is an empty list."""
    try:
        with open(path or PATH, encoding="utf-8") as f:
            data = json.load(f)
        return [n for n in data if isinstance(n, dict) and n.get("text")]
    except (OSError, ValueError):
        return []


def save(notes, path=None):
    """Write the notes atomically (a file written in pieces would be lost when the battery is pulled)."""
    path = path or PATH
    tmp = path + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def add(notes, text, now=None):
    """A new list with the note at the front; blank text adds nothing."""
    text = " ".join(text.split())
    if not text:
        return list(notes)
    return [{"text": text, "ts": int(time.time() if now is None else now)}] + list(notes)


def remove(notes, index):
    """A new list without the note number `index` (an index out of range removes nothing)."""
    if not 0 <= index < len(notes):
        return list(notes)
    return notes[:index] + notes[index + 1:]


def when(ts, now=None):
    """A short date for the list: the time today, 'day.month.' otherwise."""
    now = time.time() if now is None else now
    t, n = time.localtime(ts), time.localtime(now)
    return time.strftime("%H:%M", t) if (t.tm_year, t.tm_yday) == (n.tm_year, n.tm_yday) else "%d.%d." % (t.tm_mday, t.tm_mon)


def summary(notes):
    return "no notes" if not notes else ("1 note" if len(notes) == 1 else "%d notes" % len(notes))
