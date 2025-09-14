#!/usr/bin/env python3
from typing import Protocol, Any, Tuple, List, Callable, Dict, Optional
from array import array
from enum import Enum
import math

try:
    from micropython import const
    import micropython
except ImportError:
    print("Using Micropython Faker Class")
    from micropython_faker import const
    import micropython_faker as micropython




BGCOLOR_TRANSPARENT = -1


class ColorFormat(Enum):
    RGB565 = 128
    RGB565_R = 129

class GraphicsState(Enum):
    Initial = 1
    Update = 2
    Forced = 3
    Scrolling = 4
    ScrollingFinal = 5

class Direction(Enum):
    Up = 0
    Down = 1
    Left = 2
    Right = 3

class Alignment(Enum):
    CENTER = 0
    LEFT = 1
    RIGHT = 2





class ImageStream(Protocol):
    width: int
    height: int
    remaining: int
    # Reset Stream, or restart it
    def reset(self) -> None:
        pass
    # Skip n Pixels
    def skip_pixels(self, n:int) -> None:
        pass
    # Read n Pixels, into the buffer at the given offset, returns number of pixels read. Offset is in pixels
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        return -1
    def info(self) -> str:
        return ""

class DummyImageStream():
    def __init__(self, width:int, height:int) -> None:
        self.width:int = width
        self.height:int = height
        self.remaining = self.width*self.height
    def reset(self) -> None:
        self.remaining = self.width*self.height
    def skip_pixels(self, n:int) -> None:
        if n > self.remaining:
            n = self.remaining
        self.remaining -= n
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        if n > self.remaining:
            n = self.remaining
        self.remaining -= n
        return n
    def info(self) -> str:
        return "DUMMY_STREAM("+str(self.width)+", "+str(self.height)+")"


class DisplaySpec():
    def __init__(self, width:int, height:int, color_format:ColorFormat) -> None:
        self.width:int = width
        self.height:int = height
        self.color_format:int = color_format
        self.max_dimension:int = width
        self.min_dimension:int = height
        if height > width:
            self.max_dimension:int = height
            self.min_dimension:int = width



class DisplayProtocol(Protocol):
    spec: DisplaySpec

    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int) -> None:
        pass
    def wgl_fill_seq(self, color:int, x:int, y:int, data:memoryview, n:int) -> None:
        pass
    def wgl_blit(self, image:ImageStream, x:int, y:int) -> None:
        pass





class BitBlitStream():
    def __init__(self, color_format:ColorFormat, raw_data:memoryview, width:int, height:int):
        self._color_format:ColorFormat = color_format
        self._fgcolor:int = 0xFFFF
        self.bgcolor:int = 0

        self._raw_data:memoryview = raw_data
        self.width:int = width
        self.height:int = height
        self._n_pixels:int = width*height

        self.remaining:int = self._n_pixels
        self._index:int = 0
        self._cbyte:int = self._raw_data[0]
        self._remaining_in_line:int = self.width
        self._remaining_in_byte:int = 8
        if self._remaining_in_line < 8:
            self._remaining_in_byte:inz = self._remaining_in_line
    def reset(self) -> None:
        self.remaining:int = self._n_pixels
        self._index:int = 0
        self._cbyte:int = self._raw_data[0]
        self._remaining_in_line:int = self.width
        self._remaining_in_byte:int = 8
        if self._remaining_in_line < 8:
            self._remaining_in_byte:int = self._remaining_in_line

    def skip_pixels(self, n:int) -> None:
        remaining:int = self.remaining
        if n > remaining:
            n = remaining
        while self._remaining_in_byte:
            pass
        # TODO FIX BITBLIT STREAM

        remaining -= n
        self.remaining = remaining
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        remaining:int = self.remaining
        if remaining == 0:
            raise EmptyImageStream()
        finishing:int = False
        if n >= remaining:
            finishing:int = True
            n = remaining
        c:int = n


        rem_in_byte:int = self._remaining_in_byte
        rem_in_line:int = self._remaining_in_line
        bgcolor:int = self._bgcolor
        fgcolor:int = self._bgcolor
        cbyte:int = self._cbyte
        color_format:ColorFormat = self._color_format
        while True:
            while rem_in_byte > 0 and c:
                pixel:int = cbyte&1
                color = bgcolor
                if pixel:
                    color = fgcolor
                upper_byte:int = 0
                lower_byte:int = 0
                if color_format == ColorFormat.RGB565:
                    lower_byte = color&0xFF
                    upper_byte = color>>8
                elif color_format == ColorFormat.RGB565_R:
                    lower_byte = color>>8
                    upper_byte = color&0xFF
                else:
                    raise Exception("Shouldnt Happen")
                buf[offset] = lower
                buf[offset+1] = upper
                offset += 2
                rem_in_byte -= 1
                rem_in_line -= 1
                remaining -= 1
                c -= 1
            if c == 0 and finishing:
                break
            if rem_in_byte == 0:
                self._index += 1
            if c == 0:
                pass
                # TODO FIX BITBLIT STREAM

        remaining -= n
        self.remaining = remaining
        return n


class LegacyFontWrapper():
    def __init__(self, font_data, bitblit:BitBlitStream):
        self.height:int = int(font_data.height())
        self.max_width:int = int(font_data.max_width())
        self.baseline:int = int(font_data.baseline())
        self.hmap:bool = bool(font_data.hmap())
        self.reverse:bool = bool(font_data.reverse())
        self.monospaced:bool = bool(font_data.monospaced())
        self.min_ch:int = int(font_data.min_ch())
        self.max_ch:int = int(font_data.max_ch())
        self._raw_data = font_data
        self._bitblit:BitBlitStream = bitblit
    def set_bgcolor(self, color:int) -> None:
        self._bitblit.set_bgcolor(color)
    def set_fgcolor(self, color:int) -> None:
        self._bitblit.set_fgcolor(color)
    def get_ch(ch:str) -> Tuple[BitBlitStream, int, int]:
        (px, h, w) = self._raw_data.get_ch(ch)
        self._bitblit.set_image_data(px, h, w)
        return (self._bitblit, int(h), int(w))



class DummyDisplay():
    def __init__(self, width:int, height:int, color_format:ColorFormat=ColorFormat.RGB565):
        self.spec = DisplaySpec(width, height, color_format)
    def wgl_fill(self, color:int, x:int, y:int, width:int, height:int) -> None:
        print("FILL "+hex(color)+", X:"+str(x)+", Y:"+str(y)+", W:"+str(width)+", H:"+str(height))
    def wgl_fill_seq(self, color:int, x:int, y:int, data:memoryview, n:int) -> None:
        print("FILL SEQ "+hex(color)+":")
        nx4:int = n<<2
        for i in range(0, nx4, 4):
            x += data[i+0]
            y += data[i+1]
            print("  X:"+str(x)+", Y:"+str(y)+", W:"+str(data[i+2])+", H:"+str(data[i+3]))
    def wgl_blit(self, image:ImageStream, x:int, y:int) -> None:
        print("BLIT IMAGE:    X:"+str(x)+", Y:"+str(y)+", W:"+str(image.width)+", H:"+str(image.height))
        print("  "+image.info())



class Component():
    def __init__(self, x:int, y:int, width:int, height:int, draw:Callable[["Component", "WatchGraphics"], None]):
        self.x:int = x
        self.y:int = y
        self.width:int = width
        self.height:int = height
        self.bgcolor:int = BGCOLOR_TRANSPARENT

        self.weight:int = self.width*self.height

        self.draw:Callable[["Component", "WatchGraphics"], None] = draw
        self._state: Dict[str, Any] = {}
        self.dirty:bool = True
        self._screen:"Screen" = _DUMMY_SCREEN
        self._cid:int = 0
    def set_bgcolor(self, color:int) -> None:
        if self._cid:
            raise Exception("Cant Set Background Color after adding component to screen")
        self.bgcolor = color
    def register(self, screen:"Screen", cid:int) -> None:
        self._screen = screen
        self._cid = cid
    def init_vars(self, state:Dict[str, Any]) -> None:
        self._state = state
        if not self.dirty:
            self._screen.notify_component_update(self._cid)
            self.dirty = True
    def get_var_dict(self) -> Dict[str, Any]:
        return self._state
    def get_var(self, k:str) -> Any:
        return self._state[k]
    def set_var(self, k:str, v:Any) -> None:
        if k in self._state and self._state[k] == v:
            return
        self._state[k] = v
        if not self.dirty:
            self._screen.notify_component_update(self._cid)
            self.dirty = True
    def set_var_q(self, k:str, v:Any) -> None:
        self._state[k] = v


class Screen():
    def __init__(self, bgcolor:int, display_spec:DisplaySpec, components:List['Component']):
        ncomponents:List['Component'] = []
        if len(components) > 127:
            raise Exception("Too many components")
        cid:int = 1
        self.bgcolor:int = bgcolor
        self.transparent:bool = False

        self.display_spec:DisplaySpec = display_spec

        self.bounds_x0:int = -1
        self.bounds_y0:int = -1
        self.bounds_x1:int = -1
        self.bounds_y1:int = -1
        if len(components) > 0:
            self.bounds_x0:int = components[0].x
            self.bounds_y0:int = components[0].y
            self.bounds_x1:int = self.bounds_x0+components[0].width-1
            self.bounds_y1:int = self.bounds_y0+components[0].height-1


        for c in components:
            if c.bg == BGCOLOR_TRANSPARENT:
                c.bg = bgcolor

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
        self.components:List['Component'] = ncomponents
        self.update_array = memoryview(bytearray(16))
        for i in range(0,16):
            self.update_array[i] = 0
        self.update_bitfield:int = 0
    def set_transparent(self, v:bool) -> None:
        self.transparent = v
    def notify_component_update(self, cid:int) -> None:
        byti = cid>>3
        biti = cid&0x7
        update_pattern = 1<<biti
        self.update_array[byti] |= update_pattern
        self.update_bitfield |= 1<<byti
    def draw(self, display:DisplayProtocol) -> None:
        update_bitfield:int = self.update_bitfield
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

            value:int = self.update_array[byti]&0xFF
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
            self.update_array[byti] = 0
        self.update_bitfield = 0
_DUMMY_DISPLAY_SPEC = DisplaySpec(0, 0, ColorFormat.RGB565)
_DUMMY_SCREEN:Screen = Screen(0, _DUMMY_DISPLAY_SPEC, [])





class EmptyImageStream(Exception):
    pass

class VerticalCropStream():
    def __init__(self, instream:ImageStream, skip:int, height:int) -> None:
        self.width:int = instream.width
        if skip+height > instream.height:
            height = height-(skip+height-instream.height)
        self.height:int = height
        self._instream:ImageStream = instream

        self._skip_lines:int = skip

        self._pixels_n:int = self.height*self.width
        self._skip:int = skip*self.width

        self.remaining:int = self._pixels_n
        self._instream.skip_pixels(self._skip)
        assert(self._instream.remaining >= self.remaining)
    def reset(self):
        self._instream.reset()
        self._instream.skip_pixels(self._skip)
        self.remaining:int = self._pixels_n
        assert(self._instream.remaining >= self.remaining)
    def skip_pixels(self, n:int) -> None:
        remaining:int = self.remaining
        if n > remaining:
            n = remaining
        self._instream.skip_pixels(n)
        remaining -= n
        self.remaining = remaining
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        remaining:int = self.remaining
        if remaining == 0:
            raise EmptyImageStream()
        if n > remaining:
            n = remaining
        r = self._instream.read_pixels(buf, n, offset)
        remaining -= r
        self.remaining = remaining
        return r
    def info(self) -> str:
        return "VERTICAL_CROP_STREAM("+str(self._skip_lines)+", "+str(self.height)+", "+self._instream.info()+")"


class HorizontalCropStream():
    def __init__(self, instream:ImageStream, skip:int, width:int) -> None:
        self.height:int = instream.height
        if skip+width > instream.width:
            width = width-(skip+width-instream.width)
        self.width:int = width
        self._instream:ImageStream = instream
        self._pixels_n:int = self.height*self.width

        self._skip_at_start:int = skip
        self._skip:int = instream.width-(skip+width)

        self.remaining:int = self._pixels_n
        self._remaining_in_line:int = self.width
        assert(self._instream.remaining >= self.remaining+self.height*self._skip)
        self._instream.skip_pixels(self._skip_at_start)

    def reset(self) -> None:
        self._instream.reset()
        self.remaining:int = self._pixels_n
        self._remaining_in_line:int = self.width
        assert(self._instream.remaining >= self.remaining+self.height*self._skip)
        self._instream.skip_pixels(self._skip_at_start)
    def skip_pixels(self, n:int) -> None:
        remaining:int = self.remaining
        if remaining == 0:
            raise EmptyImageStream()
        if n > remaining:
            n = remaining

        skip_total:int = 0
        skip:int = self._skip
        rem_in_line:int = self._remaining_in_line
        width:int = self.width
        while n > 0:
            if n >= rem_in_line:
                skip_total += rem_in_line+skip
                n -= rem_in_line
                remaining -= rem_in_line
                rem_in_line = width
            else:
                skip_total += n
                rem_in_line -= n
                remaining -= n
                n = 0
        self._instream.skip_pixels(skip_total)
        self.remaining = remaining
        self._remaining_in_line = rem_in_line
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        remaining:int = self.remaining
        if remaining == 0:
            raise EmptyImageStream()
        if n > remaining:
            n = remaining
        read_bytes:int = 0
        rem_in_line:int = self._remaining_in_line
        skip:int = self._skip
        width:int = self.width
        while n > 0:
            if n >= rem_in_line:
                r = self._instream.read_pixels(buf, rem_in_line, offset+read_bytes)
                read_bytes += r
                n -= rem_in_line
                self._instream.skip_pixels(skip)
                remaining -= rem_in_line
                rem_in_line = width
            else:
                r = self._instream.read_pixels(buf, n, offset+read_bytes)
                read_bytes += r
                rem_in_line -= n
                remaining -= n
                n = 0
        self.remaining = remaining
        self._remaining_in_line = rem_in_line
        return read_bytes
    def info(self) -> str:
        return "HORIZONTAL_CROP_STREAM("+str(self._skip_at_start)+", "+str(self.width)+", "+self._instream.info()+")"




class StripedStream():
    def __init__(self, instream:ImageStream, lines:int) -> None:
        self._lines_per_stripe:int = lines
        self._instream:ImageStream = instream

        self.width:int = self._instream.width
        self.height:int = 0
        self._pixels_n:int = self.width*self._lines_per_stripe

        self._stripe_start = 0

        if (self._stripe_start + self._lines_per_stripe) > self._instream.height:
            self.height = (self._stripe_start + self._lines_per_stripe) - self._instream.height
            self.remaining = self.width*self.height
        else:
            self.height = self._lines_per_stripe
            self.remaining = self._pixels_n
        assert(self._instream.remaining >= self.remaining)
    def reset(self):
        self._stripe_start += self._lines_per_strip
        if self._stripe_start >= self._instream.height:
            self._instream.reset()
            self._stripe_start = 0
            self.height = 0
        if (self._stripe_start + self._lines_per_stripe) > self._instream.height:
            self.height = (self._stripe_start + self._lines_per_stripe) - self._instream.height
            self.remaining = self.width*self.height
        else:
            self.height = self._lines_per_stripe
            self.remaining = self._pixels_n
        assert(self._instream.remaining >= self.remaining)
    def skip_pixels(self, n:int) -> None:
        remaining:int = self.remaining
        if n > remaining:
            n = remaining
        self._instream.skip_pixels(n)
        remaining -= n
        self.remaining = remaining
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        remaining:int = self.remaining
        if remaining == 0:
            raise EmptyImageStream()
        if n > remaining:
            n = remaining
        r = self._instream.read_pixels(buf, n, offset)
        remaining -= r
        self.remaining = remaining
        return r
    def info(self) -> str:
        return "STRIPED_STREAM("+str(self.height)+", "+self._instream.info()+")"







class WatchGraphics():
    _C_TO_RADIANS:float = math.pi / 180

    def __init__(self, display:DisplayProtocol) -> None:
        #self._font:LegacyFontWrapper = LegacyFontWrapper()
        # TODO FIX DEFAULT FAULT
        self.display:DisplayProtocol = display
        
        self.bgcolor = 0
        self.state:GraphicsState = GraphicsState.Initial
        self.scroll_direction:Direction = Direction.Up
        self.scroll_stripe_size:int = 20            #FIX # TODO Select better source of value
        self.scroll_y_shift:int = 0

        self.width:int = self.display.spec.width
        self.height:int = self.display.spec.height
        self._window_x:int = 0
        self._window_y:int = 0

        draw_line_buffer:array = array('b')
        for _ in range(display.spec.min_dimension*4):
            draw_line_buffer.append(0)
        self._draw_line_buffer:memoryview = memoryview(draw_line_buffer)

        self._crop_v_stream:ImageStream = VerticalCropStream(DummyImageStream(1, 1), 0, 1)
        self._crop_h_stream:ImageStream = HorizontalCropStream(DummyImageStream(1, 1), 0, 1)


    def _set_window(self, x:int, y:int, width:int, height:int, shift_x:int, shift_y:int) -> None:
        if shift_x != 0:
            raise Exception("Shifting contents by x is currently not supported")
        self._window_x = x
        self._window_y = y
        self.width = width
        self.height = height
        self.scroll_y_shift = shift_y


    def blit(self, image:ImageStream, x:int, y:int):
        y += self.scroll_y_shift
        skip_lines:int = 0
        if y < 0:
            skip_lines -= y
        reduce_by_lines:int = skip_lines
        if y+image.height > self.height:
            reduce_by_lines += (y+image.height)-self.height

        skip_cols:int = 0
        if x < 0:
            skip_cols -= x
        reduce_by_cols:int = skip_cols
        if x+image.width > self.width:
            reduce_by_cols += (x+image.width)-self.width

        if reduce_by_lines == 0 and reduce_by_cols == 0:
            self.display.wgl_blit(image, x, y)
            return

        if reduce_by_lines > 0:
            new_height:int = image.height-reduce_by_lines
            if new_height <= 0:
                return
            croppedy:ImageStream = self._crop_v_stream
            croppedy.__init__(image, skip_lines, new_height)
            image = croppedy
            y += skip_lines

        if reduce_by_cols > 0:
            new_width:int = image.width-reduce_by_cols
            if new_width <= 0:
                return
            croppedx:ImageStream = self._crop_h_stream
            croppedx.__init__(image, skip_cols, new_width)
            image = croppedx
            x += skip_cols

        self.display.wgl_blit(image, x, y)
        image.reset()

    def fill(self, color:int, x:int, y:int, width:int, height:int) -> None:
        y += self.scroll_y_shift
        if y < 0:
            height += y
            y = 0
        if x < 0:
            width += x
            x = 0
        max_y:int = y+height-1
        max_x:int = x+width-1
        if max_x >= self.width:
            width += (self.width-1)-max_x
        if max_y >= self.height:
            height += (self.height-1)-max_y
        if width <= 0 or height <= 0:
            return
        self.display.wgl_fill(color, self._window_x+x, self._window_y+y, width, height)


    # Draw a line, with a given thickness and color, between the start and endpoints,
    # Special cases like perfetly orthogonal lines are handled seperately
    # Other Lines are drawn using bresenhams line algorithm
    # with the difference that multiple oeprations to draw a single pixel are coalesced
    # into bigger operations to draw orthogonal lines.
    def draw_line(self, color:int, width:int, x0:int, y0:int, x1:int, y1:int) -> None:
        display = self.display

        # Line Thickness offset
        ltoff:int = (width-1)//2

        # Correct using line thickness offset
        x0 -= ltoff
        y0 -= ltoff
        x1 -= ltoff
        y1 -= ltoff

        start_x:int = x0+self._window_x
        start_y:int = y0+self._window_y

        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)

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
            self.fill(color, x0, y0, width, (-dy)+width)
            return


        # Shift content by y
        y0 += self.scroll_y_shift
        y1 += self.scroll_y_shift



        # Direction to move, x0-x1 cant be zero, same for y0-y1
        sx:int = 1 if (x0 < x1) else -1
        sy:int = 1 if (y0 < y1) else -1


        buffer:memoryview = self._draw_line_buffer
        pos:int = 0
        remaining_repeats = 0           # Number of fills that can be coalesced into the last fill


        dx_x2:int = dx<<1
        dy_x2:int = dy<<1

        last_x0 = x0
        last_y0 = y0

        error:int = dx_x2+dy_x2
        window_width:int = self.width
        window_height:int = self.height
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


    def draw_line_polar(self, color:int, x:int, y:int, theta:int, r0:int, r1:int, width:int):
        theta2:float = theta._C_TO_RADIANS
        xdelta:float = math.sin(theta2)
        ydelta:float = mathcos(theta2)
        x0:int = x + int(xdelta * r0)
        x1:int = x + int(xdelta * r1)
        y0:int = x - int(ydelta * r0)
        y1:int = x - int(ydelta * r1)
        self.draw_line(x0, y0, x1, y1, width, color)


    def draw_string(self, color:int, s:str, x:int, y:int) -> None:
        window_width:int = self.width
        window_height:int = self.height
        font:LegacyFontWrapper = self._font
        font.set_fgcolor(color)
        font_height = font.height()

        if y >= window_height:
            return
        if x >= window_width:
            return
        if y+font_height <= 0:
            return

        for c in s:
            (cpx, ch, cw) = font.get_ch(c)
            if x+cw <= 0:
                x += cw
                continue
            if x >= window_width:
                break
            self.blit(cpx, x, y)



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
