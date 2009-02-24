"""
SSHA is a modification of the SHA digest scheme with a salt
starting at byte 20 of the base64-encoded string.
"""

from binascii import Error as binascii_Error 
from binascii import a2b_base64 
from binascii import b2a_base64 
from random import randrange 
import sha 

__author__ = 'Dirk Datzert'

def generate_salt():
    # Salt can be any length, but not more than about 37 characters
    # because of limitations of the binascii module.
    # 7 is what Netscape's example used and should be enough.
    # All 256 characters are available.
    salt = ''
    for n in range(7):
        salt += chr(randrange(256))

    return salt

def encrypt(password):

    password = str(password)
    salt = generate_salt()

    return b2a_base64(sha.new(password + salt).digest() + salt)[:-1]

def validate(reference, attempt):
    try:
        ref = a2b_base64(reference)
    except binascii_Error:
        # Not valid base64.
        return 0

    salt = ref[20:]
    compare = b2a_base64(sha.new(attempt + salt).digest() + salt)[:-1]

    return (compare == reference)
