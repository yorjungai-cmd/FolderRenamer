import re
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Segment:
    text: str
    kind: str  # 'preserved' | 'japanese' | 'latin' | 'space'

CJK_RANGES = [(0x3000, 0x9FFF), (0xF900, 0xFAFF), (0xFF00, 0xFFFF)]

PRESERVED_PATTERNS = [
    r'\[[A-Za-z0-9][A-Za-z0-9\- ]*\]',  # [Uncensored], [BT], [4K]
    r'[A-Z]{2,6}-\d{2,5}',              # SSIS-123, ABP-789
    r'\(20\d{2}\)',                       # (2023)
    r'\b(?:4K|8K|1080p|720p|480p|FHD|UHD|HD|SDR|HDR10?)\b',
    r'\b20\d{2}\b',                       # bare year
    r'\b\d{4,}\b',                        # long numeric run
]
_PRESERVED_RE = re.compile('|'.join(PRESERVED_PATTERNS))

def is_cjk(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in CJK_RANGES)

def has_japanese(text: str) -> bool:
    return any(is_cjk(c) for c in text)

def parse_filename(stem: str) -> List[Segment]:
    segments: List[Segment] = []
    pos = 0
    for m in _PRESERVED_RE.finditer(stem):
        if m.start() > pos:
            segments.extend(_classify_free(stem[pos:m.start()]))
        segments.append(Segment(text=m.group(), kind="preserved"))
        pos = m.end()
    if pos < len(stem):
        segments.extend(_classify_free(stem[pos:]))
    return segments

def _classify_free(text: str) -> List[Segment]:
    result: List[Segment] = []
    buf = ""
    kind = None
    for ch in text:
        if ch == " ":
            if buf:
                result.append(Segment(text=buf, kind=kind or "latin"))
                buf = ""
                kind = None
            result.append(Segment(text=" ", kind="space"))
        elif is_cjk(ch):
            if kind == "japanese":
                buf += ch
            else:
                if buf:
                    result.append(Segment(text=buf, kind=kind or "latin"))
                buf, kind = ch, "japanese"
        else:
            if kind == "latin":
                buf += ch
            else:
                if buf:
                    result.append(Segment(text=buf, kind=kind or "latin"))
                buf, kind = ch, "latin"
    if buf:
        result.append(Segment(text=buf, kind=kind or "latin"))
    return result

def collect_japanese(segments: List[Segment]) -> List[Tuple[int, str]]:
    return [(i, s.text) for i, s in enumerate(segments) if s.kind == "japanese"]

def reconstruct(segments: List[Segment], translations: dict) -> str:
    parts = [translations.get(i, s.text) for i, s in enumerate(segments)]
    return "".join(parts).strip()
