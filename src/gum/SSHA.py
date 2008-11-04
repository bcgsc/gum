#####################################################################
#
# SSHA  A module implementing the SSHA encryption algorithm
#
# This software is governed by a license. See
# LICENSE.txt for the terms of this license.
#
#####################################################################
__version__='$Revision: 1402 $'[11:-2]

from binascii import a2b_base64
from binascii import b2a_base64
from binascii import Error as binascii_Error
from random import randrange
import sha


"""
SSHA is a modification of the SHA digest scheme with a salt
starting at byte 20 of the base64-encoded string.

This module contributed by Dirk Datzert
"""
# Source: [11]http://developer.netscape.com/docs/technote/ldap/pass_sha.html

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
