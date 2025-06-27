from PyPDF2 import PdfReader
from gpt4all import GPT4All
import pyttsx3
import os

class PDFProcessingAgent:
    def __init__(self):
        self.reader = None
    
    def process_pdf(self, pdf_path, chunk_size=1000):
        """Extract text from PDF and return as a single string."""
        try:
            self.reader = PdfReader(pdf_path)
            text = ""
            for page in self.reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if not text.strip():
                raise ValueError("No text could be extracted from the PDF")
                
            return text
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return ""  # Return empty string if there's an error

class TextSummarizationAgent:
    def __init__(self, model_name="orca-mini-3b-gguf2-q4_0.ggml"):
        try:
            self.model = GPT4All(model_name, allow_download=True)
        except Exception as e:
            print(f"Warning: Could not load model {model_name}. Using simple text truncation instead. Error: {str(e)}")
            self.model = None
    
    def summarize(self, text):
        """Generate a summary of the given text."""
        if self.model is None:
            # Fallback to simple text truncation if model loading failed
            return text[:500] + "... [truncated]"
            
        try:
            prompt = f"Please summarize the following text in a concise manner:\n\n{text}"
            with self.model.chat_session():
                response = self.model.generate(prompt, max_tokens=500)
            return response
        except Exception as e:
            print(f"Warning: Summarization failed: {str(e)}")
            return text[:500] + "... [truncated]"

import os
import sys
import tempfile
import time
import pyttsx3
from pydub import AudioSegment

class TTSAgent:
    def __init__(self):
        self.engine = None
        self.voices = []
        self._init_engine()
    
    def _init_engine(self):
        """Initialize the TTS engine with available voices."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.engine = pyttsx3.init()
                # Set properties for better voice quality
                self.engine.setProperty('rate', 180)  # Speed of speech
                self.engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
                
                # Get available voices
                self.voices = self.engine.getProperty('voices')
                if not self.voices:
                    raise Exception("No voices found")
                    
                print(f"[TTS] Initialized with {len(self.voices)} voice(s) available")
                return
                
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"[TTS] Warning: Could not initialize TTS engine after {max_retries} attempts: {str(e)}")
                    print("[TTS] Text-to-speech will not be available")
                else:
                    time.sleep(1)  # Wait before retrying
    
    def _save_direct_mp3(self, text, output_file):
        """Save text directly to MP3 using pyttsx3."""
        try:
            self.engine.save_to_file(text, output_file)
            self.engine.runAndWait()
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return output_file
            return None
        except Exception as e:
            print(f"[TTS] Error saving to MP3: {str(e)}")
            return None
    
    def text_to_speech(self, text, output_file):
        """Convert text to speech and save to file."""
        if not text or not text.strip():
            print("[TTS] Error: Empty text provided")
            return None
            
        if self.engine is None:
            print("[TTS] Error: TTS engine not initialized")
            return None
            
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        # Create a temporary file in the same directory as the output file
        # to avoid cross-device link issues
        temp_file = os.path.join(output_dir, f"temp_{os.urandom(8).hex()}.mp3")
        
        try:
            # Try to save directly to MP3 first
            if self._save_direct_mp3(text, temp_file):
                # Verify the file was created and has content
                if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                    # Move to final location
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                        except:
                            pass
                    os.rename(temp_file, output_file)
                    return output_file
                return None
                
            # Fall back to WAV and convert
            with tempfile.NamedTemporaryFile(suffix='.wav', dir=output_dir, delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
                
            try:
                # Generate WAV file
                self.engine.save_to_file(text, temp_wav_path)
                self.engine.runAndWait()
                
                # Verify WAV file was created and has content
                if not os.path.exists(temp_wav_path) or os.path.getsize(temp_wav_path) == 0:
                    print("[TTS] Error: WAV file not generated or is empty")
                    return None
                
                # Convert WAV to MP3
                try:
                    audio = AudioSegment.from_wav(temp_wav_path)
                    if len(audio) == 0:
                        print("[TTS] Error: Audio has 0 duration")
                        return None
                        
                    # Export to temporary file first
                    audio.export(temp_file, format="mp3", bitrate="192k")
                    
                    # Verify the MP3 was created and has content
                    if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                        print("[TTS] Error: MP3 file not generated or is empty")
                        return None
                        
                    # Move to final location
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                        except:
                            pass
                    os.rename(temp_file, output_file)
                    
                    return output_file
                    
                except Exception as e:
                    print(f"[TTS] Error converting WAV to MP3: {str(e)}")
                    return None
                    
            finally:
                # Clean up temporary files
                try:
                    os.unlink(temp_wav_path)
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except:
                    pass
        except Exception as e:
            print(f"[TTS] Error in text-to-speech conversion: {str(e)}")
            # Clean up any partial files
            try:
                if 'temp_file' in locals() and os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
            return None

class PublishingAgent:
    def __init__(self):
        self.published_files = []
    
    def publish(self, file_path):
        """Publish the file (in this case, just track published files)."""
        if os.path.exists(file_path):
            self.published_files.append(file_path)
            return True
        return False
