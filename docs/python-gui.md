# A GUI application in Python 3, tried in the emulator

You can write a native Hildon application for the N900 in **Python 3.11**. There are no PyGTK (Python 2 only) and no PyGObject (GTK 2 and Hildon have no GObject Introspection data) for it,
so the application calls the C libraries through `ctypes`. The small layer [hildonlite](https://github.com/n900-resurrection/hildonlite) does that for you: windows, buttons, entries, lists,
dialogs, the application menu, kinetic scrolling, timers. One file, pure Python, no dependencies.

## What you need
- **For the emulator:** `make arm-python` (Python 3.11 and hildonlite from the apt repository of the project into `sysroot/opt/python3`), and `make hildon-overlay` (see [getting-started.md](getting-started.md)).
- **On the phone:** `apt-get install python3-hildonlite` (the package pulls in `python3.11`; the repository is described at <https://n900-resurrection.github.io/>), run as the user `user` inside the
  Hildon session (`DISPLAY=:0`).

## The shortest program
```python
import hildonlite as hl

hl.init()
win = hl.Window("Hello")
box = hl.VBox(spacing=8)
box.add(hl.Label("Python 3 + Hildon"), expand=True)
box.add(hl.Button("Quit", "closes the window", on_clicked=lambda b: hl.quit()))
win.add(box)
win.show()
hl.main()
```
```sh
make hildon-run SCRIPT=hello.py SHOT=build/hello.png
```

## What hildonlite offers
| | |
|---|---|
| `Window`, `set_menu(AppMenu)` | a Hildon stackable window with its own title, Back button and application menu; several windows stack |
| `Box`, `VBox`, `HBox` | `add(widget, expand=, fill=, padding=)` |
| `Label`, `Button`, `ImageButton` | `Button` is a `HildonButton` with a title and a second line (`size=hl.THUMB` is finger-sized, the default) |
| `Entry`, `TextView` | `get_text`/`set_text`; `Entry.set_completion(words)`; `Widget.on_key(fn)` sees the key presses |
| `PannableArea` | kinetic scrolling (`add` for widgets that scroll by themselves, `add_viewport` for the others) |
| `ListStore`, `ListView` | a text list (`HildonTreeView`): `append`, `rows`, `clear`, `selected`, `activate`; `row-activated` is a tap |
| `AppMenu`, `Banner`, `Dialog`, `confirm`, `info` | the menu of the title bar, the grey information banner, dialogs and Hildon notes |
| `timeout`, `idle`, `main`, `quit` | the main loop and timers; `flush()` handles pending events before a long blocking job |

Signals: `widget.connect("clicked", fn)`; `fn` gets the widget. An exception in a handler is printed and does not stop the main loop. What the layer does not cover can be called through
`hildonlite._fn("gtk" | "hil" | "gobj" | "glib", "c_function_name", restype, *argtypes)`. Full list and the install options: the README of hildonlite.

## A worked example: Quick notes (`apps/quick-notes`)
A text field and an **Add** button on top, the notes below, a menu that deletes. Three files:

- `notes.py` is the **data side**: load and save a JSON file, add and remove a note, a short date. No GUI, so it is tested on the PC with plain `unittest`.
- `quick-notes` is the **GUI**: it builds the window from hildonlite widgets, calls `notes.py`, saves after every change.
- `hildon-run.sh` tells the emulator how to start it (and puts demo notes into `/tmp`, never your real ones).

Keep this split in your own programs: the logic in a module that does not import the GUI, the GUI thin. The tests of the data side take milliseconds on the PC, and the GUI is checked by looking at it in the emulator.

### The GUI in a few lines
```python
win = hl.Window("Quick notes")
root = hl.VBox(spacing=6)
top = hl.HBox(spacing=6)                      # the controls are on top, where the thumb reaches them
entry = top.add(hl.Entry(""), expand=True)
top.add(hl.Button("Add", on_clicked=lambda b: add()))
root.add(top)
store = hl.ListStore(2)                       # two text columns: the note and its date
view = hl.ListView(store)
area = hl.PannableArea()
area.add(view)                                # ListView scrolls by itself: add, not add_viewport
root.add(area, expand=True)

menu = hl.AppMenu()
menu.add("Delete the selected note", lambda b: delete_selected())
menu.add("Quit", lambda b: hl.quit())
win.set_menu(menu)
win.add(root)
win.show()
hl.main()
```

### Try it
```sh
python3 -m unittest discover -s apps/quick-notes/tests           # the logic, on the PC, in a few milliseconds
make hildon-run APP=quick-notes SHOT=build/qn.png                # the application in the emulated desktop
make emu-shots APP=quick-notes                                   # a scripted session: type a note, tap Add, open the menu; build/shots/quick-notes/
```
The scenario `apps/quick-notes/shots.txt` is a list of steps (`SECONDS ACTION [ARGS]`: `click 300 90`, `type Buy milk`, `key F4`, `shot name`). F4 opens the application menu, Escape is Back.
To look at it and tap it yourself: `make emulator VNC=1` and connect with a VNC viewer; the launcher shows *Quick notes*.

### On the phone
The program needs only `python3-hildonlite` on the phone. Copy the folder and start it as `user`:
```sh
scp -r apps/quick-notes root@<phone>:/home/user/quick-notes
ssh root@<phone> 'su user -c "DISPLAY=:0 /opt/python3/bin/python3 /home/user/quick-notes/quick-notes"'
```
For a package with a menu entry, see the `package.sh` files of the applications in [nokia-n900-apps](https://github.com/n900-resurrection/nokia-n900-apps) (`scripts/debpack.sh` writes the control file
and the `.desktop` entry).

## Habits that make an application feel native
- **Controls on top, big and few.** A thumb covers the lower part of the screen; use `size=hl.THUMB` buttons and put the main action in a row at the top.
- **The application menu** (the title) for rare actions; use a `Banner` for short feedback ("Note added") and `confirm()` before anything that deletes.
- **Do not block the main loop.** A long job in a handler freezes the window (and Hildon may offer to kill the application); run it as a subprocess and poll with `hl.timeout()`, or call `hl.flush()` between steps.
- **Save after every change**, and write files atomically (`os.replace`); a phone loses power suddenly.
- `/tmp` of the phone is a 1 MB tmpfs: keep data in the home directory. Log errors to a file in the home directory, because an application started from the menu has no terminal.
- **Finger scrolling:** a `Label` in a `PannableArea.add_viewport` scrolls by finger without selecting text; a `TextView` selects text when you drag. A wrapped label inside a viewport needs a fixed width
  (`label.set_size_request(770, -1)`).

## Known behaviour
- With the Hildon theme the selection of a `HildonTreeView` stays empty (a tap only activates a row), so `ListView.selected()` returns the row of the last tap (or the one set by `select()`).
- `hildonlite` has no orientation switching yet; the window is 800x480 landscape.
- The emulator has no Maemo on-screen keyboard; the PC keyboard types into the focused entry.
