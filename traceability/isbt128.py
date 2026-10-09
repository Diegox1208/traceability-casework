#### created by Diego G. Salas
#
# ISBT 128 Donation Identification Number, DIN, format check and the
# ISO/IEC 7064 MOD 37-2 check character printed next to the eye-readable DIN.
#
# A DIN has 13 characters, a 5-character facility identification number, a 2-digit year and a 6-digit sequence.
# Reference value G123498654321 -> check character H, the ICCBBA worked example,
# cross-checked in tests against python-stdnum, an independent implementation.
import re

##### Character set 0-9 -> 0-9, A-Z -> 10-35, '*' -> 36
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ*"
DIN_PATTERN = re.compile(r"^[A-Z0-9]{5}[0-9]{2}[0-9]{6}$")


def check_character(din):
    total = 0
    for ch in din:
        total = ((total + ALPHABET.index(ch)) * 2) % 37
    return ALPHABET[(38 - total) % 37]


def is_well_formed(din):
    return bool(DIN_PATTERN.match(din))


def is_valid(din, check):
    return is_well_formed(din) and check_character(din) == check
