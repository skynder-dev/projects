"""Qualified text-only Qwen chat framing; no model manifest/auth changes."""
def render(system,user):
 return '<|im_start|>system\n'+system.strip()+'<|im_end|>\n<|im_start|>user\n'+user.strip()+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
