#!/usr/bin/env python3
"""
Translation script with Google Translate fallback for KrillinAI.
Handles rate limiting with exponential backoff and small batches.
"""
import json
import time
import re
import sys
from pathlib import Path
import random

def translate_google_fallback(text, src='zh-cn', dest='vi', max_retries=3):
    """
    Translate using googletrans with retry logic.
    """
    try:
        from googletrans import Translator
        
        translator = Translator()
        
        for attempt in range(max_retries):
            try:
                # Add random delay to avoid rate limiting
                if attempt > 0:
                    delay = 2 ** attempt + random.uniform(0, 1)
                    time.sleep(delay)
                
                result = translator.translate(text, src=src, dest=dest)
                
                if result and result.text:
                    # Basic validation
                    if (result.text != text and 
                        len(result.text.strip()) >= 2 and
                        not result.text.startswith('[')):
                        return result.text
                
            except Exception as e:
                print(f"  Attempt {attempt+1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
        
        return None
        
    except ImportError:
        print("googletrans not installed. Install with: pip install googletrans==4.0.0rc1")
        return None
    except Exception as e:
        print(f"Google Translate error: {e}")
        return None

def process_translation_batch(entries, batch_size=5, delay_between_batches=3):
    """
    Process translations in small batches with delays.
    """
    results = []
    total = len(entries)
    
    for i in range(0, total, batch_size):
        batch = entries[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        print(f"\nBatch {batch_num}: {len(batch)} entries")
        
        for j, entry in enumerate(batch):
            origin = entry.get('origin_text', '') or entry.get('OriginText', '')
            if not origin:
                continue
            
            print(f"  [{j+1}/{len(batch)}] Translating: {origin[:50]}...")
            
            translated = translate_google_fallback(origin)
            
            if translated:
                entry['TranslatedText'] = translated
                entry['TranslationSource'] = 'google_translate_fallback'
                entry['TranslationSuccess'] = True
                print(f"    ✓ {translated[:50]}...")
            else:
                entry['TranslationSuccess'] = False
                entry['TranslationSource'] = 'failed'
                print(f"    ✗ Translation failed")
            
            # Small delay between entries in same batch
            if j < len(batch) - 1:
                time.sleep(0.5)
        
        results.extend(batch)
        
        # Delay between batches
        if i + batch_size < total:
            print(f"Waiting {delay_between_batches}s before next batch...")
            time.sleep(delay_between_batches)
    
    return results

def load_failed_translations(workdir):
    """Load failed translations from translation_data files."""
    failed_entries = []
    translation_files = ['translation_data_0.json', 'translation_data_1.json']
    
    for fname in translation_files:
        path = Path(workdir) / fname
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    origin = item.get('OriginText', '') or item.get('origin_part', '')
                    translated = item.get('TranslatedText', '') or item.get('translated_part', '')
                    
                    # Check if translation failed
                    is_failed = (not translated or 
                                translated == origin or 
                                len(translated.strip()) < 3 or
                                translated.startswith('[') or
                                'origin_part' in translated)
                    
                    if is_failed and origin:
                        entry = {
                            'origin_text': origin,
                            'original_data': item
                        }
                        failed_entries.append(entry)
    
    return failed_entries

def create_srt_from_translations(origin_srt_path, translations_map, output_path):
    """Create SRT file using translations map."""
    
    with open(origin_srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\n+', content.strip())
    new_blocks = []
    new_index = 1
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        index = lines[0]
        time_line = lines[1]
        origin_text = '\n'.join(lines[2:])
        
        # Get translation
        translated = translations_map.get(origin_text, '')
        
        if translated:
            new_block = f"{new_index}\n{time_line}\n{translated}"
            new_blocks.append(new_block)
            new_index += 1
        else:
            # Skip untranslated entries
            continue
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(new_blocks))
    
    return len(new_blocks)

def main():
    workdir = Path("tasks/douyin-test")
    
    print("=== Translation Retry with Google Translate Fallback ===\n")
    
    # Step 1: Load failed translations
    print("1. Loading failed translations...")
    failed_entries = load_failed_translations(workdir)
    
    if not failed_entries:
        print("No failed translations found.")
        return
    
    print(f"Found {len(failed_entries)} failed translations")
    
    # Step 2: Retry with Google Translate
    print("\n2. Retrying with Google Translate (small batches)...")
    print("   Batch size: 5 entries")
    print("   Delay between batches: 3s")
    print("   This may take a few minutes...")
    
    retried_entries = process_translation_batch(failed_entries, batch_size=5, delay_between_batches=3)
    
    # Step 3: Build translations map
    translations_map = {}
    success_count = 0
    
    for entry in retried_entries:
        origin = entry.get('origin_text', '')
        translated = entry.get('TranslatedText', '')
        
        if origin and translated and entry.get('TranslationSuccess', False):
            translations_map[origin] = translated
            success_count += 1
    
    print(f"\n3. Translation Results:")
    print(f"   Successfully translated: {success_count}/{len(failed_entries)}")
    print(f"   Success rate: {success_count/len(failed_entries)*100:.1f}%")
    
    # Step 4: Create new SRT
    if success_count > 0:
        print("\n4. Creating new SRT file...")
        
        origin_srt = workdir / "origin_language_srt_fixed.srt"
        output_srt = workdir / "target_language_srt_retried.srt"
        
        entry_count = create_srt_from_translations(origin_srt, translations_map, output_srt)
        
        print(f"   Created {output_srt} with {entry_count} entries")
        
        # Also update translation_data file
        update_translation_data(workdir, retried_entries)
    else:
        print("\n4. No successful translations, skipping SRT creation")
    
    print("\n=== Complete ===")
    print("Next steps:")
    print("1. Run TTS: ./krillinai-cli.exe tts --input-srt tasks/douyin-test/target_language_srt_retried.srt")
    print("2. Render video: ./krillinai-cli.exe render-vertical --subtitle tasks/douyin-test/target_language_srt_retried.srt")

def update_translation_data(workdir, retried_entries):
    """Update translation_data files with new translations."""
    
    # Load original data
    all_data = []
    translation_files = ['translation_data_0.json', 'translation_data_1.json']
    
    for fname in translation_files:
        path = workdir / fname
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                all_data.extend(data)
    
    if not all_data:
        return
    
    # Create lookup for retried translations
    retry_map = {}
    for entry in retried_entries:
        origin = entry.get('origin_text', '')
        translated = entry.get('TranslatedText', '')
        if origin and translated and entry.get('TranslationSuccess', False):
            retry_map[origin] = translated
    
    # Update entries
    updated_count = 0
    for item in all_data:
        origin = item.get('OriginText', '') or item.get('origin_part', '')
        
        if origin in retry_map:
            item['TranslatedText'] = retry_map[origin]
            item['TranslationSource'] = 'google_translate_fallback_retry'
            updated_count += 1
    
    # Save updated data
    if updated_count > 0:
        output_path = workdir / "translation_data_retried_full.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print(f"   Updated {updated_count} entries in translation_data_retried_full.json")

if __name__ == '__main__':
    main()