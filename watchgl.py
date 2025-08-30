#import micropython
from typing import Protocol, Any, Tuple, List, Callable, Dict, Optional
from array import array
from enum import Enum



BGCOLOR_TRANSPARENT = -1


class DisplayFormat(Enum):
    RGB565 = 128
    RGB565_R = 129
    #RGB444 = 144
    #RGB666 = 176
    #RGB666_R = 177






class ImageStream(Protocol):
    width: int
    height: int
    auto_reset: bool
    remaining: int
    # Reset Stream, or restart it
    def reset(self) -> None:
        pass
    # Mark that all reading is done
    def done(self) -> None:
        pass
    # Skip n Pixels
    def skip_pixels(self, n:int):
        pass
    # Read n Pixels, into the buffer at the given offset, returns number of pixels read. Offset is in pixels
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        return -1


class DisplaySpec():
    width: int
    height: int
    format: DisplayFormat
    def __init__(self, width:int, height:int, format:DisplayFormat) -> None:
        self.width:int = width
        self.height:int = height
        self.format:int = format
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
    def wgl_blit(self, data:ImageStream, x:int, y:int) -> None:
        pass


class Component():
    def __init__(self, x:int, y:int, width:int, height:int, draw:Callable[["Component", "DisplayProtocol"], None]):
        self.x:int = x
        self.y:int = y
        self.width:int = width
        self.height:int = height
        self.bg:int = BGCOLOR_TRANSPARENT

        self.weight:int = self.width*self.height

        self.draw:Callable[["Component", "DisplayProtocol"], None] = draw
        self._state: Dict[str, Any] = {}
        self.dirty:bool = True
        self._screen:"Screen" = _DUMMY_SCREEN
        self._cid:int = 0
    def set_bgcolor(self, color:int) -> None:
        if self._cid:
            raise Exception("Cant Set Background Color after adding component to screen")
        self.bg = color
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
        self.bg:int = bgcolor
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
_DUMMY_SCREEN:Screen = Screen(0, [])





class EmptyImageStream(Exception):
    pass

class VerticalCropStream():
    def __init__(self, instream:ImageStream, skip:int, height:int) -> None:
        self.width:int = instream.width
        if skip+height > instream.height:
            height = height-(skip+height-instream.height)
        self.height:int = height
        self.auto_reset:bool = instream.auto_reset
        self._instream:ImageStream = instream

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
    def done(self) -> None:
        self.remaining = 0
        self.instream.done()
    def skip_pixels(self, n:int) -> None:
        remaining:int = self.remaining
        if n > remaining:
            n = remaining
        self._instream.skip_pixels(n)
        remaining -= n
        self.remaining = remaining
        if remaining == 0:
            self.done()
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        remaining:int = self.remaining
        if remaining == 0:
            raise EmptyImageStream()
        if n > remaining:
            n = remaining
        r = self._instream.read_pixels(buf, n, offset)
        remaining -= r
        self.remaining = remaining
        if remaining == 0:
            self.done()
        return r


class HorizontalCropStream():
    def __init__(self, instream:ImageStream, skip:int, width:int) -> None:
        self.height:int = instream.height
        if skip+width > instream.width:
            width = width-(skip+width-instream.width)
        self.width:int = width
        self.auto_reset:bool = instream.auto_reset
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
    def done(self) -> None:
        self.remaining = 0
        self._instream.done()
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
        if remaining == 0:
            self.done()
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
        if remaining == 0:
            self.done()
        return read_bytes









class WatchGraphics():
    def __init__(self, display:DisplayProtocol) -> None:
        self.display:DisplayProtocol = display
        self.font = None

        draw_line_buffer:array = array('b')
        for _ in range(display.spec.min_dimension*4):
            draw_line_buffer.append(0)
        self._draw_line_buffer:memoryview = memoryview(draw_line_buffer)


    def draw_line(self, color:int, width:int, x0:int, y0:int, x1:int, y1:int) -> None:
        display = self.display

        ltoff:int = (width-1)//2
        # Line Thickness offset
        x0 -= ltoff
        y0 -= ltoff
        x1 -= ltoff
        y1 -= ltoff

        start_x:int = x0
        start_y:int = y0

        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)

        if dx == 0 and dy == 0:
            display.wgl_fill(color, x0, y0, width, width)
            return
        elif dy == 0:
            if x0 > x1:
                x2 = x0
                x0 = x1
                x1 = x2
            display.wgl_fill(color, x0, y0, dx+width, width)
            return
        elif dx == 0:
            if y0 > y1:
                y2 = y0
                y0 = y1
                y1 = y2
            display.wgl_fill(color, x0, y0, width, (-dy)+width)
            return


        # Direction to move, x0-x1 cant be zero, same for y0-y1
        sx:int = 1 if (x0 < x1) else -1
        sy:int = 1 if (y0 < y1) else -1


        buffer:memoryview = self._draw_line_buffer
        pos:int = 0
        pos2:int = pos-4

        error:int = (dx + dy)<<1
        last_x:int = -1
        last_y:int = -1
        x_offset:int = 0
        y_offset:int = 0

        dy_x2:int = dy<<1
        dx_x2:int = dx<<1

        remaining_repeats = 63
        while True:
            if last_y == y0 and remaining_repeats > 0:
                if sx < 0:
                    buffer[pos2+0] -= 1
                buffer[(pos2+2] += 1
                last_y = y0
                remaining_repeats -= 1
            elif last_x == x0 and remaining_repeats > 0:
                if sy < 0:
                    buffer[pos2+1] -= 1
                buffer[pos2+3] += 1
                last_y = y0
                remaining_repeats -= 1
            else:
                buffer[pos] = x_offset
                buffer[pos+1] = y_offset
                buffer[pos+2] = width
                buffer[pos+3] = width
                pos += 4
                pos2 += 4
                x_offset = 0
                y_offset = 0
                last_x = x0
                last_y = y0
                remaining_repeats = 63
            if error >= dy:
                if x0 == x1:
                    break
                error += dy_x2
                x0 += sx
                x_offset += sx
            if error <= dx:
                if y0 == y1:
                    break
                error += dx_x2
                y0 += sy
                y_offset += sy
        n_fills:int = pos>>2
        display.wgl_fill_seq(color, start_x, start_y, buffer, n_fills)
