import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

# Output configuration
INCLUDE_WORDS: bool = False  # set True to include detailed word boxes
MAX_WORDS: int = 200  # cap when INCLUDE_WORDS is True
ENABLE_GEOCODE: bool = True  # set False to skip network geocoding
GEOCODE_SLEEP_SECONDS: float = 1.1  # Nominatim polite rate limit
ENABLE_LLM: bool = True  # use OpenRouter LLM to normalize location
OPENROUTER_MODEL: str = "deepseek/deepseek-chat-v3.1:free"
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER: str = "http://localhost"
OPENROUTER_TITLE: str = "backend_JIR"
OPENROUTER_API_KEY_DEFAULT: str = "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"


def try_imports():
    paddleocr = None
    easyocr = None
    pytesseract = None
    Image = None
    try:
        from paddleocr import PaddleOCR  # type: ignore
        paddleocr = PaddleOCR
    except Exception:
        paddleocr = None
    try:
        import easyocr as _easyocr  # type: ignore
        easyocr = _easyocr
    except Exception:
        easyocr = None
    try:
        import pytesseract as _pytesseract  # type: ignore
        pytesseract = _pytesseract
    except Exception:
        pytesseract = None
    try:
        from PIL import Image as _Image  # type: ignore
        Image = _Image
    except Exception:
        Image = None
    return paddleocr, easyocr, pytesseract, Image


def ocr_with_paddle(image_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    from paddleocr import PaddleOCR  # type: ignore
    ocr = PaddleOCR(use_angle_cls=True, lang="latin")
    result = ocr.ocr(image_bytes, cls=True)
    words: List[Dict[str, Any]] = []
    texts: List[str] = []
    for line in (result[0] or []):
        bbox, (txt, conf) = line
        texts.append(txt)
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        left, top = int(min(xs)), int(min(ys))
        width, height = int(max(xs) - left), int(max(ys) - top)
        words.append({
            "text": txt,
            "conf": float(conf) if conf is not None else None,
            "bbox": {"left": left, "top": top, "width": width, "height": height},
        })
    return "\n".join(texts), words


def ocr_with_easyocr(image_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    import numpy as np  # type: ignore
    import easyocr  # type: ignore
    from PIL import Image  # type: ignore
    reader = easyocr.Reader(["en", "id"], gpu=False)
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)
    result = reader.readtext(arr)
    texts: List[str] = []
    words: List[Dict[str, Any]] = []
    for bbox, txt, conf in result:
        texts.append(txt)
        xs = [float(p[0]) for p in bbox]
        ys = [float(p[1]) for p in bbox]
        left, top = int(min(xs)), int(min(ys))
        width, height = int(max(xs) - left), int(max(ys) - top)
        words.append({
            "text": txt,
            "conf": float(conf) if conf is not None else None,
            "bbox": {"left": left, "top": top, "width": width, "height": height},
        })
    return "\n".join(texts), words


def ocr_with_tesseract(image_path: Path, lang: str = "eng") -> Tuple[str, List[Dict[str, Any]]]:
    from PIL import Image  # type: ignore
    import pytesseract  # type: ignore
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang=lang)
    data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)
    words: List[Dict[str, Any]] = []
    n = int(len(data.get("text", [])))
    for i in range(n):
        w = data["text"][i]
        if not w or not str(w).strip():
            continue
        words.append({
            "text": w,
            "conf": float(data.get("conf", [0])[i]) if str(data.get("conf", [""])[i]).strip() != "" else None,
            "bbox": {
                "left": int(data.get("left", [0])[i]) if data.get("left") else None,
                "top": int(data.get("top", [0])[i]) if data.get("top") else None,
                "width": int(data.get("width", [0])[i]) if data.get("width") else None,
                "height": int(data.get("height", [0])[i]) if data.get("height") else None,
            },
        })
    return text, words


def run_ocr_for(image_path: Path) -> Dict[str, Any]:
    paddleocr, easyocr, pytesseract, Image = try_imports()

    text: str = ""
    words: List[Dict[str, Any]] = []
    engine: str = ""

    try:
        if paddleocr is not None:
            text, words = ocr_with_paddle(image_path.read_bytes())
            engine = "paddleocr"
        elif easyocr is not None and Image is not None:
            text, words = ocr_with_easyocr(image_path)
            engine = "easyocr"
        elif pytesseract is not None and Image is not None:
            # Prefer Indonesian if available; fall back to English
            try_langs = ["ind", "eng"]
            for lang in try_langs:
                try:
                    text, words = ocr_with_tesseract(image_path, lang=lang)
                    engine = f"tesseract:{lang}"
                    break
                except Exception:
                    continue
            if not engine:
                text, words = ocr_with_tesseract(image_path, lang="eng")
                engine = "tesseract:eng"
        else:
            raise RuntimeError("No OCR engine available. Install paddleocr/easyocr or tesseract.")
    except Exception as e:
        return {"file": str(image_path), "engine": engine or None, "error": str(e)}

    # --- Post-processing for cleaner JSON ---
    def normalize_text(t: str) -> str:
        # collapse multi-spaces, keep newlines
        import re
        t = t.replace("\r", "")
        # trim trailing spaces per line
        t = "\n".join(line.strip() for line in t.splitlines())
        # collapse 3+ newlines to max 2
        t = re.sub(r"\n{3,}", "\n\n", t)
        # collapse multiple internal spaces
        t = re.sub(r"[ \t]{2,}", " ", t)
        return t.strip()

    def split_lines(t: str) -> List[str]:
        lines = [ln.strip() for ln in t.splitlines()]
        return [ln for ln in lines if ln]

    def split_paragraphs(t: str) -> List[str]:
        import re
        parts = re.split(r"\n\s*\n+", t)
        return [p.strip() for p in parts if p.strip()]

    def extract_metadata(t: str) -> Dict[str, Any]:
        import re
        meta: Dict[str, Any] = {}
        # generic title: first uppercase heavy line
        first_lines = [ln for ln in t.splitlines() if ln.strip()]
        if first_lines:
            meta["title"] = first_lines[0][:200]
        # common fields in Indonesian letters
        m = re.search(r"Soreang[,\s]+([0-9]{1,2} .*? 20\d{2})", t, re.I)
        if m:
            meta["tanggal"] = m.group(1).strip()
        m = re.search(r"Nomor\s*\n?\s*([\w\-/\. ]+)", t, re.I)
        if m:
            meta["nomor"] = m.group(1).strip()
        m = re.search(r"Sifat\s*\n?\s*([A-Za-z]+)", t, re.I)
        if m:
            meta["sifat"] = m.group(1).strip()
        m = re.search(r"Perihal\s*\n?\s*([^\n]+)", t, re.I)
        if m:
            meta["perihal"] = m.group(1).strip()
        # surat pernyataan detection
        if re.search(r"SURAT\s+PERNYA?TAAN", t, re.I):
            meta["jenis_dokumen"] = "surat pernyataan"
        return meta

    def extract_locations(t: str) -> Dict[str, Any]:
        import re
        found: Dict[str, Any] = {
            "provinsi": [],
            "kabupaten": [],
            "kota": [],
            "kecamatan": [],
            "kelurahan": [],
            "rt_rw": [],  # list of {rt, rw, kelurahan?}
            "alamat": [],
            "perumahan": [],
            "raw_matches": [],
        }

        def push_unique(key: str, val: str) -> None:
            if not val:
                return
            val_norm = re.sub(r"\s+", " ", val).strip()
            arr = found[key]
            if isinstance(arr, list) and val_norm and val_norm not in arr:
                arr.append(val_norm)

        def clean_admin_name(name: str) -> str:
            name = re.split(r"\b(dan|yang|sekitamya|sekitarnya|dengan|yang\s+mengakibatkan)\b|[,\n]", name, 1, flags=re.I)[0] or name
            name = re.sub(r"[^A-Za-z\- '\.]", " ", name)
            name = re.sub(r"\s+", " ", name).strip()
            parts = name.split()
            return " ".join(parts[:3])

        # Province
        for m in re.finditer(r"\bProvinsi\s+([A-Z][A-Za-z .'-]+)", t, re.I):
            push_unique("provinsi", m.group(1))
            found["raw_matches"].append(m.group(0))

        # Kabupaten / Kota
        for m in re.finditer(r"\bKabupaten\s+([A-Z][A-Za-z .'-]+)", t, re.I):
            push_unique("kabupaten", m.group(1))
            found["raw_matches"].append(m.group(0))
        for m in re.finditer(r"\bKota\s+([A-Z][A-Za-z .'-]+)", t, re.I):
            push_unique("kota", m.group(1))
            found["raw_matches"].append(m.group(0))

        # Kecamatan / Kelurahan
        for m in re.finditer(r"\bKecamatan\s+([^\n,]+)", t, re.I):
            push_unique("kecamatan", clean_admin_name(m.group(1)))
            found["raw_matches"].append(m.group(0))
        for m in re.finditer(r"\bKelurahan\s+([^\n,]+)", t, re.I):
            push_unique("kelurahan", clean_admin_name(m.group(1)))
            found["raw_matches"].append(m.group(0))

        # RT/RW patterns
        for m in re.finditer(r"RT[ .:]?0?(\d+)\s*/?\s*RW[ .:]?0?(\d+)(?:,?\s*Kelurahan\s+([^\n]+))?", t, re.I):
            rt, rw, kel = m.group(1), m.group(2), (m.group(3) or "").strip()
            entry: Dict[str, Any] = {"rt": int(rt), "rw": int(rw)}
            if kel:
                kelc = clean_admin_name(kel)
                entry["kelurahan"] = kelc
                push_unique("kelurahan", kelc)
            found["rt_rw"].append(entry)
            found["raw_matches"].append(m.group(0))

        # Address-like lines (e.g., Ladang Kaladi RT.04 RW.06, Perumahan Taman Asri 8)
        for m in re.finditer(r"\bLadang\s+[A-Z][^\n,]*?(RT\.?\s*0?\d+\s*RW\.?\s*0?\d+)", t, re.I):
            push_unique("alamat", m.group(0))
            found["raw_matches"].append(m.group(0))
        for m in re.finditer(r"\b(Perumahan|Kompleks|Taman)\s+[A-Z][A-Za-z ]*\d*", t, re.I):
            push_unique("perumahan", m.group(0))
            found["raw_matches"].append(m.group(0))

        return found

    def geocode_locations(locs: Dict[str, Any], llm_candidates: Optional[List[str]] = None) -> Dict[str, Any]:
        if not ENABLE_GEOCODE:
            return {"enabled": False, "results": []}

        import time
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen
        import json as _json
        import re as _re

        def _norm_query(q: str) -> str:
            q = _re.sub(r"\s+", " ", q).strip()
            # common OCR fixes
            q = q.replace("Kelurahaan", "Kelurahan").replace("Kecaamatan", "Kecamatan")
            q = q.replace("Kab.", "Kabupaten ").replace("Kot.", "Kota ")
            q = q.replace("Rt.", "RT.").replace("Rw.", "RW.")
            return q

        def query_nominatim(q: str) -> Dict[str, Any]:
            base = "https://nominatim.openstreetmap.org/search"
            params = {
                "format": "jsonv2",
                "q": q,
                "addressdetails": 1,
                "limit": 1,
                "countrycodes": "id",
            }
            url = f"{base}?{urlencode(params)}"
            req = Request(url, headers={
                "User-Agent": "backend_JIR OCR geocoder (contact: local-dev)",
            })
            try:
                with urlopen(req, timeout=10) as resp:
                    data = resp.read().decode("utf-8")
                    items = _json.loads(data)
                    if isinstance(items, list) and items:
                        it = items[0]
                        return {
                            "lat": float(it.get("lat")),
                            "lon": float(it.get("lon")),
                            "display_name": it.get("display_name"),
                            "class": it.get("class"),
                            "type": it.get("type"),
                            "importance": it.get("importance"),
                        }
            except Exception as _:
                return {}
            return {}

        def query_photon(q: str) -> Dict[str, Any]:
            base = "https://photon.komoot.io/api/"
            params = {"q": q, "limit": 1, "lang": "id"}
            url = f"{base}?{urlencode(params)}"
            req = Request(url, headers={
                "User-Agent": "backend_JIR OCR geocoder (contact: local-dev)",
            })
            try:
                with urlopen(req, timeout=10) as resp:
                    data = resp.read().decode("utf-8")
                    obj = _json.loads(data)
                    feats = (obj or {}).get("features") or []
                    if feats:
                        g = feats[0].get("geometry", {})
                        props = feats[0].get("properties", {})
                        coords = g.get("coordinates") or []
                        if len(coords) >= 2:
                            return {
                                "lat": float(coords[1]),
                                "lon": float(coords[0]),
                                "display_name": props.get("name"),
                                "class": props.get("osm_value"),
                                "type": props.get("type"),
                                "importance": props.get("extent"),
                            }
            except Exception:
                return {}
            return {}

        def query_nominatim_structured(street: str = "", suburb: str = "", city: str = "", state: str = "", country: str = "Indonesia") -> Dict[str, Any]:
            base = "https://nominatim.openstreetmap.org/search"
            params = {
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 1,
                "countrycodes": "id",
            }
            if street:
                params["street"] = street
            if suburb:
                params["suburb"] = suburb
            if city:
                params["city"] = city
            if state:
                params["state"] = state
            if country:
                params["country"] = country
            url = f"{base}?{urlencode(params)}"
            req = Request(url, headers={"User-Agent": "backend_JIR OCR geocoder (contact: local-dev)"})
            try:
                with urlopen(req, timeout=10) as resp:
                    data = resp.read().decode("utf-8")
                    items = _json.loads(data)
                    if isinstance(items, list) and items:
                        it = items[0]
                        return {
                            "lat": float(it.get("lat")),
                            "lon": float(it.get("lon")),
                            "display_name": it.get("display_name"),
                            "class": it.get("class"),
                            "type": it.get("type"),
                            "importance": it.get("importance"),
                        }
            except Exception:
                return {}
            return {}

        def build_structured_candidates() -> list[Dict[str, str]]:
            prov = (locs.get("provinsi") or [""])[0]
            kota_kab = (locs.get("kota") or locs.get("kabupaten") or [""])[0]
            kec = (locs.get("kecamatan") or [""])[0]
            kel = (locs.get("kelurahan") or [""])[0]
            perums = locs.get("perumahan") or []
            alts = locs.get("alamat") or []

            def norm(s: str) -> str:
                s = s.strip()
                s = _re.sub(r"\s+", " ", s)
                return s

            city = norm(kota_kab)
            state = norm(prov)
            suburb = norm(kel)
            structured: list[Dict[str, str]] = []
            for st in (perums + alts):
                structured.append({
                    "street": norm(st),
                    "suburb": suburb,
                    "city": city,
                    "state": state,
                    "country": "Indonesia",
                })
            structured.append({
                "street": "",
                "suburb": suburb,
                "city": city,
                "state": state,
                "country": "Indonesia",
            })
            return structured

        def build_free_text_candidates() -> list[str]:
            candidates: list[str] = []
            prov = locs.get("provinsi") or []
            kab = locs.get("kabupaten") or []
            kota = locs.get("kota") or []
            kec = locs.get("kecamatan") or []
            kel = locs.get("kelurahan") or []
            perum = locs.get("perumahan") or []
            alamat = locs.get("alamat") or []

            def add(q: str) -> None:
                q = q.strip()
                if q and q not in candidates:
                    candidates.append(_norm_query(q))

            # LLM candidates first
            for c in (llm_candidates or [])[:10]:
                add(str(c))

            # Hierarchy combos
            for ke in (kel or [""]):
                for kc in (kec or [""]):
                    for kk in (kota or kab or [""]):
                        base = ", ".join([p for p in [
                            ke,
                            kc,
                            kk,
                            (prov[0] if prov else ""),
                            "Indonesia",
                        ] if p])
                        if base:
                            add(base)

            # Context city/province
            context_city = (kota or kab or [""])[0] if (kota or kab) else ""
            context_prov = (prov or [""])[0] if prov else ""
            ctx = ", ".join([p for p in [context_city, context_prov, "Indonesia"] if p])
            for p in perum:
                add(f"{p}, {ctx}" if ctx else p)
            for a in alamat:
                add(f"{a}, {ctx}" if ctx else a)

            # RT/RW
            for r in locs.get("rt_rw", []):
                rt = r.get("rt"); rw = r.get("rw"); kelr = r.get("kelurahan")
                parts = [
                    f"RT {rt:02d} / RW {rw:02d}" if isinstance(rt, int) and isinstance(rw, int) else "",
                    kelr or "",
                    ctx,
                ]
                q = ", ".join([p for p in parts if p])
                add(q)

            # Fallbacks
            for kk in (kota or kab):
                add(f"{kk}, Indonesia")
            if prov:
                add(f"{prov[0]}, Indonesia")
            return candidates[:20]

        # Try structured first
        results: list[Dict[str, Any]] = []
        for sc in build_structured_candidates():
            res = query_nominatim_structured(**sc)
            results.append({"structured": sc, "result": res or None})
            if res:
                time.sleep(GEOCODE_SLEEP_SECONDS)
                break
            time.sleep(GEOCODE_SLEEP_SECONDS)

        # Fallback free-text + Photon
        _cands = build_free_text_candidates()
        for q in _cands:
            res = query_nominatim(q)
            if not res:
                res = query_photon(q)
            results.append({"query": q, "result": res or None})
            if res:
                time.sleep(GEOCODE_SLEEP_SECONDS)
                break
            time.sleep(GEOCODE_SLEEP_SECONDS)

        primary = next((r.get("result") for r in results if r.get("result")), None)
        return {"enabled": True, "primary": primary, "results": results}

    norm = normalize_text(text or "")
    lines = split_lines(norm)
    paragraphs = split_paragraphs(norm)
    meta = extract_metadata(norm)
    locs = extract_locations(norm)

    def build_llm_prompt(text_value: str, locations: Dict[str, Any]) -> str:
        import json as _json
        snippet = text_value[:2000]
        loc_compact = {
            "kota": locations.get("kota"),
            "kecamatan": locations.get("kecamatan"),
            "kelurahan": locations.get("kelurahan"),
            "alamat": locations.get("alamat"),
            "perumahan": locations.get("perumahan"),
            "rt_rw": locations.get("rt_rw"),
        }
        schema = {
            "lokasi_banjir": {
                "nama": "string",
                "komponen": {
                    "provinsi": "string|null",
                    "kota": "string|null",
                    "kecamatan": "string|null",
                    "kelurahan": "string|null",
                    "rt": 0,
                    "rw": 0,
                    "area": "string|null"
                }
            },
            "normalized_query_candidates": ["string"],
            "ringkasan": "string"
        }
        instr = (
            "Anda asisten ekstraksi alamat Indonesia. Kembalikan JSON valid sesuai skema. "
            "Normalisasikan alamat dan pilih satu lokasi_banjir paling representatif. "
            "Jangan keluarkan teks selain JSON."
        )
        return (
            f"INSTRUKSI\n{instr}\n\n"
            f"SKEMA\n{_json.dumps(schema, ensure_ascii=False)}\n\n"
            f"ENTITAS_LOKASI\n{_json.dumps(loc_compact, ensure_ascii=False)}\n\n"
            f"TEKS\n{snippet}"
        )

    def call_openrouter_llm(prompt: str) -> Dict[str, Any]:
        import os
        import json as _json
        from urllib.request import Request, urlopen
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            key_path = Path(__file__).resolve().parent / "key.txt"
            if key_path.exists():
                key = key_path.read_text(encoding="utf-8").strip()
        if not key:
            key = OPENROUTER_API_KEY_DEFAULT
        if not key:
            return {}
        body = _json.dumps({
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "Kembalikan hanya JSON sesuai skema."},
                {"role": "user", "content": prompt},
            ],
        }).encode("utf-8")
        req = Request(f"{OPENROUTER_BASE_URL}/chat/completions", data=body)
        req.add_header("Authorization", f"Bearer {key}")
        req.add_header("Content-Type", "application/json")
        if OPENROUTER_REFERER:
            req.add_header("HTTP-Referer", OPENROUTER_REFERER)
        if OPENROUTER_TITLE:
            req.add_header("X-Title", OPENROUTER_TITLE)
        try:
            with urlopen(req, timeout=30) as resp:
                txt = resp.read().decode("utf-8")
        except Exception:
            return {}
        try:
            obj = json.loads(txt)
            content = obj.get("choices", [{}])[0].get("message", {}).get("content", "")
            s = content.find("{")
            e = content.rfind("}")
            if s != -1 and e != -1 and e > s:
                return json.loads(content[s:e+1])
            return {}
        except Exception:
            return {}

    llm_output: Dict[str, Any] = {}
    llm_candidates: List[str] = []
    if ENABLE_LLM:
        prompt = build_llm_prompt(norm, locs)
        llm_output = call_openrouter_llm(prompt) or {}
        cand = llm_output.get("normalized_query_candidates") or []
        if isinstance(cand, list):
            llm_candidates = [str(c) for c in cand if isinstance(c, str)]

    geocoding = geocode_locations(locs, llm_candidates)

    result: Dict[str, Any] = {
        "file": str(image_path),
        "engine": engine,
        "length": len(norm),
        "text": norm,
        "lines": lines,
        "paragraphs": paragraphs,
        "metadata": meta,
        "locations": locs,
        "geocoding": geocoding,
        "words_count": len(words),
        "llm": {"enabled": ENABLE_LLM, "model": OPENROUTER_MODEL, "output": llm_output or None},
    }
    if INCLUDE_WORDS:
        result["words"] = words[:MAX_WORDS]
    return result


def main() -> None:
    base_dir = Path(__file__).resolve().parent / "dokument_test"
    files = [
        base_dir / "Tangkapan Layar 2025-09-11 pukul 14.27.37.png",
    ]

    results: List[Dict[str, Any]] = []
    for path in files:
        if not path.exists():
            results.append({"file": str(path), "error": "File not found"})
            continue
        res = run_ocr_for(path)
        results.append(res)

    print("=== OCR RESULTS (summary) ===")
    for r in results:
        print(f"- {r.get('file')}: engine={r.get('engine')} length={r.get('length')} error={r.get('error')}")

    # Sanitize results to ensure JSON serializable (e.g., numpy types)
    def sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {str(k): sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize(v) for v in obj]
        if isinstance(obj, Path):
            return str(obj)
        # numpy scalar support without importing numpy explicitly
        if hasattr(obj, "item") and callable(getattr(obj, "item")):
            try:
                return obj.item()
            except Exception:
                pass
        if isinstance(obj, (int, float, str)) or obj is None:
            return obj
        try:
            return str(obj)
        except Exception:
            return None

    out_path = Path(__file__).resolve().parent / "ocr_results.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(sanitize(results), f, ensure_ascii=False, indent=2)

    # Minimal final JSON
    final_items: List[Dict[str, Any]] = []
    for r in results:
        primary = ((r.get("geocoding") or {}).get("primary")) or {}
        lokasi = None
        llm_o = (r.get("llm") or {}).get("output") or {}
        if isinstance(llm_o, dict):
            lb = llm_o.get("lokasi_banjir") or {}
            if isinstance(lb, dict):
                lokasi = lb.get("nama")
        if not lokasi:
            cand = (llm_o.get("normalized_query_candidates") if isinstance(llm_o, dict) else None) or []
            if cand:
                lokasi = str(cand[0])
            elif primary:
                lokasi = primary.get("display_name")
        msg = (llm_o.get("ringkasan") if isinstance(llm_o, dict) else None) or ""
        final_items.append({
            "message": msg,
            "lokasi": lokasi or "",
            "lat": primary.get("lat") if isinstance(primary, dict) else None,
            "long": primary.get("lon") if isinstance(primary, dict) else None,
        })
    final_path = Path(__file__).resolve().parent / "ocr_final.json"
    with final_path.open("w", encoding="utf-8") as f:
        json.dump(sanitize(final_items), f, ensure_ascii=False, indent=2)
    print(f"Saved: {out_path}\nSaved minimal: {final_path}")


if __name__ == "__main__":
    main()


