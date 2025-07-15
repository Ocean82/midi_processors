
#!/usr/bin/env python3
"""
Chord Sets Processor for Burnt Beats
Processes and organizes uploaded MIDI chord sets
"""

import os
import shutil
import mido
import json
from pathlib import Path
import argparse

class ChordSetsProcessor:
    def __init__(self, source_dir="./attached_assets", target_dir="./storage/midi/templates"):
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.chord_sets_dir = self.target_dir / "chord-sets"
        
    def analyze_chord_midi(self, midi_path):
        """Analyze a MIDI file for chord progressions"""
        try:
            mid = mido.MidiFile(midi_path)
            
            analysis = {
                "filename": os.path.basename(midi_path),
                "length": mid.length,
                "ticks_per_beat": mid.ticks_per_beat,
                "num_tracks": len(mid.tracks),
                "chord_progression": [],
                "key_signatures": [],
                "tempo_changes": [],
                "note_events": []
            }
            
            # Analyze tracks for chord data
            for track_idx, track in enumerate(mid.tracks):
                current_time = 0
                active_notes = set()
                
                for msg in track:
                    current_time += msg.time
                    
                    if msg.type == 'note_on' and msg.velocity > 0:
                        active_notes.add(msg.note)
                        
                        # Detect chord when 3+ notes are active
                        if len(active_notes) >= 3:
                            chord_notes = sorted(list(active_notes))
                            analysis["chord_progression"].append({
                                "time": current_time,
                                "notes": chord_notes,
                                "track": track_idx
                            })
                            
                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        active_notes.discard(msg.note)
                        
                    elif msg.type == 'set_tempo':
                        bpm = mido.tempo2bpm(msg.tempo)
                        analysis["tempo_changes"].append({
                            "time": current_time,
                            "bpm": round(bpm, 2)
                        })
                        
                    elif msg.type == 'key_signature':
                        analysis["key_signatures"].append({
                            "time": current_time,
                            "key": msg.key
                        })
            
            # Extract estimated key and tempo
            analysis["estimated_tempo"] = self.estimate_tempo(analysis)
            analysis["estimated_key"] = self.estimate_key(analysis)
            analysis["chord_count"] = len(analysis["chord_progression"])
            
            return analysis
            
        except Exception as e:
            return {
                "filename": os.path.basename(midi_path),
                "error": str(e),
                "status": "error"
            }
    
    def estimate_tempo(self, analysis):
        """Estimate overall tempo"""
        if analysis["tempo_changes"]:
            return analysis["tempo_changes"][0]["bpm"]
        return 120  # Default
    
    def estimate_key(self, analysis):
        """Estimate key signature"""
        if analysis["key_signatures"]:
            return analysis["key_signatures"][0]["key"]
        return "C"  # Default
    
    def categorize_chord_set(self, analysis):
        """Categorize chord set by characteristics"""
        chord_count = analysis.get("chord_count", 0)
        tempo = analysis.get("estimated_tempo", 120)
        
        if tempo < 80:
            category = "slow-progressions"
        elif tempo > 140:
            category = "fast-progressions"
        else:
            category = "medium-progressions"
            
        if chord_count > 8:
            subcategory = "complex"
        elif chord_count > 4:
            subcategory = "standard"
        else:
            subcategory = "simple"
            
        return f"{category}/{subcategory}"
    
    def process_chord_sets(self):
        """Process all MIDI files from source directory"""
        # Create chord sets directory structure
        self.chord_sets_dir.mkdir(parents=True, exist_ok=True)
        
        # Create category subdirectories
        categories = [
            "slow-progressions/simple",
            "slow-progressions/standard", 
            "slow-progressions/complex",
            "medium-progressions/simple",
            "medium-progressions/standard",
            "medium-progressions/complex",
            "fast-progressions/simple",
            "fast-progressions/standard",
            "fast-progressions/complex"
        ]
        
        for category in categories:
            (self.chord_sets_dir / category).mkdir(parents=True, exist_ok=True)
        
        # Find all MIDI files
        midi_files = list(self.source_dir.glob("*.mid")) + list(self.source_dir.glob("*.midi"))
        
        processed_files = []
        catalog = {
            "processed_at": str(Path().absolute()),
            "total_files": len(midi_files),
            "chord_sets": [],
            "categories": {}
        }
        
        print(f"🎼 Processing {len(midi_files)} chord set MIDI files...")
        
        for midi_file in midi_files:
            print(f"   📄 Analyzing: {midi_file.name}")
            
            # Analyze the MIDI file
            analysis = self.analyze_chord_midi(midi_file)
            
            if "error" not in analysis:
                # Categorize the chord set
                category = self.categorize_chord_set(analysis)
                target_path = self.chord_sets_dir / category / midi_file.name
                
                # Copy file to appropriate category
                shutil.copy2(midi_file, target_path)
                
                # Add to catalog
                chord_set_info = {
                    "original_path": str(midi_file),
                    "storage_path": str(target_path),
                    "category": category,
                    "analysis": analysis
                }
                
                catalog["chord_sets"].append(chord_set_info)
                
                # Update category stats
                if category not in catalog["categories"]:
                    catalog["categories"][category] = []
                catalog["categories"][category].append(chord_set_info)
                
                processed_files.append(midi_file.name)
            else:
                print(f"   ❌ Error processing {midi_file.name}: {analysis.get('error', 'Unknown error')}")
        
        # Save catalog
        catalog_path = self.chord_sets_dir / "chord_sets_catalog.json"
        with open(catalog_path, 'w') as f:
            json.dump(catalog, f, indent=2)
        
        print(f"\n✅ Processed {len(processed_files)} chord sets")
        print(f"💾 Catalog saved to: {catalog_path}")
        
        return catalog
    
    def get_chord_sets_by_category(self, category=None, tempo_range=None):
        """Get chord sets filtered by category and tempo"""
        catalog_path = self.chord_sets_dir / "chord_sets_catalog.json"
        
        if not catalog_path.exists():
            return []
            
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
        
        chord_sets = catalog.get("chord_sets", [])
        
        if category:
            chord_sets = [cs for cs in chord_sets if category in cs.get("category", "")]
            
        if tempo_range:
            min_tempo, max_tempo = tempo_range
            chord_sets = [
                cs for cs in chord_sets 
                if min_tempo <= cs.get("analysis", {}).get("estimated_tempo", 120) <= max_tempo
            ]
        
        return chord_sets

def main():
    parser = argparse.ArgumentParser(description='Chord Sets Processor')
    parser.add_argument('--process', action='store_true', help='Process chord sets from attached_assets')
    parser.add_argument('--list', action='store_true', help='List processed chord sets')
    parser.add_argument('--category', help='Filter by category (slow/medium/fast)-progressions/(simple/standard/complex)')
    parser.add_argument('--tempo-min', type=int, help='Minimum tempo filter')
    parser.add_argument('--tempo-max', type=int, help='Maximum tempo filter')
    
    args = parser.parse_args()
    
    processor = ChordSetsProcessor()
    
    if args.process:
        print("🎼 Burnt Beats Chord Sets Processor")
        print("=" * 40)
        catalog = processor.process_chord_sets()
        
        print(f"\n📊 Processing Summary:")
        print(f"   Total files: {catalog['total_files']}")
        print(f"   Successfully processed: {len(catalog['chord_sets'])}")
        print(f"   Categories created: {len(catalog['categories'])}")
        
        for category, sets in catalog['categories'].items():
            print(f"   - {category}: {len(sets)} chord sets")
            
    elif args.list:
        tempo_range = None
        if args.tempo_min and args.tempo_max:
            tempo_range = (args.tempo_min, args.tempo_max)
            
        chord_sets = processor.get_chord_sets_by_category(
            category=args.category,
            tempo_range=tempo_range
        )
        
        print("🎼 Chord Sets Library")
        print("=" * 40)
        
        for chord_set in chord_sets:
            analysis = chord_set.get("analysis", {})
            print(f"🎵 {analysis.get('filename', 'Unknown')}")
            print(f"   Category: {chord_set.get('category', 'Unknown')}")
            print(f"   Tempo: {analysis.get('estimated_tempo', 'Unknown')} BPM")
            print(f"   Key: {analysis.get('estimated_key', 'Unknown')}")
            print(f"   Chords: {analysis.get('chord_count', 0)}")
            print(f"   Duration: {analysis.get('length', 0):.2f}s")
            print()
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
