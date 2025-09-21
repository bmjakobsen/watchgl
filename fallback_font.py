
version = '0.33'

def height():
    return 16

def baseline():
    return 16

def max_width():
    return 16

def hmap():
    return True

def reverse():
    return False

def monospaced():
    return False

def min_ch():
    return 32

def max_ch():
    return 126

_font = b'\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80\x01\x80'

_mvfont = memoryview(_font)

def get_ch(ch):
    mvfont = _mvfont

    oc = ord(ch)

    w = 0
    if oc >= 32 and oc <= 126:
        w = 16
    return _mvfont, 16, w
