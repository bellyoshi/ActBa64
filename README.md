# MyPE64Linker

A lightweight x64 PE (PE32+) binary writer / linker developed in BASIC.

## Features
- Generates 64-bit PE executable (`PE32+`) from raw memory buffers.
- Manual construction of DOS header, NT headers, and Section headers.
- Custom `.idata` (Import Address Table) generation for 64-bit Win32 API calls (`ExitProcess`, etc.).
