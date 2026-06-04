"""
YouTube n-parameter and signature cipher decoding.
Mirrors the logic in YoutubeJavaScriptPlayerManager / YoutubeParsingHelper.
"""
import re
import json
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from typing import Optional


def _extract_function_body(js: str, func_name: str) -> Optional[str]:
    """Extract a JS function body by name."""
    escaped = re.escape(func_name)
    pattern = rf'{escaped}\s*=\s*function\s*\(([^)]*)\)\s*\{{(.*?)\}}'
    m = re.search(pattern, js, re.DOTALL)
    if m:
        return m.group(2)
    pattern2 = rf'function\s+{escaped}\s*\(([^)]*)\)\s*\{{(.*?)\}}'
    m = re.search(pattern2, js, re.DOTALL)
    if m:
        return m.group(2)
    return None


# ── n-parameter throttling ────────────────────────────────────────────────────

def _extract_n_function_name(js: str) -> Optional[str]:
    """Find the name of the n-parameter transformation function."""
    patterns = [
        r'\.get\("n"\)\)&&\(b=([a-zA-Z0-9$]{2,3})(?:\[(\d+)\])?\([a-zA-Z0-9]\)',
        r'\([a-z]\)=([a-zA-Z0-9$]{2,3})(?:\[(\d+)\])?\([a-z]\)',
        r'b=a\.get\("n"\)\)&&\(b=([a-zA-Z0-9$]+)\[(\d+)\]\(b\)',
    ]
    for pattern in patterns:
        m = re.search(pattern, js)
        if m:
            name = m.group(1)
            idx_str = m.group(2) if len(m.groups()) > 1 else None
            if idx_str is not None:
                # Function is stored in an array: NAME[idx]
                arr_pattern = rf'var {re.escape(name)}\s*=\s*\[(.+?)\]'
                am = re.search(arr_pattern, js)
                if am:
                    items = [x.strip() for x in am.group(1).split(",")]
                    idx = int(idx_str)
                    if 0 <= idx < len(items):
                        return items[idx]
            else:
                return name
    return None


def _apply_n_transform(js: str, n_value: str) -> str:
    """
    Apply the YouTube n-parameter transformation using a basic Python
    reimplementation of the JS logic extracted from the player.
    Falls back to returning original if extraction fails.
    """
    func_name = _extract_n_function_name(js)
    if not func_name:
        return n_value

    body = _extract_function_body(js, func_name)
    if not body:
        return n_value

    # Attempt execution via subprocess + node if available, else return original
    try:
        import subprocess, tempfile, os
        script = f"var b={json.dumps(n_value)};{body};console.log(b);"
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            tmp = f.name
        result = subprocess.run(
            ["node", tmp], capture_output=True, text=True, timeout=5
        )
        os.unlink(tmp)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return n_value


# ── Signature cipher ──────────────────────────────────────────────────────────

def _extract_sig_function_name(js: str) -> Optional[str]:
    patterns = [
        r'\.sig\|\|([a-zA-Z0-9$]{2,3})\(',
        r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+,(?:encodeURIComponent\()?\s*([a-zA-Z0-9$]+)\(',
        r'\b([a-zA-Z0-9$]{2,})\s*=\s*function\([a-z]\)\s*\{[a-z]=\s*[a-z]\.split\(""\)',
    ]
    for p in patterns:
        m = re.search(p, js)
        if m:
            return m.group(1)
    return None


def _parse_sig_operations(js: str, func_name: str) -> list:
    body = _extract_function_body(js, func_name)
    if not body:
        return []

    helper_obj = re.search(r';([a-zA-Z0-9$]{2,3})\.\w+\(', body)
    if not helper_obj:
        return []
    obj_name = helper_obj.group(1)

    obj_pattern = rf'var {re.escape(obj_name)}\s*=\s*\{{(.+?)\}};'
    om = re.search(obj_pattern, js, re.DOTALL)
    if not om:
        return []
    obj_body = om.group(1)

    funcs = {}
    for m in re.finditer(r'(\w+)\s*:\s*function\([a-z,]+\)\s*\{([^}]+)\}', obj_body):
        fn, fb = m.group(1), m.group(2)
        if "splice" in fb:
            funcs[fn] = "splice"
        elif "reverse" in fb:
            funcs[fn] = "reverse"
        elif len(fb.strip().split(";")) <= 2:
            funcs[fn] = "swap"

    ops = []
    for m in re.finditer(rf'{re.escape(obj_name)}\.(\w+)\([a-z],(\d+)\)', body):
        fn, n = m.group(1), int(m.group(2))
        op = funcs.get(fn)
        if op:
            ops.append((op, n))
    return ops


def _apply_sig_operations(sig: str, ops: list) -> str:
    chars = list(sig)
    for op, n in ops:
        if op == "reverse":
            chars = chars[::-1]
        elif op == "splice":
            chars = chars[n:]
        elif op == "swap":
            chars[0], chars[n % len(chars)] = chars[n % len(chars)], chars[0]
    return "".join(chars)


# ── Public API ────────────────────────────────────────────────────────────────

class SignatureCipher:
    def __init__(self, player_js: str):
        self._js = player_js
        self._n_js_url = None
        self._sig_ops = None
        self._sig_func_name = None

    def _ensure_sig_ops(self):
        if self._sig_ops is None:
            name = _extract_sig_function_name(self._js)
            self._sig_func_name = name
            self._sig_ops = _parse_sig_operations(self._js, name) if name else []

    def decode_stream_url(self, url: str) -> str:
        """Decode a stream URL that may have a signature cipher or throttled n-param."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Handle signatureCipher / cipher
        sc = params.get("signatureCipher") or params.get("cipher")
        if sc:
            cipher_params = parse_qs(sc[0])
            raw_url = cipher_params.get("url", [""])[0]
            sig = cipher_params.get("s", [""])[0]
            sp = cipher_params.get("sp", ["sig"])[0]
            if sig:
                self._ensure_sig_ops()
                sig = _apply_sig_operations(sig, self._sig_ops)
            url = f"{raw_url}&{sp}={sig}"
            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)

        # Handle n-parameter throttling
        n_vals = params.get("n")
        if n_vals:
            new_n = _apply_n_transform(self._js, n_vals[0])
            params["n"] = [new_n]
            new_query = urlencode({k: v[0] for k, v in params.items()})
            url = urlunparse(parsed._replace(query=new_query))

        return url
