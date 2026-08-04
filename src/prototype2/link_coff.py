#!/usr/bin/env python3
"""Minimal COFF→PE linker for abassembler output (i386)."""
import struct
import sys
from pathlib import Path

IMAGE_BASE = 0x00400000
TEXT_RVA = 0x00001000
SECTION_ALIGN = 0x1000
FILE_ALIGN = 0x200
SIZEOF_HEADERS = 0x400


def align(v: int, a: int) -> int:
    return (v + a - 1) & ~(a - 1)


def read_sym_name(obj: bytes, symptr: int, nsym: int, idx: int) -> str:
    o = symptr + idx * 18
    zeroes = struct.unpack_from("<I", obj, o)[0]
    if zeroes == 0:
        stroff = struct.unpack_from("<I", obj, o + 4)[0]
        stab = symptr + nsym * 18
        end = obj.index(b"\x00", stab + stroff)
        return obj[stab + stroff : end].decode("ascii", "ignore")
    return obj[o : o + 8].split(b"\x00")[0].decode("ascii", "ignore")


def undecorate(name: str) -> str:
    if name.startswith("_"):
        name = name[1:]
    if "@" in name:
        name = name.split("@", 1)[0]
    return name


def lookup_dll(func: str) -> str:
    if func in ("MessageBoxA", "MessageBoxW", "wsprintfA"):
        return "user32.dll"
    return "kernel32.dll"


def link(obj_path: Path, out_path: Path) -> None:
    obj = obj_path.read_bytes()
    machine, nsect, _td, symptr, nsym, opthdr, _ch = struct.unpack_from("<HHIIIHH", obj, 0)
    if machine != 0x14C:
        raise SystemExit("not i386 COFF")

    text = data = None
    off = 20 + opthdr
    for _ in range(nsect):
        name = obj[off : off + 8].split(b"\x00")[0].decode("ascii", "ignore")
        _vs, _va, rawsz, rawptr, relptr, _pl, nrel, _nl, _chars = struct.unpack_from(
            "<IIIIIIHHI", obj, off + 8
        )
        info = {"name": name, "raw": rawsz, "ptr": rawptr, "relptr": relptr, "nrel": nrel}
        if name == ".text":
            text = info
        elif name == ".data":
            data = info
        off += 40

    if not text or text["raw"] == 0:
        raise SystemExit(".text missing")

    code = bytearray(obj[text["ptr"] : text["ptr"] + text["raw"]])
    data_bytes = b""
    has_data = data is not None and data["raw"] > 0
    if has_data:
        data_bytes = obj[data["ptr"] : data["ptr"] + data["raw"]]

    syms = []
    i = 0
    while i < nsym:
        o = symptr + i * 18
        val, sect, _st, _scl, naux = struct.unpack_from("<IHHBB", obj, o + 8)
        syms.append(
            {
                "name": read_sym_name(obj, symptr, nsym, i),
                "val": val,
                "sect": sect,
                "naux": naux,
            }
        )
        i += 1 + naux
        while len(syms) < i and len(syms) < nsym:
            # pad aux slots so symidx from reloc matches table index
            pass
    # Rebuild full table indexed by COFF index (including aux as placeholders)
    syms = [None] * nsym
    i = 0
    while i < nsym:
        o = symptr + i * 18
        val, sect, _st, _scl, naux = struct.unpack_from("<IHHBB", obj, o + 8)
        syms[i] = {
            "name": read_sym_name(obj, symptr, nsym, i),
            "val": val,
            "sect": sect,
            "naux": naux,
        }
        for a in range(1, naux + 1):
            if i + a < nsym:
                syms[i + a] = {"name": "", "val": 0, "sect": 0, "naux": 0}
        i += 1 + naux

    g_text_virt = max(text["raw"], 0x10)
    g_data_virt = max(len(data_bytes), 4) if has_data else 0
    g_data_rva = align(TEXT_RVA + g_text_virt, SECTION_ALIGN)
    if has_data:
        g_idata_rva = align(g_data_rva + g_data_virt, SECTION_ALIGN)
    else:
        g_idata_rva = g_data_rva
        g_data_rva = 0

    sec_rva = {1: TEXT_RVA}
    if has_data:
        sec_rva[2] = g_data_rva

    # Collect imports
    imps = []
    seen = set()
    for j in range(text["nrel"]):
        _va, symidx, _rt = struct.unpack_from("<IIH", obj, text["relptr"] + j * 10)
        s = syms[symidx]
        if s["sect"] == 0:
            fn = undecorate(s["name"])
            if fn not in seen:
                seen.add(fn)
                imps.append(fn)

    # Group by DLL
    dll_order = []
    dll_funcs = {}
    for fn in imps:
        dll = lookup_dll(fn)
        if dll not in dll_funcs:
            dll_funcs[dll] = []
            dll_order.append(dll)
        dll_funcs[dll].append(fn)

    # Build .idata
    idt_size = (len(dll_order) + 1) * 20
    pos = idt_size
    ilt_off = {}
    iat_off = {}
    dll_name_off = {}
    hint_off = {}
    for dll in dll_order:
        ilt_off[dll] = pos
        pos += 4 * (len(dll_funcs[dll]) + 1)
    iat_start = pos
    for dll in dll_order:
        iat_off[dll] = pos
        pos += 4 * (len(dll_funcs[dll]) + 1)
    for dll in dll_order:
        pos = align(pos, 2)
        dll_name_off[dll] = pos
        pos += len(dll.encode()) + 1
    for dll in dll_order:
        for fn in dll_funcs[dll]:
            pos = align(pos, 2)
            hint_off[fn] = pos
            pos += 2 + len(fn.encode()) + 1
    pos = align(pos, 4)
    iat_rva = {}
    thunk_rva = {}
    for dll in dll_order:
        for i, fn in enumerate(dll_funcs[dll]):
            iat_rva[fn] = g_idata_rva + iat_off[dll] + i * 4
            thunk_rva[fn] = g_idata_rva + pos
            pos += 8

    idata_virt = pos
    idata_raw = align(max(idata_virt, 1), FILE_ALIGN)
    idata = bytearray(idata_raw)

    for di, dll in enumerate(dll_order):
        struct.pack_into("<IIIII", idata, di * 20,
                         g_idata_rva + ilt_off[dll], 0, 0,
                         g_idata_rva + dll_name_off[dll],
                         g_idata_rva + iat_off[dll])
    for dll in dll_order:
        for i, fn in enumerate(dll_funcs[dll]):
            struct.pack_into("<I", idata, ilt_off[dll] + i * 4, g_idata_rva + hint_off[fn])
            struct.pack_into("<I", idata, iat_off[dll] + i * 4, g_idata_rva + hint_off[fn])
        idata[dll_name_off[dll] : dll_name_off[dll] + len(dll)] = dll.encode()
        for fn in dll_funcs[dll]:
            hb = hint_off[fn]
            idata[hb + 2 : hb + 2 + len(fn)] = fn.encode()
            # jmp [iat]
            th = thunk_rva[fn] - g_idata_rva
            idata[th] = 0xFF
            idata[th + 1] = 0x25
            struct.pack_into("<I", idata, th + 2, IMAGE_BASE + iat_rva[fn])

    # Entry
    entry_rva = TEXT_RVA
    for s in syms:
        if s and s["sect"] == 1 and s["name"] in ("_main", "main"):
            entry_rva = TEXT_RVA + s["val"]
            break

    # Apply relocs
    for j in range(text["nrel"]):
        va, symidx, rtype = struct.unpack_from("<IIH", obj, text["relptr"] + j * 10)
        s = syms[symidx]
        if s["sect"] == 0:
            fn = undecorate(s["name"])
            if rtype == 6:
                target = IMAGE_BASE + iat_rva[fn]
            else:
                target = IMAGE_BASE + thunk_rva[fn]
        else:
            target = IMAGE_BASE + sec_rva[s["sect"]] + s["val"]
        if rtype == 0x14:
            rel = target - (IMAGE_BASE + TEXT_RVA + va + 4)
            struct.pack_into("<i", code, va, rel)
        elif rtype == 6:
            addend = struct.unpack_from("<I", code, va)[0]
            struct.pack_into("<I", code, va, (addend + target) & 0xFFFFFFFF)

    text_raw = align(len(code), FILE_ALIGN)
    data_raw = align(len(data_bytes), FILE_ALIGN) if has_data else 0
    n_pe_sect = 3 if has_data else 2
    size_image = g_idata_rva + align(idata_virt, SECTION_ALIGN)
    out_size = SIZEOF_HEADERS + text_raw + data_raw + idata_raw
    out = bytearray(out_size)

    # DOS + PE headers (simplified like ablinker)
    struct.pack_into("<H", out, 0, 0x5A4D)
    struct.pack_into("<I", out, 60, 0x80)
    out[0x4E:0x4E + 39] = b"This program cannot be run in DOS mode."
    struct.pack_into("<I", out, 0x80, 0x00004550)
    struct.pack_into("<HH", out, 0x84, 0x14C, n_pe_sect)
    struct.pack_into("<H", out, 0x80 + 20, 0xE0)  # SizeOfOptionalHeader
    struct.pack_into("<H", out, 0x80 + 22, 0x010F)  # chars
    opt = 0x80 + 24
    struct.pack_into("<H", out, opt, 0x10B)
    struct.pack_into("<II", out, opt + 4, text_raw, data_raw + idata_raw)
    struct.pack_into("<I", out, opt + 16, entry_rva)
    struct.pack_into("<I", out, opt + 20, TEXT_RVA)
    struct.pack_into("<I", out, opt + 24, g_data_rva if has_data else 0)
    struct.pack_into("<I", out, opt + 28, IMAGE_BASE)
    struct.pack_into("<II", out, opt + 32, SECTION_ALIGN, FILE_ALIGN)
    struct.pack_into("<HH", out, opt + 40, 4, 0)
    struct.pack_into("<HH", out, opt + 44, 0, 0)
    struct.pack_into("<HH", out, opt + 48, 4, 0)
    struct.pack_into("<I", out, opt + 56, size_image)
    struct.pack_into("<I", out, opt + 60, SIZEOF_HEADERS)
    struct.pack_into("<H", out, opt + 68, 3)  # CUI
    struct.pack_into("<I", out, opt + 72, 0x100000)
    struct.pack_into("<I", out, opt + 76, 0x1000)
    struct.pack_into("<I", out, opt + 80, 0x100000)
    struct.pack_into("<I", out, opt + 84, 0x1000)
    struct.pack_into("<I", out, opt + 92, 16)
    # import directory
    struct.pack_into("<II", out, opt + 96 + 8, g_idata_rva, idt_size)
    # IAT directory
    iat_size = sum(4 * (len(dll_funcs[d]) + 1) for d in dll_order)
    struct.pack_into("<II", out, opt + 96 + 96, g_idata_rva + iat_start, iat_size)

    sect = opt + 0xE0
    file_off = SIZEOF_HEADERS
    out[sect : sect + 5] = b".text"
    struct.pack_into("<IIII", out, sect + 8, g_text_virt, TEXT_RVA, text_raw, file_off)
    struct.pack_into("<I", out, sect + 36, 0x60000020)
    file_off += text_raw
    sect += 40
    if has_data:
        out[sect : sect + 5] = b".data"
        struct.pack_into("<IIII", out, sect + 8, g_data_virt, g_data_rva, data_raw, file_off)
        struct.pack_into("<I", out, sect + 36, 0xC0000040)
        file_off += data_raw
        sect += 40
    out[sect : sect + 6] = b".idata"
    struct.pack_into("<IIII", out, sect + 8, idata_virt, g_idata_rva, idata_raw, file_off)
    # サンク (FF 25 ...) を実行するため EXECUTE+READ+INIT_DATA
    struct.pack_into("<I", out, sect + 36, 0x60000020)

    off = SIZEOF_HEADERS
    out[off : off + len(code)] = code
    off += text_raw
    if has_data:
        out[off : off + len(data_bytes)] = data_bytes
        off += data_raw
    out[off : off + len(idata)] = idata

    out_path.write_bytes(out)
    print(f"OK: {obj_path} -> {out_path}")
    print(f"size={out_size} entry=0x{entry_rva:08X} imports={len(imps)} text={len(code)} data={len(data_bytes)}")


if __name__ == "__main__":
    inp = Path(sys.argv[1] if len(sys.argv) > 1 else "abc2_combined.obj")
    outp = Path(sys.argv[2] if len(sys.argv) > 2 else "abc2.exe")
    link(inp, outp)
