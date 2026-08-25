import pathlib

root = pathlib.Path(__file__).parent

def fmt_dwords(name, path):
    data = path.read_bytes()
    if len(data) % 4 != 0:
        data += b"\x00" * (4 - len(data) % 4)
    count = len(data) // 4 - 1
    lines = [f"\tDim i As Long", f"\tFor i = 0 To {count}"]
    for i in range(0, len(data), 4):
        val = int.from_bytes(data[i:i + 4], "little")
        lines.append(f"\tIf i = {i // 4} Then {name}[i] = &H{val:08X}")
    lines.append("\tNext i")
    return lines, len(data), count

vs_init, vs_len, vs_count = fmt_dwords("g_vsBytecode", root / "triangle_vs.cso")
ps_init, ps_len, ps_count = fmt_dwords("g_psBytecode", root / "triangle_ps.cso")

# Simpler: direct assignments in sub without loop
def fmt_assign(name, path):
    data = path.read_bytes()
    if len(data) % 4 != 0:
        data += b"\x00" * (4 - len(data) % 4)
    count = len(data) // 4 - 1
    lines = []
    for i in range(0, len(data), 4):
        val = int.from_bytes(data[i:i + 4], "little")
        lines.append(f"\t{name}[{i // 4}] = &H{val:08X}")
    return lines, len(data), count

vs_init, vs_len, vs_count = fmt_assign("g_vsBytecode", root / "triangle_vs.cso")
ps_init, ps_len, ps_count = fmt_assign("g_psBytecode", root / "triangle_ps.cso")

head = f"""' dx_d3d11.sbp - Direct3D 11 colored triangle sample (precompiled shaders)

Dim g_pDevice As *ID3D11Device
Dim g_pContext As *ID3D11DeviceContext
Dim g_pSwapChain As *IDXGISwapChain
Dim g_pRTV As *ID3D11RenderTargetView
Dim g_pVB As *ID3D11Buffer
Dim g_pVS As *ID3D11VertexShader
Dim g_pPS As *ID3D11PixelShader
Dim g_pLayout As *ID3D11InputLayout
Dim g_vp As D3D11_VIEWPORT

Dim g_vsBytecode[{vs_count}] As DWord
Dim g_psBytecode[{ps_count}] As DWord

Const VS_BYTECODE_SIZE = {vs_len}
Const PS_BYTECODE_SIZE = {ps_len}

' IID_ID3D11Texture2D = {{6f15aaf2-d208-4e89-9ab4-489535d34f9c}}
Dim IID_ID3D11Texture2D As GUID

Sub dx_LoadBytecode()
{chr(10).join(vs_init)}
{chr(10).join(ps_init)}
End Sub

"""

tail = pathlib.Path(root / "dx_d3d11_tail.sbp").read_text(encoding="utf-8")
tail = tail.replace("Function dx_Init(hWnd As HWND) As Long\n\tCoInitialize(NULL)",
                    "Function dx_Init(hWnd As HWND) As Long\n\tdx_LoadBytecode()\n\tCoInitialize(NULL)")
(root / "dx_d3d11.sbp").write_text(head + tail, encoding="ascii")
print("ok", vs_len, ps_len)
