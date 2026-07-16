"""
app/services/image_forensics.py

Deterministic (non-LLM) image forensics. This is the "hard evidence" layer
that sits alongside the vision-LLM opinion in app/routers/detect_image.py.

Design goals:
- No GPU, no heavy deps beyond Pillow -> runs fine on a small Render instance.
- Never raises on malformed/stripped metadata -> always returns a signals dict.
- Every signal is explainable in one line, so it can feed straight into the
  "one-line rationale" stamp UI the text detector already uses.

What it looks for (roughly strongest -> weakest signal):
1. Known AI-generator metadata fingerprints (Stable Diffusion / Automatic1111
   "parameters" PNG chunk, ComfyUI workflow JSON, Midjourney/DALL-E/Firefly
   "Software"/"XMP" tags). These are near-certain when present, but easy to
   strip, so ABSENCE proves nothing.
2. C2PA "Content Credentials" markers (JUMBF box / c2pa manifest bytes).
   Camera vendors and some AI tools (Adobe Firefly, Bing/DALL-E via Azure,
   Leica cameras) now embed these. Presence is strong signal either way IF
   the manifest can be parsed enough to read the claim_generator field.
3. Ordinary camera EXIF completeness (Make/Model/FocalLength/ExposureTime/
   GPS/LensModel). Real camera photos usually have a rich, internally
   consistent EXIF block. Its total absence is weak-but-real evidence for
   AI/screenshot/edited origin -- NOT proof, since exports (WhatsApp,
   Instagram, resizers) strip EXIF too. We surface this as a "weak" signal
   and say so explicitly.

This module intentionally returns raw findings + a heuristic score, and
leaves final verdict fusion to the router. Keep it dumb and honest.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from typing import Any

from PIL import Image, ExifTags


# Known metadata fingerprints for popular AI image generators.
# Matched case-insensitively against relevant EXIF/PNG-text/XMP fields.
AI_SOFTWARE_FINGERPRINTS = {
    "midjourney": "Midjourney",
    "dall-e": "OpenAI DALL-E",
    "dalle": "OpenAI DALL-E",
    "openai": "OpenAI (DALL-E / ChatGPT image)",
    "stable diffusion": "Stable Diffusion",
    "stablediffusion": "Stable Diffusion",
    "automatic1111": "Stable Diffusion (AUTOMATIC1111 WebUI)",
    "comfyui": "Stable Diffusion (ComfyUI)",
    "invokeai": "Stable Diffusion (InvokeAI)",
    "adobe firefly": "Adobe Firefly",
    "firefly": "Adobe Firefly",
    "leonardo.ai": "Leonardo.Ai",
    "nightcafe": "NightCafe",
    "playground ai": "Playground AI",
    "ideogram": "Ideogram",
    "flux": "Black Forest Labs FLUX",
    "runway": "Runway",
    "google gemini": "Google Gemini / Imagen",
    "imagen": "Google Imagen",
}

# PNG text/EXIF/XMP keys worth inspecting for the fingerprints above,
# and for raw generation parameters (prompt/seed/sampler/model hash).
INTERESTING_TEXT_KEYS = {
    "parameters",       # Automatic1111 SD WebUI writes the full prompt+params here
    "prompt",           # ComfyUI / others
    "workflow",         # ComfyUI node graph JSON
    "software",         # generic EXIF Software tag
    "description",
    "comment",
    "xmp",
    "generation_data",
}

CAMERA_EXIF_FIELDS = {
    "Make", "Model", "LensModel", "FocalLength", "ExposureTime",
    "FNumber", "ISOSpeedRatings", "DateTimeOriginal", "GPSInfo",
}


@dataclass
class ForensicSignal:
    id: str
    label: str
    strength: str          # "strong" | "moderate" | "weak"
    points_to: str          # "ai" | "human" | "inconclusive"
    detail: str


@dataclass
class ForensicReport:
    signals: list[ForensicSignal] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    heuristic_score: float = 0.0   # -1.0 (confidently human) .. +1.0 (confidently AI)

    def add(self, signal: ForensicSignal, weight: float) -> None:
        self.signals.append(signal)
        self.heuristic_score += weight if signal.points_to == "ai" else (
            -weight if signal.points_to == "human" else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "signals": [s.__dict__ for s in self.signals],
            "heuristic_score": round(max(-1.0, min(1.0, self.heuristic_score)), 3),
            "raw_metadata_keys": sorted(self.raw_metadata.keys()),
        }


def _find_fingerprint(text: str) -> str | None:
    lowered = text.lower()
    for needle, label in AI_SOFTWARE_FINGERPRINTS.items():
        if needle in lowered:
            return label
    return None


def _extract_png_text_chunks(img: Image.Image) -> dict[str, str]:
    # Pillow surfaces PNG tEXt/iTXt/zTXt chunks directly in Image.info
    found = {}
    for key, value in (img.info or {}).items():
        if key.lower() in INTERESTING_TEXT_KEYS and isinstance(value, str) and value.strip():
            found[key] = value
    return found


def _extract_exif(img: Image.Image) -> dict[str, Any]:
    exif_dict: dict[str, Any] = {}
    try:
        raw_exif = img.getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                # Keep it JSON-safe; bytes/rationals get stringified.
                try:
                    json.dumps(value)
                    exif_dict[tag] = value
                except TypeError:
                    exif_dict[tag] = str(value)
    except Exception:
        pass
    return exif_dict


def _detect_c2pa_marker(raw_bytes: bytes) -> bool:
    # Lightweight heuristic: look for the JUMBF/C2PA box type or manifest
    # markers in the raw byte stream. This is NOT a full C2PA manifest
    # parse/signature-verification -- just presence detection. If the
    # `c2pa` python package is available, prefer that for a real read.
    markers = (b"c2pa", b"C2PA", b"jumb", b"urn:uuid:", b"application/c2pa")
    return any(m in raw_bytes[:200_000] for m in markers)  # cap scan for speed


def analyze_image(image_bytes: bytes) -> ForensicReport:
    """
    Main entry point. Never raises -- on any parse failure, returns a
    report with an 'unreadable metadata' signal instead of crashing the
    request.
    """
    report = ForensicReport()

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception as e:
        report.add(
            ForensicSignal(
                id="unreadable",
                label="Image could not be parsed",
                strength="weak",
                points_to="inconclusive",
                detail=f"Pillow failed to decode the file ({e.__class__.__name__}); "
                       f"skipping metadata analysis.",
            ),
            weight=0.0,
        )
        return report

    # 1. AI-generator text/metadata fingerprints (strong signal)
    text_chunks = _extract_png_text_chunks(img)
    exif = _extract_exif(img)
    report.raw_metadata = {**text_chunks, **{f"exif.{k}": v for k, v in exif.items()}}

    combined_text_blobs = list(text_chunks.values()) + [
        str(exif.get(k, "")) for k in ("Software", "Artist", "ImageDescription", "XPComment")
    ]
    fingerprint_hit = None
    hit_source = None
    for key, blob in {**text_chunks, "exif.Software": str(exif.get("Software", ""))}.items():
        fp = _find_fingerprint(blob)
        if fp:
            fingerprint_hit = fp
            hit_source = key
            break

    if fingerprint_hit:
        report.add(
            ForensicSignal(
                id="ai_metadata_fingerprint",
                label=f"Embedded metadata identifies generator: {fingerprint_hit}",
                strength="strong",
                points_to="ai",
                detail=f"Field '{hit_source}' contains a known AI-tool signature. "
                       f"This is near-conclusive when present, but easily stripped "
                       f"by re-saving/screenshotting, so its absence proves nothing.",
            ),
            weight=0.9,
        )

    # 1b. Raw SD-style generation parameters (prompt/seed/sampler/model hash)
    if "parameters" in text_chunks and not fingerprint_hit:
        report.add(
            ForensicSignal(
                id="sd_generation_params",
                label="PNG contains Stable-Diffusion-style generation parameters",
                strength="strong",
                points_to="ai",
                detail="A 'parameters' text chunk with prompt/seed/sampler data is "
                       "written by SD WebUIs and not by cameras or normal editors.",
            ),
            weight=0.9,
        )

    # 2. C2PA / Content Credentials marker (moderate-strong, heuristic only)
    if _detect_c2pa_marker(image_bytes):
        report.add(
            ForensicSignal(
                id="c2pa_marker_present",
                label="Possible C2PA Content Credentials manifest detected",
                strength="moderate",
                points_to="inconclusive",
                detail="Byte-level markers suggest an embedded C2PA manifest, but this "
                       "build only detects presence -- it does not parse the manifest's "
                       "claim_generator field or verify its signature, so it can't yet "
                       "say whether the credential claims AI or camera origin.",
            ),
            weight=0.0,
        )

    # 3. Camera EXIF completeness (weak signal, explicitly caveated)
    present_camera_fields = CAMERA_EXIF_FIELDS.intersection(exif.keys())
    if len(present_camera_fields) >= 4:
        report.add(
            ForensicSignal(
                id="rich_camera_exif",
                label=f"Rich camera EXIF present ({len(present_camera_fields)} fields: "
                      f"{', '.join(sorted(present_camera_fields))})",
                strength="weak",
                points_to="human",
                detail="Consistent camera/lens/exposure metadata is typical of an "
                       "unedited camera photo. Weak signal only: many legitimate "
                       "human photos lose EXIF via messaging apps or social export, "
                       "and metadata can be forged.",
            ),
            weight=0.25,
        )
    elif not exif and not text_chunks:
        report.add(
            ForensicSignal(
                id="no_metadata",
                label="No EXIF or text metadata found",
                strength="weak",
                points_to="inconclusive",
                detail="Absence of metadata is common for AI-generated images, "
                       "screenshots, and re-compressed/re-exported photos alike -- "
                       "on its own this does not distinguish AI from human origin.",
            ),
            weight=0.0,
        )

    return report
