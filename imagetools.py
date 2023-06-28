import PIL
import colorthief
import PIL.Image
import colorsys
import sys

def get_gradient_colors(image_path):
    '''Find a fitting tile gradient for a given image'''

    first_color = "blue"

    # prefer a color if image has a consistent outer color #
    try:
        image = PIL.Image.open(image_path)
        pixels = image.load()
    except PIL.UnidentifiedImageError as e:
        print(e, file=sys.stderr)
        return("orange", "purple")

    max_x, max_y = image.size
    
    color_left   = pixels[int(max_x/2), 0]
    color_top    = pixels[0, int(max_y/2)]
    color_right  = pixels[max_x-1, int(max_y/2)]
    color_bottom = pixels[int(max_x/2), max_y-1]

    # check all colors the same #
    if len(set([color_left, color_top, color_right, color_bottom])) == 1:
        return build_brightness_gradient(color_left, brighten_color(*color_left))
    
    # find a dominant color otherwies #
    color_thief = colorthief.ColorThief(image_path)
    dominant_color = color_thief.get_color(quality=1)
    palette = color_thief.get_palette(color_count=2)

    if len(palette) < 2:
        return build_brightness_gradient(dominant_color, palette[1])
    return build_brightness_gradient(palette[0], palette[1])

def build_brightness_gradient(color_left, color_right):
    return (rgba_to_string(*color_left), rgba_to_string(*color_right))

def brighten_color(r, g, b, a=255):
    '''Generate the second part of the gradient'''

    h, l, s   = colorsys.rgb_to_hls(r,g,b)
    new_color = colorsys.hls_to_rgb(h, max(1, l)*1.5, s=s)

    # handle transparent pictures
    if a == 0:
        return *new_color, 0.5

    return new_color

def rgba_to_string(r, g, b, a=255):
    return "rgba({r},{g},{b},{a})".format(r=r, g=g, b=b, a=a)
