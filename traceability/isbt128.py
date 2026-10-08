#### created by Diego G. Salas, 2026-10-08
#
# ISBT 128 Donation Identification Number (DIN): format check and the
# ISO/IEC 7064 MOD 37-2 check character printed next to the eye-readable DIN.
#
# DIN (13 characters) = facility identification number (5) + year (2) + sequence (6).
# Reference value: G123498654321 -> check character H (ICCBBA worked example,
# cross-checked in tests against python-stdnum, an independent implementation).
import re

##### Character set: 0-9 -> 0-9, A-Z -> 10-35, '*' -> 36
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ*"
DIN_PATTERN = re.compile(r"^[A-Z0-9]{5}[0-9]{2}[0-9]{6}$")


def check_character(din):
    """Return the ISO 7064 MOD 37-2 check character for a 13-character DIN."""
    total = 0
    for ch in din:
        total = ((total + ALPHABET.index(ch)) * 2) % 37
    return ALPHABET[(38 - total) % 37]


def is_well_formed(din):
    return bool(DIN_PATTERN.match(din))


def is_valid(din, check):
    """True when the DIN is well formed and its check character matches."""
    return is_well_formed(din) and check_character(din) == check
