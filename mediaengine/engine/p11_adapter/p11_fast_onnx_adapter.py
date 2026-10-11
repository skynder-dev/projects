from __future__ import annotations
import html, importlib.metadata, json, math, re
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
from validate_p11_model_contract import SUPPORT_DIR, RUNTIME, validate

CONTEXT_LENGTH = 77
IMAGE_SIZE = 224
IMAGE_MEAN = np.asarray([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
IMAGE_STD = np.asarray([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)
ASCII_PATTERN = re.compile(r"<\|startoftext\|>|<\|endoftext\|>|'s|'t|'re|'ve|'m|'ll|'d|[A-Za-z]+|[0-9]|[^\sA-Za-z0-9]+", re.IGNORECASE)


def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, (chr(x) for x in cs)))


def get_pairs(word):
    pairs = set()
    prev = word[0]
    for char in word[1:]:
        pairs.add((prev, char)); prev = char
    return pairs


class FrozenClipProcessor:
    def __init__(self, support_dir: Path):
        self.support_dir = Path(support_dir)
        self.vocab = json.loads((self.support_dir / "vocab.json").read_text(encoding="utf-8"))
        lines = (self.support_dir / "merges.txt").read_text(encoding="utf-8").splitlines()
        if not lines or not lines[0].startswith("#version"):
            raise RuntimeError("P11_TOKENIZER_MERGES_HEADER")
        merges = [tuple(x.split()) for x in lines[1:] if x.strip()]
        self.bpe_ranks = dict(zip(merges, range(len(merges))))
        self.byte_encoder = bytes_to_unicode()
        self.cache = {"<|startoftext|>": "<|startoftext|>", "<|endoftext|>": "<|endoftext|>"}
        self.bos = int(self.vocab["<|startoftext|>"])
        self.eos = int(self.vocab["<|endoftext|>"])
        if (self.bos, self.eos) != (49406, 49407):
            raise RuntimeError("P11_TOKENIZER_SPECIAL_IDS")

    def bpe(self, token: str) -> str:
        if token in self.cache:
            return self.cache[token]
        if not token:
            return ""
        word = tuple(token[:-1]) + (token[-1] + "</w>",)
        pairs = get_pairs(word)
        if not pairs:
            return token + "</w>"
        while True:
            bigram = min(pairs, key=lambda p: self.bpe_ranks.get(p, float("inf")))
            if bigram not in self.bpe_ranks:
                break
            first, second = bigram
            new_word = []
            i = 0
            while i < len(word):
                try:
                    j = word.index(first, i); new_word.extend(word[i:j]); i = j
                except ValueError:
                    new_word.extend(word[i:]); break
                if i < len(word) - 1 and word[i] == first and word[i + 1] == second:
                    new_word.append(first + second); i += 2
                else:
                    new_word.append(word[i]); i += 1
            word = tuple(new_word)
            if len(word) == 1:
                break
            pairs = get_pairs(word)
        out = " ".join(word)
        self.cache[token] = out
        return out

    def encode_text(self, text: str):
        if not isinstance(text, str) or not text.isascii():
            raise RuntimeError("P11_TOKENIZER_ASCII_PROMPT_REQUIRED")
        text = html.unescape(html.unescape(text)).strip().lower()
        ids = []
        for token in ASCII_PATTERN.findall(text):
            encoded = "".join(self.byte_encoder[b] for b in token.encode("utf-8"))
            for piece in self.bpe(encoded).split(" "):
                try:
                    ids.append(int(self.vocab[piece]))
                except KeyError as exc:
                    raise RuntimeError("P11_TOKENIZER_UNKNOWN_PIECE:" + piece) from exc
        ids = [self.bos] + ids[: CONTEXT_LENGTH - 2] + [self.eos]
        mask = [1] * len(ids)
        if len(ids) < CONTEXT_LENGTH:
            pad = CONTEXT_LENGTH - len(ids)
            ids.extend([self.eos] * pad); mask.extend([0] * pad)
        return ids, mask

    def encode_prompts(self, prompts):
        rows = [self.encode_text(p) for p in prompts]
        return (
            np.asarray([x[0] for x in rows], dtype=np.int64),
            np.asarray([x[1] for x in rows], dtype=np.int64),
        )

    def preprocess_image(self, image: Image.Image):
        im = image.convert("RGB")
        w, h = im.size
        if min(w, h) <= 0:
            raise RuntimeError("P11_IMAGE_EMPTY")
        scale = IMAGE_SIZE / float(min(w, h))
        nw = max(IMAGE_SIZE, int(round(w * scale))); nh = max(IMAGE_SIZE, int(round(h * scale)))
        im = im.resize((nw, nh), Image.Resampling.BICUBIC)
        left = (nw - IMAGE_SIZE) // 2; top = (nh - IMAGE_SIZE) // 2
        im = im.crop((left, top, left + IMAGE_SIZE, top + IMAGE_SIZE))
        arr = np.asarray(im, dtype=np.float32) / np.float32(255.0)
        arr = (arr - IMAGE_MEAN) / IMAGE_STD
        return np.transpose(arr, (2, 0, 1)).astype(np.float32, copy=False)

    def preprocess_images(self, images):
        return np.stack([self.preprocess_image(x) for x in images], axis=0)


def _runtime_versions():
    out = {}
    for dist in ("onnxruntime", "numpy", "Pillow"):
        out[dist] = importlib.metadata.version(dist)
    return out


def load_runtime(profile_dir: Path):
    profile_dir = Path(profile_dir)
    ident = validate("FAST_LOCAL", profile_dir)
    versions = _runtime_versions()
    for name, expected in RUNTIME.items():
        if versions.get(name) != expected:
            raise RuntimeError(f"P11_RUNTIME_PIN:{name}:{versions.get(name)}!={expected}")
    import onnxruntime as ort
    processor = FrozenClipProcessor(profile_dir / SUPPORT_DIR)
    sess = ort.InferenceSession(str(profile_dir / "model_int8.onnx"), providers=["CPUExecutionProvider"])
    ins = {x.name: (x.type, x.shape) for x in sess.get_inputs()}
    outs = {x.name: (x.type, x.shape) for x in sess.get_outputs()}
    if set(ins) != {"input_ids", "pixel_values", "attention_mask"}:
        raise RuntimeError("P11_ONNX_INPUT_SCHEMA")
    if not {"logits_per_image", "logits_per_text", "text_embeds", "image_embeds"}.issubset(set(outs)):
        raise RuntimeError("P11_ONNX_OUTPUT_SCHEMA")
    ident = dict(ident)
    ident.update({"adapter": "P11_FAST_ONNX_ADAPTER_SHADOW_V1", "runtime_versions": versions, "context_length": CONTEXT_LENGTH, "image_size": IMAGE_SIZE})
    return processor, sess, ident


def semantic_logits(processor: FrozenClipProcessor, sess, images, prompts):
    if not images or not prompts:
        raise RuntimeError("P11_SEMANTIC_EMPTY_BATCH")
    if not all(isinstance(x, str) and x.isascii() for x in prompts):
        raise RuntimeError("P11_SEMANTIC_PROMPT_CONTRACT")
    input_ids, attention_mask = processor.encode_prompts(prompts)
    pixel_values = processor.preprocess_images(images)
    out = sess.run(["logits_per_image"], {
        "input_ids": input_ids,
        "pixel_values": pixel_values,
        "attention_mask": attention_mask,
    })[0]
    logits = np.asarray(out, dtype=np.float32)
    if logits.shape != (len(images), len(prompts)):
        raise RuntimeError(f"P11_SEMANTIC_OUTPUT_SHAPE:{logits.shape}")
    return logits


def semantic_margin(logits, positive_count: int):
    a = np.asarray(logits, dtype=np.float32)
    if a.ndim != 2 or positive_count < 2 or positive_count >= a.shape[1]:
        raise RuntimeError("P11_SEMANTIC_MARGIN_SHAPE")
    out = []
    for row in a:
        pos = np.sort(row[:positive_count])[-2:].mean()
        neg = np.max(row[positive_count:])
        out.append(float(pos - neg))
    return out
