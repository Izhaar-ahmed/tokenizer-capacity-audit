"""Tokenizer loader shared by bug_isolation.py and corrected_analysis.py.

Usage: enc("gpt2").encode(text) -> list[int]

On a machine with normal internet access this just wraps tiktoken:
    tiktoken.get_encoding("gpt2")
works out of the box and this module is unnecessary. It exists because the
environment this was authored in had no route to openaipublic.blob.core.
windows.net or huggingface.co. As a fallback it loads the exact same GPT-2
BPE rank table from the `openai-whisper` PyPI package's bundled assets
(whisper/assets/gpt2.tiktoken is byte-identical to tiktoken's "gpt2"
encoding), and whisper/assets/multilingual.tiktoken as a second, genuinely
multilingual byte-BPE tokenizer. Both come from a plain `pip install
openai-whisper`, no blocked hosts involved.

For the "Indic-aware" tokenizer A3 asks for, swap in a real one once you
have network access, e.g.:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("ai4bharat/IndicBERTv2-MLM-only")
    encode = lambda s: tok.encode(s, add_special_tokens=False)
"""
import os


def _whisper_assets_dir():
    candidates = [
        os.environ.get("WHISPER_ASSETS_DIR", ""),
        os.path.expanduser("~/.cache/openai_whisper_assets"),
    ]
    for d in candidates:
        if d and os.path.isdir(d):
            return d
    try:
        import whisper
        d = os.path.join(os.path.dirname(whisper.__file__), "assets")
        if os.path.isdir(d):
            return d
    except ImportError:
        pass
    return None


def enc(name: str):
    """name: 'gpt2' or 'multilingual'. Returns a tiktoken Encoding
    (call .encode(text) on it)."""
    import tiktoken
    try:
        return tiktoken.get_encoding(name)
    except Exception:
        pass  # no network route to the remote vocab; fall back below

    from tiktoken.load import load_tiktoken_bpe

    assets = _whisper_assets_dir()
    if assets is None:
        raise RuntimeError(
            "Could not reach tiktoken's remote vocab and no local "
            "openai-whisper assets were found. Run `pip install "
            "openai-whisper` (PyPI only, no blocked hosts) so this "
            "fallback can load gpt2.tiktoken / multilingual.tiktoken, "
            "or restore normal internet access."
        )
    GPT2_PAT = (
        r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+|"""
        r""" ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
    )
    ranks = load_tiktoken_bpe(f"{assets}/{name}.tiktoken")
    import tiktoken as tk
    return tk.Encoding(
        name=name, explicit_n_vocab=len(ranks),
        pat_str=GPT2_PAT, mergeable_ranks=ranks, special_tokens={},
    )
