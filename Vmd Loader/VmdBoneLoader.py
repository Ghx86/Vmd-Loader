import os
import struct
import sys
import math
try:
    import unreal
    _HAS_UNREAL = True
except Exception:
    unreal = None
    _HAS_UNREAL = False

def _pos_mmd_to_ue(pos):
    return (float(pos[0]) * 10.0, -float(pos[2]) * 10.0, float(pos[1]) * 10.0)


def _mat3_mul(a, b):
    return [
        [
            a[0][0] * b[0][0] + a[0][1] * b[1][0] + a[0][2] * b[2][0],
            a[0][0] * b[0][1] + a[0][1] * b[1][1] + a[0][2] * b[2][1],
            a[0][0] * b[0][2] + a[0][1] * b[1][2] + a[0][2] * b[2][2],
        ],
        [
            a[1][0] * b[0][0] + a[1][1] * b[1][0] + a[1][2] * b[2][0],
            a[1][0] * b[0][1] + a[1][1] * b[1][1] + a[1][2] * b[2][1],
            a[1][0] * b[0][2] + a[1][1] * b[1][2] + a[1][2] * b[2][2],
        ],
        [
            a[2][0] * b[0][0] + a[2][1] * b[1][0] + a[2][2] * b[2][0],
            a[2][0] * b[0][1] + a[2][1] * b[1][1] + a[2][2] * b[2][1],
            a[2][0] * b[0][2] + a[2][1] * b[1][2] + a[2][2] * b[2][2],
        ],
    ]


def _mat3_transpose(a):
    return [
        [a[0][0], a[1][0], a[2][0]],
        [a[0][1], a[1][1], a[2][1]],
        [a[0][2], a[1][2], a[2][2]],
    ]


def _quat_to_mat3(q):
    x, y, z, w = q
    xx = x * x
    yy = y * y
    zz = z * z
    xy = x * y
    xz = x * z
    yz = y * z
    wx = w * x
    wy = w * y
    wz = w * z
    return [
        [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy)],
        [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx)],
        [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy)],
    ]


def _mat3_to_quat(m):
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        w = 0.25 * s
        x = (m[2][1] - m[1][2]) / s
        y = (m[0][2] - m[2][0]) / s
        z = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
        w = (m[2][1] - m[1][2]) / s
        x = 0.25 * s
        y = (m[0][1] + m[1][0]) / s
        z = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
        w = (m[0][2] - m[2][0]) / s
        x = (m[0][1] + m[1][0]) / s
        y = 0.25 * s
        z = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
        w = (m[1][0] - m[0][1]) / s
        x = (m[0][2] + m[2][0]) / s
        y = (m[1][2] + m[2][1]) / s
        z = 0.25 * s
    mag = math.sqrt(x * x + y * y + z * z + w * w)
    if mag > 0.0:
        inv = 1.0 / mag
        return (x * inv, y * inv, z * inv, w * inv)
    return (0.0, 0.0, 0.0, 1.0)


def _quat_mmd_to_ue(rot):
    B = [
        [1.0, 0.0, 0.0],
        [0.0, 0.0, -1.0],
        [0.0, 1.0, 0.0],
    ]
    Bt = _mat3_transpose(B)
    Rm = _quat_to_mat3((float(rot[0]), float(rot[1]), float(rot[2]), float(rot[3])))
    Rue = _mat3_mul(_mat3_mul(B, Rm), Bt)
    return _mat3_to_quat(Rue)


def _quat_nlerp(a, b, t: float):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    dot = ax * bx + ay * by + az * bz + aw * bw
    if dot < 0.0:
        bx, by, bz, bw = -bx, -by, -bz, -bw
    x = ax + (bx - ax) * t
    y = ay + (by - ay) * t
    z = az + (bz - az) * t
    w = aw + (bw - aw) * t
    mag = math.sqrt(x * x + y * y + z * z + w * w)
    if mag > 0.0:
        inv = 1.0 / mag
        return (x * inv, y * inv, z * inv, w * inv)
    return (0.0, 0.0, 0.0, 1.0)



def _interpolate_bezier(x1, y1, x2, y2, x):
    x = 0.0 if x < 0.0 else (1.0 if x > 1.0 else float(x))
    t = 0.5
    s = 0.5
    for i in range(15):
        ft = (3.0 * s * s * t * x1) + (3.0 * s * t * t * x2) + (t * t * t) - x
        if abs(ft) < 0.0001:
            break
        if ft > 0.0:
            t -= 1.0 / float(4 << i)
        else:
            t += 1.0 / float(4 << i)
        s = 1.0 - t
    return (3.0 * s * s * t * y1) + (3.0 * s * t * t * y2) + (t * t * t)


def _bezier_params(bezier16: bytes, kind: int):
    if not bezier16 or len(bezier16) < 16:
        return None
    x1 = bezier16[kind] / 127.0
    y1 = bezier16[4 + kind] / 127.0
    x2 = bezier16[8 + kind] / 127.0
    y2 = bezier16[12 + kind] / 127.0
    return x1, y1, x2, y2


def _quat_slerp(q0, q1, t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else float(t))
    x0, y0, z0, w0 = q0
    x1, y1, z1, w1 = q1
    dot = x0 * x1 + y0 * y1 + z0 * z1 + w0 * w1
    if dot < 0.0:
        dot = -dot
        x1 = -x1
        y1 = -y1
        z1 = -z1
        w1 = -w1
    if dot > 0.9995:
        return _quat_nlerp((x0, y0, z0, w0), (x1, y1, z1, w1), t)
    theta_0 = math.acos(dot)
    sin_theta_0 = math.sin(theta_0)
    if sin_theta_0 == 0.0:
        return (x0, y0, z0, w0)
    theta = theta_0 * t
    sin_theta = math.sin(theta)
    s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0
    return (x0 * s0 + x1 * s1, y0 * s0 + y1 * s1, z0 * s0 + z1 * s1, w0 * s0 + w1 * s1)


def apply_bones(ctrl, bones, fps, num_frames, skeletal_mesh=None):
    ref_pos_map = {}
    comp = None
    if unreal is not None and skeletal_mesh is not None:
        try:
            comp = unreal.SkeletalMeshComponent()
        except Exception:
            comp = None
    if comp is not None:
        set_ok = False
        if hasattr(comp, 'set_skeletal_mesh_asset'):
            try:
                comp.set_skeletal_mesh_asset(skeletal_mesh)
                set_ok = True
            except Exception:
                set_ok = False
        if not set_ok:
            for prop in ('skeletal_mesh', 'skinned_asset', 'skeletal_mesh_asset', 'SkeletalMesh'):
                try:
                    comp.set_editor_property(prop, skeletal_mesh)
                    set_ok = True
                    break
                except Exception:
                    pass
        if set_ok:
            for bn in bones.keys():
                try:
                    bi = comp.get_bone_index(bn)
                except Exception:
                    bi = -1
                if bi is None or int(bi) < 0:
                    continue
                try:
                    rp = comp.get_ref_pose_position(int(bi))
                except Exception:
                    rp = None
                if rp is not None:
                    ref_pos_map[bn] = rp

    for bone_name, keys in bones.items():
        if not keys:
            continue
        keys_sorted = sorted(keys, key=lambda x: x[0])
        add_ok = True
        try:
            if hasattr(ctrl, "insert_bone_track"):
                ctrl.insert_bone_track(bone_name, 0, False)
            else:
                ctrl.add_bone_track(bone_name, False)
        except Exception:
            add_ok = False
        if not add_ok:
            continue

        pos_keys = []
        rot_keys = []
        scl_keys = []
        first_f = int(keys_sorted[0][0])
        last_f = int(keys_sorted[-1][0])

        j = 0
        for f in range(num_frames):
            if f <= first_f:
                frame, pos, rot = keys_sorted[0][0], keys_sorted[0][1], keys_sorted[0][2]
                p = _pos_mmd_to_ue(pos)
                q = _quat_mmd_to_ue(rot)
            elif f >= last_f:
                frame, pos, rot = keys_sorted[-1][0], keys_sorted[-1][1], keys_sorted[-1][2]
                p = _pos_mmd_to_ue(pos)
                q = _quat_mmd_to_ue(rot)
            else:
                while j + 1 < len(keys_sorted) and int(keys_sorted[j + 1][0]) <= f:
                    j += 1
                f0, pos0, rot0 = keys_sorted[j][0], keys_sorted[j][1], keys_sorted[j][2]
                f1, pos1, rot1 = keys_sorted[j + 1][0], keys_sorted[j + 1][1], keys_sorted[j + 1][2]
                f0 = int(f0)
                f1 = int(f1)
                if f1 == f0:
                    p = _pos_mmd_to_ue(pos0)
                    q = _quat_mmd_to_ue(rot0)
                else:
                    t = float(f - f0) / float(f1 - f0)
                    bez = None
                    if len(keys_sorted[j + 1]) >= 4:
                        bez = keys_sorted[j + 1][3]
                    tx = t
                    ty = t
                    tz = t
                    tr = t
                    if bez is not None:
                        px = _bezier_params(bez, 0)
                        py = _bezier_params(bez, 1)
                        pz = _bezier_params(bez, 2)
                        pr = _bezier_params(bez, 3)
                        if px is not None:
                            tx = _interpolate_bezier(px[0], px[1], px[2], px[3], t)
                        if py is not None:
                            ty = _interpolate_bezier(py[0], py[1], py[2], py[3], t)
                        if pz is not None:
                            tz = _interpolate_bezier(pz[0], pz[1], pz[2], pz[3], t)
                        if pr is not None:
                            tr = _interpolate_bezier(pr[0], pr[1], pr[2], pr[3], t)
                    m0 = pos0
                    m1 = pos1
                    pos_mmd = (
                        float(m0[0]) + (float(m1[0]) - float(m0[0])) * tx,
                        float(m0[1]) + (float(m1[1]) - float(m0[1])) * ty,
                        float(m0[2]) + (float(m1[2]) - float(m0[2])) * tz,
                    )
                    p = _pos_mmd_to_ue(pos_mmd)
                    q0 = _quat_mmd_to_ue(rot0)
                    q1 = _quat_mmd_to_ue(rot1)
                    q = _quat_slerp(q0, q1, tr)

            if bone_name in ref_pos_map:
                rp = ref_pos_map[bone_name]
                p = (p[0] + float(rp.x), p[1] + float(rp.y), p[2] + float(rp.z))
            pos_keys.append(unreal.Vector(p[0], p[1], p[2]))
            rot_keys.append(unreal.Quat(q[0], q[1], q[2], q[3]))
            scl_keys.append(unreal.Vector(1.0, 1.0, 1.0))

        try:
            ctrl.set_bone_track_keys(bone_name, pos_keys, rot_keys, scl_keys, False)
        except Exception:
            continue
