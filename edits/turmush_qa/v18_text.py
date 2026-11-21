# ================= v18: smaller captions, Montserrat for the plain lines =================
MONT = os.path.join(HERE, "Montserrat-Medium.ttf")
@lru_cache(None)
def mfont(s): return ImageFont.truetype(MONT, s)
STY["thin"] = (lambda: mfont(44), 62)
STY["bold"] = (lambda: dfont("Black", 58), 84)
STY["serif"] = (lambda: _serif(60), 78)
STY["caps"] = (lambda: dfont("Bold", 46), 66)

@lru_cache(maxsize=512)
def glyph5(ch): return shadowed(text_layer(ch, mfont(44), WHITE, pad=6), 6)
@lru_cache(maxsize=128)
def bold_img(text): return text_layer(text, dfont("Black", 58), WHITE, pad=6)
@lru_cache(maxsize=128)
def glyph_caps(ch):
    f = dfont("Bold", 46)
    im = Image.new("RGBA", (int(f.getlength(ch)) + 20, 72), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((8, 36), ch, font=f, fill=(255, 240, 214), anchor="lm")
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.6)))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0)); out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4)), (0, 3)); out.alpha_composite(im)
    return out

def anim_line(canvas, text, style, x, y, t0, t, out, center=False):
    if style not in ("serif", "caps"):
        return _anim_base(canvas, text, style, x, y, t0, t, out, center)
    u = t - t0
    if u <= 0: return
    if style == "serif":
        f = _serif(60); tw = f.getlength(text)
        lay = Image.new("RGBA", (int(tw) + 40, 90), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((20, 45), text, font=f, fill=(246, 198, 92), anchor="lm")
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0)); sh.putalpha(lay.getchannel("A").point(lambda v: int(v * 0.6)))
        comp = Image.new("RGBA", lay.size, (0, 0, 0, 0)); comp.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)), (0, 3)); comp.alpha_composite(lay)
        rev = ease_out(clamp(u / 0.6))
        m = Image.new("L", comp.size, 0); ImageDraw.Draw(m).rectangle((0, 0, int(comp.width * rev) + 20, comp.height), fill=255)
        comp.putalpha(ImageChops.multiply(comp.getchannel("A"), m.filter(ImageFilter.GaussianBlur(8))))
        x0 = (W - tw) / 2 if center else x
        paste_alpha(canvas, comp, x0 - 20, y - 12 - 24 * out, 1 - out)
    else:
        f = dfont("Bold", 46); track = 6
        widths = [f.getlength(ch) for ch in text]
        total = sum(widths) + track * (len(text) - 1)
        cx = (W - total) / 2 if center else x
        for j, ch in enumerate(text):
            lu = u - j * 0.035
            if lu > 0 and ch != " ":
                kk = spring(lu, w=15, z=0.6)
                paste_alpha(canvas, glyph_caps(ch), cx - 8, y - 6 - (1 - clamp(kk)) * 32 - 24 * out, clamp(lu / 0.12) * (1 - out))
            cx += widths[j] + track
