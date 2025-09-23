# Claude Code Interruption Feature

## Overview
The Claude Code Interruption feature allows users to interrupt Claude during code generation or debugging to provide additional guidance without losing context. This is particularly useful when you notice Claude heading in the wrong direction or when you want to provide hints without starting over.

## How It Works

### Key Components

1. **InterruptibleTransport**: A custom transport wrapper that monitors for keyboard interrupts while maintaining the conversation stream
2. **ClaudeInterruptionHandler**: Manages keyboard monitoring and user input collection
3. **InterruptionState**: Tracks conversation history and manages interruption flow

### Architecture

```
User → Keyboard Input (Ctrl+I) → InterruptionHandler
                                         ↓
ClaudeCodeService → InterruptibleTransport → Claude Code SDK
                           ↑
                    User Guidance Input
```

## Enabling the Feature

### Method 1: Environment Variable
Set the environment variable before running Klaus Kode:
```bash
export KLAUS_ENABLE_INTERRUPTION=true
```

Or add to your `.env` file:
```env
KLAUS_ENABLE_INTERRUPTION=true
```

### Method 2: Runtime Configuration
The feature can also be enabled programmatically by setting the flag in the ClaudeCodeService.

## Usage

### During Code Generation
1. Start a Klaus Kode workflow as normal
2. When Claude Code starts working, you'll see:
   ```
   📝 Claude Code is working on your application...
   💡 Press Ctrl+I to interrupt and add guidance
   ========================================================
   ```
3. Press `Ctrl+I` at any time during execution
4. You'll be prompted to add guidance:
   ```
   🔄 CLAUDE INTERRUPTION HANDLER
   ========================================================
   💡 Add guidance for Claude to help with the current task.
   (Press Enter with no text to let Claude continue)

   Your guidance: _
   ```
5. Type your guidance and press Enter
6. Claude will incorporate your guidance and continue

### During Debugging
The interruption feature also works during debug cycles:
1. When Claude is debugging errors, press `Ctrl+I`
2. Provide hints about the error or suggest a different approach
3. Claude continues with your guidance in mind

## Example Scenarios

### Scenario 1: Correcting Direction
Claude starts implementing a REST API when you wanted GraphQL:
```
Ctrl+I → "Please use GraphQL instead of REST for the API"
```

### Scenario 2: Adding Requirements
Claude is missing an important requirement:
```
Ctrl+I → "Make sure to add authentication using JWT tokens"
```

### Scenario 3: Providing Hints
Claude is struggling with a specific error:
```
Ctrl+I → "The error is related to the database connection string format"
```

## Technical Details

### Context Preservation
- All previous messages and tool uses are maintained
- Claude's partial responses are preserved
- The conversation continues seamlessly after interruption

### Keyboard Monitoring
- Uses the `keyboard` library for cross-platform support
- Runs in a background thread to avoid blocking
- Automatically cleaned up when the session ends

### Message Flow
1. User interrupts with Ctrl+I
2. Current Claude operation completes its current step
3. User is prompted for guidance
4. Guidance is injected as a UserMessage
5. Claude processes the guidance and continues

## Testing

Run the test script to verify the feature works:
```bash
python test_interruption.py
```

## Limitations

1. **Timing**: The interruption takes effect after Claude completes its current operation (e.g., after a tool use)
2. **Platform Support**: Requires appropriate permissions for keyboard monitoring on some systems
3. **Single Interruption**: Only one interruption can be queued at a time

## Troubleshooting

### Keyboard Monitoring Not Working
- On Linux: May need to run with `sudo` or add user to `input` group
- On macOS: Grant terminal accessibility permissions
- On Windows: Run terminal as administrator if needed

### Feature Not Activating
1. Check environment variable: `echo $KLAUS_ENABLE_INTERRUPTION`
2. Verify keyboard library is installed: `pip install keyboard`
3. Check logs for any error messages

### Interruption Not Responding
- Ensure you're pressing the correct key combination (Ctrl+I by default)
- Wait for the current Claude operation to complete
- Check that monitoring is active (you should see the monitoring message)

## Security Considerations

- Keyboard monitoring only captures the specific hotkey (Ctrl+I)
- No other keystrokes are recorded or logged
- Monitoring stops automatically when the session ends
- All user guidance is treated as part of the conversation context

## Future Enhancements

Potential improvements for the feature:
1. Multiple interruption points with different priorities
2. Customizable hotkeys via configuration
3. Visual indicator showing when interruption is possible
4. Queue multiple guidance messages
5. Save and replay interruption sequences for testing