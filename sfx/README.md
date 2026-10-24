# SFX kutubxonasi

Ikkita namunaviy videodan ajratib olingan 15 ta sound effect (48 kHz, stereo WAV).
Har bir SFX ning tavsifi, uzunligi va "hit" (eng kuchli nuqta) vaqti `library.json` da.

| Nomi | Turi | Qachon ishlatiladi |
|---|---|---|
| cyber_shift | transition | Tez sahna almashinuvi |
| cine_strike | impact | Kuchli urg'u, sarlavha chiqishi |
| distorting_glitch | glitch | Past, buzilgan glitch |
| basscrack | impact | Beat drop, keskin kesim |
| ripple_texture | texture | Matn/element paydo bo'lishi |
| ripple_texture_2 | texture | Sekin o'tish, zoom |
| alienated_warps | transition | Zoom-in, warp, sirli moment |
| digital_blip | ui | Matn pop, kichik urg'u |
| noise_burst | transition | Energiyali o'tish |
| impact_boom | impact | Katta urg'u, final |
| click_ticks | rhythm | Sanash, ritmik kesimlar |
| static_whoosh | texture | Uzun o'tish, fon tekstura |
| digital_glitch | glitch | Yuqori raqamli glitch |
| soft_swoosh | transition | Yengil slide |
| static_riser | riser | Kulminatsiyadan oldin kuchayish |

## Ishlatish

```bash
python3 sfx/apply_sfx.py input.mp4 --suggest          # sahna kesimlari bo'yicha cue taklifi
python3 sfx/apply_sfx.py input.mp4 cues.json out.mp4  # SFX larni videoga qo'shish
```
