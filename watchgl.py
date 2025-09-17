#!/usr/bin/env python3
from array import array
import math
import builtins

try:
    from micropython import const       # type: ignore[import-not-found]
    import micropython                  # type: ignore[import-not-found]
except ImportError:
    print("Using Micropython Faker Library")
    from micropython_faker import const
    import micropython_faker as micropython

try:
    from typing import Protocol
except ImportError:
    Protocol = object           # type: ignore[assignment]

try:
    ptr8(b'\x00')               # type: ignore[used-before-def]
except NameError:
    ptr8 = memoryview
except Exception:
    pass

try:
    ptr16(b'\x00')              # type: ignore[used-before-def]
except NameError:
    ptr16 = memoryview
except Exception:
    pass

try:
    ptr32(b'\x00')              # type: ignore[used-before-def]
except NameError:
    ptr32 = memoryview
except Exception:
    pass




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






BGCOLOR_TRANSPARENT = -1


# Enum
class ColorFormat():
    RGB565 = 128
    RGB565_R = 129

# Enum
class GraphicsState():
    Initial = 1
    Update = 2
    Forced = 3
    Scrolling = 4
    ScrollingFinal = 5

# Enum
class Direction():
    Up = 0
    Down = 1
    Left = 2
    Right = 3

# Enum
class Alignment():
    CENTER = 0
    LEFT = 1
    RIGHT = 2



class DisplaySpec():
    def __init__(self, width:int, height:int, color_format:int):
        self.width:int = width
        self.height:int = height
        self.color_format:int = color_format
        self.max_dimension:int = width
        self.min_dimension:int = height
        if height > width:
            self.max_dimension = height
            self.min_dimension = width

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
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        return -1
    def get_remaining(self) -> int:
        return -1
    def info(self) -> str:
        return ""




class DisplayProtocol(Protocol):
    spec: DisplaySpec

    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int):
        pass
    def wgl_fill_seq(self, color:int, x:int, y:int, data:memoryview, n:int):
        pass
    def wgl_blit(self, image:ImageStream, x:int, y:int):
        pass





_STREAM_XS_INIT4 = [0, 0, 0, 0]
_STREAM_XS_INIT8 = [0, 0, 0, 0, 0, 0, 0, 0]
_SX_WIDTH = const(0)
_SX_HEIGHT = const(1)
_SX_REMAINING = const(2)


class VerticalCropStream():
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, instream:ImageStream, skip:int, height:int):
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, _STREAM_XS_INIT4))
        self._setup(instream, skip, height)
    def _setup(self, instream:ImageStream, skip:int, height:int):
        self.width:int = instream.width
        if height > instream.height:
            raise Exception("Cropped height greater than source height")
        if skip+height > instream.height:
            height = height-(skip+height-instream.height)
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


class HorizontalCropStream():
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, instream:ImageStream, skip:int, width:int):
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, _STREAM_XS_INIT8))
        self._setup(instream, skip, width)
    def _setup(self, instream:ImageStream, skip:int, width:int):
        self.height:int = instream.height
        if width > instream.width:
            raise Exception("Cropped width greater than source width")
        if skip+width > instream.width:
            width = width-(skip+width-instream.width)
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

class StripedStream():
    def __init__(self, instream:ImageStream, lines:int):
        self._lines_per_stripe:int = lines
        self._instream:ImageStream = instream

        self.width:int = self._instream.width
        self.height:int = 0
        self._pixels_n:int = self.width*self._lines_per_stripe

        self._stripe_start = 0

        if (self._stripe_start + self._lines_per_stripe) > self._instream.height:
            self.height = (self._stripe_start + self._lines_per_stripe) - self._instream.height
            self._remaining = self.width*self.height
        else:
            self.height = self._lines_per_stripe
            self._remaining = self._pixels_n
        assert(self._instream.get_remaining() >= self._remaining)
    def get_remaining(self) -> int:
        return self._remaining
    def reset(self):
        self._stripe_start += self._lines_per_stripe
        if self._stripe_start >= self._instream.height:
            self._instream.reset()
            self._stripe_start = 0
            self.height = 0
        if (self._stripe_start + self._lines_per_stripe) > self._instream.height:
            self.height = (self._stripe_start + self._lines_per_stripe) - self._instream.height
            self._remaining = self.width*self.height
        else:
            self.height = self._lines_per_stripe
            self._remaining = self._pixels_n
        assert(self._instream.get_remaining() >= self._remaining)
    def skip_pixels(self, n:int):
        remaining:int = self._remaining
        if n > remaining:
            n = remaining
        if n <= 0:
            return
        skip_pixels = self._instream.skip_pixels
        skip_pixels(n)
        remaining -= n
        self._remaining = remaining
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        remaining:int = self._remaining
        if n > remaining:
            n = remaining
        if n <= 0:
            return 0
        read_pixels = self._instream.read_pixels
        r = read_pixels(buf, n, offset)
        remaining -= r
        self._remaining = remaining
        return r
    def info(self) -> str:
        return "STRIPED_STREAM("+str(self.height)+", "+self._instream.info()+")"




_PALETTE2_INITALIZER = [0, 0xFFFF]


_MIS_CBYTE = const(3)
_MIS_INDEX = const(4)
_MIS_REM_IN_L = const(5)
_MIS_REM_IN_B = const(6)


class MonoImageStream():
    _16BIT_UNSIGNED_INT = _array_get_int_type(16, unsigned=True)
    _32BIT_SIGNED_INT = _array_get_int_type(32, unsigned=False)
    def __init__(self, screen_color_format:int, raw_data:memoryview, width:int, height:int):
        self._color_format:int = screen_color_format
        self._palette:memoryview = memoryview(array(self._16BIT_UNSIGNED_INT, _PALETTE2_INITALIZER))
        self._extra_state:memoryview = memoryview(array(self._32BIT_SIGNED_INT, _STREAM_XS_INIT8))
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
        if cf == ColorFormat.RGB565:
            self._palette[n] = color
        elif cf == ColorFormat.RGB565_R:
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

        for _ in range(n):
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

        for _ in range(n):
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
        self.x:int = x
        self.y:int = y
        self.width:int = width
        self.height:int = height

        self.weight:int = self.width*self.height

        self.draw = draw_function
        self._state:dict[str, object] = {}
        self.dirty:bool = True
        self._screen:"Screen" = _DUMMY_SCREEN
        self._cid:int = 0
    def register(self, screen:"Screen", cid:int):
        self._screen = screen
        self._cid = cid
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


class Screen():
    def __init__(self, bgcolor:int, display_spec:DisplaySpec, components:list['Component']):
        ncomponents:list['Component'] = []
        if len(components) > 127:
            raise Exception("Too many components")
        cid:int = 1
        self.bgcolor:int = bgcolor

        self.display_spec:DisplaySpec = display_spec

        self.bounds_x0:int = -1
        self.bounds_y0:int = -1
        self.bounds_x1:int = -1
        self.bounds_y1:int = -1
        if len(components) > 0:
            self.bounds_x0 = components[0].x
            self.bounds_y0 = components[0].y
            self.bounds_x1 = self.bounds_x0+components[0].width-1
            self.bounds_y1 = self.bounds_y0+components[0].height-1


        for c in components:
            if c.x < self.bounds_x0:
                self.bounds_x0 = c.x
            if c.y < self.bounds_y0:
                self.bounds_y0 = c.y
            cx1 = c.x+c.width-1
            cy1 = c.y+c.height-1
            if cx1 > self.bounds_x1:
                self.bounds_x1 = cx1
            if cy1 > self.bounds_y1:
                self.bounds_y1 = cy1
            
            c.register(self, cid)
            ncomponents.append(c)
            cid = cid+1
        self.components:list['Component'] = ncomponents
        self.update_array = memoryview(bytearray(16))
        for i in range(0,16):
            self.update_array[i] = 0
        self.update_bitfield:int = 0
    @micropython.viper
    def notify_component_update(self, cid:int):
        py_int = builtins.int
        byti:int = cid>>3
        biti:int = cid&0x7
        update_pattern:int = 1<<biti
        byti2:int = int(self.update_array[byti]) | update_pattern
        biti2:int = int(self.update_bitfield) | 1<<byti
        # TODO: Use pointers to set value
        self.update_array[byti] = py_int(byti2)
        self.update_bitfield = py_int(biti2)
    #@micropython.viper
    def draw(self, display):
        py_int = builtins.int
        # Use Pointers to set value
        update_bitfield:int = int(self.update_bitfield)
        if update_bitfield == 0:
            return
        id_block_off:int = -8
        for byti in range(0,16):
            id_block_off += 8
            id_block_used:int = update_bitfield&1
            update_bitfield >>= 1
            if not id_block_used:
                if update_bitfield == 0:
                    break
                continue

            value:int = int(self.update_array[byti])&0xFF
            for id_sub in range(0,8):
                id_used = value&1
                value >>= 1
                if not id_used:
                    if value == 0:
                        break
                    continue
                cid = id_block_off+id_sub
                com = self.components[cid]
                com.draw(com, display)
            self.update_array[byti] = py_int(0)
        self.update_bitfield = py_int(0)








class _LegacyFontWrapper():
    def __init__(self, font_data, bitblit:MonoImageStream):
        self.height:int = int(font_data.height())
        self.max_width:int = int(font_data.max_width())
        self.baseline:int = int(font_data.baseline())
        self.hmap:bool = bool(font_data.hmap())
        self.reverse:bool = bool(font_data.reverse())
        self.monospaced:bool = bool(font_data.monospaced())
        self.min_ch:int = int(font_data.min_ch())
        self.max_ch:int = int(font_data.max_ch())
        self._raw_data = font_data
        self._bitblit:MonoImageStream = bitblit
    def set_bgcolor(self, color:int):
        self._bitblit.set_color(0, color)
    def set_fgcolor(self, color:int):
        self._bitblit.set_color(1, color)
    def get_ch(self, ch:str) -> MonoImageStream:
        (px, h, w) = self._raw_data.get_ch(ch)
        bitblit:MonoImageStream = self._bitblit
        bitblit._setup(px, w, h)
        return bitblit




_C_TO_RADIANS:float = (math.pi / 180)
class WatchGraphics():
    _8BIT_UNSIGNED_INT = _array_get_int_type(8, unsigned=True)

    def __init__(self, display:DisplayProtocol):
        self.display:DisplayProtocol = display

        self._legacy_font_stream:MonoImageStream = MonoImageStream(display.spec.color_format, memoryview(b'\x00'), 8, 1)
        #self._font:_LegacyFontWrapper = _LegacyFontWrapper(default_font, )
        # TODO FIX DEFAULT FONT

        self.bgcolor = 0
        self.graphics_state:int = GraphicsState.Initial
        self.scroll_direction:int = Direction.Up
        self.scroll_stripe_size:int = 20            #FIX # TODO Select better source of value
        self.scroll_y_shift:int = 0

        self.width:int = self.display.spec.width
        self.height:int = self.display.spec.height
        self._window_x:int = 0
        self._window_y:int = 0

        draw_line_buffer:array = array(self._8BIT_UNSIGNED_INT)
        for _ in range(display.spec.min_dimension*4):
            draw_line_buffer.append(0)
        self._draw_line_buffer:memoryview = memoryview(draw_line_buffer)

        self._crop_v_stream:VerticalCropStream = VerticalCropStream(DummyImageStream(1, 1), 0, 1)
        self._crop_h_stream:HorizontalCropStream = HorizontalCropStream(DummyImageStream(1, 1), 0, 1)


    def _set_window(self, x:int, y:int, width:int, height:int, shift_x:int, shift_y:int):
        if shift_x != 0:
            raise Exception("Shifting contents by x is currently not supported")
        self._window_x = x
        self._window_y = y
        self.width = width
        self.height = height
        self.scroll_y_shift = shift_y


    #@micropython.viper
    def blit(self, image, x:int, y:int):
        y += int(self.scroll_y_shift)
        width:int = int(self.width)
        height:int = int(self.height)
        image_width:int = int(image.width)
        image_height:int = int(image.height)
        skip_lines:int = 0
        if y < 0:
            skip_lines -= y
        reduce_by_lines:int = skip_lines
        if y+image_height > height:
            reduce_by_lines += (y+image_height)-height

        skip_cols:int = 0
        if x < 0:
            skip_cols -= x
        reduce_by_cols:int = skip_cols
        if x+image_width > width:
            reduce_by_cols += (x+image_width)-width

        if reduce_by_lines == 0 and reduce_by_cols == 0:
            self.display.wgl_blit(image, x, y)
            return

        if reduce_by_lines > 0:
            new_height:int = image_height-reduce_by_lines
            if new_height <= 0:
                return
            croppedy:VerticalCropStream = self._crop_v_stream
            croppedy._setup(image, skip_lines, new_height)
            image = croppedy
            y += skip_lines

        if reduce_by_cols > 0:
            new_width:int = image_width-reduce_by_cols
            if new_width <= 0:
                return
            croppedx:HorizontalCropStream = self._crop_h_stream
            croppedx._setup(image, skip_cols, new_width)
            image = croppedx
            x += skip_cols

        self.display.wgl_blit(image, x, y)
        image.reset()

    #@micropython.viper
    def fill(self, color:int, x:int, y:int, width:int, height:int):
        y += int(self.scroll_y_shift)
        sheight:int = int(self.height)
        swidth:int = int(self.width)
        if y < 0:
            height += y
            y = 0
        if x < 0:
            width += x
            x = 0
        max_y:int = y+height-1
        max_x:int = x+width-1
        if max_x >= swidth:
            width += (swidth-1)-max_x
        if max_y >= sheight:
            height += (sheight-1)-max_y
        if width <= 0 or height <= 0:
            return
        self.display.wgl_fill(color, int(self._window_x)+x, int(self._window_y)+y, width, height)


    # Draw a line, with a given thickness and color, between the start and endpoints,
    # Special cases like perfetly orthogonal lines are handled seperately
    # Other Lines are drawn using bresenhams line algorithm
    # with the difference that multiple oeprations to draw a single pixel are coalesced
    # into bigger operations to draw orthogonal lines.
    @micropython.viper
    def draw_line(self, color:int, width:int, x0:int, y0:int, x1:int, y1:int):
        display = self.display

        # Line Thickness offset
        ltoff:int = (width-1)//2

        # Correct using line thickness offset
        x0 -= ltoff
        y0 -= ltoff
        x1 -= ltoff
        y1 -= ltoff

        start_x:int = x0+int(self._window_x)
        start_y:int = y0+int(self._window_y)

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


        # Shift content by y
        yshift:int = int(self.scroll_y_shift)
        y0 += yshift
        y1 += yshift



        # Direction to move, x0-x1 cant be zero, same for y0-y1
        sx:int = 1 if (x0 < x1) else -1
        sy:int = 1 if (y0 < y1) else -1


        buffer:ptr8 = ptr8(self._draw_line_buffer)
        pos:int = 0
        remaining_repeats = 0           # Number of fills that can be coalesced into the last fill


        dx_x2:int = dx<<1
        dy_x2:int = dy<<1

        last_x0 = x0
        last_y0 = y0

        error:int = dx_x2+dy_x2
        window_width:int = int(self.width)
        window_height:int = int(self.height)
        while True:
            width_change:int = 0
            height_change:int = 0

            max_width:int = window_width-x0
            max_height:int = window_height-y0
            max_y:int = y0+width-1

            x02:int = x0
            y02:int = y0

            if x02 < 0:
                x02 = 0
                width_change += x02
            if width > max_width:
                width_change += max_width-width
            if y02 < 0:
                y02 = 0
                height_change += y02
            if width > max_height:
                height_change += max_height-width

            rwidth:int = width+width_change
            rheight:int = width+height_change

            x_offset:int = x02-last_x0
            y_offset:int = y02-last_y0
            if rwidth <= 0 or rheight <= 0:
                remaining_repeats = 0
            elif y_offset == 0 and rheight == buffer[pos-4+3] and remaining_repeats > 0:
                if x_offset < 0:
                    buffer[pos-4+0] += x_offset
                    buffer[pos-4+2] -= x_offset
                else:
                    buffer[pos-4+2] += x_offset
                remaining_repeats -= 1
            elif x_offset == 0 and rwidth == buffer[pos-4+2] and remaining_repeats > 0:
                if y_offset < 0:
                    buffer[pos-4+1] += y_offset
                    buffer[pos-4+3] -= y_offset
                else:
                    buffer[pos-4+3] += y_offset
                remaining_repeats -= 1
            else:
                buffer[pos] = x_offset
                buffer[pos+1] = y_offset
                buffer[pos+2] = rwidth
                buffer[pos+3] = rheight
                pos += 4
                last_x0 = x02
                last_y0 = y02
                remaining_repeats = 63

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
        n_fills:int = pos>>2
        if n_fills > 0:
            display.wgl_fill_seq(color, start_x, start_y, buffer, n_fills)


    #@micropython.native
    def draw_line_polar(self, color:int, x:int, y:int, theta:int, r0:int, r1:int, width:int):
        theta2:float = theta*_C_TO_RADIANS
        xdelta:float = math.sin(theta2)
        ydelta:float = math.cos(theta2)
        x0:int = x + int(xdelta * r0)
        x1:int = x + int(xdelta * r1)
        y0:int = x - int(ydelta * r0)
        y1:int = x - int(ydelta * r1)
        self.draw_line(x0, y0, x1, y1, width, color)


    # Returns a tuple of integers
    #@micropython.native
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



    #@micropython.native
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

    def draw_string_a(self, color:int, s:str, x:int, y:int, align:Alignment):
        (rw, rh) = self.string_bounding_box(s)
        rwidth:int = int(rw)
        if align == Alignment.CENTER:
            offset:int = (rwidth>>1)
            self.draw_string(color, s, x-offset, y)
        elif align == Alignment.LEFT:
            self.draw_string(color, s, x, y)
        elif align == Alignment.RIGHT:
            self.draw_string(color, s, x-rwidth, y)
        else:
            raise Exception("Shouldnt Happen")





_DUMMY_SCREEN:Screen = Screen(0, DisplaySpec(0, 0, ColorFormat.RGB565), [])
class DummyDisplay(DisplayProtocol):
    def __init__(self, width:int, height:int, color_format:int=ColorFormat.RGB565):
        self.spec = DisplaySpec(width, height, color_format)
    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int):
        print("FILL "+hex(color)+", X:"+str(x)+", Y:"+str(y)+", W:"+str(width)+", H:"+str(height))
    def wgl_fill_seq(self, color:int, x:int, y:int, data:memoryview, n:int):
        print("FILL SEQ "+hex(color)+":")
        nx4:int = n<<2
        for i in range(0, nx4, 4):
            x += data[i+0]
            y += data[i+1]
            print("  X:"+str(x)+", Y:"+str(y)+", W:"+str(data[i+2])+", H:"+str(data[i+3]))
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
    dg.draw_line(0, 1,  0, 1,  0, 1)
    dg.draw_line(0, 1,  0, 1,  6, 4)
    dg.draw_line(0, 3,  -1, -1,  6, 4)

    img = DummyImageStream(240, 240)
    img2 = DummyImageStream(10, 10)
    img3 = StripedStream(DummyImageStream(240, 240), 20)

    dg.blit(img, 10, 10)
    dg.blit(img2, 10, 10)
    dg.blit(img2, 239, 239)
    for i in range(0, 240, 20):
        dg.blit(img3, 0, i)
