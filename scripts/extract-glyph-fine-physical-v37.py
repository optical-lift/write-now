import json, math, hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.measure import label, regionprops, perimeter, euler_number, moments_hu
from skimage.morphology import skeletonize
from sklearn.decomposition import PCA
import networkx as nx

FONT='/usr/share/fonts/truetype/noto/NotoSansHebrew-Regular.ttf'
CPS=[1425,1426,1427,1428,1429,1430,1431,1432,1433,1434,1435,1436,1437,1438,1439,1440,1441,1443,1444,1445,1446,1447,1448,1449,1450,1451,1452,1453,1454,1469]
SIZE=512
font=ImageFont.truetype(FONT,SIZE)
font_bytes=Path(FONT).read_bytes()

def render(cp):
    ch=chr(cp); bbox=font.getbbox(ch)
    w=max(1,bbox[2]-bbox[0]); h=max(1,bbox[3]-bbox[1])
    img=Image.new('L',(w+80,h+80),0); d=ImageDraw.Draw(img)
    d.text((40-bbox[0],40-bbox[1]),ch,font=font,fill=255)
    a=np.array(img); ys,xs=np.where(a>16)
    if len(xs)==0: raise RuntimeError(cp)
    a=a[ys.min():ys.max()+1,xs.min():xs.max()+1]
    scale=256/max(a.shape); nh=max(1,round(a.shape[0]*scale)); nw=max(1,round(a.shape[1]*scale))
    r=np.array(Image.fromarray(a).resize((nw,nh),Image.Resampling.LANCZOS))
    c=np.zeros((320,320),dtype=np.uint8); y=(320-nh)//2; x=(320-nw)//2; c[y:y+nh,x:x+nw]=r
    return c

def graph_from_skel(sk):
    pts=np.argwhere(sk); idx={tuple(p):i for i,p in enumerate(pts)}; G=nx.Graph()
    for i,p in enumerate(pts): G.add_node(i,y=int(p[0]),x=int(p[1]))
    nbrs=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    for i,(y,x) in enumerate(pts):
        for dy,dx in nbrs:
            j=idx.get((int(y+dy),int(x+dx)))
            if j is not None and j>i: G.add_edge(i,j,weight=math.sqrt(2) if dy and dx else 1.0)
    return G

def branch_lengths(G):
    if len(G)==0:return []
    deg=dict(G.degree()); anchors={n for n,d in deg.items() if d!=2}; seen=set(); out=[]
    for a in anchors:
        for b in G.neighbors(a):
            ek=tuple(sorted((a,b)))
            if ek in seen: continue
            seen.add(ek); length=G[a][b]['weight']; prev=a; cur=b
            while cur not in anchors:
                ns=[n for n in G.neighbors(cur) if n!=prev]
                if not ns: break
                nxt=ns[0]; seen.add(tuple(sorted((cur,nxt)))); length+=G[cur][nxt]['weight']; prev,cur=cur,nxt
            out.append(length)
    return out

def projection_bins(mask,axis,bins=6):
    v=mask.sum(axis=axis).astype(float)
    if v.sum(): v/=v.sum()
    return [float(x.sum()) for x in np.array_split(v,bins)]

def radial_bins(mask,bins=6):
    ys,xs=np.where(mask); cy=ys.mean(); cx=xs.mean(); r=np.sqrt((ys-cy)**2+(xs-cx)**2); mx=max(r.max(),1)
    hist,_=np.histogram(r,bins=bins,range=(0,mx)); return (hist/hist.sum()).tolist()

def features(cp):
    img=render(cp); mask=img>64; lab=label(mask,connectivity=2); props=regionprops(lab)
    area=float(mask.sum()); bbox=np.argwhere(mask); ymin,xmin=bbox.min(0); ymax,xmax=bbox.max(0); h=ymax-ymin+1; w=xmax-xmin+1
    sk=skeletonize(mask); G=graph_from_skel(sk); deg=np.array([d for _,d in G.degree()],dtype=float) if len(G) else np.array([])
    endpoints=int((deg==1).sum()) if len(deg) else 0; junctions=int((deg>=3).sum()) if len(deg) else 0; branches=branch_lengths(G)
    comps=len(props); holes=int(comps-euler_number(mask,connectivity=2)); per=float(perimeter(mask,neighborhood=8))
    ys,xs=np.where(mask); cy=float(ys.mean()/319); cx=float(xs.mean()/319)
    coords=np.c_[xs-xs.mean(),ys-ys.mean()]; cov=np.cov(coords,rowvar=False) if len(coords)>1 else np.eye(2)
    vals,vecs=np.linalg.eigh(cov); order=np.argsort(vals)[::-1]; vals=vals[order]; vecs=vecs[:,order]
    angle=float(math.atan2(vecs[1,0],vecs[0,0])/math.pi); ecc=float(math.sqrt(max(0,1-(vals[1]/vals[0] if vals[0]>0 else 1))))
    fm=mask.astype(float); symv=1-float(np.mean(np.abs(fm-np.fliplr(fm)))); symh=1-float(np.mean(np.abs(fm-np.flipud(fm)))); sym180=1-float(np.mean(np.abs(fm-np.rot90(fm,2))))
    solidity=float(sum(p.area for p in props)/max(1,sum(p.area_convex for p in props))); compact=float(4*math.pi*area/(per*per)) if per else 0
    hu=[float(-math.copysign(1,x)*math.log10(abs(x)+1e-30)) for x in moments_hu(mask.astype(float))]
    comp_areas=np.array([p.area for p in props],dtype=float); comp_cent=np.array([p.centroid for p in props],dtype=float) if props else np.zeros((0,2))
    if len(props)>1:
        ds=[]; ang=[]
        for i in range(len(props)):
            for j in range(i+1,len(props)):
                dy=comp_cent[j,0]-comp_cent[i,0]; dx=comp_cent[j,1]-comp_cent[i,1]; ds.append(math.hypot(dx,dy)/max(w,h)); ang.append(math.atan2(dy,dx)/math.pi)
        comp_dist_mean=float(np.mean(ds)); comp_dist_max=float(np.max(ds)); comp_angle_mean=float(np.mean(ang)); comp_cent_spread=float(np.std(comp_cent[:,0]/320)+np.std(comp_cent[:,1]/320))
    else: comp_dist_mean=comp_dist_max=comp_angle_mean=comp_cent_spread=0.0
    bl=np.array(branches,dtype=float); diam=0.0
    if len(G):
        for cc in nx.connected_components(G):
            sg=G.subgraph(cc)
            if len(sg)>1:
                s=next(iter(sg.nodes)); d1=nx.single_source_dijkstra_path_length(sg,s,weight='weight'); u=max(d1,key=d1.get); d2=nx.single_source_dijkstra_path_length(sg,u,weight='weight'); diam=max(diam,max(d2.values()))
    raw48={'components':comps,'holes':holes,'euler':int(euler_number(mask,connectivity=2)),'endpoints':endpoints,'junctions':junctions,'skeleton_length':float(sk.sum()/256),'width':float(w/256),'height':float(h/256),'aspect':float(w/h),'area_density':float(area/(w*h)),'bbox_occupancy':float(area/(320*320)),'perimeter_norm':per/256,'compactness':compact,'solidity':solidity,'eccentricity':ecc,'orientation_pi':angle,'centroid_x':cx,'centroid_y':cy,'sym_vertical':symv,'sym_horizontal':symh,'sym_rot180':sym180}
    for i,v in enumerate(projection_bins(mask,0)):raw48[f'proj_x_{i}']=v
    for i,v in enumerate(projection_bins(mask,1)):raw48[f'proj_y_{i}']=v
    for i,v in enumerate(radial_bins(mask)):raw48[f'radial_{i}']=v
    for i,v in enumerate(hu[:7]):raw48[f'hu_{i}']=v
    raw48['boundary_complexity']=per/max(1,math.sqrt(area)); raw48['axis_ratio']=float(math.sqrt(vals[1]/vals[0])) if vals[0]>0 else 0
    rel=dict(raw48); rel.update({'graph_degree_mean':float(deg.mean()) if len(deg) else 0,'graph_degree_std':float(deg.std()) if len(deg) else 0,'graph_degree_max':float(deg.max()) if len(deg) else 0,'graph_diameter':float(diam/256),'branch_count':len(branches),'branch_len_mean':float(bl.mean()/256) if len(bl) else 0,'branch_len_std':float(bl.std()/256) if len(bl) else 0,'branch_len_max':float(bl.max()/256) if len(bl) else 0,'terminal_ratio':float(endpoints/max(1,len(G))),'component_area_mean':float(comp_areas.mean()/area) if len(comp_areas) else 0,'component_area_std':float(comp_areas.std()/area) if len(comp_areas) else 0,'component_area_max':float(comp_areas.max()/area) if len(comp_areas) else 0,'component_area_min':float(comp_areas.min()/area) if len(comp_areas) else 0,'component_size_ratio':float(comp_areas.max()/max(1,comp_areas.min())) if len(comp_areas) else 0,'component_dist_mean':comp_dist_mean,'component_dist_max':comp_dist_max,'component_angle_mean':comp_angle_mean,'component_centroid_spread':comp_cent_spread})
    for k in range(1,7):rel[f'degree_frac_{k}']=float((deg==k).mean()) if len(deg) else 0
    for qi,q in enumerate([.25,.5,.75,.9]):rel[f'branch_q_{qi}']=float(np.quantile(bl,q)/256) if len(bl) else 0
    rel['component_x_spread']=float(np.std(comp_cent[:,1]/max(1,w))) if len(props) else 0; rel['component_y_spread']=float(np.std(comp_cent[:,0]/max(1,h))) if len(props) else 0
    rel['relation_pair_count']=float(comps*(comps-1)/2); rel['component_entropy']=float(-(lambda p:np.sum(p*np.log(p+1e-15)))(comp_areas/comp_areas.sum())) if len(comp_areas) else 0
    return raw48,rel,hashlib.sha256(img.tobytes()).hexdigest()

rows={}
for cp in CPS:
    r48,r80,h=features(cp); rows[str(cp)]={'fine48':r48,'rel80':r80,'render_hash':h}

def pca_repr(field,names=None):
    if names is None:names=list(next(iter(rows.values()))[field].keys())
    X=np.array([[rows[str(cp)][field][n] for n in names] for cp in CPS],float); med=np.median(X,axis=0); mad=np.median(np.abs(X-med),axis=0)*1.4826; sd=X.std(axis=0); scale=np.where(mad>1e-12,mad,np.where(sd>1e-12,sd,1.0)); Z=np.clip((X-med)/scale,-5,5); varying=Z.std(axis=0)>1e-12; Zv=Z[:,varying]
    pca=PCA().fit(Zv); cum=np.cumsum(pca.explained_variance_ratio_); k=int(np.searchsorted(cum,.95)+1); P=pca.transform(Zv)[:,:k]; ps=P.std(axis=0); ps=np.where(ps>1e-12,ps,1); P=P/ps
    return {'k':k,'cumulative_explained':float(cum[k-1]),'pcs':{str(cp):P[i].tolist() for i,cp in enumerate(CPS)}}

out={'font':{'path_basename':Path(FONT).name,'sha256':hashlib.sha256(font_bytes).hexdigest(),'size_bytes':len(font_bytes)},'glyphs':rows,'lane2':pca_repr('fine48'),'lane3':pca_repr('rel80')}
fine_names=list(next(iter(rows.values()))['fine48'].keys()); rel_names=list(next(iter(rows.values()))['rel80'].keys()); topology={'components','holes','euler','endpoints','junctions','skeleton_length'}; symmetry={'sym_vertical','sym_horizontal','sym_rot180'}; graph={n for n in rel_names if n.startswith('graph_') or n.startswith('branch_') or n.startswith('degree_frac_') or n=='terminal_ratio'}; internal={n for n in rel_names if n.startswith('component_') or n=='relation_pair_count'}; geometry=set(fine_names)-topology-symmetry
out['feature_families']={k:sorted(v) for k,v in {'topology':topology,'geometry':geometry,'symmetry':symmetry,'graph':graph,'internal_relations':internal}.items()}; out['ablations']={}
for family,members in out['feature_families'].items(): out['ablations']['minus_'+family]=pca_repr('rel80',[n for n in rel_names if n not in set(members)])
coll={}
for cp in CPS:coll.setdefault(rows[str(cp)]['render_hash'],[]).append(cp)
out['render_hash_collisions']=[v for v in coll.values() if len(v)>1]
Path('/mnt/data/v37_glyph_features.json').write_text(json.dumps(out,sort_keys=True,separators=(',',':')))
