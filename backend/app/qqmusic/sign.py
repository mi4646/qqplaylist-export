"""QQ音乐请求签名算法，移植自 Go 版 misc/utils/qqmusic_sign.go 的 Encrypt。

生产路径用纯算法（md5 + 自定义 base64），不依赖 JS 引擎。
"""
import hashlib

# 十六进制字符 -> 数值
_K1 = {c: i for i, c in enumerate("0123456789ABCDEF")}

# 异或常量表
_L1 = [212, 45, 80, 68, 195, 163, 163, 203, 157, 220, 254, 91, 204, 79, 104, 6]

# 自定义 base64 字母表
_T = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="


def _select(s: str, indices: list[int]) -> str:
    return "".join(s[i] for i in indices)


def encrypt(param: str) -> str:
    md5_str = hashlib.md5(param.encode()).hexdigest().upper()
    t1 = _select(md5_str, [21, 4, 9, 26, 16, 20, 27, 30])
    t3 = _select(md5_str, [18, 11, 3, 2, 1, 7, 6, 25])

    ls2: list[int] = []
    for i in range(16):
        x1 = _K1[md5_str[i * 2]]
        x2 = _K1[md5_str[i * 2 + 1]]
        x3 = ((x1 * 16) ^ x2) ^ _L1[i]
        ls2.append(x3)

    ls3: list[str] = []
    for i in range(6):
        if i == 5:
            ls3.append(_T[ls2[-1] >> 2])
            ls3.append(_T[(ls2[-1] & 3) << 4])
        else:
            a, b, c = ls2[i * 3], ls2[i * 3 + 1], ls2[i * 3 + 2]
            x4 = a >> 2
            x5 = (b >> 4) ^ ((a & 3) << 4)
            x6 = (c >> 6) ^ ((b & 15) << 2)
            x7 = 63 & c
            ls3.append(_T[x4] + _T[x5] + _T[x6] + _T[x7])

    t2 = "".join(ls3)
    # ponytail: 原版 Go 用 strings.ReplaceAll(t2, "[\\/+]","") 做字面量替换，
    # base64 字母表不含 [ ]，该替换实为 no-op；此处保持一致以字节级对齐生产签名。
    t2 = t2.replace("[\\/+]", "")
    return "zzb" + (t1 + t2 + t3).lower()


if __name__ == "__main__":
    # 自检：与 Go Encrypt 算法对齐的参考向量（由 node 复现 Go 算法交叉验证）
    info = (
        '{"req_0":{"module":"music.srfDissInfo.aiDissInfo","method":"uniform_get_Dissinfo",'
        '"param":{"disstid":7364061065,"enc_host_uin":"","tag":1,"userinfo":1,'
        '"song_begin":1,"song_num":1024}},'
        '"comm":{"g_tk":5381,"uin":0,"format":"json","platform":"h5"}}'
    )
    expected = "zzbdd5bd143o9ynidy81gzlaeolyfu2ogdf1ff565"
    got = encrypt(info)
    assert got == expected, f"sign mismatch: {got} != {expected}"
    print("sign self-check passed:", got)
