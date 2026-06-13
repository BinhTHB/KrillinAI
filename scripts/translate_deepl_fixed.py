#!/usr/bin/env python3
"""
Translate SRT using DeepL API (free tier) - fixed version.
"""
import deepl
import re
import time
import os
from pathlib import Path

# Your DeepL API key
API_KEY = "e887c262-298b-445e-81a6-3dbd75f5b3ae:fx"

def load_srt_entries(srt_path):
    """Load SRT entries with timing and text."""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    entries = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        index = lines[0]
        timing = lines[1]
        text = '\n'.join(lines[2:])
        
        entries.append({
            'index': index,
            'timing': timing,
            'text': text,
            'translated': None
        })
    
    return entries

def translate_with_deepl(entries, batch_size=3, delay=2):
    """Translate entries using DeepL API with rate limiting."""
    translator = deepl.Translator(API_KEY)
    
    total = len(entries)
    print(f"Translating {total} entries with DeepL...")
    
    # Test API connection
    try:
        usage = translator.get_usage()
        print(f"DeepL quota: {usage.character.count}/{usage.character.limit} characters used")
    except Exception as e:
        print(f"ERROR: Failed to connect to DeepL API: {e}")
        return False
    
    success = 0
    for i in range(0, total, batch_size):
        batch = entries[i:i+batch_size]
        print(f"\nBatch {i//batch_size + 1}: {len(batch)} entries")
        
        for j, entry in enumerate(batch, 1):
            try:
                # DeepL translation - remove unsupported parameters
                result = translator.translate_text(
                    entry['text'],
                    source_lang="ZH",
                    target_lang="VI"
                )
                
                entry['translated'] = result.text
                success += 1
                print(f"  ✓ [{j}] {entry['text'][:40]}...")
                print(f"    → {result.text[:40]}...")
                
                # Small delay to respect rate limits
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ✗ [{j}] Error: {e}")
                # Keep original text if translation fails
                entry['translated'] = entry['text']
        
        if i + batch_size < total:
            print(f"Waiting {delay}s before next batch...")
            time.sleep(delay)
    
    print(f"\nTranslation complete: {success}/{total} entries")
    return True

def create_translated_srt(entries, output_path):
    """Create translated SRT file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(f"{entry['index']}\n")
            f.write(f"{entry['timing']}\n")
            f.write(f"{entry['translated'] if entry['translated'] else entry['text']}\n\n")
    
    print(f"Created translated SRT: {output_path}")

def main():
    workdir = Path("tasks/douyin-test")
    
    # Check if we need to create origin SRT first
    origin_srt = workdir / "origin_language_srt.srt"
    if not origin_srt.exists():
        print("ERROR: No origin SRT file found.")
        return
    
    # Load origin SRT
    entries = load_srt_entries(origin_srt)
    print(f"Loaded {len(entries)} entries from {origin_srt}")
    
    # Translate with DeepL
    if not translate_with_deepl(entries, batch_size=3, delay=2):
        print("\n⚠️  Using original text for failed translations")
    
    # Save translated SRT
    output_srt = workdir / "target_language_srt_deepl.srt"
    create_translated_srt(entries, output_srt)
    
    # Also copy to default target SRT name
    default_srt = workdir / "target_language_srt.srt"
    with open(output_srt, 'r', encoding='utf-8') as src:
        with open(default_srt, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    print(f"Copied to default: {default_srt}")
    
    print("\n✅ Translation complete")

if __name__ == "__main__":
    main()