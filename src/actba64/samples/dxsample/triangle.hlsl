struct VS_IN {
    float3 pos : POSITION;
    float4 col : COLOR;
};

float4 VS(VS_IN i) : SV_POSITION {
    return float4(i.pos, 1);
}

float4 PS(float4 c : COLOR) : SV_Target {
    return c;
}
