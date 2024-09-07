#####################################################################################
#CHIP-TUNE HEX DUMP GENERATOR
#   Author: Jack Ray
#   Date: 6/14/24
#
#CONTEXT:
#   A class which converts dual-voiced "chip-tune" songs into a minimalistic hex-dump
#   Octaves range from two to seven
#
#FORMAT:
#    BPM(1 BYTE) 
#    VOICE1: VALUE(1 BYTE) BEAT_LENGTH(1 BYTE)
#    VOICE2: VALUE(1 BYTE) BEAT_LENGTH(1 BYTE)
#    ...
#
#EXAMPLE: 
#   Tempo:     | 120 Bpm
#   Segment 1: | Voice 1 - C#4, Quarter Note       | Voice 2 - Rest, Eight Note
#   Segment 2: | Voice 1 - G7,  Thirty-second Note | Voice 2 - C2,   Whole Note
#   ---------------------------------------------------------------------------------
#   >>> x = Song(bpm = 120)
#   >>> x.push_segment(1, TONAL_VAL.C_SHARP, BEAT.NOTE_4, 4)
#   >>> x.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_8, 4)
#   >>> x.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 4)
#   >>> x.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_1, 2)
#   >>> x.push_segment(2, TONAL_VAL.A_SHARP, BEAT.NOTE_8, 2)
#   >>> x.print_song()
#   BPM: 120
#   Segment 1: Voice 1: C_SHARP   Octave-4  Duration-NOTE_4       Voice 2: REST                Duration-NOTE_8
#   Segment 2: Voice 1: G_NATURAL Octave-4  Duration-NOTE_32      Voice 2: C_NATURAL Octave-2  Duration-NOTE_1
#   Segment 3: Voice 1: Empty                                     Voice 2: A_SHARP   Octave-2  Duration-NOTE_8
#   >>> print(x.hex_dump())
#   
#   BPM: 78
#   Segment 1: 19 08 3d 04
#   Segment 2: 1f 01 00 20
#   Segment 3: 00 00 0a 04
#
#   bytearray(b'x\x19\x08=\x04\x1f\x01\x00 \x00\x00\n\x04')

from enum import IntEnum, auto
from math import floor, remainder, log2
from print_color import print

#Spaces in each segment- " 00 00 00 00" -> SEGMENT_STR_LEN = 12
SEGMENT_STR_LEN = 18

#Byte length of each segment- " 00 00 00 00" -> SEGMENT_BYTE_LEN = 8
SEGMENT_BYTE_LEN = 8

NUM_VOICES = 2 #Number of voices
NUM_ELEMENTS = 3 #Number of elements per each voice

#Lower and upper octave limits
LOWER_OCTAVE = 2
UPPER_OCTAVE = 7

class TONAL_VAL(IntEnum):
    C_NATURAL = 0
    C_SHARP = auto()
    D_NATURAL = auto()
    D_SHARP = auto()
    E_NATURAL = auto()
    F_NATURAL = auto()
    F_SHARP = auto()
    G_NATURAL = auto()
    G_SHARP = auto()
    A_NATURAL = auto()
    A_SHARP = auto()
    B_NATURAL = auto()
    REST = 73

class BEAT(IntEnum):
    NOTE_1 = 32
    NOTE_2 = 16
    NOTE_4 = 8
    NOTE_8 = 4
    NOTE_16 = 2
    NOTE_32 = 1

class INSTRUMENT(IntEnum):
    PIANO = 0
    EPIANO = auto()
    FLUTE = auto()
    CLARINET = auto()
    SINE = auto()
    SQUARE = auto()
    SAW = auto()
    VIOLIN = auto()
    DRUM = auto()

class Song:
    def __init__(self, bpm: None | int = None, byte_string: None | str = None):
        #Verify that only one of the two arguments, bpm and byte_string, are provided
        if not ((bpm == None) ^ (byte_string == None)):
            raise ValueError("Must provide only either bpm or byte_string argument")

        #Declare field member voices
        self._voices = [[],[]]

        #Declare field member bpm if provided
        if(bpm != None): self._bpm = bpm

        #Declare field member byte_string if provided
        elif(byte_string != None):
            #Check for invalid byte_string argument by evaluating length
            if(remainder(len(byte_string[2:]), SEGMENT_STR_LEN) != 0):
                raise ValueError("Invalid byte_string argument")
            
            #Convert byte_string into segmented data
            else:
                #Isolate bpm value from segments
                self._bpm = int(byte_string[:2], base=16)
                
                #Iterate through each segment
                for i in range(int(len(byte_string[2:]) / SEGMENT_STR_LEN)):
                    #Iterate through each segment element
                    for j in range(NUM_ELEMENTS):
                        tone_val = int((byte_string[2 + j * 4 + i * SEGMENT_STR_LEN:]
                        )[:2], base=16)
                        
                        beat_val = int((byte_string[3 + j * 4 + i * SEGMENT_STR_LEN:]
                        )[:3], base=16)

                        instrument_val = int((byte_string[4 + j * 4 + i * SEGMENT_STR_LEN:]
                        )[:4], base=16)#MEKOFMEOFMOI
                        
                        if(beat_val == 0): continue
                        self._voices[j].append([tone_val, beat_val, instrument_val])

    #Method to add a note value segment to either voice
    def push_segment(self, voice_num: int, note: TONAL_VAL = TONAL_VAL.REST,
    length: BEAT = BEAT.NOTE_4, octave: int | None = None,
    instrument: INSTRUMENT = INSTRUMENT.PIANO):
        #Check for invalid arguments
        if voice_num not in range(1, NUM_VOICES + 1):
            raise ValueError("Voice number exceeds range") 
        if length > 255 or length < 0:
            raise ValueError("Invalid note length")

        #Handle the octave argument
        if(octave == None and note != TONAL_VAL.REST):
            raise ValueError("Octave must be specified for non rest-note")
        elif(octave != None and (octave < LOWER_OCTAVE or octave > UPPER_OCTAVE)):
            raise ValueError("Octave argument exceeds 2-7 range")

        #Condition for rest notes
        if note == TONAL_VAL.REST:
            self._voices[voice_num - 1].append([note, length, instrument])

        #Scale non rest-note value by twelve notes according to octave and push data
        else:
            self._voices[voice_num - 1].append(
            [note + (octave - LOWER_OCTAVE) * 12, length, instrument])

    #Method to add a note value segment to either voice
    def insert_segment(self, seg_num: int, voice_num: int,
    note: TONAL_VAL = TONAL_VAL.REST, length: BEAT = BEAT.NOTE_4,
    octave: int | None = None, instrument: INSTRUMENT = INSTRUMENT.PIANO):
        #Check for invalid arguments
        if voice_num not in range(1, NUM_VOICES + 1):
            raise ValueError("Voice number exceeds range") 
        if length > 255 or length < 0:
            raise ValueError("Invalid note length")
        
        #Handle the octave argument
        if(octave == None and note != TONAL_VAL.REST):
            raise ValueError("Octave must be specified for non rest-note")
        elif(octave != None and (octave < LOWER_OCTAVE or octave > UPPER_OCTAVE)):
            raise ValueError("Octave argument exceeds 2-7 range")

        #Condition for rest notes
        if note == TONAL_VAL.REST:
            self._voices[voice_num - 1].insert(seg_num, [note, length, instrument])

        #Scale non rest-note value by twelve notes according to octave and push data
        else: 
            self._voices[voice_num - 1].insert(seg_num,
            [note + (octave - LOWER_OCTAVE) * 12, length, instrument])

    #Method to remove a note value segment to either voice
    def remove_segment(self, voice_num, seg_num):
        self._voices[voice_num - 1].pop(seg_num - 1)

    #Method to print song pre hex-dump
    def print_song(self):
        #Print Bpm
        print(f"BPM: ", color="red")
        print(self._bpm, color="white")

        #Print each segment value
        max_len = max(len(self._voices[0]), len(self._voices[1]))
        for i in range(max_len):
            for j in range(NUM_VOICES):
                #Print Segment number
                if(j == 0): print(f"Segment {i + 1}: ", color="red", end='')

                #Print voice number
                print(f"Voice {j + 1}: ", color="yellow", end='')

                #Skip rest of code and print "empty" if empty
                if(len(self._voices[j]) - 1 < i):
                    print(f"Empty".ljust(42), end='')
                    continue

                if(self._voices[j][i][0] == TONAL_VAL.REST): #Rest note print
                    print(TONAL_VAL(self._voices[j][i][0])._name_.ljust(10),
                    end='')
                else: #Regular note print
                    print(TONAL_VAL(self._voices[j][i][0] % 12)._name_.ljust(10),
                    end='')

                #Octave print
                if(self._voices[j][i][0] != TONAL_VAL.REST):
                    print(("Octave-" +
                    str(floor(self._voices[j][i][0] / 12) + 2)).ljust(10), end='')
                else: print("".ljust(10), end='')

                #Note duration print
                if(remainder(log2(self._voices[j][i][1]), 1) == 0 and self._voices[j][i][1] <= 32):
                    print(f"Duration-{BEAT(self._voices[j][i][1])._name_}".ljust(22), end='')
                else:
                    print(f"Duration-{self._voices[j][i][1]}x32 Notes".ljust(22), end='')

                #Instrument Print
                print(f"Instrument-{INSTRUMENT(self._voices[j][i][2])._name_}".ljust(22), end='')
                
            print(end='\n')

    #Method to return a hex dump representation of the song
    def hex_dump(self) -> bytearray:
        #Convert bpm to hex
        byte_string = self._bpm.to_bytes().hex()

        #Print bpm in hex
        print(f"\nBPM: {byte_string}")

        #Iterate through segments
        max_len = max(len(self._voices[0]), len(self._voices[1]))
        for i in range(max_len):
            #Print each segment
            print(f"Segment {i + 1}:", end='')
            for j in range(NUM_VOICES):
                #If empty, print and add four zeros instead
                if len(self._voices[j]) - 1 < i:
                    for k in range(NUM_ELEMENTS):
                        print(f" 00", end='')
                        byte_string += "00"
                #Add each value to a byte string in hex
                else:
                    for k in range(NUM_ELEMENTS):
                        #Convert value to hex
                        byte_string += self._voices[j][i][k].to_bytes().hex()

                        #Print value in hex
                        print(f" {self._voices[j][i][k].to_bytes().hex()}", end='')
            print(end='\n')
        print(end='\n')

        #Convert to bytearray
        byte_string = bytearray.fromhex(byte_string)

        """
        print("const uint8_t baby_shark[" + str(len(byte_string) + 4) + "] = {", end='')
        for i in range(len(byte_string)):
            print(str(hex(byte_string[i])) + ", ", end='')
        print("0x0, 0x0, 0x0, 0x0};\n")
        """

        #Return bytearray byte_string
        return byte_string

"""
baby_shark = Song(bpm=115)

baby_shark.push_segment(1, TONAL_VAL.D_NATURAL, BEAT.NOTE_4, 5)
baby_shark.push_segment(1, TONAL_VAL.E_NATURAL, BEAT.NOTE_4, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)

baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.D_NATURAL, BEAT.NOTE_8, 5)
baby_shark.push_segment(1, TONAL_VAL.E_NATURAL, BEAT.NOTE_8, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)

baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.D_NATURAL, BEAT.NOTE_8, 5)
baby_shark.push_segment(1, TONAL_VAL.E_NATURAL, BEAT.NOTE_8, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)

baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_16, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.REST, BEAT.NOTE_32, 5)
baby_shark.push_segment(1, TONAL_VAL.F_SHARP, BEAT.NOTE_2, 5)

################################################################################

baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_2)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32) 
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.D_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(2, TONAL_VAL.D_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 4)

baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32) 
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.D_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_8, 4)
baby_shark.push_segment(2, TONAL_VAL.D_NATURAL, BEAT.NOTE_16, 4)

baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32) 
baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 3)
baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 3)
baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_16, 4)

baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32) 
baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 3)
baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_8, 4)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 3)

baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32) 
baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.B_NATURAL, BEAT.NOTE_16, 3)
baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(2, TONAL_VAL.B_NATURAL, BEAT.NOTE_16, 3)
baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_16, 4)

baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_16 + BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32) 
baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_32, 3)
baby_shark.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_32)
baby_shark.push_segment(2, TONAL_VAL.B_NATURAL, BEAT.NOTE_16, 3)
baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_8, 4)
baby_shark.push_segment(2, TONAL_VAL.B_NATURAL, BEAT.NOTE_16, 3)

baby_shark.push_segment(2, TONAL_VAL.D_NATURAL, BEAT.NOTE_2, 4)

baby_shark.hex_dump()
baby_shark.print_song()
"""