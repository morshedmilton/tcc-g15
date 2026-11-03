from enum import Enum
from typing import Tuple

class Colors(Enum):
    DARK_GREY   = '#0e1015'
    GREY        = '#3a3f4d'
    WHITE       = '#f5f5f7'
    GREEN       = '#30d158'
    YELLOW      = '#ffd60a'
    RED         = '#ff453a'
    BLUE        = '#0a84ff'
    CYAN        = '#5ac8fa'
    
    def rgb(self) -> Tuple[int, int, int]:
        color = self.value.lstrip('#')
        return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
