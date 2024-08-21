#!/bin/bash

# Define the list of text numbers and their digit equivalents
declare -A numbers=(
    ["Twenty-One"]="21"
    ["Twenty-Two"]="22"
    ["Twenty-Three"]="23"
    ["Twenty-Four"]="24"
    ["Twenty-Five"]="25"
    ["Twenty-Six"]="26"
    ["Twenty-Seven"]="27"
    ["Twenty-Eight"]="28"
    ["Twenty-Nine"]="29"
    ["Thirty-One"]="31"
    ["Thirty-Two"]="32"
    ["Thirty-Three"]="33"
    ["Thirty-Four"]="34"
    ["Thirty-Five"]="35"
    ["Thirty-Six"]="36"
    ["Thirty-Seven"]="37"
    ["Thirty-Eight"]="38"
    ["Thirty-Nine"]="39"
    ["Forty-One"]="41"
    ["Forty-Two"]="42"
    ["Forty-Three"]="43"
    ["Forty-Four"]="44"
    ["Forty-Five"]="45"
    ["Forty-Six"]="46"
    ["Forty-Seven"]="47"
    ["Forty-Eight"]="48"
    ["Forty-Nine"]="49"
    ["One"]="1"
    ["Two"]="2"
    ["Three"]="3"
    ["Four"]="4"
    ["Five"]="5"
    ["Six"]="6"
    ["Seven"]="7"
    ["Eight"]="8"
    ["Nine"]="9"
    ["Ten"]="10"
    ["Eleven"]="11"
    ["Twelve"]="12"
    ["Thirteen"]="13"
    ["Fourteen"]="14"
    ["Fifteen"]="15"
    ["Sixteen"]="16"
    ["Seventeen"]="17"
    ["Eighteen"]="18"
    ["Nineteen"]="19"
    ["Twenty"]="20"
    ["Thirty"]="30"
    ["Forty"]="40"
    ["Fifty"]="50"
)

# Path to the Markdown file
file_path="$1"

# Check if the file exists
if [[ ! -f "$file_path" ]]; then
    echo "File not found!"
    exit 1
fi

# Iterate over the text numbers and replace them with digits
# Process compound numbers first by sorting keys by length (longest first)
for key in $(echo "${!numbers[@]}" | tr ' ' '\n' | awk '{ print length, $0 }' | sort -rn | cut -d" " -f2-); do
    sed -i "s/\b$key\b/${numbers[$key]}/g" "$file_path"
done

echo "Text numbers have been replaced with digits in $file_path"

