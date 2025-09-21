
#!/usr/bin/env python3
from array import array
import math
import fallback_font
import builtins
from time import ticks_ms, ticks_add, ticks_diff



# TODO; Check drawing functions if they use correct yshift, and apply window coordinates correctly
# TODO: Implement a screen that can just be used, without lazy drawing, or components, needed for games and for draw565 Frontend
# TODO: Rewrite draw565 to be a simple frontend to this library, as the size of the binary must be reduces, so the native and viper functions need to go
# TODO: Implement Drawing and Switching of screens
# TODO: For smooth scrolling it would be required to get the components of a screen efficiently, that overlap with a stripe on the screen.
# 




try:
    from micropython import const       # type: ignore[import-not-found]
    import micropython                  # type: ignore[import-not-found]
except ImportError:
    print("Using Micropython Faker Library")
    from micropython_faker import const
    import micropython_faker as micropython
    ptr8 = memoryview
    ptr16 = memoryview
    ptr32 = memoryview


try:
    import gc
    def _gc_collect():
        gc.collect()
except (ImportError, AttributeError):
    def _gc_collect():
        gc.collect()


TILE_SIZE = const(16)                       # Size of tiles on the screen, all components must be aligned to tiles
_TILE_SIZE_DIV = const(4)                   # Number of bits to shift right by to divide by the Tile Size
_TILE_SIZE_MOD_MASK = const(0xfffff0)       # Bitmask to get the modulo, x%TILE_SIZE => x&TILE_SIZE_MOD_MASK

_TILES_PER_VSCROLL_STRIPE = const(2)
_VSCROLL_STRIPE_SIZE = const(TILE_SIZE*_TILES_PER_VSCROLL_STRIPE)
_VSCROLL_STRIPE_SIZE2 = const(_VSCROLL_STRIPE_SIZE*2)


_MAX_TILES_PER_DIM = const(16)

# The Max size of the screen is dependent on the tile size, currently it is assumed that all screens have at most 16 Tiles in the width
_MAX_SCREEN_WIDTH = const(TILE_SIZE*_MAX_TILES_PER_DIM)
_MAX_SCREEN_HEIGHT = const(TILE_SIZE*_MAX_TILES_PER_DIM)



try:
    from typing import Protocol
except ImportError:
    Protocol = object           # type: ignore[assignment]




_ARRAY_TEST_MIN_MAX_SIZE = {
    (8,  False):  (       -128,          127),
    (8,  True):   (          0,          255),
    (16, False):  (     -32768,        32767),
    (16, True):   (          0,        65535),
    (32, False):  (-2147483648,   2147483647),
    (32, True):   (          0,   4294967295)
}
_ARRAY_TEST_INTEGERS = {
    False:      [ 'b', 'h', 'i', 'l', 'q' ],
    True:       [ 'B', 'H', 'I', 'L', 'Q' ]
}

def _array_get_int_type(n:int, unsigned:bool=False) -> str:
    global _ARRAY_TEST_MIN_MAX_SIZE, _ARRAY_TEST_INTEGERS
    if n not in [8, 16, 32]:
        raise Exception("Invalid Choice")
    (min, max) = _ARRAY_TEST_MIN_MAX_SIZE[(n, unsigned)]
    minm = min-1
    maxm = max+1
    for ctype in _ARRAY_TEST_INTEGERS[unsigned]:
        a = array(ctype, [0])
        try:
            a[0] = min
            if a[0] != min:
                continue
            a[0] = max
            if a[0] != max:
                continue
        except OverflowError:
            continue

        try:
            a[0] = minm
            if a[0] == minm:
                continue
        except OverflowError:
            pass

        try:
            a[0] = maxm
            if a[0] == maxm:
                continue
        except OverflowError:
            pass
        return ctype
    raise Exception("Unable to get fitting ctype")






COLORFORMAT_RGB565 = const(128)
COLORFORMAT_RGB565_R = const(129)


DIRECTION_UP = const(0)
DIRECTION_DOWN = const(1)
DIRECTION_LEFT = const(2)
DIRECTION_RIGHT = const(3)

ALIGNMENT_CENTER = const(0)
ALIGNMENT_LEFT = const(1)
ALIGNMENT_RIGHT = const(2)


class ImageStream(Protocol):
    width: int
    height: int
    # Reset Stream, or restart it
    def reset(self):
        pass
    # Skip n Pixels
    def skip_pixels(self, n:int):
        pass
    # Read n Pixels, into the buffer at the given offset, returns number of pixels read. Offset is in pixels
    # The streams signals that it is emptry by returning a number smaller than the number of requested pixels
    # The stream is never allowed to return less pixels than requested, while the stream has not reached its end

    # A Reader can expect that a stream does not have too many pixels, or that the number of remaining pixels changes unless by the amount specified in skip_pixels or when reading_pixels

    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        return -1
    # Get Remaining number of pixels, should only be used in a few cases, like ensuring the stream has enough pixels before starting to read it, as it can be slow.
    def get_remaining(self) -> int:
        return -1
    def info(self) -> str:
        return ""



class DisplaySpec():
    _SUPPORTED_SCROLLS = set([DIRECTION_UP, DIRECTION_DOWN])
    def __init__(self, width:int, height:int, color_format:int, scroll_directions:frozenset[int]=frozenset([DIRECTION_UP, DIRECTION_DOWN]), vscroll_stripe_size:int=_VSCROLL_STRIPE_SIZE2, hscroll_stripe_size:int=0):
        self.width:int = width
        self.height:int = height
        self.color_format:int = color_format
        self.max_dimension:int = width
        self.min_dimension:int = height

        if height > width:
            self.max_dimension = height
            self.min_dimension = width


        if width > _MAX_SCREEN_WIDTH:
            raise Exception("The screen is too wide to handle, currently not more than "+str(_MAX_SCREEN_WIDTH)+" is allowed")
        if height > _MAX_SCREEN_WIDTH:
            raise Exception("The screen is too wide to handle, currently not more than "+str(_MAX_SCREEN_HEIGHT)+" is allowed")

        self.tiled_height:int = height>>_TILE_SIZE_DIV
        self.tiled_width:int = width>>_TILE_SIZE_DIV


        if vscroll_stripe_size < 0:
            raise Exception("vscroll_stripe_size must not be negative")
        if vscroll_stripe_size < _VSCROLL_STRIPE_SIZE2:
            if DIRECTION_UP in scroll_directions or DIRECTION_DOWN in scroll_directions:
                raise Exception("Vertical Scrolling area is too small to implement scrolling, must specify allowed scrolling directions to not include UP or DOWN")

        scroll_directions = frozenset(scroll_directions)
        for scd in scroll_directions:
            if scd == DIRECTION_UP:
                continue
            if scd == DIRECTION_DOWN:
                continue
            raise Exception("Unsupported Scroll Direction used")

        if hscroll_stripe_size != 0:
            raise Exception("Horizontal Scrolling is not supported, so hscroll_stripe_size must be zero")

        self.scroll_directions:frozenset[int] = scroll_directions




class DisplayProtocol(Protocol):
    spec: DisplaySpec

    def wgl_vscroll(self, pixels:int):
        pass

    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int):
        pass
    # Removed as it is probably not necessary, and that the buffers needed to use would cause more problems
    #def wgl_fill_seq(self, color:int, x:int, y:int, data:memoryview, n:int):
    #    pass

    # The Function
    def wgl_blit(self, image:ImageStream, x:int, y:int):
        pass





_SX_WIDTH = const(0)
_SX_HEIGHT = const(1)
_SX_REMAINING = const(2)


# Image Stream used to wrap another image stream and crop it vertically, by specifiying the new reduced height, and the number of lines skipped at the start
class VerticalCropStream():
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, instream:ImageStream, skip:int, height:int):
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(3*4)))
        self._setup(instream, skip, height)
    def _setup(self, instream:ImageStream, skip:int, height:int):
        self.width:int = instream.width
        if skip < 0:
            raise Exception("Number of skipped lines must not be negative")
        if skip+height > instream.height:
            raise Exception("Cropped height greater than source height")
        self.height:int = height
        self._instream:ImageStream = instream

        self._skip_lines:int = skip

        self._pixels_n:int = self.height*self.width
        self._skip:int = skip*self.width

        self._instream.skip_pixels(self._skip)
        self._extra_state[_SX_REMAINING] = self._pixels_n
        assert(self._instream.get_remaining() >= self._pixels_n)
    def reset(self):
        self._instream.reset()
        self._instream.skip_pixels(self._skip)
        self._extra_state[_SX_REMAINING] = self._pixels_n
        assert(self._instream.get_remaining() >= self._pixels_n)
    def get_remaining(self) -> int:
        return self._extra_state[_SX_REMAINING]
    @micropython.viper
    def skip_pixels(self, n:int):
        state:ptr32 = ptr32(self._extra_state)
        remaining:int = state[_SX_REMAINING]
        if n > remaining:
            n = remaining
        if n <= 0:
            return
        skip_pixels = self._instream.skip_pixels
        skip_pixels(n)
        state[_SX_REMAINING] = remaining - n
    @micropython.viper
    def read_pixels(self, buf, n:int, offset:int) -> int:
        state:ptr32 = ptr32(self._extra_state)
        remaining:int = state[_SX_REMAINING]
        if n > remaining:
            n = remaining
        if n <= 0:
            return 0
        read_pixels = self._instream.read_pixels
        r:int = int(read_pixels(buf, n, offset))
        remaining -= r
        state[_SX_REMAINING] = remaining
        return r
    def info(self) -> str:
        return "VERTICAL_CROP_STREAM("+str(self._skip_lines)+", "+str(self.height)+", "+self._instream.info()+")"


_HCS_SKIP = const(3)
_HCS_REM_IN_L = const(4)


# Image Stream used to wrap another image stream and crop it horizontally, by specifiying the new reduced width, and the number of columns skipped at the start
class HorizontalCropStream():
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, instream:ImageStream, skip:int, width:int):
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(5*4)))
        self._setup(instream, skip, width)
    def _setup(self, instream:ImageStream, skip:int, width:int):
        self.height:int = instream.height
        if skip < 0:
            raise Exception("Number of skipped columns must not be negative")
        if skip+width > instream.width:
            raise Exception("Cropped width greater than source width")
        self.width:int = width
        self._instream:ImageStream = instream
        self._pixels_n:int = self.height*self.width


        # Amount that is skipped at the start of a line
        self._skip_at_start:int = skip

        # Amoung that is skipped between two lines
        self._skip:int = instream.width-width

        # Amount of pixels that are required in the inner stream
        self._instream_required:int = self._pixels_n+self.height*self._skip

        # State for easy access by viper code
        self._extra_state[_SX_WIDTH] = self.width
        self._extra_state[_SX_HEIGHT] = self.height
        self._extra_state[_HCS_SKIP] = self._skip


        self._extra_state[_SX_REMAINING] = self._pixels_n
        self._extra_state[_HCS_REM_IN_L] = self.width
        assert(self._instream.get_remaining() >= self._instream_required)
        self._instream.skip_pixels(self._skip_at_start)
    def get_remaining(self) -> int:
        return self._extra_state[_SX_REMAINING]

    def reset(self):
        self._instream.reset()
        self._extra_state[_SX_REMAINING] = self._pixels_n
        self._extra_state[_HCS_REM_IN_L] = self.width
        assert(self._instream.get_remaining() >= self._instream_required)
        self._instream.skip_pixels(self._skip_at_start)
    @micropython.viper
    def skip_pixels(self, n:int):
        state:ptr32 = ptr32(self._extra_state)
        remaining:int = state[_SX_REMAINING]
        if n > remaining:
            n = remaining
        if n <= 0:
            return

        skip_pixels = self._instream.skip_pixels
        skip_total:int = 0

        WIDTH:int = state[_SX_WIDTH]
        SKIP:int = state[_HCS_SKIP]
        rem_in_l:int = state[_HCS_REM_IN_L]

        while n > 0:
            if n >= rem_in_l:
                skip_total += rem_in_l+SKIP
                n -= rem_in_l
                remaining -= rem_in_l
                rem_in_l = WIDTH
            else:
                skip_total += n
                rem_in_l -= n
                remaining -= n
                n = 0
        skip_pixels(skip_total)
        state[_SX_REMAINING] = remaining
        state[_HCS_REM_IN_L] = rem_in_l
    @micropython.viper
    def read_pixels(self, buf, n:int, offset:int) -> int:
        state:ptr32 = ptr32(self._extra_state)

        remaining:int = state[_SX_REMAINING]
        if n > remaining:
            n = remaining
        if n <= 0:
            return 0

        skip_pixels = self._instream.skip_pixels
        read_pixels = self._instream.read_pixels

        WIDTH:int = state[_SX_WIDTH]
        SKIP:int = state[_HCS_SKIP]
        rem_in_l:int = state[_HCS_REM_IN_L]

        read_bytes:int = 0
        while n > 0:
            if n >= rem_in_l:
                r = int(read_pixels(buf, rem_in_l, offset+read_bytes))
                read_bytes += r
                n -= rem_in_l
                skip_pixels(SKIP)
                remaining -= rem_in_l
                rem_in_l = WIDTH
            else:
                r = int(read_pixels(buf, n, offset+read_bytes))
                read_bytes += r
                rem_in_l -= n
                remaining -= n
                n = 0
        state[_SX_REMAINING] = remaining
        state[_HCS_REM_IN_L] = rem_in_l
        return read_bytes
    def info(self) -> str:
        return "HORIZONTAL_CROP_STREAM("+str(self._skip_at_start)+", "+str(self.width)+", "+self._instream.info()+")"


_DEFAULT_TEXT_FGCOLOR:int = const(0xFFFF)
_PALETTE2_INITALIZER = [0, _DEFAULT_TEXT_FGCOLOR]


_MIS_CBYTE = const(3)
_MIS_INDEX = const(4)
_MIS_REM_IN_L = const(5)
_MIS_REM_IN_B = const(6)


# Streamer for reading a memoryview (1 byte per element) as an uncompressed image, with one bit per pixel
class MonoImageStream():
    _16BIT_UNSIGNED_INT = _array_get_int_type(16, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, screen_color_format:int, raw_data:memoryview, width:int, height:int):
        self._color_format:int = screen_color_format
        self._palette:memoryview = memoryview(array(self._16BIT_UNSIGNED_INT, _PALETTE2_INITALIZER))
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(7*4)))
        self._setup(raw_data, width, height)
    def _setup(self, raw_data:memoryview, width:int, height:int):
        if width <= 0 or height <= 0:
            raise Exception("Image must have a positive size greater than 0")

        self._raw_data:memoryview = raw_data
        self.width:int = width
        self.height:int = height
        self._n_pixels:int = width*height

        # Width
        self._extra_state[_SX_WIDTH] = self.width
        # Height
        self._extra_state[_SX_HEIGHT] = self.height


        #Remaining
        self._extra_state[_SX_REMAINING] = self._n_pixels
        #cbyte
        self._extra_state[_MIS_CBYTE] = self._raw_data[0]
        #index
        self._extra_state[_MIS_INDEX] = 0
        # Remaining in line
        self._extra_state[_MIS_REM_IN_L] = self.width
        # Remaining in byte
        self._extra_state[_MIS_REM_IN_B] = 8
        if self._extra_state[_MIS_REM_IN_L] < 8:
            self._extra_state[_MIS_REM_IN_B] = self._extra_state[_MIS_REM_IN_L]

    def get_remaining(self) -> int:
        return self._extra_state[_SX_REMAINING]

    def set_color(self, n:int, color:int):
        if n < 0 or n > 1:
            raise Exception("Invalid Palette Index")
        if n < 0:
            raise Exception("Negative Color given")
        color &= 0xFFFF
        cf:int = self._color_format
        if cf == COLORFORMAT_RGB565:
            self._palette[n] = color
        elif cf == COLORFORMAT_RGB565_R:
            color2:int = (color>>8)&0xFF
            color = (color<<8)&0xFF00
            self._palette[n] = color | color2
        else:
            raise Exception("Unknown Color format specified")


    def reset(self):
        # Set State required for reading the image

        #Remaining
        self._extra_state[_SX_REMAINING] = self._n_pixels
        #cbyte
        self._extra_state[2] = self._raw_data[0]
        #index
        self._extra_state[3] = 0
        # Remaining in line
        self._extra_state[4] = self.width
        # Remaining in byte
        self._extra_state[5] = 8
        if self._extra_state[4] < 8:
            self._extra_state[5] = self._extra_state[2]

    @micropython.viper
    def skip_pixels(self, n:int):
        state:ptr32 = ptr32(self._extra_state)

        remaining:int = state[_SX_REMAINING]
        if n > remaining:
            n = remaining
        if n <= 0:
            return


        raw_data:ptr8 = ptr8(self._raw_data)

        WIDTH:int = state[_SX_WIDTH]
        cbyte:int = state[_MIS_CBYTE]
        index:int = state[_MIS_INDEX]
        rem_in_b:int = state[_MIS_REM_IN_B]
        rem_in_l:int = state[_MIS_REM_IN_L]

        n2:int = n
        while n2 > 0:
            n2 -= 1

            cbyte >>= 1
            rem_in_b -= 1
            rem_in_l -= 1
            remaining -= 1
            if remaining <= 0:
                break
            if rem_in_b == 0:
                rem_in_b = 8
                if rem_in_l == 0:
                    rem_in_l = WIDTH
                elif rem_in_l < 8:
                    rem_in_b = rem_in_l
                index += 1
                cbyte = raw_data[index]
        state[_SX_REMAINING] = remaining
        state[_MIS_CBYTE] = cbyte
        state[_MIS_INDEX] = index
        state[_MIS_REM_IN_B] = rem_in_b
        state[_MIS_REM_IN_L] = rem_in_l

    @micropython.viper
    def read_pixels(self, buf, n:int, offset:int) -> int:
        state:ptr32 = ptr32(self._extra_state)

        buf2:ptr8 = ptr8(buf)
        remaining:int = state[_SX_REMAINING]
        if n >= remaining:
            n = remaining
        if n <= 0:
            return 0
        # Offset is in pixels, but offset is required in bytes
        offset = (offset<<1)


        palette:ptr16 = ptr16(self._palette)
        raw_data:ptr8 = ptr8(self._raw_data)

        WIDTH:int = state[_SX_WIDTH]
        cbyte:int = state[_MIS_CBYTE]
        index:int = state[_MIS_INDEX]
        rem_in_b:int = state[_MIS_REM_IN_B]
        rem_in_l:int = state[_MIS_REM_IN_L]

        n2:int = n
        while n2 > 0:
            n2 -= 1

            color:int = palette[cbyte&1]
            buf2[offset] = color&0xFF
            buf2[offset+1] = (color>>8)&0xFF
            offset += 2

            cbyte >>= 1
            rem_in_b -= 1
            rem_in_l -= 1
            remaining -= 1
            if remaining <= 0:
                break
            if rem_in_b == 0:
                rem_in_b = 8
                if rem_in_l == 0:
                    rem_in_l = WIDTH
                elif rem_in_l < 8:
                    rem_in_b = rem_in_l
                index += 1
                cbyte = raw_data[index]
        state[_SX_REMAINING] = remaining
        state[_MIS_CBYTE] = cbyte
        state[_MIS_INDEX] = index
        state[_MIS_REM_IN_B] = rem_in_b
        state[_MIS_REM_IN_L] = rem_in_l
        return n






# The Draw Function of a component takes a Component as parameter and a WatchGraphics instance
def _draw_function_sample(com:'Component', wg:'WatchGraphics'):
    return None

class Component():
    def __init__(self, x:int, y:int, width:int, height:int, draw_function):
        if (x < 0 or x&_TILE_SIZE_MOD_MASK != 0 or
          y < 0 or y&_TILE_SIZE_MOD_MASK != 0 or
          width <= 0 or width&_TILE_SIZE_MOD_MASK != 0 or
          height <= 0 or height&_TILE_SIZE_MOD_MASK != 0):
            raise Exception("Invalid Sizing or Positioning of Component, Components Size and Position must be aligned to "+str(TILE_SIZE)+", Position must not be negative and Size must be greater than 0")

        self.x:int = x
        self.y:int = y
        self.width:int = width
        self.height:int = height


        self.draw = draw_function
        self._state:dict[str, object] = {}
        self.dirty:bool = True
        self._screen:"Screen" = _DUMMY_SCREEN
        self._cid:int = 0
    def init_vars(self, state:dict[str, object]):
        self._state = state
        if not self.dirty:
            self._screen.notify_component_update(self._cid)
            self.dirty = True
    def get_var_dict(self) -> dict[str, object]:
        return self._state
    def get_var(self, k:str) -> object:
        return self._state[k]
    def set_var(self, k:str, v:object):
        if k in self._state and self._state[k] == v:
            return
        self._state[k] = v
        if not self.dirty:
            self._screen.notify_component_update(self._cid)
            self.dirty = True
    def set_var_q(self, k:str, v:object):
        self._state[k] = v


_SC_WIDTH = const(0)
_SC_HEIGHT = const(1)
_SC_THEIGHT = const(2)

class Screen():
    _8BIT_UNSIGNED_INT = _array_get_int_type(8, unsigned=True)
    _16BIT_UNSIGNED_INT = _array_get_int_type(16, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)


    _CREATION_OVERLAP_BITMASK:memoryview = memoryview(array(_16BIT_UNSIGNED_INT, bytearray(_MAX_TILES_PER_DIM*4)))
    def __init__(self, bgcolor:int, display_spec:DisplaySpec, components:list['Component']):
        if len(components) > 127:
            raise Exception("Too many components")
        self.bgcolor:int = bgcolor

        self.display_spec:DisplaySpec = display_spec


        tiled_height:int = display_spec.width>>_TILE_SIZE_DIV
        tiled_width:int = display_spec.height>>_TILE_SIZE_DIV
        self.tiled_height = tiled_height

        self._screen_info:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(3*4)))
        self._screen_info[_SC_WIDTH] = display_spec.width
        self._screen_info[_SC_HEIGHT] = display_spec.height
        self._screen_info[_SC_THEIGHT] = tiled_height

        assert(tiled_height <= _MAX_TILES_PER_DIM and tiled_width <= _MAX_TILES_PER_DIM)

        com_map_y:list[list[int]] = []

        # The bitfield is used to detect overlaps in components
        # Each array index is a row and each bit says wether that column is occupied by a component
        bitfield:memoryview = self._CREATION_OVERLAP_BITMASK
        for i in range(tiled_height):
            bitfield[i] = 0
            com_map_y.append([])


        ncomponents:list['Component'] = []
        cid:int = 1
        for c in components:
            # Get y range occupied by tile
            cy0:int = (c.y)>>_TILE_SIZE_DIV
            cy1:int = cy0+(c.height>>_TILE_SIZE_DIV)

            # Get x range occupied by tile
            cx0:int = (c.x)>>_TILE_SIZE_DIV
            cx1:int = cx0+(c.width>>_TILE_SIZE_DIV)

            if cy1 > tiled_height or cx1 > tiled_width:
                raise Exception("Component goes out of screen bounds")

            # Check and set flags in bitfield wether a given position is already occupied by another component
            for cyp in range(cy0, cy1):
                com_map_y[cyp].append(cid)
                value = bitfield[cyp]
                for i in range(cx0, cx1):
                    if (value>>i)&1:
                        raise Exception("Overlapping components detected")
                    bitfield[cyp] |= 1<<i

            # Register this screen to the component so that it nows its id and has a reference to the screen
            c._screen = self
            c._cid = cid

            ncomponents.append(c)
            cid = cid+1


        map_empty_row:memoryview = memoryview(array(self._8BIT_UNSIGNED_INT, [0]))
        last_used_memoryview:memoryview = map_empty_row
        last_used_list:list[int] = [0]

        com_map_y2:list[memoryview] = []
        for r in com_map_y:
            r.append(0)
            if len(r) == 1:
                com_map_y2.append(map_empty_row)
            elif r == last_used_list:
                com_map_y2.append(last_used_memoryview)
            else:
                last_used_list = r
                last_used_memoryview = memoryview(array(self._8BIT_UNSIGNED_INT, r))
                com_map_y2.append(last_used_memoryview)
        self.com_map_y:list[memoryview] = com_map_y2


        self.components:list['Component'] = ncomponents
        self.update_array = memoryview(array(self._16BIT_UNSIGNED_INT, bytearray(9*2)))
    @micropython.viper
    def notify_component_update(self, cid:int):
        update_array:ptr16 = ptr16(self.update_array)

        byti:int = 1+(cid>>4)
        biti:int = cid&0xf

        update_array[0] |= 1<<byti
        update_array[byti] |= 1<<biti


    @micropython.viper
    def draw_lazy(self, wg):
        update_array:ptr16 = ptr16(self.update_array)
        set_com_context = wg._set_component_context
        builtin_false = builtins.bool(False)

        # Use Pointers to set value
        update_bitfield:int = update_array[0]
        if update_bitfield == 0:
            return
        update_bitfield >>= 1
        id_block_off:int = -16
        byti:int = 0
        while byti < (8+1):
            id_block_off += 16
            id_block_used:int = update_bitfield&1
            byti += 1
            update_bitfield >>= 1

            if not id_block_used:
                if update_bitfield == 0:
                    break
                continue

            value:int = update_array[byti]&0xFFFF
            update_array[byti] = 0

            id_sub:int = 0
            while id_sub < 16:
                id_sub += 1

                id_used = value&1
                value >>= 1
                if not id_used:
                    if value == 0:
                        break
                    continue
                cid = id_block_off+id_sub
                com = self.components[cid]
                set_com_context(com.x, com.y, com.width, com.height, 0)
                com_draw = com.draw
                com_draw(com, wg)
                com.dirty = builtin_false
        update_array[0] = 0


    @micropython.viper
    def draw_full(self, wg):
        update_array:ptr16 = ptr16(self.update_array)
        set_com_context = wg._set_component_context

        n2:int = 0
        while n2 < 9:
            update_array[n2] = 0
        builtin_false = builtins.bool(False)
        for com in self.components:
            set_com_context(com.x, com.y, com.width, com.height, 0)
            com_draw = com.draw
            com_draw(com, wg)
            com.dirty = builtin_false

    @micropython.viper
    def draw_scroll(self, wg, scroll_direction:int):
        if scroll_direction != DIRECTION_UP and scroll_direction != DIRECTION_DOWN:
            raise Exception("Invalid Direction given")
        window_info:ptr32 = ptr32(self._screen_info)
        height:int = window_info[_SC_HEIGHT]
        tiled_height:int = window_info[_SC_THEIGHT]






class _LegacyFontWrapper():
    def __init__(self, font_data, color_format:int):
        (px, h, w) = font_data.get_ch('T')
        self._bitblit:MonoImageStream = MonoImageStream(color_format, px, h, w)
        self._setup(font_data)
    def _setup(self, font_data):
        self._fgcolor:int = _DEFAULT_TEXT_FGCOLOR
        self._bitblit.set_color(0, _DEFAULT_TEXT_FGCOLOR)

        self.height:int = int(font_data.height())
        self.max_width:int = int(font_data.max_width())
        self.baseline:int = int(font_data.baseline())
        self.hmap:bool = bool(font_data.hmap())
        self.reverse:bool = bool(font_data.reverse())
        self.monospaced:bool = bool(font_data.monospaced())
        self.min_ch:int = int(font_data.min_ch())
        self.max_ch:int = int(font_data.max_ch())
        self._raw_data = font_data
    def set_bgcolor(self, color:int):
        self._bitblit.set_color(0, color)
    def set_fgcolor(self, color:int):
        if self._fgcolor != color:
            self._bitblit.set_color(1, color)
            self._fgcolor = color
    def get_ch(self, ch:str) -> MonoImageStream:
        (px, h, w) = self._raw_data.get_ch(ch)
        bitblit:MonoImageStream = self._bitblit
        bitblit._setup(px, w, h)
        return bitblit





_WGWI_WIDTH = const(0)
_WGWI_HEIGHT = const(1)
_WGWI_XPOS = const(2)
_WGWI_YPOS = const(3)
_WGWI_YSHIFT = const(4)

_DEFAULT_BGCOLOR = const(0)

_C_TO_RADIANS:float = (math.pi / 180)
class WatchGraphics():
    _BIT_UNSIGNED_INT = _array_get_int_type(8, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)

    def __init__(self, display:DisplayProtocol, gc_collect:bool=True):
        self.display:DisplayProtocol = display

        self._font:_LegacyFontWrapper = _LegacyFontWrapper(fallback_font, display.spec.color_format)

        self.bgcolor:int = _DEFAULT_BGCOLOR
        self._text_bgcolor:int = _DEFAULT_BGCOLOR
        self._text_bgcolor_modified:bool = True

        self.scroll_direction:int = DIRECTION_UP

        self.width:int = self.display.spec.width
        self.height:int = self.display.spec.height

        self._window_info:memoryview = memoryview(array(self._32BIT_SIGNED_INT, bytearray(5*4)))

        # Setup window info
        self._window_info[_WGWI_WIDTH] = self.width
        self._window_info[_WGWI_HEIGHT] = self.height
        self._window_info[_WGWI_XPOS] = 0
        self._window_info[_WGWI_YPOS] = 0
        self._window_info[_WGWI_YSHIFT] = 0


        # Init Crop Streamers used for Blitting images that dont fit in their components
        self._crop_v_stream:VerticalCropStream = VerticalCropStream(DummyImageStream(1, 1), 0, 1)
        self._crop_h_stream:HorizontalCropStream = HorizontalCropStream(DummyImageStream(1, 1), 0, 1)

        # Call garbage collection to clean up potential temporary allocated objects
        if gc_collect:
            _gc_collect()

    def _set_screen_context(self, bgcolor:int):
        self.bgcolor = bgcolor
        self._set_component_context(0, 0, self.display.spec.width, self.display.spec.height, 0)

    def _set_component_context(self, x:int, y:int, width:int, height:int, shift_y:int):
        self.width = width
        self.height = height
        bgcolor:int = self.bgcolor
        if self._text_bgcolor != bgcolor or self._text_bgcolor_modified:
            self._text_bgcolor = bgcolor
            self._text_bgcolor_modified = False
            self._font.set_bgcolor(bgcolor)

        # Setup window info
        self._window_info[_WGWI_WIDTH] = self.width
        self._window_info[_WGWI_HEIGHT] = self.height
        self._window_info[_WGWI_XPOS] = x
        self._window_info[_WGWI_YPOS] = y
        self._window_info[_WGWI_YSHIFT] = shift_y







    # Set the background color of text, will be reset to the background color after switching components
    def set_text_bgcolor(self, bgcolor:int):
        old_tbgcolor:int = self._text_bgcolor
        if old_tbgcolor != bgcolor:
            self._text_bgcolor = bgcolor
            self._text_bgcolor_modified = True
            self._font.set_bgcolor(bgcolor)

    # Bit image to the screen at position, will automatically be cropped if it goes out of bounds
    @micropython.viper
    def blit(self, image, x:int, y:int):
        window_info:ptr32 = ptr32(self._window_info)

        y += window_info[_WGWI_YSHIFT]
        window_width:int = window_info[_WGWI_WIDTH]
        window_height:int = window_info[_WGWI_HEIGHT]

        width:int = int(image.width)
        height:int = int(image.height)
        skip_lines:int = 0
        if y < 0:
            skip_lines -= y
        reduce_by_lines:int = skip_lines
        if y+height > window_height:
            reduce_by_lines += (y+height)-window_height

        skip_cols:int = 0
        if x < 0:
            skip_cols -= x
        reduce_by_cols:int = skip_cols
        if x+width > window_width:
            reduce_by_cols += (x+width)-window_width

        if reduce_by_lines == 0 and reduce_by_cols == 0:
            self.display.wgl_blit(image, x, y)
            return

        if reduce_by_lines > 0:
            height -= reduce_by_lines
            if height <= 0:
                return
            croppedy:VerticalCropStream = self._crop_v_stream
            croppedy._setup(image, skip_lines, height)
            image = croppedy
            y += skip_lines

        if reduce_by_cols > 0:
            width -= reduce_by_cols
            if width <= 0:
                return
            croppedx:HorizontalCropStream = self._crop_h_stream
            croppedx._setup(image, skip_cols, width)
            image = croppedx
            x += skip_cols

        self.display.wgl_blit(image, window_info[_WGWI_XPOS]+x, window_info[_WGWI_YPOS]+y)
        image.reset()


    # Fill an area on the screen, will automatically be cropped to not leave the specified component
    @micropython.viper
    def fill(self, color:int, x:int, y:int, width:int, height:int):
        window_info:ptr32 = ptr32(self._window_info)

        y += window_info[_WGWI_YSHIFT]
        window_height:int = window_info[_WGWI_HEIGHT]
        window_width:int = window_info[_WGWI_WIDTH]
        if y < 0:
            height += y
            y = 0
        if x < 0:
            width += x
            x = 0
        max_y:int = y+height-1
        max_x:int = x+width-1
        if max_x >= window_width:
            width += (window_width-1)-max_x
        if max_y >= window_height:
            height += (window_height-1)-max_y
        if width <= 0 or height <= 0:
            return
        self.display.wgl_fill(color, window_info[_WGWI_XPOS]+x, window_info[_WGWI_YPOS]+y, width, height)


    # Draw a line, with a given thickness and color, between the start and endpoints,
    # Special cases like perfetly orthogonal lines are handled seperately
    # Other Lines are drawn using bresenhams line algorithm
    # with the difference that multiple oeprations to draw a single pixel are coalesced
    # into bigger operations to draw orthogonal lines.
    @micropython.viper
    def draw_line(self, color:int, width:int, x0:int, y0:int, x1:int, y1:int):
        # Line Thickness offset
        ltoff:int = (width-1)//2

        # Correct using line thickness offset
        x0 -= ltoff
        y0 -= ltoff
        x1 -= ltoff
        y1 -= ltoff

        dx:int = int(abs(x1 - x0))
        dy:int = int(-abs(y1 - y0))
        mdy:int = 0-dy

        # Check if line ends where it starts
        if dx == 0 and dy == 0:
            self.fill(color, x0, y0, width, width)
            return
        # Line doesnt span vertically, meaning its horizontal so it can be drawn using a single fill operation
        elif dy == 0:
            if x0 > x1:
                x2 = x0
                x0 = x1
                x1 = x2
            self.fill(color, x0, y0, dx+width, width)
            return
        # Line doesnt span horizontally, meaning its vertical, so it can be drawn with a single fill operation
        elif dx == 0:
            if y0 > y1:
                y2 = y0
                y0 = y1
                y1 = y2
            self.fill(color, x0, y0, width, mdy+width)
            return


        window_info:ptr32 = ptr32(self._window_info)

        # Shift content by y, do not shift before, else it would be shifted twice, when using simple fill operations
        yshift:int = window_info[_WGWI_YSHIFT]
        y0 += yshift
        y1 += yshift



        # Direction to move, x0-x1 cant be zero, same for y0-y1
        sx:int = 1 if (x0 < x1) else -1
        sy:int = 1 if (y0 < y1) else -1


        dx_x2:int = dx<<1
        dy_x2:int = dy<<1


        fill_x:int = -1
        fill_y:int = -1
        fill_w:int = -1
        fill_h:int = -1

        error:int = dx_x2+dy_x2
        window_width:int = window_info[_WGWI_WIDTH]
        window_height:int = window_info[_WGWI_HEIGHT]

        wgl_fill = self.display.wgl_fill


        wxpos:int = window_info[_WGWI_XPOS]
        wypos:int = window_info[_WGWI_YPOS]

        while True:
            # Cropping the current point so it doesnt overdraw
            rx0:int = x0
            ry0:int = y0

            rwidth:int = width
            rheight:int = width

            if rx0 < 0:
                rwidth += rx0
                rx0 = 0
            if ry0 < 0:
                rheight += ry0
                ry0 = 0

            max_width:int = window_width-rx0
            max_height:int = window_height-ry0

            if rwidth > max_width:
                rwidth += max_width-rwidth
            if rheight > max_height:
                rheight += max_height-rheight

            # Check how much the x and y coordinates differ from the current fill operation
            # Note: Since y/rx0 are guaranteed to be zero or greater, x_offset and y_offset cant be 0 if fill_x is -1
            x_offset:int = rx0-fill_x
            y_offset:int = ry0-fill_y

            if rwidth <= 0 or rheight <= 0:
                if fill_x != -1:
                    wgl_fill(color, wxpos+fill_x, wypos+fill_y, fill_w, fill_h)
                    fill_x = -1
                    fill_y = -1
            elif y_offset == 0 and x_offset == 0:
                if rheight > fill_h:
                    fill_h = rheight
                if rwidth > fill_w:
                    fill_w = rwidth
            elif y_offset == 0 and rheight == fill_h:
                if x_offset < 0:
                    fill_x += x_offset
                    fill_w -= x_offset
                else:
                    fill_w += x_offset
            elif x_offset == 0 and rwidth == fill_w:
                if y_offset < 0:
                    fill_y += y_offset
                    fill_h -= y_offset
                else:
                    fill_h += y_offset
            else:
                if fill_x != -1:
                    wgl_fill(color, wxpos+fill_x, wypos+fill_y, fill_w, fill_h)
                fill_x = rx0
                fill_y = ry0
                fill_w = rwidth
                fill_h = rheight

            error_change:int = 0
            if error >= dy:
                if x0 == x1:
                    break
                error_change += dy_x2
                x0 += sx
            if error <= dx:
                if y0 == y1:
                    break
                error_change += dx_x2
                y0 += sy
            error += error_change
        if fill_x != -1:
            wgl_fill(color, wxpos+fill_x, wypos+fill_y, fill_w, fill_h)


    # Draw a line using polar coordinates
    @micropython.native
    def draw_line_polar(self, color:int, x:int, y:int, theta:int, r0:int, r1:int, width:int):
        theta2:float = theta*_C_TO_RADIANS
        xdelta:float = math.sin(theta2)
        ydelta:float = math.cos(theta2)
        x0:int = x + int(xdelta * r0)
        x1:int = x + int(xdelta * r1)
        y0:int = x - int(ydelta * r0)
        y1:int = x - int(ydelta * r1)
        self.draw_line(x0, y0, x1, y1, width, color)


    # Get bounding box of a string drawn on the screen
    @micropython.native
    def string_bounding_box(self, s:str) -> tuple[int, int]:
        font:_LegacyFontWrapper = self._font
        height:int = font.height
        width:int = 0
        for c in s:
            cpx = font.get_ch(c)
            cw2:int = int(cpx.width)
            ch2:int = int(cpx.height)
            width += cw2
            if ch2 > height:
                height = ch2
        return (width, height)



    # Draw string to the screen at position, sadly cant be viper as it doesnt
    @micropython.native
    def draw_string(self, color:int, s:str, x:int, y:int):
        window_width:int = self.width
        window_height:int = self.height
        font:_LegacyFontWrapper = self._font
        font.set_fgcolor(color)
        font_height = font.height

        if y >= window_height:
            return
        if x >= window_width:
            return
        if y+font_height <= 0:
            return

        for c in s:
            cpx = font.get_ch(c)
            cw:int = int(cpx.width)
            ch:int = int(cpx.height)
            if x+cw <= 0:
                x += cw
                continue
            if x >= window_width:
                break
            self.blit(cpx, x, y)

    def draw_string_a(self, color:int, s:str, x:int, y:int, align:int):
        (rw, rh) = self.string_bounding_box(s)
        rwidth:int = int(rw)
        if align == ALIGNMENT_CENTER:
            offset:int = (rwidth>>1)
            self.draw_string(color, s, x-offset, y)
        elif align == ALIGNMENT_LEFT:
            self.draw_string(color, s, x, y)
        elif align == ALIGNMENT_RIGHT:
            self.draw_string(color, s, x-rwidth, y)
        else:
            raise Exception("Shouldnt Happen")





_DUMMY_SCREEN:Screen = Screen(0, DisplaySpec(0, 0, COLORFORMAT_RGB565, scroll_directions=frozenset([])), [])
class DummyDisplay(DisplayProtocol):
    def __init__(self, width:int, height:int, color_format:int=COLORFORMAT_RGB565):
        self.spec = DisplaySpec(width, height, color_format, scroll_directions=frozenset([]))
    def wgl_vscroll(self, pixels:int):
        pass
    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int):
        print("FILL "+hex(color)+", X:"+str(x)+", Y:"+str(y)+", W:"+str(width)+", H:"+str(height))
    def wgl_blit(self, image:ImageStream, x:int, y:int):
        print("BLIT IMAGE:    X:"+str(x)+", Y:"+str(y)+", W:"+str(image.width)+", H:"+str(image.height))
        print("  "+image.info())
class DummyImageStream():
    def __init__(self, width:int, height:int):
        self.width:int = width
        self.height:int = height
        self._remaining:int = self.width*self.height
    def get_remaining(self) -> int:
        return self._remaining
    def reset(self):
         self._remaining = self.width*self.height
    def skip_pixels(self, n:int):
        if n > self._remaining:
            n = self._remaining
        if n <= 0:
            return
        self._remaining -= n
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        if n > self._remaining:
            n = self._remaining
        if n <= 0:
            return 0
        self._remaining -= n
        return n
    def info(self) -> str:
        return "DUMMY_STREAM("+str(self.width)+", "+str(self.height)+")"




if __name__ == '__main__':
    dis = DummyDisplay(240, 240)
    dg = WatchGraphics(dis)
    print("Draw Line 1")
    dg.draw_line(0, 1,  0, 1,  0, 1)
    print("Draw Line 2")
    dg.draw_line(0, 1,  0, 1,  6, 4)
    print("Draw Line 3")
    dg.draw_line(0, 3,  -1, -1,  6, 4)
    print("Done")

    img = DummyImageStream(240, 240)
    img2 = DummyImageStream(10, 10)

    dg.blit(img, 10, 10)
    dg.blit(img2, 10, 10)
    dg.blit(img2, 239, 239)
