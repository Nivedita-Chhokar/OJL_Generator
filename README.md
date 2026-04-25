# OJL Generator

Automates the process of generating daily internship logs and intelligently overlaying them onto a standardized PDF template. 

## Features
- **AI-Powered Formatting**: Uses the Google Gemini API to clean up and expand raw, shorthand internship notes into cohesive, professional sentences.
- **Round-Robin API Key Handling**: Built-in support for multiple Gemini API keys. The script seamlessly distributes the workload across your keys to avoid hitting usage limits, and instantly fails over if a rate limit is detected.
- **Visual PDF Mapping**: Includes a local, web-based configurator tool (`configure_coords.py`) that lets you visually click on your PDF to set perfectly aligned X/Y coordinates for the text overlays.
- **Batch Processing**: Automatically parses a CSV of any size and overlays the configured text perfectly onto standard PDF layouts.

## Setup Requirements

1. **Python 3.10+**
2. Install necessary Python dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
   *(If prompted on modern Ubuntu versions, you can safely use the `--break-system-packages` flag for local use, or create a virtual environment).*

## Getting Started

1. **Provide Your Data and Template:**
   - Add your raw data file and name it `input.csv`. Ensure it has logical headers (e.g., date, tasks, notes, tools_used).
   - Add your blank template PDF and name it `OJL_pdf.pdf`.
   - *(Note: These files are ignored by git intentionally to protect your data).*

2. **Add Your Gemini API Keys:**
   Create a `.env` file in the root directory and add your API keys (separated by commas):
   ```env
   GEMINI_API_KEYS=your_first_key,your_second_key,your_third_key
   ```

3. **Configure Text Placement Coordinates:**
   Map out where the generated text should sit on your specific PDF by opening the visual tool:
   ```bash
   python3 configure_coords.py
   ```
   Follow the interface prompt in your browser to click the exact locations. This saves your mappings to a local map file.

4. **Generate the Final PDF:**
   ```bash
   python3 generate.py
   ```
   Your completed, formatted logs will be created as `output.pdf`.
   

# MOJ KARO 
![ai_baby](https://media1.tenor.com/m/31KSghEQxPYAAAAd/baby-ai.gif)

#
### feel free to open issues and PRs :)
