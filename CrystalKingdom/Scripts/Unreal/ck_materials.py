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
        m = unreal.load_asset(path)
        ML.delete_all_material_expressions(m)
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
CRYSTAL_COLOR = r"""
float t = saturate(VC.g);
float3 body = lerp(Deep, Base, saturate(0.25 + 0.6*M.g + 0.35*t));
body *= lerp(0.45, 1.35, VC.b);   // every facet catches light differently
float h = IridScale*(F*1.35 + VC.b*0.75 + M.b*0.45 + VC.r*0.35) + IridShift;
float3 irid = 0.5 + 0.5*cos(6.28318*(h + float3(0.0, 0.33, 0.67)));
irid = lerp(irid, float3(0.62,0.38,0.95)*irid*1.6, 0.25);
float im = saturate(IridStr * (pow(F, 0.7)*1.2 + VC.b*0.5 + M.g*0.35 - 0.1));
float3 c = lerp(body, irid, im);
c = lerp(c, float3(0.95,0.98,1.0), saturate(M.r*CrackStr));
c = lerp(c, Gold, saturate((VC.b - 0.86)*5.0) * GoldAmt);
return c;
"""

CRYSTAL_EMIT = r"""
float t = saturate(VC.g);
float inner = (0.3 + 0.7*M.g) * (0.35 + 0.65*t);
float3 e = GlowColor * Glow * inner * lerp(0.35, 1.4, VC.b);
e += GlowColor * Glow * 1.2 * pow(F, 3.0);   // bright rim where facets turn away
e += GlowColor * Glow * 0.9 * pow(M2.r, 2.0) * InnerCrack * (0.6 + 0.4*t);
e += GlowColor * Glow * 0.8 * M.r * CrackStr * 0.5;
return e;
"""


def build_crystal(name, translucent=False):
    m = new_material(name)
    if translucent:
        m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE)
        m.set_editor_property("two_sided", False)
    g = G(m)
    vc = g.node(unreal.MaterialExpressionVertexColor)
    uvs = g.scalar("UVScale", 2.0)
    tc = g.node(unreal.MaterialExpressionTextureCoordinate)
    uv = g.mul(tc, uvs)
    tm = g.tex("CrystalMask", TEX + "/T_Crystal_M", uv)
    bo = g.node(unreal.MaterialExpressionBumpOffset, height_ratio=-0.18, reference_plane=0.0)
    uv2 = g.mul(uv, g.const(0.73))
    g.link(uv2, "", bo, "Coordinate")
    g.link(g.scalar("InnerDepth", 1.0), "", bo, "Height")
    tm2 = g.tex("CrystalMaskInner", TEX + "/T_Crystal_M", bo)
    tn = g.tex("CrystalNormal", TEX + "/T_Crystal_N", uv, normal=True)
    fr = g.node(unreal.MaterialExpressionFresnel)
    g.link(g.scalar("FresnelExp", 2.2), "", fr, "ExponentIn")
    g.link(g.scalar("FresnelBase", 0.04), "", fr, "BaseReflectFractionIn")
    base = g.vec("BaseTint", (0.26, 0.54, 0.60))
    deep = g.vec("DeepTint", (0.02, 0.13, 0.20))
    gold = g.vec("GoldTint", (1.0, 0.72, 0.30))
    col = g.custom(CRYSTAL_COLOR, [("F", fr), ("VC", vc), ("M", tm), ("Base", base), ("Deep", deep),
                                   ("IridStr", g.scalar("IridStrength", 0.65)), ("IridScale", g.scalar("IridScale", 1.0)),
                                   ("IridShift", g.scalar("IridShift", 0.55)), ("CrackStr", g.scalar("CrackStrength", 0.08)),
                                   ("Gold", gold), ("GoldAmt", g.scalar("GoldAmount", 0.6))], desc="CrystalColor")
    emi = g.custom(CRYSTAL_EMIT, [("F", fr), ("VC", vc), ("M", tm), ("M2", tm2), ("GlowColor", g.vec("GlowColor", (0.30, 0.85, 1.0))),
                                  ("Glow", g.scalar("GlowIntensity", 0.55)), ("InnerCrack", g.scalar("InnerCrack", 0.35)),
                                  ("CrackStr", g.scalar("CrackStrength", 0.08))], desc="CrystalEmissive")
    rough = g.custom("return lerp(RMin, RMax, saturate(VC.b*0.7 + M.g*0.3)) + M.r*0.15;",
                     [("VC", vc), ("M", tm), ("RMin", g.scalar("RoughnessMin", 0.02)), ("RMax", g.scalar("RoughnessMax", 0.22))],
                     out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, desc="FacetRoughness")
    nrm = g.flat_normal(tn, g.scalar("NormalStrength", 0.3))
    g.out(col, MP.MP_BASE_COLOR)
    g.out(emi, MP.MP_EMISSIVE_COLOR)
    g.out(rough, MP.MP_ROUGHNESS)
    g.out(nrm, MP.MP_NORMAL)
    g.out(g.scalar("Specular", 0.75), MP.MP_SPECULAR)
    if translucent:
        op = g.custom("return saturate(Op + F*0.55 + M.r*0.3);", [("Op", g.scalar("Opacity", 0.28)), ("F", fr), ("M", tm)],
                      out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, desc="Opacity")
        g.out(op, MP.MP_OPACITY)
        g.out(g.scalar("IOR", 1.45), MP.MP_REFRACTION)
    finish(m)
    return m


# --------------------------------------------------------------------------- rock
ROCK_COLOR = r"""
float macro = saturate(N1.g*0.7 + N2.g*0.3);
float3 c = lerp(Dark, Light, saturate(M.r*0.55 + macro*0.45));
c = lerp(c, Tint, saturate(macro*1.4 - 0.6) * TintAmt);
c *= lerp(0.8, 1.0, M.g);
float wet = 1.0 - saturate((WP.z - WaterZ) / WetH);
c *= lerp(1.0, 0.5, wet);
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
    n1 = g.tex("MacroNoise", TEX + "/T_Crystal_M", g.mul(wpm, g.const(0.00011)))
    n2 = g.tex("MacroNoise2", TEX + "/T_Rock_M", g.mul(wpm, g.const(0.0006)))
    col = g.custom(ROCK_COLOR, [("M", tm), ("N1", n1), ("N2", n2), ("Dark", g.vec("DarkColor", (0.035, 0.045, 0.055), "Rock")),
                                ("Light", g.vec("LightColor", (0.17, 0.19, 0.21), "Rock")), ("Tint", g.vec("TintColor", (0.18, 0.40, 0.45), "Rock")),
                                ("TintAmt", g.scalar("TintAmount", 0.4, "Rock")), ("WP", wp), ("WaterZ", g.scalar("WaterZ", 0.0, "Rock")),
                                ("WetH", g.scalar("WetHeight", 120.0, "Rock"))], desc="RockColor")
    rough = g.custom("float wet = 1.0 - saturate((WP.z - WaterZ) / WetH); return lerp(lerp(0.65, 0.92, M.r), 0.18, wet);",
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
float3 c = Color * (0.86 + 0.28*(M.g - 0.5));
c *= lerp(1.0, 0.62, M.r);
c *= lerp(1.0, 0.78, saturate(M.b*1.3 - 0.35) * Grime);
float low = 1.0 - saturate((WP.z - WaterZ) / 300.0);
c = lerp(c, c*float3(0.55,0.75,0.78), low*0.6);
return c;
"""


def build_stone():
    m = new_material("M_Stone_Master")
    g = G(m)
    uv = g.mul(g.node(unreal.MaterialExpressionTextureCoordinate), g.scalar("UVScale", 1.0, "Stone"))
    tm = g.tex("StoneMask", TEX + "/T_Stone_M", uv)
    tn = g.tex("StoneNormal", TEX + "/T_Stone_N", uv, normal=True)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    col = g.custom(STONE_COLOR, [("M", tm), ("Color", g.vec("StoneColor", (0.62, 0.60, 0.56), "Stone")),
                                 ("Grime", g.scalar("Grime", 0.6, "Stone")), ("WP", wp), ("WaterZ", g.scalar("WaterZ", 0.0, "Stone"))], desc="StoneColor")
    g.out(col, MP.MP_BASE_COLOR)
    g.out(g.custom("return lerp(R0, R0+0.2, M.r);", [("M", tm), ("R0", g.scalar("Roughness", 0.62, "Stone"))],
                   out=unreal.CustomMaterialOutputType.CMOT_FLOAT1, desc="StoneRough"), MP.MP_ROUGHNESS)
    g.out(g.flat_normal(tn, g.scalar("NormalStrength", 1.0, "Stone")), MP.MP_NORMAL)
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
    g.link(g.vec("Scattering", (0.006, 0.04, 0.045), "Water"), "", wo, "ScatteringCoefficients")
    g.link(g.vec("Absorption", (0.30, 0.04, 0.032), "Water"), "", wo, "AbsorptionCoefficients")
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
    for k, v in (scalars or {}).items():
        ML.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in (vectors or {}).items():
        ML.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
    ML.update_material_instance(mi)
    EAL.save_loaded_asset(mi)
    return mi


def main():
    cm = build_crystal("M_Crystal_Master")
    cg = build_crystal("M_Crystal_Glass", translucent=True)
    rk = build_rock()
    st = build_stone()
    gl = build_simple("M_WindowGlow", (0.05, 0.03, 0.01), 0.5, (1.0, 0.58, 0.22), 30.0)
    dr = build_simple("M_Door", (0.09, 0.055, 0.035), 0.55)
    wt = build_water()
    mo = build_mote()

    mi = {}
    mi["Crystal_Teal"] = instance("MI_Crystal_Teal", cm)
    mi["Crystal_White"] = instance("MI_Crystal_White", cm, {"GlowIntensity": 0.9, "IridStrength": 0.55},
                                   {"BaseTint": (0.48, 0.68, 0.74), "DeepTint": (0.10, 0.30, 0.38)})
    mi["Crystal_Violet"] = instance("MI_Crystal_Violet", cm, {"IridShift": 0.78, "IridStrength": 0.85, "GlowIntensity": 0.9},
                                    {"BaseTint": (0.42, 0.33, 0.66), "DeepTint": (0.12, 0.06, 0.26), "GlowColor": (0.65, 0.45, 1.0)})
    mi["Crystal_Glow"] = instance("MI_Crystal_Glow", cm, {"GlowIntensity": 2.0, "InnerCrack": 1.6}, {"GlowColor": (0.35, 0.95, 1.0)})
    mi["Crystal_Opal"] = instance("MI_Crystal_Opal", cm, {"IridStrength": 1.0, "IridScale": 1.8, "GlowIntensity": 0.35},
                                  {"BaseTint": (0.55, 0.58, 0.66)})
    mi["Crystal_Block"] = instance("MI_Crystal_Block", cm, {"GlowIntensity": 0.3, "IridStrength": 0.95, "IridScale": 1.4, "RoughnessMax": 0.12, "CrackStrength": 0.04, "InnerCrack": 0.12},
                                   {"BaseTint": (0.13, 0.32, 0.38), "DeepTint": (0.02, 0.07, 0.10)})
    mi["Crystal_BlockViolet"] = instance("MI_Crystal_BlockViolet", cm, {"GlowIntensity": 0.3, "IridStrength": 1.0, "IridShift": 0.8, "RoughnessMax": 0.12, "CrackStrength": 0.04, "InnerCrack": 0.12},
                                         {"BaseTint": (0.25, 0.17, 0.42), "DeepTint": (0.05, 0.03, 0.12), "GlowColor": (0.6, 0.45, 1.0)})
    mi["Crystal_Glass"] = instance("MI_Crystal_Glass", cg, {"Opacity": 0.25, "GlowIntensity": 1.5})
    mi["CaveRock"] = instance("MI_CaveRock", rk, {"UVScale": 0.35})
    mi["Rock"] = instance("MI_Rock", rk, {"TintAmount": 0.25, "UVScale": 0.6}, {"LightColor": (0.14, 0.15, 0.17)})
    mi["Stone"] = instance("MI_Stone", st)
    mi["StoneTrim"] = instance("MI_StoneTrim", st, {"Grime": 0.35, "Roughness": 0.5}, {"StoneColor": (0.78, 0.77, 0.73)})
    mi["Roof"] = instance("MI_Roof", st, {"UVScale": 2.0, "Grime": 0.8, "Roughness": 0.45}, {"StoneColor": (0.42, 0.55, 0.58)})

    slot_map = {"M_Crystal": mi["Crystal_Teal"], "M_Rock": mi["Rock"], "M_CaveRock": mi["CaveRock"], "M_Stone": mi["Stone"],
                "M_StoneTrim": mi["StoneTrim"], "M_Roof": mi["Roof"], "M_WindowGlow": gl, "M_Door": dr, "M_GlowMote": mo}
    special = {"CeilingGiant": mi["Crystal_White"], "Opal": mi["Crystal_Opal"], "Glow": mi["Crystal_Glass"], "ColumnMass_02": mi["Crystal_Violet"],
               "ColumnMass_05": mi["Crystal_Violet"], "Branch_03": mi["Crystal_Violet"]}
    count = 0
    for folder in ("Crystals", "Rocks", "Cave", "Architecture", "Props"):
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
                if mat:
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
