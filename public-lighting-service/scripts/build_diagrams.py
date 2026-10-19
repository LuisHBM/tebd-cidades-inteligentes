"""Desenha os DERs com as colunas conferidas no PostgreSQL."""
import json, pathlib, subprocess, tempfile
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
PROJECT_DIR=pathlib.Path(__file__).resolve().parents[1]
SCHEMA_COLUMNS=json.loads((PROJECT_DIR/'docs/validation/postgresql_columns.json').read_text())
TYPE={'smallint':'smallint','integer':'integer','bigint':'bigint','text':'text','date':'date'}
PK={'rpa':'rpa_id','bairro':'bairro_id','grupo_servico':'grupo_id','servico':'servico_id','situacao':'situacao_id','solicitacao':'solicitacao_id','dim_data':'data_sk','dim_bairro':'bairro_sk','dim_servico':'servico_sk','dim_situacao':'situacao_sk','fato_solicitacao':'solicitacao_id'}
FK={('bairro','rpa_id'),('servico','grupo_id'),('solicitacao','bairro_id'),('solicitacao','servico_id'),('solicitacao','situacao_id'),('fato_solicitacao','data_demanda_sk'),('fato_solicitacao','data_situacao_sk'),('fato_solicitacao','bairro_sk'),('fato_solicitacao','servico_sk'),('fato_solicitacao','situacao_sk')}
REL={
 'oltp':[('rpa','bairro','contem'),('bairro','solicitacao','localiza'),('grupo_servico','servico','agrupa'),('servico','solicitacao','tipifica'),('situacao','solicitacao','descreve')],
 'olap':[('dim_data','fato_solicitacao','data_demanda'),('dim_data','fato_solicitacao','data_ultima_situacao'),('dim_bairro','fato_solicitacao','localiza'),('dim_servico','fato_solicitacao','tipifica'),('dim_situacao','fato_solicitacao','descreve')]
}
REGULAR_FONT_PATH='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
pdfmetrics.registerFont(TTFont('DER',REGULAR_FONT_PATH))
class Drawing:
 def __init__(self,w,h,pdf):
  self.w=w;self.h=h;self.c=canvas.Canvas(str(pdf),pagesize=(w,h));self.svg=[]
  self.rect(0,0,w,h,fill='white',stroke='white')
 def line(self,points,dashed=False):
  c=self.c;c.setStrokeColorRGB(0,0,0);c.setLineWidth(2)
  c.setDash([8,6] if dashed else [])
  p=c.beginPath();p.moveTo(points[0][0],self.h-points[0][1])
  for x,y in points[1:]:p.lineTo(x,self.h-y)
  c.drawPath(p);c.setDash([])
  pts=' '.join(f'{x},{y}' for x,y in points)
  dash=' stroke-dasharray="8 6"' if dashed else ''
  self.svg.append(f'<polyline points="{pts}" fill="none" stroke="black" stroke-width="2"{dash}/>')
 def rect(self,x,y,w,h,fill='white',stroke='black'):
  c=self.c;c.setFillColorRGB(1,1,1);c.setStrokeColorRGB(1,1,1) if stroke=='white' else c.setStrokeColorRGB(0,0,0)
  c.setLineWidth(2);c.rect(x,self.h-y-h,w,h,fill=1,stroke=1)
  self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
 def circle(self,x,y,r):
  c=self.c;c.setFillColorRGB(1,1,1);c.setStrokeColorRGB(0,0,0);c.setLineWidth(2);c.circle(x,self.h-y,r,fill=1,stroke=1)
  self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="black" stroke-width="2"/>')
 def text(self,x,y,t,size=30,anchor='start'):
  font='DER';c=self.c;c.setFillColorRGB(0,0,0);c.setFont(font,size)
  width=pdfmetrics.stringWidth(t,font,size)
  dx=width if anchor=='end' else width/2 if anchor=='middle' else 0
  c.drawString(x-dx,self.h-y,t)
  self.svg.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans" font-size="{size}" font-weight="400" text-anchor="{anchor}">{escape(t)}</text>')
 def marker(self,p,nextp,kind):
  x,y=p;dx,dy=nextp[0]-x,nextp[1]-y
  length=(dx*dx+dy*dy)**.5;ux,uy=dx/length,dy/length;vx,vy=-uy,ux
  def pt(a,b=0):return x+a*ux+b*vx,y+a*uy+b*vy
  if kind=='one':
   for a in [12,23]:self.line([pt(a,-11),pt(a,11)])
  else:
   # O círculo e a bifurcação indicam zero ou muitos registros filhos.
   for b in [-12,0,12]:self.line([pt(19),pt(0,b)])
   self.circle(*pt(34),7)
 def relation(self,points,label=None):
  self.line(points,dashed=True)
  self.marker(points[0],points[1],'one')
  self.marker(points[-1],points[-2],'many')
  if label:self.text(*label,size=23)
 def entity(self,schema,name,x,y,w):
  cols=[c for c in SCHEMA_COLUMNS if c['table_schema']==schema and c['table_name']==name]
  h=50+42*len(cols)
  self.rect(x,y,w,h);self.line([(x,y+50),(x+w,y+50)])
  self.text(x+16,y+35,name,size=34)
  for i,c in enumerate(cols):
   col=c['column_name'];ty=TYPE[c['data_type']];baseline=y+50+42*i+29
   key='PK' if col==PK[name] else 'FK' if (name,col) in FK else ''
   self.text(x+12,baseline,key,size=22)
   self.text(x+58,baseline,col,size=29)
   self.text(x+w-12,baseline,ty,size=23,anchor='end')
   namewidth=pdfmetrics.stringWidth(col,'DER',29)
   typewidth=pdfmetrics.stringWidth(ty,'DER',23)
   assert 58+namewidth+20+typewidth<=w-12,(name,col,'texto sobreposto')
 def save(self,p):
  self.c.showPage();self.c.save()
  p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="1600" height="{self.h}">\n'+ '\n'.join(self.svg)+'\n</svg>')
def build(kind):
 folder=PROJECT_DIR/'docs/diagrams';folder.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='lighting_der_') as tmp:
  pdf=pathlib.Path(tmp)/'model.pdf'
  if kind=='oltp':
   d=Drawing(1600,850,pdf)
   d.relation([(370,111),(430,111),(430,153),(500,153)],(395,90,'contém'))
   d.relation([(370,431),(430,431),(430,473),(500,473)],(395,410,'agrupa'))
   d.relation([(900,111),(970,111),(970,313),(1040,313)],(920,90,'localiza'))
   d.relation([(900,431),(940,431),(940,355),(1040,355)],(947,335,'tipifica'))
   d.relation([(900,751),(1005,751),(1005,397),(1040,397)],(909,729,'descreve'))
   nodes=[('rpa',20,40,350),('bairro',500,40,400),('grupo_servico',20,360,350),('servico',500,360,400),('situacao',500,680,400),('solicitacao',1040,200,540)]
  else:
   d=Drawing(1600,1160,pdf)
   d.relation([(650,322),(650,460)],(672,397,'abertura'))
   d.relation([(950,322),(950,460)],(972,417,'última situação'))
   d.relation([(370,531),(430,531),(430,657),(490,657)],(380,510,'localiza'))
   d.relation([(1190,531),(1150,531),(1150,699),(1110,699)],(1115,510,'tipifica'))
   d.relation([(850,1010),(850,846)],(875,942,'descreve'))
   nodes=[('dim_data',550,20,500),('dim_bairro',20,460,350),('dim_servico',1190,460,390),('dim_situacao',640,1010,420),('fato_solicitacao',490,460,620)]
  for name,x,y,w in nodes:d.entity(kind,name,x,y,w)
  d.save(folder/f'{kind}_model.svg')
  subprocess.run(['pdftoppm','-singlefile','-scale-to-x','3200','-scale-to-y','-1','-png',str(pdf),str(folder/f'{kind}_model')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 lines=['erDiagram','    direction LR']
 for name,x,y,w in nodes:
  lines += [f'    {name} {{']
  for c in SCHEMA_COLUMNS:
   if c['table_schema']!=kind or c['table_name']!=name:continue
   col=c['column_name'];key=' PK' if col==PK[name] else ' FK' if (name,col) in FK else ''
   lines += [f"        {TYPE[c['data_type']]} {col}{key}"]
  lines += ['    }']
 for parent,child,label in REL[kind]:lines += [f'    {parent} ||..o{{ {child} : {label}']
 (folder/f'{kind}_model.mmd').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':
 for kind in ['oltp','olap']:build(kind)
