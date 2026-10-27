# Shared timeline data for render + SFX cue generation (stuttering Q&A).
SEG = [
    (0.00, 1.80, "full", None, 1.10),
    (1.80, 6.15, "split", "ask", 1.00),
    (6.15, 9.40, "split", "stutter", 1.12),
    (9.40, 13.40, "split", "syrup", 1.00),
    (13.40, 16.30, "full", None, 1.00),
    (16.30, 22.85, "split", "causes", 1.15),
    (22.85, 27.40, "split", "home", 1.00),
    (27.40, 30.30, "full", None, 1.04),
    (30.30, 38.30, "split", "nomagic", 1.12),
    (38.30, 41.20, "full", None, 1.00),
    (41.20, 47.30, "split", "exercise", 1.14),
    (47.30, 51.60, "split", "logoped", 1.00),
    (51.60, 54.60, "split", "follow", 1.00),
    (54.60, 99.0, "full", None, 1.10),
]
TAP_T = 53.64

# (lines[(text, style, t_in)], t_out, where)   where: auto | bubble
CAPTIONS = [
    ([("1 daqiqada", "thin", 0.05), ("1 savolga javob", "bold", 0.78)], 1.72, "auto"),
    ([("Savollarni oldindan", "thin", 1.86), ("o'qimaganman", "bold", 2.88)], 3.70, "auto"),
    ([("Qizim 4 yoshda,", "thin", 3.78), ("1 oydan beri", "bold", 4.76), ("duduqlanyapti", "thin", 5.40)], 6.05, "bubble"),
    ([("Oldin umuman yo'q edi.", "thin", 6.18), ("Tuzalib ketadimi?", "bold", 8.58)], 9.32, "auto"),
    ([("Nevrologga olib bordik,", "thin", 9.42), ("sirop berdi —", "thin", 10.92), ("foydasi yo'q", "bold", 12.18)], 13.32, "auto"),
    ([("Bolada duduqlanish", "thin", 13.76), ("kelib chiqishining", "bold", 15.36)], 16.22, "auto"),
    ([("bir nechta", "thin", 17.04), ("sabablari bor", "bold", 17.78)], 18.95, "auto"),
    ([("Qo'rquv bo'lishi mumkin,", "thin", 19.04), ("nevrologik muammo", "bold", 20.86)], 22.80, "auto"),
    ([("Eng muhimi —", "thin", 22.96), ("uyda tinch muhit", "bold", 23.98), ("bo'lishi kerak", "thin", 25.06)], 27.32, "auto"),
    ([("Duduqlanish paydo", "thin", 27.92), ("bo'lganda", "bold", 29.08)], 30.22, "auto"),
    ([("sehrli dorilar, siroplar,", "thin", 30.36), ("tabletkalar yoki tok", "bold", 31.90)], 33.95, "auto"),
    ([("yoki til tagini kesish —", "thin", 34.58), ("nutqni ravon qilmaydi", "bold", 36.94)], 38.22, "auto"),
    ([("Albatta bola bilan", "thin", 38.52), ("mashq qilish kerak", "bold", 40.12)], 41.12, "auto"),
    ([("to'g'ri nafas olib", "thin", 42.00), ("chiqarish", "bold", 42.96)], 44.40, "auto"),
    ([("va nutq ustida", "thin", 44.48), ("ishlash kerak", "bold", 46.48)], 47.28, "auto"),
    ([("Buni logoped-defektolog", "thin", 47.40), ("qiladi", "bold", 48.62)], 49.20, "auto"),
    ([("Albatta logopedning", "thin", 49.26), ("konsultatsiyasiga", "bold", 50.42), ("olib boring", "thin", 51.08)], 51.55, "auto"),
    ([("Sahifamga hali", "thin", 51.66), ("obuna bo'lmagan bo'lsangiz,", "thin", 52.86), ("obuna bo'ling", "bold", 53.64)], 54.52, "auto"),
    ([("Ota-onalar va yosh", "thin", 54.62), ("logopedlar uchun", "bold", 55.58), ("kerakli ma'lumotlar", "thin", 56.72)], 99, "auto"),
]
