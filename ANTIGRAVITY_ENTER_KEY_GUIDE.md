# Antigravity Prompt Submission & Newline Key Configuration Guide

This guide documents how to prevent accidental prompt submissions when pressing <kbd>Enter</kbd> across both Antigravity surfaces:
1. **Antigravity IDE (VS Code / Code-based)**
2. **Antigravity 2.0 (Standalone Desktop App, Electron-based, e.g. v2.17.0)**

---

## 1. Antigravity IDE (VS Code / VCS-Based)

In the IDE version, keyboard shortcuts and editor behavior are fully customizable through the standard VS Code settings and keybinding subsystem.

### Option A: Via Settings UI (Recommended)
1. Open Settings by pressing <kbd>Ctrl</kbd> + <kbd>,</kbd> (or go to **File** > **Preferences** > **Settings**).
2. In the top search bar, type:
   ```text
   chat.submitOnEnter
   ```
3. **Uncheck** `Chat: Submit On Enter` (or set it to `false`).
4. **Behavior after change**:
   - <kbd>Enter</kbd> inserts a newline.
   - <kbd>Ctrl</kbd> + <kbd>Enter</kbd> (or <kbd>Cmd</kbd> + <kbd>Enter</kbd>) submits the prompt.

---

### Option B: Custom Keybindings (`keybindings.json`)
If you specifically want <kbd>Shift</kbd> + <kbd>Enter</kbd> (or <kbd>Ctrl</kbd> + <kbd>Enter</kbd>) to submit and <kbd>Enter</kbd> to add newlines:

1. Press <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> to open the Command Palette.
2. Select **`Preferences: Open Keyboard Shortcuts (JSON)`**.  
   *(File path on Windows: `%APPDATA%\Antigravity\User\keybindings.json` or `%APPDATA%\Code\User\keybindings.json`)*
3. Add the following entries inside the JSON array (`[ ... ]`):

```json
[
  {
    "key": "enter",
    "command": "-workbench.action.chat.submit",
    "when": "inChatInput && !suggestWidgetVisible"
  },
  {
    "key": "shift+enter",
    "command": "workbench.action.chat.submit",
    "when": "inChatInput"
  },
  {
    "key": "ctrl+enter",
    "command": "workbench.action.chat.submit",
    "when": "inChatInput"
  }
]
```

- The leading `-` in `-workbench.action.chat.submit` disables the default submission on plain <kbd>Enter</kbd>.
- The remaining two blocks explicitly bind submission to <kbd>Shift</kbd> + <kbd>Enter</kbd> and <kbd>Ctrl</kbd> + <kbd>Enter</kbd>.

---

## 2. Antigravity 2.0 (Standalone Desktop Application)

### Current Architecture & Limitation (v2.17.0+)
- **No in-app toggle**: The standalone desktop app is built on Electron with a custom React chat canvas. Its Settings menu (the gear icon on the left sidebar) handles model configuration, execution policies, sandboxing, and permissions, but does **not** expose a keybinding editor or a `submitOnEnter` toggle.
- **Hardcoded behavior**:
  - <kbd>Enter</kbd> &rarr; **Submits prompt immediately**
  - <kbd>Shift</kbd> + <kbd>Enter</kbd> &rarr; **Inserts a newline**

---

### Workaround 1: AutoHotkey v2 (Seamless Window-Scoped Remap)

This is the cleanest and most reliable solution. It intercepts keystrokes **only** when the Antigravity desktop window is active. All other applications (browser, IDE, terminal) remain completely unaffected.

#### Steps:
1. Install [AutoHotkey v2](https://www.autohotkey.com/).
2. Create a file named `AntigravityKeyFix.ahk` (e.g. in your Documents folder or startup folder).
3. Paste the following script:

```autohotkey
#Requires AutoHotkey v2.0

; Apply remaps ONLY when Antigravity Desktop is the focused window
#HotIf WinActive("ahk_exe Antigravity.exe")

; Pressing Enter sends Shift+Enter (inserts a newline instead of submitting)
Enter::+Enter

; Pressing Ctrl+Enter sends Enter (submits the prompt)
^Enter::Enter

#HotIf
```

4. Double-click `AntigravityKeyFix.ahk` to run it.
5. *(Optional)* To launch it automatically on Windows login:
   - Press <kbd>Win</kbd> + <kbd>R</kbd>, type `shell:startup`, and press Enter.
   - Place a shortcut to `AntigravityKeyFix.ahk` in that folder.

#### Result:
- Tapping <kbd>Enter</kbd> inside Antigravity adds a newline.
- Pressing <kbd>Ctrl</kbd> + <kbd>Enter</kbd> sends the message.

---

### Workaround 2: Windows PowerToys Keyboard Manager

If you already use Microsoft PowerToys:
1. Open **PowerToys Settings** > **Keyboard Manager**.
2. Under **Shortcuts**, click **Remap a shortcut**.
3. Target App: `Antigravity.exe`
4. Map:
   - `Enter` &rarr; `Shift + Enter`
   - `Ctrl + Enter` &rarr; `Enter`

---

### Workaround 3: External Multi-Line Draft & Paste
When drafting detailed prompts without external tools:
1. Write the text in any scratch editor (Notepad, Notepad++, IDE tab).
2. Copy and paste into Antigravity with <kbd>Ctrl</kbd> + <kbd>V</kbd>.
3. Pasted multi-line text will keep all newlines intact and will **not** trigger premature submission.
