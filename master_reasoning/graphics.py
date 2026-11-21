"""Deterministic, evidence-driven vector-like PNG graphics embedded in the DOCX.

Only the DOCX is written to disk. Each graphic is created in-memory from the
current inference objects, so the manually re-run workflow refreshes graphics.
"""
from __future__ import annotations
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from .deductions import name

BG='#FFFFFF'; NAVY='#1F3345'; DARK='#263746'; LIGHT='#EFF6F5'
TEAL='#247C7B'; PALE='#E6F2F0'; TAN='#FDF0E8'; ORANGE='#A45A36'
GREY='#607181'; LINE='#D8E2E4'; PURPLE='#57568C'


def _font(size=30,bold=False):
    paths=['/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',
           '/usr/share/fonts/truetype/liberation2/LiberationSans'+('-Bold' if bold else '-Regular')+'.ttf',
           '/usr/share/fonts/truetype/liberation/LiberationSans'+('-Bold' if bold else '-Regular')+'.ttf']
    for p in paths:
        try:return ImageFont.truetype(p,size)
        except OSError:pass
    return ImageFont.load_default()


def _wrap(draw,text,font,limit,maxlines=2):
    words=str(text).replace('_',' ').replace('→','to').split()
    lines=[]; curr=''
    for word in words:
        trial=(curr+' '+word).strip()
        if draw.textbbox((0,0),trial,font=font)[2]<=limit:
            curr=trial; continue
        if curr:lines.append(curr)
        curr=word
    if curr: lines.append(curr)
    if len(lines)>maxlines:
        lines=lines[:maxlines]
        while lines[-1] and draw.textbbox((0,0),lines[-1]+'…',font=font)[2]>limit:
            lines[-1]=lines[-1][:-1].rstrip()
        lines[-1]+='…'
    return lines


def _centered(draw,rect,text,font,color,maxlines=2,pad=20,spacing=6):
    x0,y0,x1,y1=rect; lines=_wrap(draw,text,font,(x1-x0)-2*pad,maxlines)
    height=len(lines)*(font.size+spacing)-spacing
    y=y0+(y1-y0-height)/2
    for line in lines:
        bb=draw.textbbox((0,0),line,font=font)
        draw.text((x0+(x1-x0-(bb[2]-bb[0]))/2,y),line,font=font,fill=color)
        y+=font.size+spacing


def _box(draw,rect,fill,stroke,rad=14,width=2):
    draw.rounded_rectangle(rect,radius=rad,fill=fill,outline=stroke,width=width)


def _line(draw,a,b,color,width=5,arrow=True,bar=False):
    draw.line([a,b],fill=color,width=width)
    if bar:
        draw.line([(b[0],b[1]-13),(b[0],b[1]+13)],fill=color,width=7)
    elif arrow:
        draw.polygon([(b[0],b[1]),(b[0]-18,b[1]-10),(b[0]-18,b[1]+10)],fill=color)


def _stream(image):
    buff=BytesIO();image.save(buff,format='PNG',optimize=True);buff.seek(0);return buff


def trend_map(trend):
    """Source-anchored positive topology and separate brake, visually distinct."""
    W,H=1320,345
    im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
    strong=_font(31,True);body=_font(29);small=_font(24)
    d.text((24,13),'DRIVING PATHWAYS',font=_font(21,True),fill=TEAL)
    paths=trend.get('network_path',[])
    if len(paths)==3:
        left=[name(paths[0]),name(paths[2])]
        target=name(paths[1]); source_label='Enabling routes'
    else:
        left=[f"Repeated direction: {trend.get('rule_key',[None,'change'])[1].replace('_',' ')}",
              'Independent dated assessments']
        target=name(trend.get('subject') or 'assessed system');source_label='Convergent evidence'
    d.text((790,13),source_label.upper(),font=_font(21,True),fill=TEAL)
    _box(d,(30,53,475,117),PALE,'#9CC6C2')
    _box(d,(30,135,475,199),PALE,'#9CC6C2')
    _centered(d,(30,53,475,117),left[0],body,NAVY)
    _centered(d,(30,135,475,199),left[1],body,NAVY)
    _box(d,(825,76,1286,190),'#E3EEF0',TEAL,rad=18,width=3)
    _centered(d,(825,76,1286,190),target,_font(35,True),NAVY)
    _line(d,(475,84),(825,110),TEAL,4)
    _line(d,(475,167),(825,156),TEAL,4)
    d.line([(24,220),(1295,220)],fill=LINE,width=2)
    counter=(trend.get('counterforces') or [])
    blocker=counter[0] if counter else None
    title=blocker['title'] if blocker else 'Check the critical transmission assumptions'
    label='INFERRED COUNTERFORCE / BRAKE' if blocker and blocker['kind']!='structural_gate' else 'MODEL CONSTRAINT'
    d.text((26,228),label,font=_font(21,True),fill=ORANGE)
    _box(d,(28,263,994,331),TAN,'#E6BEA3',rad=12)
    _centered(d,(28,263,994,331),title,_font(29,True),NAVY,maxlines=2)
    _line(d,(1006,297),(1255,297),ORANGE,5,arrow=False,bar=True)
    return _stream(im)


def overview(counts):
    """Amounts describe numbers of inferred entries, not real-world frequencies."""
    W,H=1320,340;im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    keys=[('TRENDS','trends',TEAL),('DISRUPTIONS','disruptions',PURPLE),
          ('RISKS','risks',ORANGE),('OPPORTUNITIES','opportunities','#456A98')]
    top=60; bottom=288
    mx=max((counts.get(k,0) for _,k,_ in keys),default=1) or 1
    for i,(label,key,color) in enumerate(keys):
        x=34+i*325
        d.text((x,17),label,font=_font(23,True),fill=NAVY)
        y=106
        d.rounded_rectangle((x,y,x+268,y+42),radius=12,fill='#EDF1F2')
        span=int(268*counts.get(key,0)/mx)
        if span>0:d.rounded_rectangle((x,y,x+span,y+42),radius=12,fill=color)
        d.text((x,160),str(counts.get(key,0)),font=_font(48,True),fill=color)
    d.line([(24,238),(1296,238)],fill=LINE,width=2)
    d.text((28,254),'Counts represent distinct inferred readings in this edition — not likelihood, importance or measured event frequency.',
           font=_font(20),fill=GREY)
    return _stream(im)


def scenario_grid(scenarios,axes,third_state):
    """Real 2x2 slices of 2x2x2, arranged by the actual axis-state keys."""
    first,second,third=[a['id'] for a in axes]
    W,H=1320,750;im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    d.text((30,14),f"{axes[2]['name']} — {third_state.upper()}",font=_font(27,True),fill=NAVY)
    d.text((32,58),f"COLUMNS — {axes[0]['name']}: LOW on left, HIGH on right  |  ROWS — {axes[1]['name']}: HIGH above, LOW below",font=_font(19),fill=GREY)
    # y: second axis high, low; x: first axis low, high.
    dy=320;dx=625;oy=112;ox=30
    for y,second_state in enumerate(('high','low')):
        for x,first_state in enumerate(('low','high')):
            s=next((q for q in scenarios if q['axis_states']=={first:first_state,second:second_state,third:third_state}),None)
            rect=(ox+dx*x,oy+dy*y,ox+dx*x+592,oy+dy*y+291)
            fill=['#EFF7F5','#F8F1EA','#ECF1FA','#F5F0F7'][(y*2+x)]
            _box(d,rect,fill,'#CAD8DB',rad=18,width=3)
            t=(s or {}).get('emergent_world','No scenario generated')
            d.text((rect[0]+20,rect[1]+21),f"{axes[1]['name'][:18]} {second_state.upper()}  /  {axes[0]['name'][:18]} {first_state.upper()}", 
                   font=_font(19,True),fill=GREY)
            line=_wrap(d,t,_font(31,True),545,2)
            for j,txt in enumerate(line):
                d.text((rect[0]+20,rect[1]+78+j*42),txt,font=_font(31,True),fill=NAVY)
            detail=(s or {}).get('interaction_inference','')
            words=_wrap(d,detail,_font(23),540,3)
            for j,txt in enumerate(words):
                d.text((rect[0]+20,rect[1]+160+j*32),txt,font=_font(23),fill=DARK)
    return _stream(im)


def section_flow(kind):
    patterns={
      'disruptions':('Initiating change','Shared dependency','System reconfiguration'),
      'risks':('Upstream expansion','Unresolved interface','Exposure / loss'),
      'opportunities':('New capability','Conversion interface','Value creation'),
    }
    labels=patterns[kind];W,H=1320,210
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    for i,(label,color) in enumerate(zip(labels,[TEAL,PURPLE,ORANGE])):
        x=25+i*442
        _box(d,(x,55,x+360,169),PALE if i==0 else ('#F1F0F8' if i==1 else TAN),LINE,rad=18)
        _centered(d,(x+5,60,x+350,162),label,_font(30,True),NAVY)
        if i<2:_line(d,(x+365,110),(x+430,110),GREY,6)
    return _stream(im)


def system_map(item):
    """Multi-node signed evidence graph. Boxes = verified claim anchors;
    all lines = transparent, defeasible bridge assumptions, NOT observed effects.
    """
    s=item.get('systemic') or {};focus=s.get('focus','')
    W,H=1600,580;im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    f=_font(26,True);sm=_font(21);accent=_font(18,True)
    d.text((30,14),'INDEPENDENTLY SOURCED SYSTEM NODES',font=accent,fill=GREY)
    d.text((1030,14),'LINKS ARE TESTABLE CAUSAL HYPOTHESES',font=accent,fill=ORANGE)
    positive=list(dict.fromkeys(s.get('drivers') or [])); negative=list(dict.fromkeys(s.get('constraints') or []))
    downstream=list(dict.fromkeys(s.get('downstream') or []))
    focus_label=name(focus) or 'Shared interface'
    positives=positive[:4]
    if not positives:positives=['Independent evidence streams']
    n=len(positives)
    ys=([270] if n==1 else [135,405] if n==2 else [98,270,442] if n==3 else [91,211,331,451])
    for i,(label,y) in enumerate(zip(positives,ys)):
        rect=(34,y-42,490,y+42)
        _box(d,rect,PALE,'#8EBFBA',rad=13)
        _centered(d,rect,label,f,NAVY,pad=19)
        d.line([(490,y),(680,265)],fill=TEAL,width=4)
    if len(positive)>4:
        d.text((34,530),f'+ {len(positive)-4} additional independently observed route(s)',font=sm,fill=GREY)
    focal=(682,217,1124,332)
    _box(d,focal,'#DDEEF0',TEAL,rad=20,width=4)
    _centered(d,focal,focus_label,_font(34,True),NAVY)
    d.text((727,351),'SHARED TRANSFER / ABSORPTION GATE',font=accent,fill=TEAL)
    if downstream:
        rect=(1205,215,1570,328)
        _box(d,rect,'#F0EEF8',PURPLE,rad=16,width=3)
        _centered(d,rect,downstream[0],f,NAVY)
        _line(d,(1124,268),(1205,268),PURPLE,width=5)
        d.text((1205,345),'CONDITIONAL SECOND STAGE',font=accent,fill=PURPLE)
    if negative:
        rect=(605,442,1180,522)
        _box(d,rect,TAN,'#CC8B64',rad=14,width=3)
        _centered(d,rect,'Restrictive force: '+negative[0],f,NAVY)
        d.line([(907,442),(907,371)],fill=ORANGE,width=5)
        d.line([(890,371),(924,371)],fill=ORANGE,width=6)
    else:
        d.text((658,467),'No independently anchored inhibitory bridge in this subgraph',font=sm,fill=GREY)
    d.line([(20,548),(1575,548)],fill=LINE,width=2)
    d.text((30,556),'Observed nodes: qualifying workbook-verified claims    |    Positive lines: enabling models    |    Stop-bar: constraining model',
           font=_font(17),fill=GREY)
    return _stream(im)


def temporal_map(item):
    """Show dated independent reporting without fabricating a measured slope."""
    from datetime import date
    W,H=1500,340;im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    d.text((25,14),'MULTI-SOURCE TEMPORAL EVIDENCE',font=_font(26,True),fill=NAVY)
    proof=[p for p in item.get('proof',[]) if p.get('date')]
    proof=sorted(proof,key=lambda p:p['date'])[:7]
    dates=[]
    for p in proof:
        try:dates.append(date.fromisoformat(p['date'][:10]))
        except ValueError:dates.append(None)
    aligned=[(p,dt) for p,dt in zip(proof,dates) if dt]
    if not aligned:return _stream(im)
    left,right=95,1410;y=162
    d.line([(left,y),(right,y)],fill=GREY,width=5)
    lo=min(dt.toordinal() for p,dt in aligned);hi=max(dt.toordinal() for p,dt in aligned)
    if hi==lo:hi+=1
    for i,(p,dt) in enumerate(aligned):
        x=left+(right-left)*(dt.toordinal()-lo)/(hi-lo)
        x=max(left+18,min(right-18,x))
        d.ellipse((x-10,y-10,x+10,y+10),fill=TEAL)
        above=i%2==0; yy=72 if above else 240
        d.line([(x,y-10 if above else y+10),(x,yy+18 if above else yy-12)],fill=TEAL,width=3)
        label=(str(p.get('source') or 'Independent report')[:22]+' · '+dt.strftime('%b %Y'))
        bb=d.textbbox((0,0),label,font=_font(18,True));tx=max(12,min(W-(bb[2]-bb[0])-12,x-(bb[2]-bb[0])/2))
        d.text((tx,yy),label,font=_font(18,True),fill=NAVY)
    d.text((23,301),'This plots independently dated source assessments, not an estimated trend magnitude or growth rate.',
           font=_font(18),fill=GREY)
    return _stream(im)


def frontier_map(item):
    """Multi-layer signed topology of the specific abductive reconstruction.

    Does not draw a statistically inferred network: node anchors are verified;
    directed edges are the editable, hypothetical mechanism registry.
    """
    f=item.get('frontier') or {}
    nodes=f.get('nodes') or []
    edges=f.get('edges') or []
    focus=f.get('focus','')
    if not nodes:return temporal_map(item)
    W,H=1800,930
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    d.text((38,18),'INTERACTING SYSTEMS  /  CONDITIONAL CAUSAL TOPOLOGY',font=_font(24,True),fill=NAVY)
    d.text((39,56),'Verified observation at each node  ·  arrows are inspectable mechanism assumptions  ·  orange lines constrain',font=_font(20),fill=GREY)
    positive=[e for e in edges if e['relation']!='constrains']
    from collections import defaultdict,deque
    reverse=defaultdict(list);forward=defaultdict(list)
    for b in positive:
        forward[b['from']].append(b['to']);reverse[b['to']].append(b['from'])
    def levels(graph):
        seen={focus:0};q=deque([focus])
        while q:
            x=q.popleft()
            for y in graph.get(x,[]):
                if y not in seen:seen[y]=seen[x]+1;q.append(y)
        return seen
    ancestors=levels(reverse);descendants=levels(forward)
    degrees=defaultdict(int);inhibited=set()
    for b in edges:
        degrees[b['from']]+=1;degrees[b['to']]+=1
        if b['relation']=='constrains':inhibited.add(b['from'])
    seed={p['object'] for p in item.get('proof',[]) if p.get('object')}
    ranked=sorted([x for x in nodes if x!=focus],key=lambda n:
       (-int(n in seed),-int(n in inhibited),-degrees[n],n))
    chosen={focus}
    # Ensure chart stays legible. The full model is retained outside the figure.
    for n in ranked:
        if len(chosen)>=13:break
        if any(b['from']==n and b['to'] in chosen or b['to']==n and b['from'] in chosen for b in edges):
            chosen.add(n)
    for n in ranked:
        if len(chosen)>=13:break
        if n not in chosen and any(b['from']==n and b['to'] in chosen or b['to']==n and b['from'] in chosen for b in edges):chosen.add(n)
    axis={-2:[], -1:[],0:[],1:[],2:[]}
    axis[0].append(focus)
    for n in sorted(chosen-{focus}):
        a=ancestors.get(n,999);z=descendants.get(n,999)
        if a!=999 and (a<=z or z==999): col=-2 if a>=2 else -1
        elif z!=999: col=2 if z>=2 else 1
        else:col=-1 if n in inhibited else 1
        axis[col].append(n)
    # Enforce max four vertically; move overflow near the focal interface.
    for col in (-2,-1,1,2):
        overflow=axis[col][4:];axis[col]=axis[col][:4]
        for n in overflow:
            options=[c for c in (-2,-1,1,2) if len(axis[c])<4]
            if options:axis[min(options,key=lambda c:abs(c-col))].append(n)
    positions={}
    xcoord={-2:45,-1:394,0:750,1:1090,2:1440}
    for col,labels in axis.items():
        n=len(labels)
        for i,label in enumerate(labels):
            xpos=xcoord[col]; ypos=140+(i+0.5)*(690/max(n,1))-48
            positions[label]=(int(xpos),int(ypos),int(xpos+310),int(ypos+96))
    for e in edges:
        if e['from'] not in positions or e['to'] not in positions:continue
        a=positions[e['from']];b=positions[e['to']]
        # Place arrows behind nodes. A line displays an assumed relationship,
        # not a measured transfer rate, causal estimate or realized change.
        ax=(a[0]+a[2])/2;ay=(a[1]+a[3])/2
        bx=(b[0]+b[2])/2;by=(b[1]+b[3])/2
        dx=bx-ax;dy=by-ay
        if abs(dx)>=abs(dy):
            sx=a[2] if dx>0 else a[0];tx=b[0] if dx>0 else b[2]
            sy=ay;ty=by
        else:
            sx=ax;tx=bx;sy=a[3] if dy>0 else a[1];ty=b[1] if dy>0 else b[3]
        color=ORANGE if e['relation']=='constrains' else (PURPLE if e['relation']=='substitutes' else TEAL)
        d.line([(sx,sy),(tx,ty)],width=4,fill=color)
        if e['relation']=='constrains':
            if abs(dx)>=abs(dy):d.line([(tx,ty-12),(tx,ty+12)],fill=color,width=6)
            else:d.line([(tx-12,ty),(tx+12,ty)],fill=color,width=6)
        else:
            # Terminal arrow triangle follows actual edge orientation.
            import math
            theta=math.atan2(ty-sy,tx-sx);L=14
            d.polygon([(tx,ty),
              (tx-L*math.cos(theta-.57),ty-L*math.sin(theta-.57)),
              (tx-L*math.cos(theta+.57),ty-L*math.sin(theta+.57))],fill=color)
    for label,rect in positions.items():
        center=(label==focus)
        restricted=label in inhibited
        _box(d,rect,'#D8EFEC' if center else (TAN if restricted else '#F0F5F5'),
            TEAL if center else (ORANGE if restricted else LINE),rad=13,width=4 if center else 2)
        _centered(d,rect,name(label),_font(22,True) if center else _font(20),NAVY,pad=12)
    d.line([(38,850),(1760,850)],fill=LINE,width=2)
    hidden=len(nodes)-len(positions)
    if hidden:
        d.text((45,852),'Part of the anchored network is hidden to keep this figure readable.',font=_font(18),fill=GREY)
    d.text((45,882),'All arrows are testable mechanism assumptions; no quantitative effect, timing or probability is estimated.',
       font=_font(18),fill=GREY)
    return _stream(im)
