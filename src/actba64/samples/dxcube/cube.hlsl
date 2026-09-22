struct VS_IN {
    float3 pos : POSITION;
    float4 col : COLOR;
};

struct VS_OUT {
    float4 pos : SV_POSITION;
    float4 col : COLOR;
};

VS_OUT VS(VS_IN i) {
    VS_OUT o;
    float3 p = i.pos;
    // Y ~35deg, X ~25deg
    float3 p1 = float3(0.819 * p.x + 0.574 * p.z, p.y, -0.574 * p.x + 0.819 * p.z);
    float3 p2 = float3(p1.x, 0.906 * p1.y - 0.423 * p1.z, 0.423 * p1.y + 0.906 * p1.z);
    float z = p2.z + 2.2;
    o.pos = float4(p2.x * 1.6 / z, p2.y * 1.6 / z, (z - 0.5) / 4.0, 1.0);
    o.col = i.col;
    return o;
}

float4 PS(VS_OUT i) : SV_Target {
    return i.col;
}
