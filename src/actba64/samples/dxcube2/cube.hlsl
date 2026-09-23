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
    o.pos = float4(i.pos, 1);
    o.col = i.col;
    return o;
}

float4 PS(VS_OUT i) : SV_Target {
    return i.col;
}
