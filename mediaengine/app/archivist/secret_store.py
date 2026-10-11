from __future__ import annotations

import ctypes
import os
import re
from ctypes import wintypes

_PREFIX="Archivist/"
_CRED_TYPE_GENERIC=1
_CRED_PERSIST_LOCAL_MACHINE=2
_ERROR_NOT_FOUND=1168
_MAX_BLOB_BYTES=2500
_KEY_RE=re.compile(r"^[A-Za-z0-9._:@/\-]{1,180}$")

class _CREDENTIALW(ctypes.Structure):
    _fields_=[
        ("Flags",wintypes.DWORD),
        ("Type",wintypes.DWORD),
        ("TargetName",wintypes.LPWSTR),
        ("Comment",wintypes.LPWSTR),
        ("LastWritten",wintypes.FILETIME),
        ("CredentialBlobSize",wintypes.DWORD),
        ("CredentialBlob",ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist",wintypes.DWORD),
        ("AttributeCount",wintypes.DWORD),
        ("Attributes",ctypes.c_void_p),
        ("TargetAlias",wintypes.LPWSTR),
        ("UserName",wintypes.LPWSTR),
    ]

def _windows():
    return os.name=="nt"

def _target(name):
    key=str(name or "").strip()
    if not _KEY_RE.fullmatch(key):
        raise ValueError("Invalid secret key")
    return _PREFIX+key

def _api():
    if not _windows():
        raise RuntimeError("OS-backed secret store is not implemented on this platform")
    adv=ctypes.WinDLL("Advapi32.dll",use_last_error=True)
    adv.CredWriteW.argtypes=[ctypes.POINTER(_CREDENTIALW),wintypes.DWORD]
    adv.CredWriteW.restype=wintypes.BOOL
    adv.CredReadW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(_CREDENTIALW))]
    adv.CredReadW.restype=wintypes.BOOL
    adv.CredDeleteW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD]
    adv.CredDeleteW.restype=wintypes.BOOL
    adv.CredFree.argtypes=[ctypes.c_void_p]
    adv.CredFree.restype=None
    return adv

def capabilities():
    return {
        "adapter":"windows_credential_manager" if _windows() else "not_implemented",
        "implemented":_windows(),
        "validated":_windows(),
        "plaintext_config_allowed":False,
        "supabase_secret_storage_allowed":False,
        "max_secret_bytes":_MAX_BLOB_BYTES if _windows() else 0,
        "scope":"current_windows_user" if _windows() else None,
    }

def set_secret(name,value):
    target=_target(name)
    secret=str(value)
    raw=secret.encode("utf-16-le")
    if not raw:
        raise ValueError("Secret value must not be empty")
    if len(raw)>_MAX_BLOB_BYTES:
        raise ValueError("Secret exceeds Windows Credential Manager blob limit")
    adv=_api()
    buf=ctypes.create_string_buffer(raw)
    cred=_CREDENTIALW()
    cred.Flags=0
    cred.Type=_CRED_TYPE_GENERIC
    cred.TargetName=target
    cred.Comment="Archivist OS-backed secret"
    cred.CredentialBlobSize=len(raw)
    cred.CredentialBlob=ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte))
    cred.Persist=_CRED_PERSIST_LOCAL_MACHINE
    cred.AttributeCount=0
    cred.Attributes=None
    cred.TargetAlias=None
    cred.UserName="Archivist"
    if not adv.CredWriteW(ctypes.byref(cred),0):
        err=ctypes.get_last_error()
        raise OSError(err,"CredWriteW failed")
    return True

def get_secret(name):
    target=_target(name)
    adv=_api()
    out=ctypes.POINTER(_CREDENTIALW)()
    if not adv.CredReadW(target,_CRED_TYPE_GENERIC,0,ctypes.byref(out)):
        err=ctypes.get_last_error()
        if err==_ERROR_NOT_FOUND:
            return None
        raise OSError(err,"CredReadW failed")
    try:
        cred=out.contents
        raw=ctypes.string_at(cred.CredentialBlob,int(cred.CredentialBlobSize)) if cred.CredentialBlobSize else b""
        return raw.decode("utf-16-le")
    finally:
        adv.CredFree(out)

def delete_secret(name):
    target=_target(name)
    adv=_api()
    if adv.CredDeleteW(target,_CRED_TYPE_GENERIC,0):
        return True
    err=ctypes.get_last_error()
    if err==_ERROR_NOT_FOUND:
        return False
    raise OSError(err,"CredDeleteW failed")

def has_secret(name):
    return get_secret(name) is not None
