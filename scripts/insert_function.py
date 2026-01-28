#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick script to insert the toggleRelayPause function into script.js
Creates a new file instead of modifying in place
"""

# Read the function to insert
with open('toggle_relay_function.tmp', 'r', encoding='utf-8') as f:
    function_code = f.read()

# Read the original script.js
with open('static/script.js', 'r', encoding='utf-8') as f:
    original_content = f.read()

# Find the position to insert (before "function restartApp()")
search_text = "function restartApp()"
pos = original_content.find(search_text)

if pos == -1:
    print("ERROR: Could not find 'function restartApp()' in script.js")
    exit(1)

# Insert the new function before restartApp
new_content = (
    original_content[:pos] + 
    "\n" + function_code + "\n\n" +
    original_content[pos:]
)

# Write to a NEW file
with open('static/script_fixed.js', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✓ Successfully created script_fixed.js with toggleRelayPause() function")
print(f"  Inserted at position: {pos}")
print(f"  New file size: {len(new_content)} bytes")
print("\nNext step: Rename script_fixed.js to script.js after closing VS Code/editors")
