"""Build Crystal Kingdom master materials + instances and assign them to imported meshes.

Masters (Content/CrystalKingdom/Materials/Master):
  M_Crystal_Master      opaque crystal: thin-film iridescence (fresnel/facet/cloud driven),
                        parallax inner fractures, inner glow toward the tips, per-facet roughness
  M_Crystal_Glass       translucent refractive crystal (hero pieces only, non-Nanite)
  M_Rock_Master         triplanar-free box-UV rock with macro variation and waterline wetness
  M_Stone_Master        masonry stone for architecture (block tint, mortar, grime)
  M_WindowGlow          warm emissive window light
  M_Door                dark closed doors
  M_Water               Single Layer Water lake surface with two panning ripple layers
  M_GlowMote            emissive floating motes (WPO bobbing)
"""
import unreal

ML = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MASTER = "/Game/CrystalKingdom/Materials/Master"
INST = "/Game/CrystalKingdom/Materials/Instances"
TEX = "/Game/CrystalKingdom/Textures"
MP = unreal.MaterialProperty
FAILS = []


def new_material(name):
    path = MASTER + "/" + name
    if EAL.does_asset_exist(path):
        m = unreal.load_asset(path) or EAL.load_asset(path)
        if m is None:  # seen once right after a rebuild while shaders were still compiling
            import time
            for _ in range(10):
                time.sleep(2)
                m = EAL.load_asset(path)
                if m:
                    break
        if m is None:
            raise RuntimeError("cannot load " + path)
        ML.delete_all_material_expressions(m)
        # delete_all leaves some nodes behind (e.g. SingleLayerWaterMaterialOutput); a second SLW output
        # node makes the water fail to compile, so remove whatever is left one by one.
        for _ in range(5):
            left = list(ML.get_material_expressions(m))
            if not left:
                break
            for e in left:
                ML.delete_material_expression(m, e)
        if ML.get_num_material_expressions(m):
            print("WARNING %s still has %d expressions after clearing" % (name, ML.get_num_material_expressions(m)))
        return m
    return AT.create_asset(name, MASTER, unreal.Material, unreal.MaterialFactoryNew())


class G:
    """Tiny graph helper."""

    def __init__(self, mat):
        self.m = mat
        self.x = -1600
        self.y = 0

    def node(self, cls, **props):
        n = ML.create_material_expression(self.m, cls, self.x, self.y)
        self.y += 140
        if self.y > 2400:
            self.y = 0
            self.x += 320
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def scalar(self, name, v, group="Crystal"):
        return self.node(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=v, group=group)

    def vec(self, name, rgb, group="Crystal"):
        return self.node(unreal.MaterialExpressionVectorParameter, parameter_name=name,
                         default_value=unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0), group=group)

    def const(self, v):
        return self.node(unreal.MaterialExpressionConstant, r=v)

    def tex(self, name, tex_path, uv=None, normal=False):
        n = self.node(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=name,
                      texture=unreal.load_asset(tex_path),
                      sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        if uv is not None:
            self.link(uv, "", n, "UVs")
        return n

    def custom(self, code, inputs, out=unreal.CustomMaterialOutputType.CMOT_FLOAT3, desc="Custom"):
        ins = []
        for k, _ in inputs:
            ci = unreal.CustomInput()
            ci.set_editor_property("input_name", k)
            ins.append(ci)
        n = self.node(unreal.MaterialExpressionCustom, code=code, output_type=out, description=desc, inputs=ins)
        for k, src in inputs:
            if isinstance(src, tuple):
                self.link(src[0], src[1], n, k)
            else:
                self.link(src, "", n, k)
        got = ML.get_inputs_for_material_expression(self.m, n)
        names = [k for k, _ in inputs]
        missing = [names[i] for i in range(len(names)) if i >= len(got) or got[i] is None]
        if missing:
            print("CUSTOM %s missing after link: %s (got %d inputs)" % (desc, missing, len(got)))
        return n

    def link(self, a, aout, b, bin_):
        if not ML.connect_material_expressions(a, aout, b, bin_):
            FAILS.append("%s.%s -> %s.%s" % (a.get_name(), aout, b.get_name(), bin_))

    def out(self, a, prop, aout=""):
        if not ML.connect_material_property(a, aout, prop):
            FAILS.append("%s -> %s" % (a.get_name(), prop))

    def mul(self, a, b):
        n = self.node(unreal.MaterialExpressionMultiply)
        self.link(a, "", n, "A")
        self.link(b, "", n, "B")
        return n

    def flat_normal(self, nrm, strength):
        """Lerp normal toward (0,0,1) by strength."""
        flat = self.node(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(0, 0, 1, 1))
        lp = self.node(unreal.MaterialExpressionLinearInterpolate)
        self.link(flat, "", lp, "A")
        self.link(nrm, "", lp, "B")
        self.link(strength, "", lp, "Alpha")
        return lp


def finish(m):
    ML.layout_material_expressions(m)
    ML.recompile_material(m)
    EAL.save_loaded_asset(m)


# --------------------------------------------------------------------------- crystal
# Inputs shared by the colour / emissive nodes:
#   M  surface sample  (R fractures, G milky cloud, B opal field)
#   P  opal patch sample (larger scale, offset per crystal piece by VC.r)
#   D1 shallow parallax layer, D2 deep parallax layer (read "inside" the crystal)
#   MP macro sample (very large scale; slow hue drift across a giant crystal)
OPAL = r"""
float t = saturate(VC.g);
// fade the 2 m tiling detail toward its mean with distance (giants 50-200 m away otherwise shimmer like sequins)
float fd = saturate((Dpt - FadeNear) / FadeRange);
M.rgb  = lerp(M.rgb,  float3(0.0, 0.5, 0.5), fd);
D1.rgb = lerp(D1.rgb, float3(0.0, 0.5, 0.5), fd);
D2.r   = lerp(D2.r, 0.0, fd);
float Pf = P.b*0.6 + D2.b*0.4;
// hue: facet (VC.b) and piece (VC.r) pick a base hue, view angle and the soft patch field shift it
float h = IridScale*(Pf*0.8 + M.b*0.35 + F*0.9 + VC.b*1.1 + MP.b*0.6) + VC.r*0.7 + IridShift;   // plan: each flat facet flashes its own hue   // M.b: play-of-colour inside a patch
// opal palette (violet, blue, teal, pink, gold) instead of a full rainbow - no yellow-green
float3 pal[5] = { float3(0.55,0.25,1.0), float3(0.15,0.50,1.0), float3(0.10,1.0,0.80), float3(1.0,0.35,0.80), float3(1.0,0.68,0.18) };   // plan step 4: richer, gold-heavy
float x = frac(h)*5.0;
int i0 = (int)floor(x);
int i1 = (i0 + 1) % 5;
float3 irid = lerp(pal[i0], pal[i1], smoothstep(0.0, 1.0, frac(x)));
float pm = smoothstep(0.32, 0.44, Pf*0.40 + D1.g*0.10 + VC.b*0.55);   // flashes follow facets, not cloudy blotches
float im = saturate(IridStr*(pm*0.9 + pow(F, 1.2)*0.7));
float cloud = saturate(0.4 + (M.g - 0.5)*0.35 + (D1.g - 0.5)*0.45);   // soft milkiness, no camouflage blotches
"""

CRYSTAL_COLOR = OPAL + r"""
float3 body = lerp(Deep, Base, saturate(0.6 + 0.4*cloud + 0.2*t));   // no dark camouflage blotches
body = lerp(body, Milk, saturate(cloud*MilkAmt*0.7));
body *= lerp(0.78, 1.15, VC.b);                 // facets differ more
float3 c = lerp(body, irid*lerp(0.8, 1.05, cloud), im);
float ck = smoothstep(0.30, 0.70, M.r*CrackStr*1.6);
c += Gold*0.30*smoothstep(0.12, 0.35, M.r*CrackStr)*(1.0 - ck);   // golden halo along cracks
c = lerp(c, float3(0.10,0.07,0.04), ck*0.85);                       // crisp dark crack lines
c = lerp(c, float3(0.92,0.96,1.0), saturate(D1.r*InnerCrack*0.5));  // white inner fractures
return c;
"""

CRYSTAL_EMIT = OPAL + r"""
float3 e = GlowColor*Glow*(0.2 + 0.8*cloud)*(0.35 + 0.65*t)*lerp(0.6, 1.25, VC.b);
e += irid*im*OpalGlow*(0.4 + 0.6*cloud);         // opal fire glows from inside
// plan step 4: warm light trapped inside the crystal (reference: gold glow behind the facets), strongest face-on
e += Gold*InnerGlow*pow(saturate(1.0 - F), 1.5)*(0.35 + 0.65*saturate(D1.g*0.6 + D2.b*0.6))*(0.5 + 0.5*t);
e += GlowColor*Glow*0.9*pow(F, 3.0);             // rim
e += float3(1.0,0.95,0.85)*EdgeGlow*pow(F, 4.0);   // bright white edges like the reference
e += GlowColor*Glow*1.2*pow(D2.r, 1.5)*InnerCrack*(0.5 + 0.5*t);
e += Gold*(Glow*0.6 + 0.25)*smoothstep(0.12, 0.35, M.r*CrackStr)*(1.0 - smoothstep(0.30, 0.70, M.r*CrackStr*1.6));   // gold fire at the crack edges
return e;
"""


def build_crystal(name, translucent=False):
    m = new_material(name)
    if translucent:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
        m.set_editor_property("two_sided", False)
    else:
        m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_CLEAR_COAT)
    g = G(m)
    vc = g.node(unreal.MaterialExpressionVertexColor)
    uvs = g.scalar("UVScale", 2.0)
    tc = g.node(unreal.MaterialExpressionTextureCoordinate)
    uv = g.mul(tc, uvs)
    F2 = unreal.CustomMaterialOutputType.CMOT_FLOAT2
    tm = g.tex("CrystalMask", TEX + "/T_Crystal_M", uv)
    puv = g.custom("return UV*S + VC.r*float2(3.7, 7.1);", [("UV", uv), ("S", g.scalar("PatchScale", 0.14)), ("VC", vc)], out=F2, desc="PatchUV")
    tp = g.tex("CrystalPatch", TEX + "/T_Crystal_M", puv)
    muv = g.custom("return UV*S + VC.r*float2(0.31, 0.57);", [("UV", uv), ("S", g.scalar("MacroScale", 0.035)), ("VC", vc)], out=F2, desc="MacroUV")
    tmac = g.tex("CrystalMacro", TEX + "/T_Crystal_M", muv)
    depth = g.scalar("InnerDepth", 1.0)
    bo1 = g.node(unreal.MaterialExpressionBumpOffset, height_ratio=-0.10, reference_plane=0.0)
    g.link(g.mul(uv, g.const(0.73)), "", bo1, "Coordinate")
    g.link(depth, "", bo1, "Height")
    td1 = g.tex("CrystalInner1", TEX + "/T_Crystal_M", bo1)
    bo2 = g.node(unreal.MaterialExpressionBumpOffset, height_ratio=-0.28, reference_plane=0.0)
    g.link(puv, "", bo2, "Coordinate")
    g.link(depth, "", bo2, "Height")
    td2 = g.tex("CrystalInner2", TEX + "/T_Crystal_M", bo2)
    tn = g.tex("CrystalNormal", TEX + "/T_Crystal_N", uv, normal=True)
    fr = g.node(unreal.MaterialExpressionFresnel)
    g.link(g.scalar("FresnelExp", 2.2), "", fr, "ExponentIn")
    g.link(g.scalar("FresnelBase", 0.04), "", fr, "BaseReflectFractionIn")
    base = g.vec("BaseTint", (0.55, 0.74, 0.78))
    deep = g.vec("DeepTint", (0.05, 0.20, 0.27))
    milk = g.vec("MilkTint", (0.82, 0.88, 0.92))
    gold = g.vec("GoldTint", (1.0, 0.72, 0.30))
    glowc = g.vec("GlowColor", (0.30, 0.85, 1.0))
    s = {k: g.scalar(k, v) for k, v in (("IridStrength", 1.6), ("IridScale", 1.0), ("IridShift", 0.55), ("CrackStrength", 0.55),
                                         ("GlowIntensity", 0.45), ("InnerCrack", 0.5), ("OpalGlow", 0.55), ("MilkAmount", 0.3))}
    dpt = g.node(unreal.MaterialExpressionPixelDepth)
    common = [("F", fr), ("VC", vc), ("M", tm), ("P", tp), ("D1", td1), ("D2", td2), ("MP", tmac), ("Dpt", dpt),
              ("FadeNear", g.scalar("DetailFadeNear", 2500.0)), ("FadeRange", g.scalar("DetailFadeRange", 9000.0)),
              ("IridStr", s["IridStrength"]), ("IridScale", s["IridScale"]), ("IridShift", s["IridShift"])]
    col = g.custom(CRYSTAL_COLOR, common + [("Base", base), ("Deep", deep), ("Milk", milk), ("MilkAmt", s["MilkAmount"]),
                                             ("Gold", gold), ("CrackStr", s["CrackStrength"]), ("InnerCrack", s["InnerCrack"])], desc="CrystalColor")
    emi = g.custom(CRYSTAL_EMIT, common + [("GlowColor", glowc), ("Glow", s["GlowIntensity"]), ("InnerCrack", s["InnerCrack"]),
                                            ("OpalGlow", s["OpalGlow"]), ("Gold", gold), ("CrackStr", s["CrackStrength"]), ("EdgeGlow", g.scalar("EdgeGlow", 0.6)), ("InnerGlow", g.scalar("InnerGlow", 0.06))], desc="CrystalEmissive")
    rough = g.custom("return lerp(RMin, RMax, saturate(M.g*0.6 + VC.b*0.4)) + M.r*0.2;",
                     [("VC", vc), ("M", tm), ("RMin", g.scalar("RoughnessMin", 0.10)), ("RMax", g.scalar("RoughnessMax", 0.45))],
                     out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, desc="BodyRoughness")
    nrm = g.flat_normal(tn, g.scalar("NormalStrength", 0.35))
    spec = g.scalar("Specular", 0.5)
    if translucent:
        g.out(col, MP.MP_BASE_COLOR)
        g.out(emi, MP.MP_EMISSIVE_COLOR)
        g.out(rough, MP.MP_ROUGHNESS)
        g.out(nrm, MP.MP_NORMAL)
        g.out(spec, MP.MP_SPECULAR)
        op = g.custom("return saturate(Op + F*0.55 + M.r*0.3);", [("Op", g.scalar("Opacity", 0.28)), ("F", fr), ("M", tm)],
                      out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, desc="Opacity")
        g.out(op, MP.MP_OPACITY)
        g.out(g.scalar("IOR", 1.45), MP.MP_REFRACTION)
    else:
        # glossy coat over a milky body: sharp reflections of window light and shafts.
        # ClearCoat pins are not exposed to Python as MaterialProperty -> go through MakeMaterialAttributes.
        m.set_editor_property("use_material_attributes", True)
        ma = g.node(unreal.MaterialExpressionMakeMaterialAttributes)
        coat_r = g.custom("return lerp(C0, C1, VC.b) + M.r*0.15;", [("VC", vc), ("M", tm), ("C0", g.scalar("CoatRoughMin", 0.02)),
                                                                     ("C1", g.scalar("CoatRoughMax", 0.09))],
                          out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, desc="CoatRough")
        for src, pin in ((col, "BaseColor"), (emi, "EmissiveColor"), (rough, "Roughness"), (nrm, "Normal"), (spec, "Specular"),
                         (g.scalar("ClearCoat", 1.0), "ClearCoat"), (coat_r, "ClearCoatRoughness")):
            g.link(src, "", ma, pin)
        g.out(ma, MP.MP_MATERIAL_ATTRIBUTES)
    finish(m)
    return m


# --------------------------------------------------------------------------- rock
ROCK_COLOR = r"""
float macro = saturate(N1.b*0.7 + N2.b*0.3);
float3 c = lerp(Dark, Light, saturate(M.r*0.65 + macro*0.35));
c = lerp(c, Tint, saturate(macro*1.4 - 0.6) * TintAmt);
c *= lerp(CrackDark, 1.0, M.g);                  // fractures read dark (cave shell: softer, big shells showed dashed contours)
float dz = WP.z - WaterZ;
float wet = 1.0 - saturate(dz / WetH);
float under = saturate(-dz / 150.0);              // fully submerged 1.5 m below the surface
c *= lerp(1.0, 0.55, wet*(1.0 - under));          // dark wet band at the shoreline
c = lerp(c, Silt*lerp(0.75, 1.1, M.r), under*SiltAmt);   // pale lake bed seen through clear water
return c;
"""


def build_rock():
    m = new_material("M_Rock_Master")
    m.set_editor_property("two_sided", True)  # cave shell must block the sun from both sides
    g = G(m)
    uv = g.mul(g.node(unreal.MaterialExpressionTextureCoordinate), g.scalar("UVScale", 1.0, "Rock"))
    tm = g.tex("RockMask", TEX + "/T_Rock_M", uv)
    tn = g.tex("RockNormal", TEX + "/T_Rock_N", uv, normal=True)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    wpm = g.node(unreal.MaterialExpressionComponentMask, r=True, g=True, b=False, a=False)
    g.link(wp, "", wpm, "")
    n1 = g.tex("MacroNoise", TEX + "/T_Rock_M", g.mul(wpm, g.const(0.00011)))
    n2 = g.tex("MacroNoise2", TEX + "/T_Rock_M", g.mul(wpm, g.const(0.0006)))
    col = g.custom(ROCK_COLOR, [("M", tm), ("N1", n1), ("N2", n2), ("Dark", g.vec("DarkColor", (0.05, 0.05, 0.055), "Rock")),
                                ("Light", g.vec("LightColor", (0.40, 0.36, 0.31), "Rock")), ("Tint", g.vec("TintColor", (0.20, 0.36, 0.40), "Rock")),
                                ("TintAmt", g.scalar("TintAmount", 0.12, "Rock")), ("Silt", g.vec("SiltColor", (0.62, 0.68, 0.62), "Rock")),
                                ("SiltAmt", g.scalar("SiltAmount", 0.85, "Rock")), ("WP", wp), ("WaterZ", g.scalar("WaterZ", 0.0, "Rock")),
                                ("WetH", g.scalar("WetHeight", 120.0, "Rock")), ("CrackDark", g.scalar("CrackDark", 0.35, "Rock"))], desc="RockColor")
    rough = g.custom("float wet = 1.0 - saturate((WP.z - WaterZ) / WetH); return lerp(lerp(0.6, 0.9, M.r), 0.15, wet) + (1.0 - M.g)*0.1;",
                     [("WP", wp), ("M", tm), ("WaterZ", g.scalar("WaterZ", 0.0, "Rock")), ("WetH", g.scalar("WetHeight", 120.0, "Rock"))],
                     out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, desc="RockRoughness")
    g.out(col, MP.MP_BASE_COLOR)
    g.out(rough, MP.MP_ROUGHNESS)
    g.out(g.flat_normal(tn, g.scalar("NormalStrength", 1.0, "Rock")), MP.MP_NORMAL)
    pass  # cavity AO dropped: read as cobblestone cells
    finish(m)
    return m


# --------------------------------------------------------------------------- stone
STONE_COLOR = r"""
// weathered white-gold marble ashlar (reference buildings): per-block tone + hue, deep joints, veins, rain streaks
float id = M.g;
float3 warm = float3(1.06, 0.97, 0.86), cool = float3(0.93, 0.97, 1.04);
float3 c = Color * lerp(0.88, 1.11, id) * lerp(float3(1,1,1), lerp(warm, cool, frac(id * 7.31)), 0.55);   // subtle: strong per-block tone read as a checkerboard
c *= lerp(0.88, 1.07, Macro.b);   // (input must not be named MAC: that is a platform #define in the shader headers)                                   // 15 m macro blotches: no flat, even wall
c *= 1.0 - VeinAmt * 0.21 * smoothstep(0.35, 0.8, V.r);        // fine marble veins
c *= lerp(1.0, 0.62, saturate(M.r * 1.25));                    // dark recessed mortar joints + chips
float streak = saturate(S.g * 1.7 - 0.75);
c *= lerp(1.0, 0.78, streak * Grime);                          // vertical rain / seepage streaks
c *= lerp(1.0, 0.89, saturate(M.b * 1.3 - 0.35) * Grime);     // surface grime noise
float low = 1.0 - saturate((WP.z - WaterZ) / 300.0);
c = lerp(c, c * float3(0.55, 0.75, 0.78), low * 0.6);          // wet tide band at the water line
return c;
"""

STONE_ROUGH = r"""
return saturate(R0 + 0.28 * M.r + 0.12 * (1.0 - M.g) + 0.15 * saturate(S.g * 1.7 - 0.75) - 0.08 * V.r);
"""

STONE_NORMAL = r"""
// block normal (joints, chisel marks) + fine pitted detail; xy add, z renormalised
float3 a = float3(NA.xy * SA, 1.0);       // samplers are Normal type: already unpacked to -1..1
float3 b = float3(NB.xy * SB, 0.0);
return normalize(float3(a.xy + b.xy, a.z));
"""


def build_stone():
    m = new_material("M_Stone_Master")
    g = G(m)
    uvs = g.scalar("UVScale", 1.0, "Stone")
    tc = g.node(unreal.MaterialExpressionTextureCoordinate)
    uv = g.mul(tc, uvs)
    tm = g.tex("StoneMask", TEX + "/T_Stone_M", uv)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    F2 = unreal.CustomMaterialOutputType.CMOT_FLOAT2
    # world-space macro variation and vertical streaks (independent of the mesh UV layout)
    mac_uv = g.custom("return float2(WP.x + WP.z * 0.37, WP.y - WP.z * 0.21) * 0.00007;", [("WP", wp)], out=F2, desc="MacroUV")
    mac = g.tex("StoneMacro", TEX + "/T_Rock_M", mac_uv)
    st_uv = g.custom("return float2((WP.x + WP.y) * 0.0021, WP.z * 0.00035);", [("WP", wp)], out=F2, desc="StreakUV")
    strk = g.tex("StoneStreak", TEX + "/T_Rock_M", st_uv)
    vein = g.tex("StoneVein", TEX + "/T_Crystal_M", g.mul(uv, g.const(0.45)))
    col = g.custom(STONE_COLOR, [("M", tm), ("Macro", mac), ("S", strk), ("V", vein),
                                 ("Color", g.vec("StoneColor", (0.70, 0.68, 0.63), "Stone")),
                                 ("Grime", g.scalar("Grime", 0.6, "Stone")), ("VeinAmt", g.scalar("VeinAmount", 0.6, "Stone")),
                                 ("WP", wp), ("WaterZ", g.scalar("WaterZ", 0.0, "Stone"))], desc="StoneColor")
    g.out(col, MP.MP_BASE_COLOR)
    g.out(g.custom(STONE_ROUGH, [("M", tm), ("S", strk), ("V", vein), ("R0", g.scalar("Roughness", 0.5, "Stone"))],
                   out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, desc="StoneRough"), MP.MP_ROUGHNESS)
    na = g.tex("StoneNormal", TEX + "/T_Stone_N", uv, normal=True)
    nb = g.tex("StoneDetailN", TEX + "/T_Rock_N", g.mul(uv, g.const(3.1)), normal=True)
    nrm = g.custom(STONE_NORMAL, [("NA", na), ("NB", nb), ("SA", g.scalar("NormalStrength", 2.3, "Stone")),
                                  ("SB", g.scalar("DetailNormal", 0.65, "Stone"))],
                   out=unreal.CustomMaterialOutputType.CMOT_FLOAT3, desc="StoneNormal")
    g.out(nrm, MP.MP_NORMAL)
    g.out(g.vec("Emissive", (0.0, 0.0, 0.0), "Stone"), MP.MP_EMISSIVE_COLOR)
    finish(m)
    return m


def build_simple(name, base, rough, emissive=None, emissive_mul=1.0):
    m = new_material(name)
    g = G(m)
    g.out(g.vec("Color", base, "Main"), MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", rough, "Main"), MP.MP_ROUGHNESS)
    if emissive:
        g.out(g.mul(g.vec("EmissiveColor", emissive, "Main"), g.scalar("EmissiveIntensity", emissive_mul, "Main")), MP.MP_EMISSIVE_COLOR)
    finish(m)
    return m


def build_water():
    m = new_material("M_Water")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    g = G(m)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    wpm = g.node(unreal.MaterialExpressionComponentMask, r=True, g=True, b=False, a=False)
    g.link(wp, "", wpm, "")
    uv1 = g.mul(wpm, g.const(0.0011))
    uv2 = g.mul(wpm, g.const(0.00043))
    p1 = g.node(unreal.MaterialExpressionPanner, speed_x=0.006, speed_y=0.004)
    g.link(uv1, "", p1, "Coordinate")
    p2 = g.node(unreal.MaterialExpressionPanner, speed_x=-0.003, speed_y=0.005)
    g.link(uv2, "", p2, "Coordinate")
    n1 = g.tex("Ripple1", TEX + "/T_Water_N", p1, normal=True)
    n2 = g.tex("Ripple2", TEX + "/T_Water_N", p2, normal=True)
    nb = g.custom("float3 n = float3(A.xy + B.xy, A.z*B.z); n.xy *= S; return normalize(n);",
                  [("A", n1), ("B", n2), ("S", g.scalar("RippleStrength", 0.22, "Water"))], desc="BlendNormals")
    g.out(nb, MP.MP_NORMAL)
    g.out(g.vec("WaterColor", (0.01, 0.04, 0.05), "Water"), MP.MP_BASE_COLOR)
    g.out(g.scalar("Roughness", 0.03, "Water"), MP.MP_ROUGHNESS)
    g.out(g.scalar("Specular", 0.5, "Water"), MP.MP_SPECULAR)
    g.out(g.scalar("Opacity", 1.0, "Water"), MP.MP_OPACITY)
    wo = g.node(unreal.MaterialExpressionSingleLayerWaterMaterialOutput)
    g.link(g.vec("Scattering", (0.005, 0.035, 0.035), "Water"), "", wo, "ScatteringCoefficients")
    g.link(g.vec("Absorption", (0.08, 0.010, 0.008), "Water"), "", wo, "AbsorptionCoefficients")
    g.link(g.scalar("PhaseG", 0.2, "Water"), "", wo, "PhaseG")
    finish(m)
    return m


def build_mote():
    m = new_material("M_GlowMote")
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    g = G(m)
    vc = g.node(unreal.MaterialExpressionVertexColor)
    tm = g.node(unreal.MaterialExpressionTime)
    wpo = g.custom("float s = sin(T*0.6 + VC.r*40.0); float c = cos(T*0.45 + VC.b*33.0); return float3(c*30.0, s*30.0, s*c*45.0 + sin(T*0.3+VC.r*9.0)*60.0);",
                   [("T", tm), ("VC", vc)], desc="Bob")
    g.out(wpo, MP.MP_WORLD_POSITION_OFFSET)
    em = g.custom("return Col * I * (0.5 + 0.5*sin(T*1.7 + VC.r*50.0));", [("Col", g.vec("Color", (0.45, 0.9, 1.0), "Mote")),
                                                                          ("I", g.scalar("Intensity", 8.0, "Mote")), ("T", tm), ("VC", vc)], desc="Twinkle")
    g.out(em, MP.MP_EMISSIVE_COLOR)
    finish(m)
    return m


# --------------------------------------------------------------------------- instances
def instance(name, parent, scalars=None, vectors=None):
    path = INST + "/" + name
    mi = unreal.load_asset(path) if EAL.does_asset_exist(path) else AT.create_asset(name, INST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    ML.set_material_instance_parent(mi, parent)
    ML.clear_all_material_instance_parameters(mi)  # drop overrides tuned for an older master
    for k, v in (scalars or {}).items():
        ML.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items():
        ML.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
    ML.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    return mi


def main():
    # only=crystal|rock|stone|water rebuilds just that master (others are loaded as they are); every
    # rebuild recompiles shaders and a render taken meanwhile shows fallback materials.
    only = globals().get("CK_ARGS", {}).get("only", "")

    def get(key, name, fn):
        if only and only != key:
            return unreal.load_asset(MASTER + "/" + name)
        return fn()

    cm = get("crystal", "M_Crystal_Master", lambda: build_crystal("M_Crystal_Master"))
    cg = get("crystal", "M_Crystal_Glass", lambda: build_crystal("M_Crystal_Glass", translucent=True))
    rk = get("rock", "M_Rock_Master", build_rock)
    st = get("stone", "M_Stone_Master", build_stone)
    gl = get("simple", "M_WindowGlow", lambda: build_simple("M_WindowGlow", (0.05, 0.03, 0.01), 0.5, (1.0, 0.58, 0.22), 30.0))
    dr = get("simple", "M_Door", lambda: build_simple("M_Door", (0.09, 0.055, 0.035), 0.55))
    plant = get("simple", "M_Plant", lambda: build_simple("M_Plant", (0.07, 0.20, 0.07), 0.8))
    flower = get("simple", "M_Flower", lambda: build_simple("M_Flower", (0.75, 0.28, 0.62), 0.6, (0.35, 0.10, 0.30), 0.6))
    soil = get("simple", "M_Soil", lambda: build_simple("M_Soil", (0.07, 0.05, 0.035), 0.95))
    metal = get("simple", "M_Metal", lambda: build_simple("M_Metal", (0.035, 0.035, 0.04), 0.4))
    fabric = get("simple", "M_Fabric", lambda: build_simple("M_Fabric", (0.36, 0.05, 0.10), 0.85))
    wt = get("water", "M_Water", build_water)
    mo = get("simple", "M_GlowMote", build_mote)

    mi = {}
    violet = {"BaseTint": (0.58, 0.50, 0.78), "DeepTint": (0.15, 0.08, 0.30), "GlowColor": (0.65, 0.45, 1.0)}
    # crystal vs cave-wall contrast: keep the opal hues, but halve the self-glow and darken the milky body
    DIM = float(globals().get("CK_ARGS", {}).get("crystaldim", "0.5"))

    def crystal(name, scalars=None, vectors=None):
        sc = {"GlowIntensity": 0.45, "OpalGlow": 0.55}
        sc.update(scalars or {})
        sc["GlowIntensity"] *= DIM
        sc["OpalGlow"] *= DIM
        sc.setdefault("EdgeGlow", 0.3)
        sc.setdefault("InnerGlow", 0.035)
        vc = {"MilkTint": (0.62, 0.66, 0.70)}
        vc.update(vectors or {})
        return instance(name, cm, sc, vc)

    mi["Crystal_Teal"] = crystal("MI_Crystal_Teal")
    mi["Crystal_White"] = crystal("MI_Crystal_White", {"GlowIntensity": 0.25, "MilkAmount": 0.45, "IridStrength": 1.1},
                                   {"BaseTint": (0.70, 0.82, 0.86), "DeepTint": (0.20, 0.35, 0.42)})
    mi["Crystal_Violet"] = crystal("MI_Crystal_Violet", {"IridShift": 0.78, "IridStrength": 0.9, "GlowIntensity": 0.6}, violet)
    mi["Crystal_Glow"] = instance("MI_Crystal_Glow", cm, {"GlowIntensity": 1.8, "InnerCrack": 1.4}, {"GlowColor": (0.35, 0.95, 1.0)})
    mi["Crystal_Opal"] = crystal("MI_Crystal_Opal", {"IridStrength": 1.0, "IridScale": 1.6, "MilkAmount": 0.5, "OpalGlow": 0.8, "GlowIntensity": 0.3},
                                  {"BaseTint": (0.75, 0.76, 0.82)})
    block = {"IridStrength": 1.8, "IridScale": 1.2, "MilkAmount": 0.3, "OpalGlow": 0.45, "GlowIntensity": 0.12, "CrackStrength": 0.85, "PatchScale": 0.22}
    mi["Crystal_Block"] = crystal("MI_Crystal_Block", block, {"BaseTint": (0.50, 0.58, 0.62), "DeepTint": (0.06, 0.10, 0.13)})
    mi["Crystal_BlockViolet"] = crystal("MI_Crystal_BlockViolet", dict(block, IridShift=0.8), violet)
    mi["Crystal_Glass"] = instance("MI_Crystal_Glass", cg, {"Opacity": 0.25, "GlowIntensity": 1.5})
    mi["CaveRock"] = instance("MI_CaveRock", rk, {"UVScale": 0.35, "TintAmount": 0.0, "NormalStrength": 1.4, "CrackDark": 0.8},   # reference: grey-brown rough ceiling
                              {"DarkColor": (0.10, 0.08, 0.065), "LightColor": (0.50, 0.42, 0.34)})
    mi["Rock"] = instance("MI_Rock", rk, {"TintAmount": 0.15, "UVScale": 0.6, "CrackDark": 0.6},   # pale terraces/banks like the reference
                          {"LightColor": (0.58, 0.54, 0.48), "DarkColor": (0.16, 0.14, 0.12)})
    mi["Stone"] = instance("MI_Stone", st, {"Grime": 0.35}, {"StoneColor": (0.86, 0.82, 0.74)})   # plan: white-gold marble
    mi["StoneTrim"] = instance("MI_StoneTrim", st, {"Grime": 0.35, "Roughness": 0.5}, {"StoneColor": (0.93, 0.89, 0.80)})
    mi["Roof"] = instance("MI_Roof", st, {"UVScale": 2.0, "Grime": 0.8, "Roughness": 0.45}, {"StoneColor": (0.42, 0.55, 0.58)})

    slot_map = {"M_Crystal": mi["Crystal_Teal"], "M_Rock": mi["Rock"], "M_CaveRock": mi["CaveRock"], "M_Stone": mi["Stone"],
                "M_StoneTrim": mi["StoneTrim"], "M_Roof": mi["Roof"], "M_WindowGlow": gl, "M_Door": dr, "M_GlowMote": mo,
                "M_Plant": plant, "M_Flower": flower, "M_Soil": soil, "M_Metal": metal, "M_Fabric": fabric}
    special = {"CeilingGiant": mi["Crystal_Opal"],   # plan: colourful chandeliers, not milky white
                "Opal": mi["Crystal_Opal"], "Glow": mi["Crystal_Glass"], "ColumnMass_02": mi["Crystal_Violet"],
               "ColumnMass_05": mi["Crystal_Violet"], "Branch_03": mi["Crystal_Violet"]}
    count = 0
    for folder in ("Crystals", "Rocks", "Cave", "Architecture", "Props", "Roads"):   # Props: street furniture, Roads: road bodies
        for p in EAL.list_assets("/Game/CrystalKingdom/Meshes/" + folder, recursive=False):
            sm = unreal.load_asset(p)
            if not isinstance(sm, unreal.StaticMesh):
                continue
            changed = False
            for i, s in enumerate(sm.static_materials):
                slot = str(s.material_slot_name)
                mat = slot_map.get(slot)
                for key, v in special.items():
                    if key in sm.get_name() and slot == "M_Crystal":
                        mat = v
                if mat and sm.get_material(i) != mat:  # only touch meshes whose slot really changes (resaving 182 Nanite meshes took ~5 min)
                    sm.set_material(i, mat)
                    changed = True
            if "Crystal_Glow" in sm.get_name():  # translucent -> no Nanite
                ns = sm.get_editor_property("nanite_settings")
                ns.enabled = False
                sm.set_editor_property("nanite_settings", ns)
            if changed:
                EAL.save_loaded_asset(sm)
                count += 1
    print("materials built; meshes assigned:", count)
    print("FAILED LINKS:", FAILS if FAILS else "none")


main()
