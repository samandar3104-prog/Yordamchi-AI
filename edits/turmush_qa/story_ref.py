# v5 — styled after the reference reel: B-roll hook + green title box, expert jump-cut zooms,
# small word-by-word captions on the chest, B-roll inserts, follow pill at the end.
# Captions = her own words only. *word* = bold emphasis. kinds: n (normal), cap (ExtraBold caps), it (ExtraBold italic caps)
HOOK = ("TURMUSHGA CHIQMAYAPMAN,", "YOSHIM O'TIB KETDI", 0.10, 3.50)
BROLL = [  # (t0, t1, clip, clip_start, crop)
    (0.00, 3.55, "frustrated", 0.5, None),
    (5.60, 7.80, "broll3/bride", 1.0, None),
    (8.96, 10.92, "rings", 9.2, "rings"),
    (12.00, 13.60, "broll3/quran", 1.0, None),
    (26.82, 29.32, "smile", 0.0, None),
    (31.76, 33.50, "study", 0.5, None),
]
FOLLOW_T = 46.2   # follow pill appears; toggle tapped ~1.3 s later
CAPTIONS = [
    ([("Hech ham oila qurish", "n", 2.56), ("kerak *emasmikan?*", "n", 3.16)], 4.00),
    ([("Shu o'zi *xayrli vaqtida* bo'ladi", "n", 4.02)], 5.55),
    ([("Kimningdir taqdiriga", "n", 5.60), ("18 YOSHDA YOZILGAN", "it", 6.56)], 7.78),
    ([("kimningdir taqdiriga", "n", 7.82), ("26–27 YOSHDA YOZILGAN", "it", 8.96)], 10.90),
    ([("Eng *muhimi* Alloh taolo", "n", 10.96), ("chiroyli *baxt* bersin", "n", 12.36)], 13.58),
    ([("O'SHA INSON", "cap", 13.62), ("*xayrli* bo'lib kelsin", "n", 14.16)], 15.20),
    ([("o'sha inson sizning", "n", 15.24), ("*o'sishingizga* sabab bo'lsin", "n", 16.24)], 17.90),
    ([("Qancha oilalar bor,", "n", 18.46), ("yosh oila qurgan,", "n", 19.66)], 21.15),
    ([("AJRASHIB KETGAN", "it", 21.18), ("hayoti *tubdan* o'zgarib ketgan", "n", 22.18)], 23.88),
    ([("Undan ko'ra", "n", 23.92), ("siz *kutayotgan* ekansiz", "n", 24.38)], 26.60),
    ([("siz misli ko'rilmagan darajada", "n", 26.82), ("BAXTLI BO'LING", "it", 28.50)], 29.30),
    ([("siz oldingizga qo'ygan", "n", 30.26), ("*maqsadlaringizga*", "n", 31.76)], 32.44),
    ([("erishish uchun", "n", 32.48), ("u qanaqadir *mos* bo'lsin", "n", 33.52)], 35.40),
    ([("SHUNAQA INSON BO'LSIN", "cap", 35.44)], 37.00),
    ([("Shuning uchun *hech qachon*", "n", 37.14), ("ko'nglingizga olib, *xafa* bo'lib", "n", 38.62)], 40.20),
    ([("yoki kimdirlarning gapiga", "n", 40.24), ("*kayfiyatingiz* o'zgarishi kerak emas", "n", 41.64)], 43.90),
    ([("O'ZI", "cap", 44.12), ("o'z *vaqtida* bo'ladi", "n", 44.70)], 45.58),
    ([("Men kutayotgan vaqtda", "n", 45.62), ("*baxt* bor", "n", 47.14)], 47.82),
    ([("men *harakat* qilyapman,", "n", 47.86), ("MOTIVATSIYA", "cap", 49.22)], 999),
]
