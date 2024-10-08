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
            #Check for invalid byte_string
            if(remainder(len(byte_string[2:]), 12) != 0):
                raise ValueError("Invalid byte_string argument")
            
            #Convert byte string into segmented data
            else:
                self.byte_string = byte_string
                self._bpm = int(byte_string[:2], base=16)
                for i in range(int(len(byte_string[2:]) / 8)):
                    for j in range(2):
                        tone_val = int((
                        byte_string[2 + j * 4 + i * 8:])[:2], base=16)
                        
                        beat_val = int((
                        byte_string[3 + j * 4 + i * 8:])[:3], base=16)
                        
                        if(beat_val == 0): continue
                        self._voices[j].append([tone_val, beat_val])

    #Method to add a note value segment to either voice
    def push_segment(self, voice_num, note, length, octave = None):
        #Check for invalid arguments
        if voice_num != 1 and voice_num != 2:
            raise ValueError("Voice num must be 1 or 2") 
        if note > TONAL_VAL.REST or note < 0:
            raise ValueError("Note argument exceeds 2-7 octave range")
        if length > 255:
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
            self._voices[voice_num - 1].append([note, length])

        #Scale non rest-note value by twelve notes according to octave and push data
        else:
            self._voices[voice_num - 1].append([note + (octave - 2) * 12, length])

    #Method to add a note value segment to either voice
    def insert_segment(self, seg_num, voice_num, note, length, octave = None):
        #Check for invalid arguments
        if voice_num != 1 and voice_num != 2:
            raise ValueError("Voice num must be 1 or 2") 
        if note > 61 or note < 0:
            raise ValueError("Note argument exceeds 2-7 octave range")
        if length > 255:
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
                    print(f"Empty".ljust(42), end='')
                    continue

                #Rest note print
                if(self._voices[j][i][0] == TONAL_VAL.REST):
                    print(TONAL_VAL(self._voices[j][i][0])._name_.ljust(10),
                    end='')

                #Regular note print
                else:
                    print(TONAL_VAL(self._voices[j][i][0] % 12)._name_.ljust(10),
                    end='')

                #Octave print
                if(self._voices[j][i][0] != TONAL_VAL.REST):
                    print(("Octave-" +
                    str(floor(self._voices[j][i][0] / 12) + 2)).ljust(10), end='')
                else: print("".ljust(10), end='')

                #Note duration print
                if(remainder(log2(self._voices[j][i][1]), 1) == 0 and self._voices[j][i][1] <= 32):
                    print(f"Duration-{BEAT(self._voices[j][i][1])._name_}".ljust(22),
                    end='')
                else:
                    print(f"Duration-{self._voices[j][i][1]}x32 Notes".ljust(22),
                    end='')
                
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
            for j in range(2):
                #If empty, print and add four zeros instead
                if len(self._voices[j]) - 1 < i:
                    print(f" 00 00", end='')
                    byte_string += "0000"
                    continue
                #Add each value to a byte string in hex
                for k in range(2):
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
"""
"""
baby_shark.push_segment(1, TONAL_VAL.C_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(1, TONAL_VAL.E_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(1, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 4)
baby_shark.push_segment(1, TONAL_VAL.E_NATURAL, BEAT.NOTE_16, 4)

baby_shark.push_segment(2, TONAL_VAL.C_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(2, TONAL_VAL.G_NATURAL, BEAT.NOTE_16, 5)
baby_shark.push_segment(2, TONAL_VAL.E_NATURAL, BEAT.NOTE_16, 5)
"""
"""
baby_shark.hex_dump()
baby_shark.print_song()
"""