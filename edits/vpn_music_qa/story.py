# Instagram post music via JumpJump VPN — layouts: full / split (50-50) / circle (expert in a round frame) / vo (hidden)
SEG = [
    (0.00, 3.50, "full", "full", 1.00),
    (3.50, 5.42, "split", "split", 1.00),
    (5.42, 11.50, "split", "split", 1.00),
    (11.50, 18.30, "split", "circle", 1.00),
    (18.30, 23.10, "split", "split", 1.00),
    (23.10, 28.90, "split", "circle", 1.00),
    (28.90, 32.80, "split", "split", 1.00),
    (32.80, 38.20, "split", "circle", 1.00),
    (38.20, 45.80, "split", "split", 1.00),
    (45.80, 99.0, "full", "full", 1.00),
]
SCENES = [(3.50, 5.42, "nomusic"), (5.42, 11.50, "store"), (11.50, 18.30, "vpn"), (18.30, 23.10, "timer"),
          (23.10, 28.90, "music"), (28.90, 32.80, "publish"), (32.80, 38.20, "persist"), (38.20, 45.80, "edit")]
TAP_T = 99

CAPTIONS = [
    ([("Instagram'dagi postlaringizga", "thin", 0.05), ("hali musiqa", "thin", 1.28), ("qo'yolmayapsizmi?", "bold", 1.86)], 2.56),
    ([("Videoni oxirigacha ko'ring", "thin", 2.62)], 3.16),
    ([("buni tekin qo'yishni", "thin", 3.68), ("o'rgataman", "bold", 4.46)], 5.30),
    ([("Birinchi navbatda", "thin", 5.48), ("Play Market yoki App Store'dan", "thin", 6.06), ("JumpJump VPN", "bold", 7.52)], 8.96),
    ([("yuklab olishingiz kerak,", "thin", 9.02), ("rasmi tepada", "bold", 9.94)], 11.40),
    ([("Shartlarga rozilik bildirgach,", "thin", 11.62), ("serverni tanlaysiz:", "thin", 14.58), ("New York (free)", "bold", 16.46)], 18.20),
    ([("Tanlaganingizdan keyin", "thin", 18.36), ("taxminan", "thin", 19.68), ("2 soat vaqt beradi", "bold", 19.96)], 21.16),
    ([("Shu orada darhol", "thin", 21.22), ("Instagram'ga kirasiz", "bold", 21.94)], 23.00),
    ([("O'zingiz xohlagan musiqani", "thin", 23.66), ("yoki Instagram tavsiya qilganini", "thin", 25.42), ("tanlab qo'yasiz", "bold", 28.00)], 28.80),
    ([("Tanlaganingizdan keyin", "thin", 29.38), ("publish qilasiz", "bold", 30.84)], 32.70),
    ([("Keyin qayta kirsangiz ham,", "thin", 33.04), ("postingizda musiqa", "thin", 35.88), ("turgan bo'ladi", "bold", 37.52)], 38.10),
    ([("Oldin joylagan postlaringizni", "thin", 38.20), ("edit qilib", "bold", 41.60), ("musiqa qo'ysangiz,", "thin", 42.86)], 43.48),
    ([("ularda ham", "thin", 43.54), ("musiqa ko'rinadi", "bold", 44.10)], 45.70),
    ([("Video foydali bo'lsa", "thin", 45.84), ("like bosing", "bold", 47.02)], 47.62),
    ([("va shu muammosi bor", "thin", 47.74), ("tanishingizga yuboring", "bold", 49.04)], 99),
]
