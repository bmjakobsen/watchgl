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



class DisplayProtocol(Protocol):
    spec: DisplaySpec

    linebuffer: memoryview
    linebuffer_size: int

    def fill(self, color:int, xy:Tuple[int, int], wh:Tuple[int, int]) -> None:
        pass
    def fill_seq(self, color:int, xywh:List[Tuple[int, int, int, int]]) -> None:
        pass
    def blit(self, data:ImageStream, xy:Tuple[int, int]) -> None:
        pass


class Component():
    def __init__(self, xywh:Tuple[int,int,int,int], draw:Callable[["Component", "DisplayProtocol"], None]):
        self.x:int = xywh[0]
        self.y:int = xywh[1]
        self.width:int = xywh[2]
        self.height:int = xywh[3]
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
    def __init__(self, bgcolor:int, components:List['Component']):
        ncomponents:List['Component'] = []
        if len(components) > 127:
            raise Exception("Too many components")
        cid:int = 1
        self.bg:int = bgcolor
        self.transparent:bool = False

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

        self._remaining:int = self._pixels_n
        self._instream.skip_pixels(self._skip)
    def reset(self):
        self._instream.reset()
        self._instream.skip_pixels(self._skip)
        self._remaining:int = self._pixels_n
    def done(self) -> None:
        if self._remaining != -1:
            self._remaining = -1
            self._instream.done()
    def skip_pixels(self, n:int) -> None:
        if self._remaining <= 0:
            self.done()
            return
        if n > self._remaining:
            n = self._remaining
        self._instream.skip_pixels(n)
        self._remaining -= n
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        if self._remaining <= 0:
            self.done()
            return 0
        if n > self._remaining:
            n = self._remaining
        r = self._instream.read_pixels(buf, n, offset)
        self._remaining -= r
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
        self._skip:int = instream.width-(skip+width)

        self._remaining_in_line:int = self.width
        self._remaining:int = self._pixels_n
        self._instream.skip_pixels(skip)

    def reset(self) -> None:
        self._instream.reset()
        self._remaining_in_line:int = self.width
        self._remaining:int = self._pixels_n
        self._instream.skip_pixels(skip)
    def done(self) -> None:
        if self._remaining != -1:
            self._remaining = -1
            self._instream.done()
    def skip_pixels(self, n:int) -> None:
        if self._remaining <= 0:
            self.done()
            return
        if n > self._remaining:
            n = self._remaining

	skip_total:int = 0
        while n > 0:
            if n >= self._remaining_in_line:
		skip_total += self._remaining_in_line+self._skip
                n -= self._remaining_in_line
                self._remaining -= self._remaining_in_line
                self._remaining_in_line = self.width
            else:
		skip_total += n
                self._remaining_in_line -= n
                self._remaining -= n
                n = 0
        self._instream.skip_pixels(skip_total)
    def read_pixels(self, buf:memoryview, n:int, offset:int) -> int:
        if self._remaining <= 0:
            self.done()
            return 0
        if n > self._remaining:
            n = self._remaining
        read_bytes = 0
        while n > 0:
            if n >= self._remaining_in_line:
                r = self._instream.read_pixels(buf, self._remaining_in_line, offset+read_bytes)
                read_bytes += r
                n -= self._remaining_in_line
                self._instream.skip_pixels(self._skip)
                self._remaining -= self._remaining_in_line
                self._remaining_in_line = self.width
            else:
                r = self._instream.read_pixels(buf, n, offset+read_bytes)
                read_bytes += r
                self._remaining_in_line -= n
                self._remaining -= n
                n = 0
        return read_bytes
