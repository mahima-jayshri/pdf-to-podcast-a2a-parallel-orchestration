# PDF to Podcast Converter

A Python-based tool that converts PDF documents into audio podcasts, making it easier to consume written content on the go.

## Features

- Extracts text from PDF files
- Processes and summarizes content
- Converts text to speech
- Combines audio segments into a single podcast file
- Saves output in MP3 format

## Requirements

- Python 3.7+
- FFmpeg (required for audio processing)
- Internet connection (for TTS services)

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd A2A(parallel)
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Install FFmpeg:
   - Windows: Download from [FFmpeg's official website](https://ffmpeg.org/download.html) and add it to your system PATH
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

## Usage

1. Place your PDF file in the project directory
2. Run the script:
   ```
   python main.py
   ```
3. The generated podcast will be saved in the `output` directory as `podcast.mp3`

## Configuration

You can modify the following settings in the code:
- Voice settings in the TTS module
- Audio output format and quality
- Processing parameters for text chunking and summarization

## Output

The generated podcast will be saved as `output/podcast.mp3` with the following details:
- Format: MP3
- Sample rate: 44.1kHz
- Bitrate: 128kbps

## Troubleshooting

- If you encounter any issues with audio processing, ensure FFmpeg is properly installed and accessible in your system PATH
- For TTS issues, check your internet connection and API keys (if using cloud-based TTS services)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
