"""PDF, placement maps and offline browser guide generated from one model."""
import html
import json
from pathlib import Path
from bricklib import COLORS, PARTS, bbox, dumps, inventory, shape

def placements(model, step):
    by={p['id']:p for p in model['parts']}
    return [{'marker':i,'instance':id,'part_id':by[id]['part'],'color_id':by[id]['color'],
             'x':by[id]['x'],'y':by[id]['y'],'z':by[id]['z'],'rotation':by[id]['rotation']} for i,id in enumerate(step['parts'],1)]

def map_svg(model,step,previous):
    by={p['id']:p for p in model['parts']};x0,y0,_,x1,y1,_=bbox(model)
    unit=min(240/(x1-x0),240/(y1-y0));ox=32;oy=24
    W=(x1-x0)*unit+64;H=(y1-y0)*unit+60
    rows=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="white"/>']
    for x in range(x0,x1+1):
        px=ox+(x-x0)*unit
        rows.append(f'<path d="M {px} {oy} V {oy+(y1-y0)*unit}" stroke="#dce3e8" stroke-width=".6"/>')
        if x<x1:rows.append(f'<text x="{px+unit/2}" y="15" text-anchor="middle" font-family="sans-serif" font-size="9" fill="#53616c">{x}</text>')
    for y in range(y0,y1+1):
        py=oy+(y1-y)*unit
        rows.append(f'<path d="M {ox} {py} H {ox+(x1-x0)*unit}" stroke="#dce3e8" stroke-width=".6"/>')
        if y<y1:rows.append(f'<text x="20" y="{py-unit/2+3}" text-anchor="middle" font-family="sans-serif" font-size="9" fill="#53616c">{y}</text>')
    for id in sorted(previous,key=lambda id:by[id]['z']):
        p=by[id];w,d,_=shape(p)
        rows.append(f'<rect x="{ox+(p["x"]-x0)*unit+1}" y="{oy+(y1-p["y"]-d)*unit+1}" width="{w*unit-2}" height="{d*unit-2}" fill="#edf0f2" stroke="#cbd3da"/>')
    for item in placements(model,step):
        p=by[item['instance']];w,d,_=shape(p);px=ox+(p['x']-x0)*unit;py=oy+(y1-p['y']-d)*unit
        rows.append(f'<rect x="{px+1}" y="{py+1}" width="{w*unit-2}" height="{d*unit-2}" fill="{COLORS[p["color"]]["hex"]}" stroke="#26333c" stroke-width="1.2"/>')
        for ix in range(w):
            for iy in range(d):rows.append(f'<circle cx="{px+(ix+.5)*unit}" cy="{py+(iy+.5)*unit}" r="{unit*.19}" fill="none" stroke="#ffffff" stroke-opacity=".55"/>')
        cx=px+w*unit/2;cy=py+d*unit/2
        rows.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="#fff" stroke="#23364b"/><text x="{cx}" y="{cy+3}" text-anchor="middle" font-family="sans-serif" font-size="9" font-weight="bold">{item["marker"]}</text>')
    rows.append(f'<text x="{W/2}" y="{H-8}" text-anchor="middle" font-family="sans-serif" font-size="10" fill="#53616c">FRONT / Y = {y0}</text></svg>')
    return ''.join(rows)

def export_steps(model,out):
    by={p['id']:p for p in model['parts']};steps=[];previous=set();view='front-right'
    for n,step in enumerate(model['steps'],1):
        view=step.get('view',view)
        (out/f'instructions/map-{n:03}.svg').write_text(map_svg(model,step,previous))
        steps.append(dict(number=n,title=step['title'],note=step.get('note',''),view=view,
                          image=f'step-{n:03}.png',map=f'map-{n:03}.svg',parts=inventory([by[id] for id in step['parts']]),
                          placements=placements(model,step)))
        previous.update(step['parts'])
    result={'schema_version':'1.0','model_id':model['id'],'steps':steps}
    (out/'instructions/steps.json').write_text(dumps(result));return steps

def browser(model,steps,out,style='studio'):
    payload=json.dumps({'model':{k:model[k] for k in ('id','title','author')},'steps':steps,'colors':COLORS},ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · Building guide</title><style>
:root{--ink:#19394b;--muted:#637786;--line:#dfe7ed;--blue:#006d9c;--paper:#f4f8fb}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}header{padding:20px 4vw;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:20px}header strong{font-size:19px;letter-spacing:-.5px}header nav{display:flex;gap:20px}a{color:var(--ink);text-underline-offset:4px;font-size:14px}main{max-width:1300px;margin:auto;padding:28px 4vw}.heading{display:flex;align-items:center;gap:22px;margin-bottom:20px}.number{font:700 56px/1 ui-monospace,SFMono-Regular,monospace;color:var(--blue);letter-spacing:-5px}h1{font-size:clamp(20px,3vw,30px);letter-spacing:-.7px;line-height:1.15;margin:0}.counter{font:13px ui-monospace,monospace;color:var(--muted)}.layout{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:40px}.assembly{background:#fff;display:block;width:100%;max-height:66vh;object-fit:contain}.aside h2{font-size:13px;text-transform:uppercase;letter-spacing:1px;margin:0 0 12px}.part{display:flex;align-items:center;gap:12px;margin:12px 0}.swatch{width:20px;height:20px;border-radius:3px;box-shadow:inset 0 0 0 1px #0002;flex-shrink:0}.part small{display:block;font-size:12px;color:var(--muted)}.part b{font:600 18px ui-monospace,monospace;margin-left:auto}.map{width:100%;max-height:245px;margin-top:18px}.note{font-size:14px;color:var(--muted)}.placements{font:11px/1.7 ui-monospace,monospace;color:var(--muted);margin-top:8px}footer{display:flex;gap:12px;align-items:center;padding-top:24px}button,select{font:inherit;color:var(--ink);border:1px solid #b5c9d7;background:#fff;padding:10px 15px;border-radius:5px}button{cursor:pointer}button:last-child{background:var(--ink);color:#fff;margin-left:auto}button:disabled{opacity:.4;cursor:default}select{max-width:55%;font-size:14px}button:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #008cbd;outline-offset:3px}.view{font-size:12px;color:var(--muted);margin:8px 0}noscript{display:block;padding:30px} @media(max-width:760px){header{align-items:flex-start}header nav{gap:12px;flex-wrap:wrap}main{padding-top:20px}.layout{grid-template-columns:1fr;gap:24px}.assembly{max-height:55vh}.aside{display:grid;grid-template-columns:1fr 1fr;gap:16px}.map{margin:0}.placements{grid-column:1/-1}.number{font-size:44px}footer{position:sticky;bottom:0;background:var(--paper);padding:14px 0}.note{grid-column:1/-1}}
</style><header><strong>__TITLE__</strong><nav><a href="../instructions.pdf">PDF</a><a href="../parts.csv">Parts CSV</a><a href="../model.ldr">Model</a></nav></header>
<main><div class="heading"><span class="number" id="number"></span><div><div class="counter" id="counter"></div><h1 id="title"></h1></div></div><div class="layout"><div><img class="assembly" id="assembly" alt=""><p class="view" id="view"></p></div><aside class="aside"><div><h2>Parts to add</h2><div id="parts"></div></div><img class="map" id="map" alt="Top-down placement map"><div class="placements" id="placements"></div><p class="note" id="note"></p></aside></div><footer><button id="prev" aria-label="Previous step">← Back</button><select id="jump" aria-label="Building step"></select><button id="next" aria-label="Next step">Next →</button></footer></main><noscript>Open the PDF above to read the building instructions without JavaScript.</noscript>
<script type="application/json" id="data">__DATA__</script><script>
const data=JSON.parse(document.getElementById('data').textContent);let index=0;const el=id=>document.getElementById(id);
data.steps.forEach((s,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${i+1}. ${s.title}`;el('jump').append(o)});
function show(){const s=data.steps[index];el('number').textContent=String(index+1).padStart(2,'0');el('counter').textContent=`${index+1} / ${data.steps.length}`;el('title').textContent=s.title;el('assembly').src=s.image;el('assembly').alt=`Step ${index+1}: ${s.title}`;el('map').src=s.map;el('note').textContent=s.note;el('view').textContent=s.view.replaceAll('-',' ');el('parts').replaceChildren();s.parts.forEach(p=>{const row=document.createElement('div');row.className='part';const sw=document.createElement('span');sw.className='swatch';sw.style.background=data.colors[p.color_id].hex;const label=document.createElement('span');label.textContent=p.part_name;const small=document.createElement('small');small.textContent=`${p.color_name} · ${p.part_id}`;label.append(small);const q=document.createElement('b');q.textContent=`${p.quantity}×`;row.append(sw,label,q);el('parts').append(row)});el('placements').replaceChildren();s.placements.forEach(p=>{const row=document.createElement('div');row.textContent=`${p.marker}: x${p.x} y${p.y} z${p.z} · ${p.rotation}°`;el('placements').append(row)});el('jump').value=index;el('prev').disabled=index===0;el('next').disabled=index===data.steps.length-1}
el('prev').onclick=()=>{if(index>0){index--;show()}};el('next').onclick=()=>{if(index<data.steps.length-1){index++;show()}};el('jump').onchange=e=>{index=Number(e.target.value);show()};document.addEventListener('keydown',e=>{if(e.target.matches('select,input,textarea'))return;if(e.key==='ArrowRight'){e.preventDefault();el('next').click()}if(e.key==='ArrowLeft'){e.preventDefault();el('prev').click()}});show();
</script></html>'''
    if style=='technical':
        page=page.replace('</style>', '''
body{background:#fff}.layout{grid-template-columns:240px minmax(0,1fr);gap:32px}.layout>div{grid-column:2;grid-row:1}.aside{grid-column:1;grid-row:1}.map,.placements{display:none}.part{display:grid;grid-template-columns:88px 1fr;gap:8px;margin:4px 0 18px}.part .part-icon{width:88px;height:88px;object-fit:contain}.part b{grid-column:2;grid-row:1;margin:0;font-size:20px}.part>span{grid-column:1/-1;font-size:13px}.note{font-size:12px}.assembly{max-height:70vh}footer{background:#fff}
@media(max-width:760px){.layout{display:flex;flex-direction:column;gap:12px}.aside{display:block;order:-1}.aside>div>div{display:flex;flex-wrap:wrap;gap:16px}.part{width:132px;grid-template-columns:80px 1fr}.part .part-icon{width:80px;height:80px}.aside h2{display:none}.assembly{max-height:60vh}.note:empty{display:none}}
</style>''')
        page=page.replace("const sw=document.createElement('span');sw.className='swatch';sw.style.background=data.colors[p.color_id].hex;", "const sw=document.createElement('img');sw.className='part-icon';sw.src=`parts/${p.part_id}-${p.color_id}.png`;sw.alt=`${p.color_name} ${p.part_name}`;")
        page=page.replace("el('view').textContent=s.view.replaceAll('-',' ');", "el('view').textContent=index>0&&s.view!==data.steps[index-1].view?'↻ '+s.view.replaceAll('-',' '):'';")
    (out/'instructions/index.html').write_text(page.replace('__TITLE__',html.escape(model['title'])).replace('__DATA__',payload))

def pdf(model,steps,report,out,style='studio'):
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab
    fonts=Path(reportlab.__file__).parent/'fonts'
    for name,file in [('Body','Vera.ttf'),('Bold','VeraBd.ttf')]:pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    c=canvas.Canvas(str(out/'instructions.pdf'),pagesize=(842,595),invariant=1)
    c.setTitle(model['title']);c.setAuthor(model['author']);ink=HexColor('#19394b');muted=HexColor('#637786');blue=HexColor('#006d9c')
    def text(x,y,t,size=11,font='Body',color=ink):
        c.setFillColor(color);c.setFont(font,size);c.drawString(x,y,t)
    def wrap(t,width,size=11,font='Body'):
        lines=[];line=''
        words=[]
        for word in t.split():
            chunk=''
            for char in word:
                if chunk and pdfmetrics.stringWidth(chunk+char,font,size)>width:
                    words.append(chunk);chunk=char
                else:chunk+=char
            if chunk:words.append(chunk)
        for word in words:
            if pdfmetrics.stringWidth((line+' '+word).strip(),font,size)>width and line:lines.append(line);line=word
            else:line=(line+' '+word).strip()
        return lines+[line] if line else lines
    def footer(page):
        text(34,22,model['title'],9,color=muted);text(755,22,str(page),9,color=muted)
    text(36,545,'BUILDING GUIDE',11,'Bold',blue)
    yy=468
    for line in wrap(model['title'],310,36,'Bold'):text(36,yy,line,36,'Bold');yy-=43
    text(36,yy-20,f'{len(model["parts"])} parts / {len(steps)} steps',13)
    yy-=72
    for line in wrap(model['description'],285,11):text(36,yy,line,11,color=muted);yy-=17
    text(36,108,'Digitally checked · not physically test-built',10,color=muted)
    text(36,87,model['author'],10,color=muted)
    c.drawImage(str(out/'renders/front-right.png'),350,75,455,455,preserveAspectRatio=True,mask='auto');footer(1);c.showPage()
    by={p['id']:p for p in model['parts']}
    if style=='technical':
        for n,s in enumerate(steps,1):
            text(36,535,f'{n:02}',36,'Bold',blue)
            for i,line in enumerate(wrap(s['title'],670,20,'Bold')):text(110,546-i*25,line,20,'Bold')
            c.drawImage(str(out/'instructions'/s['image']),265,48,540,470,preserveAspectRatio=True,anchor='c',mask='auto')
            text(36,479,'PARTS TO ADD',9,'Bold',muted)
            dense=len(s['parts'])>4;pitch=86 if dense else 112;icon_size=64 if dense else 80
            for i,p in enumerate(s['parts']):
                x=36+(i%2)*112;y=(402 if dense else 382)-(i//2)*pitch
                c.drawImage(str(out/f'instructions/parts/{p["part_id"]}-{p["color_id"]}.png'),x,y+10,icon_size,icon_size,mask='auto')
                text(x+81,y+44,f'{p["quantity"]}x',13,'Bold')
                text(x,y,p['part_name'],9,'Bold')
                text(x,y-13,p['part_id'],8,color=muted)
            yy=112
            if n>1 and s['view']!=steps[n-2]['view']:
                text(36,yy,'TURN / '+s['view'].replace('-',' ').upper(),9,'Bold',blue);yy-=20
            if s['note']:
                for line in wrap(s['note'],215,9):text(36,yy,line,9,color=muted);yy-=13
            if n==1:text(36,54,'Blue edges: parts added in this step',8,color=blue)
            footer(n+1);c.showPage()
        inv=inventory(model['parts']);page=len(steps)+2
        for start in range(0,len(inv),12):
            text(36,540,'Parts inventory',26,'Bold')
            text(36,514,'LDraw IDs / color availability not checked',10,color=muted)
            for i,p in enumerate(inv[start:start+12]):
                x=36+(i%3)*258;y=388-(i//3)*112
                c.drawImage(str(out/f'instructions/parts/{p["part_id"]}-{p["color_id"]}.png'),x,y,94,94,mask='auto')
                text(x+108,y+61,f'{p["quantity"]}x',18,'Bold')
                text(x+108,y+42,p['part_name'],10,'Bold')
                text(x+108,y+25,p['color_name'],9,color=muted)
                text(x+108,y+10,p['part_id'],8,color=muted)
            footer(page);page+=1;c.showPage()
        c.save();return
    for n,s in enumerate(steps,1):
        text(34,538,f'{n:02}',34,'Bold',blue)
        title_lines=wrap(s['title'],650,20,'Bold')
        for i,line in enumerate(title_lines):text(106,547-i*25,line,20,'Bold')
        c.drawImage(str(out/'instructions'/s['image']),25,80,490,440,preserveAspectRatio=True,anchor='c',mask='auto')
        text(555,496,'PARTS TO ADD',10,'Bold',blue);yy=473
        for p in s['parts']:
            c.setFillColor(HexColor(COLORS[p['color_id']]['hex']));c.setStrokeColor(HexColor('#c5cdd2'));c.rect(555,yy-3,13,13,fill=1,stroke=1)
            text(578,yy,f'{p["quantity"]} x {p["part_name"]}',10,'Bold');text(578,yy-13,f'{p["color_name"]} / {p["part_id"]}',8,color=muted);yy-=30
        # Vector top view shares the same coordinates as the SVG export.
        x0,y0,_,x1,y1,_=bbox(model);unit=min(210/(x1-x0),min(155,yy-145)/(y1-y0));ox=571;oy=125
        for x in range(x0,x1):text(ox+(x-x0+.5)*unit-2,oy+(y1-y0)*unit+8,str(x),7,color=muted)
        for y in range(y0,y1):text(ox-16,oy+(y-y0+.5)*unit-2,str(y),7,color=muted)
        c.setStrokeColor(HexColor('#dce3e8'));c.setLineWidth(.5)
        for x in range(x1-x0+1):c.line(ox+x*unit,oy,ox+x*unit,oy+(y1-y0)*unit)
        for y in range(y1-y0+1):c.line(ox,oy+y*unit,ox+(x1-x0)*unit,oy+y*unit)
        for p in s['placements']:
            source=by[p['instance']];w,d,_=shape(source);xx=ox+(p['x']-x0)*unit;yyy=oy+(p['y']-y0)*unit
            c.setFillColor(HexColor(COLORS[p['color_id']]['hex']));c.setStrokeColor(ink);c.rect(xx+1,yyy+1,w*unit-2,d*unit-2,fill=1,stroke=1)
            cx=xx+w*unit/2;cy=yyy+d*unit/2;c.setFillColor(HexColor('#ffffff'));c.circle(cx,cy,6,fill=1,stroke=0);text(cx-2,cy-2,str(p['marker']),6,'Bold')
        text(ox+60,oy-14,'FRONT',8,color=muted)
        # Compact explicit placement references are helpful for exact reconstruction.
        yy=96
        for line in wrap('  '.join(f'{p["marker"]}: ({p["x"]},{p["y"]},{p["z"]}) {p["rotation"]}°' for p in s['placements']),245,7):text(555,yy,line,7,color=muted);yy-=10
        if s['note']:
            for i,line in enumerate(wrap(s['note'],470,9)):text(36,65-i*12,line,9,color=muted)
        text(36,78,s['view'].replace('-',' '),8,color=muted)
        footer(n+1);c.showPage()
    inv=inventory(model['parts']);page=len(steps)+2
    for start in range(0,len(inv),17):
        text(36,540,'Parts inventory',26,'Bold');text(36,514,'LDraw IDs · color availability not checked',10,color=muted)
        yy=480
        for p in inv[start:start+17]:
            c.setFillColor(HexColor(COLORS[p['color_id']]['hex']));c.rect(36,yy-3,13,13,fill=1,stroke=0)
            text(65,yy,p['part_name'],11);text(270,yy,p['part_id'],11);text(390,yy,p['color_name'],11);text(700,yy,str(p['quantity']),12,'Bold');yy-=24
        footer(page);page+=1;c.showPage()
    c.save()
