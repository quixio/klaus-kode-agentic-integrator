# Interruption Key Configuration

## Default Key: F2

The interruption feature uses **F2** by default because:
- It doesn't conflict with terminal shortcuts
- It's easy to reach
- It works across all platforms

## Why Not Ctrl+I?

**Ctrl+I** equals Tab in terminal environments, causing issues:
- In most terminals, Ctrl+I literally sends a Tab character
- This causes indentation in the output instead of triggering interruption
- It's a fundamental terminal limitation, not a bug

## Configuring a Different Key

You can set a custom key via environment variable:

```bash
export KLAUS_INTERRUPT_KEY=f3       # Use F3 instead
export KLAUS_INTERRUPT_KEY=f4       # Use F4 instead
export KLAUS_INTERRUPT_KEY=ctrl+g   # Use Ctrl+G (less common conflict)
export KLAUS_INTERRUPT_KEY=ctrl+b   # Use Ctrl+B (less common conflict)
```

Add to your `.env` file:
```env
KLAUS_INTERRUPT_KEY=f3
```

## Recommended Keys

### Best Options (No Conflicts)
- **F2** (default) - No terminal conflicts
- **F3** - Also safe
- **F4** - Safe but may close some terminals
- **F5-F12** - Generally safe

### Possible Options (Check Your Terminal)
- **Ctrl+G** - Usually safe (bell character, rarely used)
- **Ctrl+B** - Usually safe (if not using tmux)
- **Ctrl+Q** - Can work (if XON/XOFF flow control disabled)

### Keys to AVOID
- **Ctrl+C** - Interrupts the entire program
- **Ctrl+D** - EOF, exits many programs
- **Ctrl+Z** - Suspends process
- **Ctrl+I** - Same as Tab
- **Ctrl+M** - Same as Enter
- **Ctrl+J** - Same as Line Feed
- **Ctrl+H** - Same as Backspace
- **Ctrl+L** - Clears screen
- **Ctrl+A** - Start of line (readline)
- **Ctrl+E** - End of line (readline)
- **Ctrl+K** - Kill line (readline)
- **Ctrl+U** - Kill backward (readline)
- **Ctrl+W** - Delete word (readline)
- **Ctrl+R** - Reverse search (readline)
- **Ctrl+S** - Stop output (XON/XOFF)
- **Ctrl+V** - Paste or literal next

## Platform Notes

### Linux
- May need to run with `sudo` for global keyboard hooks
- Or add user to `input` group: `sudo usermod -a -G input $USER`

### macOS
- Needs accessibility permissions for terminal app
- System Preferences → Security & Privacy → Accessibility → Add Terminal

### Windows
- Function keys work best
- Some Ctrl combinations may conflict with Windows Terminal

## Testing Your Key Choice

Test your chosen key with this script:

```python
import keyboard
import time

key = "f2"  # Change to your preferred key
print(f"Testing key: {key}")
print("Press the key to test, Ctrl+C to exit")

def on_press():
    print(f"✓ {key} detected!")

keyboard.add_hotkey(key, on_press)

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nTest complete")
```

If the key is detected properly, it will work for interruption.