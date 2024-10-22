import os
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING
from PIL import Image, ImageDraw, ImageFont, ImageOps

if TYPE_CHECKING:
    from ballsdex.core.models import BallInstance

SOURCES_PATH = Path(os.path.dirname(os.path.abspath(__file__)), "./src")
WIDTH = 1500
HEIGHT = 2000
RECTANGLE_WIDTH = WIDTH - 40
RECTANGLE_HEIGHT = (HEIGHT // 5) * 2
CORNERS = ((34, 261), (1393, 992))
artwork_size = [b - a for a, b in zip(*CORNERS)]

title_font = ImageFont.truetype(str(SOURCES_PATH / "Hobeaux-Bold.ttf"), 170)
capacity_name_font = ImageFont.truetype(str(SOURCES_PATH / "Hobeaux-Bold.ttf"), 110)
capacity_description_font = ImageFont.truetype(str(SOURCES_PATH / "CooperFiveOpti-Black.ttf"), 75)
stats_font = ImageFont.truetype(str(SOURCES_PATH / "Hobeaux-Bold.ttf"), 130)
credits_font = ImageFont.truetype(str(SOURCES_PATH / "OpenSans-Semibold.ttf"), 40)

def get_scaled_font_size(text: str, max_width: int, max_height: int, font_path: str, starting_size: int, min_size: int = 40) -> tuple[int, list[str]]:
    font_size = starting_size
    font = ImageFont.truetype(str(font_path), font_size)
    dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    wrapped_text = textwrap.wrap(text, width=28)
    
    if len(wrapped_text) >= 4:
        font_size = max(min_size, starting_size - (10 * (len(wrapped_text) - 4)))
        font = ImageFont.truetype(str(font_path), font_size)
        wrapped_text = textwrap.wrap(text, width=25)
        while len(wrapped_text) > 7:
            font_size -= 2
            if font_size < min_size:
                font_size = min_size
                break
            font = ImageFont.truetype(str(font_path), font_size)
            wrapped_text = textwrap.wrap(text, width=25)
    else:
        text_height = len(wrapped_text) * font_size * 1.1
        while text_height > max_height or any(dummy_draw.textlength(line, font=font) > max_width for line in wrapped_text):
            font_size -= 2
            if font_size < min_size:
                font_size = min_size
                break
            font = ImageFont.truetype(str(font_path), font_size)
            wrapped_text = textwrap.wrap(text, width=28)
            text_height = len(wrapped_text) * font_size * 1.1
    
    return font_size, wrapped_text

def draw_card(ball_instance: "BallInstance"):
    def remove_leading_space(text):
        return text.lstrip()

    ball = ball_instance.countryball
    ball_health = (237, 115, 101, 255)

    artwork = Image.open("." + ball.collection_card).convert("RGBA")
    artwork = ImageOps.fit(artwork, artwork_size)

    base_image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))

    base_image.paste(artwork, CORNERS[0], artwork)

    if ball_instance.shiny:
        card = Image.open(str(SOURCES_PATH / "shiny.png")).convert("RGBA")
        ball_health = (255, 255, 255, 255)
    elif special_image := ball_instance.special_card:
        card = Image.open("." + special_image).convert("RGBA")
    else:
        card = Image.open("." + ball.cached_regime.background).convert("RGBA")

    base_image.paste(card, (0, 0), card)

    icon = Image.open("." + ball.cached_economy.icon).convert("RGBA") if ball.cached_economy else None

    draw = ImageDraw.Draw(base_image)

    draw.text(
        (50, 20),
        remove_leading_space(ball.short_name or ball.country),
        font=title_font,
        fill=(255, 255, 255, 255),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 255)
    )

    ability_text = f"Ability: {remove_leading_space(ball.capacity_name)}"
    ability_font_size, wrapped_ability = get_scaled_font_size(
        ability_text,
        RECTANGLE_WIDTH - 150,
        200,
        SOURCES_PATH / "Hobeaux-Bold.ttf",
        110,
        90
    )
    dynamic_ability_font = ImageFont.truetype(str(SOURCES_PATH / "Hobeaux-Bold.ttf"), ability_font_size)

    desc_font_size, wrapped_desc = get_scaled_font_size(
        remove_leading_space(ball.capacity_description),
        RECTANGLE_WIDTH - 120,
        300,
        SOURCES_PATH / "CooperFiveOpti-Black.ttf",
        75,
        60
    )
    dynamic_desc_font = ImageFont.truetype(str(SOURCES_PATH / "CooperFiveOpti-Black.ttf"), desc_font_size)

    ability_y = 1050
    line_spacing = 1.05 if len(wrapped_ability) >= 5 else 1.1
    for i, line in enumerate(wrapped_ability):
        draw.text(
            (50, ability_y + (i * ability_font_size * line_spacing)),
            line,
            font=dynamic_ability_font,
            fill=(230, 230, 230, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255)
        )

    desc_y = ability_y + (len(wrapped_ability) * ability_font_size * line_spacing) + 50
    desc_spacing = 1.05 if len(wrapped_desc) >= 5 else 1.1
    for i, line in enumerate(wrapped_desc):
        draw.text(
            (50, desc_y + (i * desc_font_size * desc_spacing)),
            line,
            font=dynamic_desc_font,
            fill=(255, 255, 255, 255),
            stroke_width=2,
            stroke_fill=(0, 0, 0, 255)
        )

    draw.text(
        (320, 1670),
        str(ball_instance.health),
        font=stats_font,
        fill=ball_health,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255)
    )

    draw.text(
        (1120, 1670),
        str(ball_instance.attack),
        font=stats_font,
        fill=(252, 194, 76, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 255),
        anchor="ra"
    )

    draw.text(
        (32, 1838),
        "FanmadeDex owned by Venus\nBallsDex created by El Laggron\n" + f"Monster owner: {ball.credits}",
        font=credits_font,
        fill=(255, 255, 255, 255),
        stroke_width=1,
        stroke_fill=(0, 0, 0, 255)
    )

    if icon:
        icon = ImageOps.fit(icon, (192, 192))
        base_image.paste(icon, (1200, 30), mask=icon)

    return base_image
