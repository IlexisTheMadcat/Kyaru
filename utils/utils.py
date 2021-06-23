from typing import List, Tuple, Callable

Color = Tuple[int,int,int]

def lin_interp(color_from: Color, color_to: Color, proportion: float) -> Color:
    r = color_to[0]*proportion + color_from[0]*(1-proportion)
    g = color_to[1]*proportion + color_from[1]*(1-proportion)
    b = color_to[2]*proportion + color_from[2]*(1-proportion)
    return (round(r),round(g),round(b))

def interp_many(parts: List[Tuple[int, int, int]]) -> Callable[[float], Color]:
    n = len(parts)-1
    def wrapper(x):
        for i in range(1,n+1):
            if x<=i/n: # from (i-1)/n to i/n
                return lin_interp(parts[i-1],parts[i],(x-(i-1)/n)*n)
        return ValueError(x)
    return wrapper