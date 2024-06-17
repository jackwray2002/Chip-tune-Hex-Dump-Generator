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
#    VOICE1: VALUE(1 BYTE) BEAT_LENGTH(2 BYTE)
#    VOICE2: VALUE(1 BYTE) BEAT_LENGTH(2 BYTE)
#    ...
#
#EXAMPLE: 
#   Tempo:     | 120 Bpm
#   Segment 1: | Voice 1 - C#4, Quarter Note       | Voice 2 - Rest, Eight Note
#   Segment 2: | Voice 1 - G7,  Thirty-second Note | Voice 2 - C2,   Whole Note
#   ---------------------------------------------------------------------------------
#   >>> x.push_segment(1, TONAL_VAL.C_SHARP, BEAT.NOTE_4, 4)
#   >>> x.push_segment(2, TONAL_VAL.REST, BEAT.NOTE_8, 4)
#   >>> x.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_32, 4)
#   >>> x.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_1, 2)
#   >>> x.push_segment(2, TONAL_VAL.A_SHARP, BEAT.NOTE_8, 2)
#   >>> x.print_song()
#   BPM: 120
#   Segment 1: Voice 1: C_SHARP   Octave-4  Duration-NOTE_4   Voice 2: REST                Duration-NOTE_8
#   Segment 2: Voice 1: G_NATURAL Octave-4  Duration-NOTE_32  Voice 2: C_NATURAL Octave-2  Duration-NOTE_1
#   Segment 3: Voice 1: Empty                                 Voice 2: A_SHARP   Octave-2  Duration-NOTE_8
#   >>> print(x.hex_dump())
#   
#   BPM: 78
#   Segment 1: 19 0008 3d 0004
#   Segment 2: 1f 0001 00 0020
#   Segment 3: 00 0000 0a 0004
#
#   781900083d00041f00010000200000000a0004
#
#

from enum import IntEnum, auto
from math import floor, remainder, log2

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
    REST = 61

class BEAT(IntEnum):
    NOTE_1 = 32
    NOTE_2 = 16
    NOTE_4 = 8
    NOTE_8 = 4
    NOTE_16 = 2
    NOTE_32 = 1

class Song:
    def __init__(self, bpm = None, byte_string = None):
        #Check if too little or too many arguments provided
        if(bpm == None and byte_string == None):
            raise ValueError("No arguments provided")
        elif(bpm != None and byte_string != None):
            raise ValueError("Too many arguments provided")

        #Declare field member voices
        self._voices = [[],[]]

        #Declare field member bpm if applicable
        if(bpm != None):
            if(type(bpm) != int): raise ValueError("bpm must be an int")
            else: self._bpm = bpm

        #Declare field member byte_string if applicable
        if(byte_string != None):
            if(type(byte_string) != str):
                raise ValueError("byte_sring must be an str")
            elif(remainder(len(byte_string[2:]), 12) != 0):
                raise ValueError("Invalid byte_sring argument")
            else:
                self.byte_string = byte_string
                self._bpm = int(byte_string[:2], base=16)
                for i in range(int(len(byte_string[2:]) / 12)):
                    for j in range(2):
                        tone_val = int((
                        byte_string[2 + j * 6 + i * 12:])[:2], base=16)
                        
                        beat_val = int((
                        byte_string[4 + j * 6 + i * 12:])[:4], base=16)
                        
                        if(beat_val == 0): continue
                        self._voices[j].append([tone_val, beat_val])

    #Method to add a note value segment to either voice
    def push_segment(self, voice_num, note, length, octave = None):
        #Check for invalid arguments
        if voice_num != 1 and voice_num != 2:
            raise ValueError("Voice num must be 1 or 2") 
        if note > 61 or note < 0:
            raise ValueError("Note argument exceeds 2-7 octave range")
        if length > 0xffff:
            raise ValueError("Note Length argument is too long")
        if length < 0:
            raise ValueError("Note Length cannot be negative")
        
        #Handle the octave argument
        if(octave == None and note != TONAL_VAL.REST):
            raise ValueError("Octave must be specified for non rest-note")
        elif(octave != None and (octave < 2 or octave > 7)):
            raise ValueError("Octave argument exceeds 2-7 range")

        #Condition for rest notes
        if note == TONAL_VAL.REST: self._voices[voice_num - 1].append([note, length])

        #Scale non rest-note value by twelve notes according to octave and push data
        else: self._voices[voice_num - 1].append([note + (octave - 2) * 12, length])

    #Method to add a note value segment to either voice
    def insert_segment(self, seg_num, voice_num, note, length, octave = None):
        #Check for invalid arguments
        if voice_num != 1 and voice_num != 2:
            raise ValueError("Voice num must be 1 or 2") 
        if note > 61 or note < 0:
            raise ValueError("Note argument exceeds 2-7 octave range")
        if length > 0xffff:
            raise ValueError("Note Length argument is too long")
        if length < 0:
            raise ValueError("Note Length cannot be negative")
        
        #Handle the octave argument
        if(octave == None and note != TONAL_VAL.REST):
            raise ValueError("Octave must be specified for non rest-note")
        elif(octave != None and (octave < 2 or octave > 7)):
            raise ValueError("Octave argument exceeds 2-7 range")

        #Condition for rest notes
        if note == TONAL_VAL.REST:
            self._voices[voice_num - 1].insert(seg_num, [note, length])

        #Scale non rest-note value by twelve notes according to octave and push data
        else: 
            self._voices[voice_num - 1].insert(seg_num, 
            [note + (octave - 2) * 12, length])

    #Method to remove a note value segment to either voice
    def remove_segment(self, voice_num, seg_num):
        self._voices[voice_num - 1].pop(seg_num - 1)

    #Method to print song pre hex-dump
    def print_song(self):
        #Print Bpm
        print(f"BPM: {self._bpm}")

        #Print each segment value
        max_len = max(len(self._voices[0]), len(self._voices[1]))
        for i in range(max_len):
            for j in range(2):
                #Print Segment number
                if(j == 0): print(f"Segment {i + 1}: ", end='')

                #Print Voice 1 data
                print(f"Voice {j + 1}: ", end='')

                #Skip rest of code and print "empty" if empty
                if(len(self._voices[j]) - 1 < i):
                    print(f"Empty".ljust(38), end='')
                    continue

                #Rest note print
                if(self._voices[j][i][0] == 61):
                    print(TONAL_VAL(self._voices[j][i][0])._name_.ljust(10),
                    end='')

                #Regular note print
                else:
                    print(TONAL_VAL(self._voices[j][i][0] % 12)._name_.ljust(10),
                    end='')

                #Octave print
                if(self._voices[j][i][0] != 61):
                    print(("Octave-" + str(floor(self._voices[j][i][0] / 12) + 2)
                    ).ljust(10), end='')
                else: print("".ljust(10), end='')

                #Note duration print
                if(remainder(log2(self._voices[j][i][1]), 1) == 0):
                    print(f"Duration-{BEAT(self._voices[j][i][1])._name_}".ljust(22),
                    end='')
                else:
                    print(f"Duration-{self._voices[j][i][1]}x32 Notes".ljust(22),
                    end='')
                
            print(end='\n')

    #Method to return a hex dump representation of the song
    def hex_dump(self, song_name: str):
        #Convert bpm to hex
        byte_string = self._bpm.to_bytes().hex()

        #Print bpm in hex
        print(f"\nBPM: {byte_string}")

        #Iterate through segments
        max_len = max(len(self._voices[0]), len(self._voices[1]))
        for i in range(max_len):
            #Print each segment
            print(f"Segment {i + 1}:", end='')
            for j in range(2):
                if len(self._voices[j]) - 1 < i:
                    print(f" 00 0000", end='')
                    byte_string += "000000"
                    continue
                for k in range(2):
                    if k == 0:
                        #Convert tone value to hex
                        byte_string += self._voices[j][i][k].to_bytes().hex()

                        #Print tone value in hex
                        print(f" {self._voices[j][i][k].to_bytes().hex()}", end='')
                    elif k == 1:
                        #Converted to a string and rejoined to mitigate overflow
                        bit_string = str(bin(self._voices[j][i][k])[2:].zfill(16))
                        bit_string_a = int(bit_string[8:], base = 2).to_bytes().hex()
                        bit_string_b = int(bit_string[:8], base = 2).to_bytes().hex()
                        byte_string += bit_string_b + bit_string_a

                        #Print duration value in hex
                        print(f" {bit_string_b + bit_string_a}", end='')
            print(end='\n')
        print(end='\n')

        #Convert to bytearray
        byte_string = bytearray.fromhex(byte_string)

        #Write byte_string to binary file of class instance name
        file = open(f"{song_name}.bin", "wb")
        file.write(byte_string)

        #Return bytearray byte_string
        return byte_string