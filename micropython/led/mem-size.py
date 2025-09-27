import esp, esp32

print("Flash:", esp.flash_size(), "bytes")

HEAP_DATA     = getattr(esp32, "HEAP_DATA", 1)
HEAP_EXTERNAL = getattr(esp32, "HEAP_EXTERNAL", 0)
HEAP_SPIRAM   = getattr(esp32, "HEAP_SPIRAM", 0)

try:
    regions = esp32.idf_heap_info(HEAP_DATA | HEAP_EXTERNAL | HEAP_SPIRAM)
except TypeError:
    regions = esp32.idf_heap_info(HEAP_DATA)

psram_total = 0
for r in regions:
    caps, total, free, largest = (r[:4] if isinstance(r, (list, tuple)) else
                                  (r.get("caps"), r.get("total"), r.get("free"), r.get("largest")))
    caps_str = str(caps)
    is_ext = (isinstance(caps, int) and ((HEAP_EXTERNAL and (caps & HEAP_EXTERNAL)) or (HEAP_SPIRAM and (caps & HEAP_SPIRAM)))) \
             or ("SPIRAM" in caps_str or "EXTERNAL" in caps_str)
    if is_ext:
        psram_total += int(total)
    print("caps=%s total=%s free=%s largest=%s%s" %
          (caps_str, total, free, largest, "  <-- PSRAM?" if is_ext else ""))

print("PSRAM total (heuristic):", psram_total, "bytes" if psram_total else "not separated from DATA")
