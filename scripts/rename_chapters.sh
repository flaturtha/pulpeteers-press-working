#!/bin/bash

# Directory containing the files
directory="./"  # Use "./" if the files are in the current directory

# Loop through files that match the pattern ch_*.md
for file in "$directory"ch_*.md; do
    # Extract the base name (e.g., "ch_1.md" -> "ch_1")
    base_name=$(basename "$file" .md)
    
    # Remove the underscore (e.g., "ch_1" -> "ch1")
    new_name="${base_name/_/}"

    # Rename the file
    mv "$file" "$directory$new_name.md"
done

echo "File renaming completed!"

