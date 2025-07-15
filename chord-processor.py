
#!/usr/bin/env python3
"""
Chord progression processor for uploaded chord sets
"""

import os
import json
import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import mido
from music21 import stream, chord, key, pitch, meter, tempo, metronome


class ChordProcessor:
    def __init__(self):
        self.chord_sets_dir = Path("./storage/midi/chord-sets")
        self.chord_sets_dir.mkdir(parents=True, exist_ok=True)
        
    def process_chord_zip(self, zip_path: str) -> Dict[str, Any]:
        """Process uploaded chord set zip file"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract to temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_ref.extractall(temp_dir)
                    
                    # Process extracted files
                    chord_data = self._analyze_chord_files(temp_dir)
                    
                    # Save processed chord data
                    chord_set_name = Path(zip_path).stem
                    output_path = self.chord_sets_dir / f"{chord_set_name}_processed.json"
                    
                    with open(output_path, 'w') as f:
                        json.dump(chord_data, f, indent=2)
                    
                    return {
                        "success": True,
                        "chord_set_name": chord_set_name,
                        "output_path": str(output_path),
                        "chord_count": len(chord_data.get("progressions", [])),
                        "metadata": chord_data.get("metadata", {})
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_chord_files(self, directory: str) -> Dict[str, Any]:
        """Analyze chord files in directory"""
        progressions = []
        metadata = {"file_count": 0, "formats": []}
        
        for file_path in Path(directory).rglob("*"):
            if file_path.is_file():
                metadata["file_count"] += 1
                
                # Process different file types
                if file_path.suffix.lower() in ['.mid', '.midi']:
                    prog_data = self._process_midi_chords(file_path)
                    if prog_data:
                        progressions.append(prog_data)
                        metadata["formats"].append("MIDI")
                
                elif file_path.suffix.lower() in ['.txt', '.chord']:
                    prog_data = self._process_text_chords(file_path)
                    if prog_data:
                        progressions.append(prog_data)
                        metadata["formats"].append("Text")
                
                elif file_path.suffix.lower() == '.json':
                    prog_data = self._process_json_chords(file_path)
                    if prog_data:
                        progressions.append(prog_data)
                        metadata["formats"].append("JSON")
        
        return {
            "progressions": progressions,
            "metadata": metadata
        }
    
    def _process_midi_chords(self, file_path: Path) -> Dict[str, Any]:
        """Extract chord progressions from MIDI file"""
        try:
            mid = mido.MidiFile(str(file_path))
            
            # Use music21 for chord analysis
            score = stream.Score()
            part = stream.Part()
            
            # Convert MIDI to music21 format
            for msg in mid.play():
                if msg.type == 'note_on' and msg.velocity > 0:
                    # Add note to stream
                    note = pitch.Pitch(msg.note)
                    part.append(note)
            
            score.append(part)
            
            # Analyze chords
            chords = score.chordify()
            chord_symbols = []
            
            for element in chords.flat:
                if isinstance(element, chord.Chord):
                    chord_symbols.append(element.pitchedCommonName)
            
            return {
                "filename": file_path.name,
                "type": "MIDI",
                "chord_progression": chord_symbols,
                "tempo": self._extract_tempo(mid),
                "time_signature": "4/4"  # Default, could be analyzed
            }
            
        except Exception as e:
            print(f"Error processing MIDI file {file_path}: {e}")
            return None
    
    def _process_text_chords(self, file_path: Path) -> Dict[str, Any]:
        """Process text-based chord files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple chord extraction (can be enhanced)
            chord_patterns = []
            lines = content.split('\n')
            
            for line in lines:
                # Look for chord patterns like "C Am F G"
                words = line.strip().split()
                potential_chords = []
                
                for word in words:
                    # Basic chord detection
                    if self._is_chord_symbol(word):
                        potential_chords.append(word)
                
                if potential_chords:
                    chord_patterns.append(potential_chords)
            
            return {
                "filename": file_path.name,
                "type": "Text",
                "chord_progressions": chord_patterns,
                "raw_content": content[:500]  # First 500 chars
            }
            
        except Exception as e:
            print(f"Error processing text file {file_path}: {e}")
            return None
    
    def _process_json_chords(self, file_path: Path) -> Dict[str, Any]:
        """Process JSON chord files"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                "filename": file_path.name,
                "type": "JSON",
                "data": data
            }
            
        except Exception as e:
            print(f"Error processing JSON file {file_path}: {e}")
            return None
    
    def _is_chord_symbol(self, text: str) -> bool:
        """Basic chord symbol detection"""
        # Enhanced chord detection
        chord_roots = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
        modifiers = ['m', 'maj', 'min', '7', '9', '11', '13', 'sus', 'add', 'dim', 'aug']
        
        if not text or len(text) < 1:
            return False
        
        # Check if starts with chord root
        if text[0] in chord_roots:
            return True
        
        # Check for flat/sharp notation
        if len(text) > 1 and text[0] in ['b', '#'] and text[1] in chord_roots:
            return True
        
        return False
    
    def _extract_tempo(self, mid: mido.MidiFile) -> int:
        """Extract tempo from MIDI file"""
        for track in mid.tracks:
            for msg in track:
                if msg.type == 'set_tempo':
                    return int(mido.tempo2bpm(msg.tempo))
        return 120  # Default tempo
    
    def generate_midi_from_chords(self, chord_progression: List[str], 
                                 tempo: int = 120, 
                                 output_path: str = None) -> str:
        """Generate MIDI file from chord progression"""
        try:
            # Create music21 stream
            score = stream.Score()
            part = stream.Part()
            
            # Add tempo
            part.append(metronome.MetronomeMark(number=tempo))
            
            # Add chords
            for chord_symbol in chord_progression:
                try:
                    chord_obj = chord.Chord(chord_symbol)
                    chord_obj.quarterLength = 4.0  # Whole note
                    part.append(chord_obj)
                except:
                    # Skip invalid chord symbols
                    continue
            
            score.append(part)
            
            # Generate output path if not provided
            if not output_path:
                # Ensure the directory exists
                os.makedirs("./storage/midi/generated", exist_ok=True)
                output_path = f"./storage/midi/generated/chord_progression_{len(chord_progression)}_chords.mid"
            
            # Write MIDI file
            score.write('midi', fp=output_path)
            
            return output_path
            
        except Exception as e:
            print(f"Error generating MIDI from chords: {e}")
            return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Process chord sets')
    parser.add_argument('--process-zip', help='Process chord set zip file')
    parser.add_argument('--generate-midi', help='Generate MIDI from chord progression file')
    
    args = parser.parse_args()
    
    processor = ChordProcessor()
    
    if args.process_zip:
        result = processor.process_chord_zip(args.process_zip)
        print(json.dumps(result, indent=2))
    
    elif args.generate_midi:
        # Example usage
        chords = ["C", "Am", "F", "G", "C"]
        output_path = processor.generate_midi_from_chords(chords)
        print(f"Generated MIDI: {output_path}")
