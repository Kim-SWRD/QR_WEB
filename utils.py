import io
import zlib
import base64
import struct

# 將 VERSION 與 CHUNK 調小，減少單張 QR Code 的尺寸，提高掃描成功率
VERSION = 15
CHUNK   = 500

_EXP = [0]*512; _LOG = [0]*256; _x = 1
for _i in range(255):
    _EXP[_i] = _x; _LOG[_x] = _i; _x <<= 1
    if _x & 256: _x ^= 0x11d
for _i in range(255, 512): _EXP[_i] = _EXP[_i-255]

_rs_cache = {}
def _rs_gen(n):
    if n in _rs_cache: return _rs_cache[n]
    g = [1]
    for i in range(n):
        ng = [0]*(len(g)+1)
        for j, c in enumerate(g):
            if c: lc=_LOG[c]; ng[j]^=_EXP[lc]; ng[j+1]^=_EXP[lc+i]
        g = ng
    _rs_cache[n] = g; return g

def _rs(data, n):
    g=_rs_gen(n); r=bytearray(data)+bytearray(n); L=len(data)
    for i in range(L):
        if r[i]:
            li=_LOG[r[i]]
            for j in range(len(g)):
                if g[j]: r[i+j]^=_EXP[_LOG[g[j]]+li]
    return bytes(r[-n:])

_ECL = [(0,0,0,0,0),
 (7,1,19,0,0),(10,1,34,0,0),(15,1,55,0,0),(20,1,80,0,0),(26,1,108,0,0),
 (18,2,68,0,0),(20,2,78,0,0),(24,2,97,0,0),(30,2,116,0,0),(18,2,68,2,69),
 (20,4,81,0,0),(24,2,92,2,93),(26,4,107,0,0),(30,3,115,1,116),(22,5,87,1,88),
 (24,5,98,1,99),(28,1,107,5,108),(30,5,120,1,121),(28,3,113,4,114),(28,3,107,5,108),
 (28,4,116,4,117),(28,2,111,7,112),(30,4,121,5,122),(30,6,117,4,118),(26,8,106,4,107),
 (28,10,114,2,115),(30,8,122,4,123),(30,3,117,10,118),(30,7,116,7,117),(30,5,115,10,116),
 (30,13,115,3,116),(30,17,115,0,0),(30,17,115,1,116),(30,13,115,6,116),(30,12,121,7,122),
 (30,6,121,14,122),(30,17,122,4,123),(30,4,122,18,123),(30,20,117,4,118),(30,19,118,6,119),
 ]

def _align_pos(v):
    if v < 2: return []
    n=v//7+2; last=4*v+10
    if n==2: return [6, last]
    step=-(-(last-6)//(n-1))
    if step%2: step+=1
    pos=[last]
    for _ in range(n-2): pos.insert(0, pos[0]-step)
    pos.insert(0,6); return pos

def _fmt_info(mask):
    d=(1<<3)|mask; r=d<<10
    for i in range(14,9,-1):
        if r&(1<<i): r^=0x537<<(i-10)
    return (d<<10|r)^0x5412

def _ver_info(v):
    d=v<<12
    for i in range(17,11,-1):
        if d&(1<<i): d^=0x1F25<<(i-12)
    return (v<<12)|d

def _encode_cw(data, v):
    ec,g1n,g1d,g2n,g2d=_ECL[v]; total=g1n*g1d+g2n*g2d
    cc=8 if v<=9 else 16; n=len(data)
    bits=[0,1,0,0]
    for i in range(cc-1,-1,-1): bits.append((n>>i)&1)
    for b in data:
        for i in range(7,-1,-1): bits.append((b>>i)&1)
    bits+=[0]*min(4, total*8-len(bits))
    rem=(8-len(bits)%8)%8; bits+=[0]*min(rem, total*8-len(bits))
    cw=[int(''.join(str(b) for b in bits[i:i+8]),2) for i in range(0,len(bits),8)]
    pads=[0xEC,0x11]; pi=0
    while len(cw)<total: cw.append(pads[pi]); pi^=1
    return cw

def _interleave(dcw, v):
    ec,g1n,g1d,g2n,g2d=_ECL[v]; blks=[]; pos=0
    for _ in range(g1n): blks.append(dcw[pos:pos+g1d]); pos+=g1d
    for _ in range(g2n): blks.append(dcw[pos:pos+g2d]); pos+=g2d
    ecb=[_rs(b,ec) for b in blks]; res=bytearray()
    for i in range(max(len(b) for b in blks)):
        for b in blks:
            if i<len(b): res.append(b[i])
    for i in range(ec):
        for e in ecb: res.append(e[i])
    return bytes(res)

def make_qr(text):
    data=text.encode() if isinstance(text,str) else bytes(text)
    v=VERSION; S=4*v+17
    stream=_interleave(_encode_cw(data,v),v)
    bits=[]
    for b in stream:
        for i in range(7,-1,-1): bits.append((b>>i)&1)
    rem=7 if v in(2,3,4,5,6) else 4 if 21<=v<=27 else 3 if 14<=v<=34 else 0
    bits+=[0]*rem

    M=bytearray(S*S); F=bytearray(S*S)
    def _s(r,c,val,fn=True):
        if 0<=r<S and 0<=c<S: M[r*S+c]=val; F[r*S+c]=int(bool(fn))
    def _rect(r0,c0,w,h,val,fn=True):
        for i in range(h):
            for j in range(w): _s(r0+i,c0+j,val,fn)
    def _finder(r,c):
        _rect(r-1,c-1,9,9,0); _rect(r,c,7,7,1)
        _rect(r+1,c+1,5,5,0); _rect(r+2,c+2,3,3,1)

    _finder(0,0); _finder(0,S-7); _finder(S-7,0)
    for ar in _align_pos(v):
        for ac in _align_pos(v):
            if not F[ar*S+ac]:
                _rect(ar-2,ac-2,5,5,1); _rect(ar-1,ac-1,3,3,0); _s(ar,ac,1)
    for i in range(S):
        if not F[6*S+i]: _s(6,i,int(i%2==0))
        if not F[i*S+6]: _s(i,6,int(i%2==0))
    _s(4*v+9,8,1)
    if v>=7:
        vi=_ver_info(v)
        for i in range(6):
            for j in range(3):
                b=(vi>>(i*3+j))&1; _s(i,S-11+j,b); _s(S-11+j,i,b)

    for i in range(9): F[8*S+i]=1; F[i*S+8]=1
    for i in range(1,9): F[(S-i)*S+8]=1
    for i in range(8):   F[8*S+(S-8+i)]=1

    cells=[]; dr=-1; r=S-1; c=S-1
    while c>0:
        if c==6: c-=1
        for _ in range(S):
            for j in [0,1]:
                cc=c-j
                if not F[r*S+cc]: cells.append(r*S+cc)
            r+=dr
        r-=dr; dr=-dr; c-=2
    for k,pos in enumerate(cells):
        M[pos]=bits[k] if k<len(bits) else 0

    def _penalty(T):
        score=0
        for i in range(S):
            for horiz in (True,False):
                run=1; prev=T[i*S] if horiz else T[i]
                for j in range(1,S):
                    cur=T[i*S+j] if horiz else T[j*S+i]
                    if cur==prev: run+=1
                    else:
                        if run>=5: score+=run-2
                        run=1; prev=cur
                if run>=5: score+=run-2
        for r2 in range(S-1):
            for c2 in range(S-1):
                v0=T[r2*S+c2]
                if v0==T[r2*S+c2+1]==T[(r2+1)*S+c2]==T[(r2+1)*S+c2+1]: score+=3
        dark=sum(T); pct=dark*100//(S*S); p5=(pct//5)*5
        score+=min(abs(p5-50),abs(p5+5-50))//5*10
        return score

    def _mask_fn(m,r,c):
        if m==0: return (r+c)%2==0
        if m==1: return r%2==0
        if m==2: return c%3==0
        if m==3: return (r+c)%3==0
        if m==4: return (r//2+c//3)%2==0
        if m==5: return (r*c)%2+(r*c)%3==0
        if m==6: return ((r*c)%2+(r*c)%3)%2==0
        return ((r+c)%2+(r*c)%3)%2==0

    best=None; bmat=None
    for mask in range(8):
        T=bytearray(M)
        for pos in cells:
            r2,c2=divmod(pos,S)
            if _mask_fn(mask,r2,c2): T[pos]^=1
        fi=_fmt_info(mask); vo=ho=0
        for i in range(8):
            vb=(fi>>i)&1; hb=(fi>>(14-i))&1
            if i==6: vo=1; ho=1
            T[(i+vo)*S+8]=vb; T[8*S+i+ho]=hb
            T[8*S+S-1-i]=vb; T[(S-1-i)*S+8]=hb
        T[(S-8)*S+8]=1
        sc=_penalty(T)
        if best is None or sc<best: best=sc; bmat=T

    return [[bmat[r2*S+c2] for c2 in range(S)] for r2 in range(S)]

_F = {
    ' ':0b00000_00000_00000_00000_00000_00000_00000,
    '0':0b01110_10001_10011_10101_11001_10001_01110,
    '1':0b00100_01100_00100_00100_00100_00100_01110,
    '2':0b01110_10001_00001_00010_00100_01000_11111,
    '3':0b11111_00010_00100_00010_00001_10001_01110,
    '4':0b00010_00110_01010_10010_11111_00010_00010,
    '5':0b11111_10000_11110_00001_00001_10001_01110,
    '6':0b00110_01000_10000_11110_10001_10001_01110,
    '7':0b11111_00001_00010_00100_01000_01000_01000,
    '8':0b01110_10001_10001_01110_10001_10001_01110,
    '9':0b01110_10001_10001_01111_00001_00010_01100,
    '/':0b00001_00001_00010_00100_01000_10000_10000,
}

def _draw_label(buf, width, y0, label, px=6):
    cw=(5+1)*px; x0=max((width-cw*len(label))//2, 0)
    for ci,ch in enumerate(label):
        bits=_F.get(ch,_F[' ']); gx=x0+ci*cw
        for row in range(7):
            for col in range(5):
                on=(bits>>(34-row*5-col))&1
                color=0 if on else 255
                for dy in range(px):
                    for dx in range(px):
                        px_x=gx+col*px+dx; px_y=y0+row*px+dy
                        if 0<=px_x<width: buf[px_y*width+px_x]=color

def create_qr_image_bytes(M, px=10, border=4, label=None):
    """
    修改自原始 save_png[cite: 1]。
    將生成的 PNG 寫入記憶體 buffer 中，供 Streamlit 直接讀取顯示。
    """
    S=len(M); side=(S+border*2)*px
    lh=(7*6+6*2) if label else 0
    W=side; H=side+lh
    buf=bytearray(b'\xff'*(W*H))
    if label: _draw_label(buf,W,6,label)
    for r in range(side):
        qr=r//px-border
        for c in range(side):
            qc=c//px-border
            buf[(lh+r)*W+c]=0 if (0<=qr<S and 0<=qc<S and M[qr][qc]) else 255
    raw=bytearray()
    for r in range(H): raw.append(0); raw+=buf[r*W:(r+1)*W]
    comp=zlib.compress(bytes(raw),9)
    def ck(tag,data):
        p=tag+data; return struct.pack('>I',len(data))+p+struct.pack('>I',zlib.crc32(p)&0xFFFFFFFF)
    
    out = io.BytesIO()
    out.write(b'\x89PNG\r\n\x1a\n')
    out.write(ck(b'IHDR',struct.pack('>IIBBBBB',W,H,8,0,0,0,0)))
    out.write(ck(b'IDAT',comp))
    out.write(ck(b'IEND',b''))
    return out.getvalue()

def process_data_to_qrs(raw_bytes):
    """
    接收二進位資料，依照 zlib 壓縮並進行 Base64 編碼，再切塊產生 QR Code[cite: 1]。
    """
    b64 = base64.b64encode(zlib.compress(raw_bytes, 9)).decode()
    chunks = [b64[i:i+CHUNK] for i in range(0, len(b64), CHUNK)]
    total = len(chunks)
    
    images = []
    for i, chunk in enumerate(chunks, 1):
        M = make_qr(chunk)
        img_bytes = create_qr_image_bytes(M, px=10, border=4, label=f'{i}/{total}')
        images.append(img_bytes)
        
    return images