"""PE-Core L/14 (ONNX, int8) as a local image/text scorer for "AI+".

Same job as the accepted FAST_LOCAL adapter: frames are compared with short English descriptions and the result is a
logit per (frame, description). Preprocessing and tokenizer follow open_clip's config for timm/PE-Core-L-14-336
(336 px squash resize, bilinear, mean/std 0.5; CLIP BPE, 32 tokens, padding with 0). CI compares this adapter with
the open_clip PyTorch reference (tests/pe_core_probe.py).
"""
from __future__ import annotations

import html, json, re
from pathlib import Path

import numpy as np
from PIL import Image

import p13_pe_core_contract as contract

ADAPTER = "P13_PE_CORE_ONNX_ADAPTER_V1"
LOGIT_SCALE = 100.0           # cosine similarity x 100 (the scale only stretches margins; reels normalise them)
_TOKEN_RE = re.compile(r"<\|startoftext\|>|<\|endoftext\|>|'s|'t|'re|'ve|'m|'ll|'d|[A-Za-z]+|[0-9]|[^\sA-Za-z0-9]+", re.IGNORECASE)


def _bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, (chr(x) for x in cs)))


def _pairs(word):
    return {(a, b) for a, b in zip(word, word[1:])}


class ClipTokenizer:
    """open_clip SimpleTokenizer for ASCII prompts (the prompts are fixed English texts)."""

    def __init__(self, model_dir: Path, context_length: int = contract.CONTEXT_LENGTH):
        model_dir = Path(model_dir)
        self.vocab = json.loads((model_dir / "vocab.json").read_text(encoding="utf-8"))
        lines = (model_dir / "merges.txt").read_text(encoding="utf-8").splitlines()
        if not lines or not lines[0].startswith("#version"):
            raise RuntimeError("P13_TOKENIZER_MERGES_HEADER")
        merges = [tuple(x.split()) for x in lines[1:] if x.strip()]
        self.ranks = dict(zip(merges, range(len(merges))))
        self.byte_encoder = _bytes_to_unicode()
        self.sot, self.eot = int(self.vocab["<|startoftext|>"]), int(self.vocab["<|endoftext|>"])
        self.context_length = int(context_length)
        self.cache: dict[str, str] = {}

    def _bpe(self, token: str) -> str:
        if token in self.cache:
            return self.cache[token]
        word = tuple(token[:-1]) + (token[-1] + "</w>",)
        pairs = _pairs(word)
        if not pairs:
            return token + "</w>"
        while True:
            bigram = min(pairs, key=lambda p: self.ranks.get(p, float("inf")))
            if bigram not in self.ranks:
                break
            first, second = bigram
            new, i = [], 0
            while i < len(word):
                try:
                    j = word.index(first, i)
                except ValueError:
                    new.extend(word[i:]); break
                new.extend(word[i:j]); i = j
                if i < len(word) - 1 and word[i] == first and word[i + 1] == second:
                    new.append(first + second); i += 2
                else:
                    new.append(word[i]); i += 1
            word = tuple(new)
            if len(word) == 1:
                break
            pairs = _pairs(word)
        out = " ".join(word)
        self.cache[token] = out
        return out

    def encode(self, text: str) -> list[int]:
        if not isinstance(text, str) or not text.isascii():
            raise RuntimeError("P13_TOKENIZER_ASCII_PROMPT_REQUIRED")
        text = re.sub(r"\s+", " ", html.unescape(html.unescape(text))).strip().lower()
        ids = []
        for token in _TOKEN_RE.findall(text):
            token = "".join(self.byte_encoder[b] for b in token.encode("utf-8"))
            ids.extend(int(self.vocab[p]) for p in self._bpe(token).split(" "))
        ids = [self.sot] + ids[: self.context_length - 2] + [self.eot]
        return ids + [0] * (self.context_length - len(ids))

    def batch(self, texts) -> np.ndarray:
        return np.asarray([self.encode(t) for t in texts], dtype=np.int64)


def preprocess(image: Image.Image) -> np.ndarray:
    """open_clip transform for PE-Core: squash to 336 x 336 (no crop), bilinear, (x - 0.5) / 0.5, CHW float32."""
    im = image.convert("RGB").resize((contract.IMAGE_SIZE, contract.IMAGE_SIZE), Image.Resampling.BILINEAR)
    arr = np.asarray(im, dtype=np.float32) / np.float32(255.0)
    arr = (arr - np.asarray(contract.IMAGE_MEAN, np.float32)) / np.asarray(contract.IMAGE_STD, np.float32)
    return np.transpose(arr, (2, 0, 1)).astype(np.float32, copy=False)


def _embedding_output(sess) -> str:
    outs = [o for o in sess.get_outputs() if len(o.shape or []) == 2]
    for o in outs:
        if "embed" in o.name.lower():
            return o.name
    if outs:
        return outs[0].name
    raise RuntimeError("P13_ONNX_NO_EMBEDDING_OUTPUT")


class PECoreScorer:
    def __init__(self, model_dir: Path, full_check: bool = True, threads: int | None = None):
        import onnxruntime as ort
        model_dir = Path(model_dir)
        self.identity = dict(contract.validate(model_dir, full_check))
        self.tokenizer = ClipTokenizer(model_dir)
        so = ort.SessionOptions()
        if threads:
            so.intra_op_num_threads = int(threads)
        self.vision = ort.InferenceSession(str(model_dir / "vision_model_int8.onnx"), so, providers=["CPUExecutionProvider"])
        self.text = ort.InferenceSession(str(model_dir / "text_model_int8.onnx"), so, providers=["CPUExecutionProvider"])
        self.vision_in = self.vision.get_inputs()[0].name
        self.vision_out = _embedding_output(self.vision)
        self.text_ins = [x.name for x in self.text.get_inputs()]
        self.text_out = _embedding_output(self.text)
        self.identity.update({"adapter": ADAPTER, "vision_io": [self.vision_in, self.vision_out],
                              "text_io": [self.text_ins, self.text_out]})
        self._text_cache: dict[tuple, np.ndarray] = {}

    @staticmethod
    def _norm(x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float32)
        return x / np.maximum(np.linalg.norm(x, axis=1, keepdims=True), 1e-12)

    # the published ONNX graphs are exported for one item at a time (a reshape keeps batch 1), so items go one by one
    def encode_text(self, texts) -> np.ndarray:
        key = tuple(texts)
        if key not in self._text_cache:
            rows = []
            for ids in self.tokenizer.batch(texts):
                ids = ids[None, :]
                feed = {name: (ids if "mask" not in name.lower() else (ids != 0).astype(np.int64)) for name in self.text_ins}
                rows.append(np.asarray(self.text.run([self.text_out], feed)[0], np.float32).reshape(1, -1))
            self._text_cache[key] = self._norm(np.concatenate(rows, axis=0))
        return self._text_cache[key]

    def encode_images(self, images) -> np.ndarray:
        rows = []
        for im in images:
            px = preprocess(im)[None, ...]
            rows.append(np.asarray(self.vision.run([self.vision_out], {self.vision_in: px})[0], np.float32).reshape(1, -1))
        return self._norm(np.concatenate(rows, axis=0))

    def logits(self, images, prompts) -> np.ndarray:
        if not images or not prompts:
            raise RuntimeError("P13_EMPTY_BATCH")
        return LOGIT_SCALE * (self.encode_images(images) @ self.encode_text(prompts).T)


def margin(logits, positive_count: int) -> list[float]:
    """Same rule as the accepted hook: mean of the two best positive descriptions minus the best negative one."""
    a = np.asarray(logits, dtype=np.float32)
    out = []
    for row in a:
        out.append(float(np.sort(row[:positive_count])[-2:].mean() - np.max(row[positive_count:])))
    return out
