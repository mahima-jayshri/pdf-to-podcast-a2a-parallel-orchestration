
import os
import sys
import time
import threading
import queue
from agents import PDFProcessingAgent, TextSummarizationAgent, TTSAgent, PublishingAgent
from pydub import AudioSegment

# Ensure the output directory exists
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Shared queues between agents
text_queue = queue.Queue()
summary_queue = queue.Queue()
audio_queue = queue.Queue()

# Setup agents
pdf_agent = PDFProcessingAgent()
summarizer = TextSummarizationAgent()
tts_agent = TTSAgent()
publisher = PublishingAgent()

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)


def extract_text_chunks(pdf_path, chunk_size=1000):
    print("[PDF] Extracting text...")
    try:
        full_text = pdf_agent.process_pdf(pdf_path)
        if not full_text:
            print("[PDF] Error: No text could be extracted from the PDF")
            text_queue.put(None)
            return
            
        # Split text into chunks
        chunks = []
        for i in range(0, len(full_text), chunk_size):
            chunk = full_text[i:i + chunk_size].strip()
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
        
        if not chunks:
            print("[PDF] Error: No valid text chunks could be created")
            text_queue.put(None)
            return
            
        print(f"[PDF] Extracted {len(chunks)} text chunks")
        for idx, chunk in enumerate(chunks):
            text_queue.put((idx, chunk))
        text_queue.put(None)  # Poison pill
        
    except Exception as e:
        print(f"[PDF] Error: {str(e)}")
        text_queue.put(None)  # Ensure we don't deadlock


def summarize_chunks():
    while True:
        item = text_queue.get()
        if item is None:
            summary_queue.put(None)  # Pass poison pill forward
            break
        idx, chunk = item
        print(f"[Summarizer] Processing chunk of {len(chunk)} characters")
        summary = summarizer.summarize(chunk)  # Fixed method name
        print(f"[Summarizer] Generated summary of {len(summary)} characters")
        summary_queue.put((idx, summary))
        print(f"[Summarizer] Processed chunk {idx}")


def tts_chunks():
    print("\n[TTS] Starting text-to-speech processing...")
    
    if not hasattr(tts_agent, 'engine') or tts_agent.engine is None:
        print("[!] WARNING: TTS engine not available. Audio will not be generated.")
        audio_queue.put(None)  # Signal end of processing
        return
    
    processed = 0
    failed = 0
    
    try:
        while True:
            item = summary_queue.get()
            if item is None:  # End of processing signal
                print(f"\n[TTS] Completed: {processed} chunks processed, {failed} failed")
                audio_queue.put(None)  # Signal end of processing
                break
                
            idx, summary = item
            if not summary or not summary.strip():
                print(f"[TTS] Warning: Empty text for chunk {idx}")
                failed += 1
                continue
            
            try:
                # Create output directory if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)
                
                # Generate a unique filename for this chunk
                audio_path = os.path.abspath(os.path.join(output_dir, f"chunk_{idx}.mp3"))
                temp_audio_path = os.path.join(output_dir, f"temp_chunk_{idx}_{os.urandom(4).hex()}.mp3")
                
                print(f"\n[TTS] Processing chunk {idx}")
                print(f"  - Text length: {len(summary)} characters")
                
                # Check if file already exists and is valid
                if os.path.exists(audio_path):
                    try:
                        audio = AudioSegment.from_file(audio_path)
                        if len(audio) > 0:
                            print(f"  - Using existing audio file: {os.path.basename(audio_path)}")
                            audio_queue.put((idx, audio_path))
                            processed += 1
                            continue
                        else:
                            print("  - Warning: Existing audio file is empty, regenerating...")
                            os.remove(audio_path)
                    except Exception as e:
                        print(f"  - Warning: Corrupted audio file, regenerating: {str(e)}")
                        try:
                            os.remove(audio_path)
                        except:
                            pass
                
                # Generate new audio
                print(f"  - Generating speech...")
                start_time = time.time()
                
                # Generate to temp file first
                result = tts_agent.text_to_speech(summary, temp_audio_path)
                
                if result and os.path.exists(temp_audio_path) and os.path.getsize(temp_audio_path) > 0:
                    # Verify the audio file can be loaded
                    try:
                        audio = AudioSegment.from_file(temp_audio_path)
                        if len(audio) > 0:
                            # Move temp file to final location
                            if os.path.exists(audio_path):
                                try:
                                    os.remove(audio_path)
                                except:
                                    pass
                            os.rename(temp_audio_path, audio_path)
                            
                            elapsed = time.time() - start_time
                            print(f"  - Success: Generated {len(audio)//1000}s of audio in {elapsed:.1f}s")
                            print(f"  - Saved to: {os.path.basename(audio_path)}")
                            audio_queue.put((idx, audio_path))
                            processed += 1
                        else:
                            raise Exception("Generated audio has 0 duration")
                    except Exception as e:
                        print(f"  - Error: Generated audio is invalid: {str(e)}")
                        failed += 1
                else:
                    print("  - Error: TTS did not generate output file")
                    failed += 1
                
            except Exception as e:
                print(f"  - Error during TTS: {str(e)}")
                failed += 1
            finally:
                # Clean up temp file if it exists
                if 'temp_audio_path' in locals() and os.path.exists(temp_audio_path):
                    try:
                        os.remove(temp_audio_path)
                    except:
                        pass
            
            # Small delay to prevent overwhelming the TTS engine
            time.sleep(0.5)
            
    except Exception as e:
        print(f"[TTS] Fatal error in TTS processing: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure we always signal the end of processing
        audio_queue.put(None)


def merge_audio(output_file="podcast.mp3"):
    print("\n[Publisher] Starting audio processing...")
    chunks = {}
    processed_chunks = 0
    total_chunks = 0
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # First, collect all audio files from the queue
    audio_files = []
    while True:
        item = audio_queue.get()
        if item is None:  # End of queue marker
            break
        audio_files.append(item)
    
    total_chunks = len(audio_files)
    if total_chunks == 0:
        print("[Publisher] No audio chunks to process")
        return
    
    print(f"[Publisher] Found {total_chunks} audio chunks to process")
    
    # Process each audio file
    for idx, audio_path in audio_files:
        try:
            print(f"\n[Publisher] Processing chunk {idx}: {os.path.basename(audio_path)}")
            
            # Check if file exists and has content
            if not os.path.exists(audio_path):
                print(f"  - Error: File not found: {audio_path}")
                continue
                
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                print(f"  - Error: Empty file: {audio_path}")
                try:
                    os.remove(audio_path)  # Remove empty file
                except:
                    pass
                continue
                
            print(f"  - Size: {file_size / 1024:.1f} KB")
            
            # Try to load the audio file
            try:
                audio = AudioSegment.from_file(audio_path)
                if len(audio) == 0:
                    print("  - Error: Could not load audio (0 duration)")
                    try:
                        os.remove(audio_path)  # Remove corrupted file
                    except:
                        pass
                    continue
                    
                chunks[idx] = audio
                processed_chunks += 1
                print(f"  - Success: Loaded {len(audio)}ms of audio")
                
            except Exception as e:
                print(f"  - Error loading audio: {str(e)}")
                # Try alternative method if available
                try:
                    audio = AudioSegment.from_file(audio_path, format="wav")
                    if len(audio) > 0:
                        chunks[idx] = audio
                        processed_chunks += 1
                        print(f"  - Success: Loaded with WAV format")
                    else:
                        raise Exception("WAV file has 0 duration")
                except Exception as e2:
                    print(f"  - Error loading as WAV: {str(e2)}")
                    try:
                        os.remove(audio_path)  # Remove corrupted file
                    except:
                        pass
                    
        except Exception as e:
            print(f"[Publisher] Error processing chunk {idx}: {str(e)}")
    
    # Check if we have any chunks to merge
    if not chunks:
        print("\n❌ No valid audio chunks found to merge.")
        print("Please check if the TTS engine is working correctly.")
        return
    
    # Sort chunks by their index
    sorted_indices = sorted(chunks.keys())
    print(f"\n[Publisher] Merging {len(chunks)}/{total_chunks} valid audio chunks...")
    
    # Create a temporary file for the final output
    temp_output = os.path.join(output_dir, f"temp_{os.urandom(8).hex()}.mp3")
    final_path = os.path.join(output_dir, output_file)
    
    try:
        # Start with the first chunk
        print(f"  - Starting with chunk {sorted_indices[0]}")
        final_audio = chunks[sorted_indices[0]]
        
        # Concatenate remaining chunks with progress
        for i, idx in enumerate(sorted_indices[1:], 1):
            print(f"  - Adding chunk {idx} ({i+1}/{len(sorted_indices)})")
            final_audio += chunks[idx]
        
        # Export to temporary file first
        print("  - Exporting final audio...")
        final_audio.export(
            temp_output,
            format="mp3",
            bitrate="192k",
            tags={"title": "Generated Podcast", "artist": "PDF to Podcast"}
        )
        
        # Verify the output file
        if os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
            # Remove existing output file if it exists
            if os.path.exists(final_path):
                try:
                    os.remove(final_path)
                except:
                    pass
            
            # Rename temp file to final name
            os.rename(temp_output, final_path)
            
            # Get final stats
            duration_sec = len(final_audio) / 1000  # Convert ms to seconds
            size_mb = os.path.getsize(final_path) / (1024 * 1024)
            
            print("\n" + "=" * 50)
            print("✅ Podcast generation completed successfully!")
            print(f"   Output file: {os.path.abspath(final_path)}")
            print(f"   Duration: {duration_sec:.1f} seconds")
            print(f"   File size: {size_mb:.2f} MB")
            print("=" * 50)
        else:
            print("\n❌ Failed to generate output file")
            
    except Exception as e:
        print(f"\n❌ Error during audio merging: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temporary file if it exists
        if os.path.exists(temp_output):
            try:
                os.remove(temp_output)
            except:
                pass


if __name__ == "__main__":
    pdf_path = "Atomic habits ( PDFDrive )-34-38.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        sys.exit(1)
    
    print(f"Starting podcast generation from: {pdf_path}")
    print("-" * 50)
    
    try:
        # Launch threads for each agent
        threads = [
            threading.Thread(target=extract_text_chunks, args=(pdf_path,)),
            threading.Thread(target=summarize_chunks),
            threading.Thread(target=tts_chunks),
            threading.Thread(target=merge_audio, args=("podcast.mp3",))
        ]
        
        for t in threads:
            t.daemon = True  # Ensure threads exit when main program exits
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
            
        print("\n" + "=" * 50)
        print("Podcast generation completed!" if os.path.exists(os.path.join(output_dir, "podcast.mp3")) 
              else "Podcast generation completed with some errors.")
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Cleaning up...")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        print("Exiting...")
