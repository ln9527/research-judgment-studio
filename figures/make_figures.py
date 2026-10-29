"""Build submission figures (Nature/Science style). Data: Gong, Li & Zhou 2026 (arXiv:2603.16659v3, SI Tables ST1, ST13; main text Sec. 2)
and Li 2026c manuscript v3 (Table 2, SI Table 2, fig2 source data)."""
import matplotlib as mpl, matplotlib.pyplot as plt, numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
SHOTS = os.path.join(HERE, '..', 'platform', 'screenshots')
os.makedirs(OUT, exist_ok=True)
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','Liberation Sans','Nimbus Sans','DejaVu Sans'],
 'font.size':7,'axes.titlesize':7,'axes.labelsize':7,'xtick.labelsize':6.5,'ytick.labelsize':6.5,'legend.fontsize':6.5,
 'axes.linewidth':0.5,'xtick.major.width':0.5,'ytick.major.width':0.5,'xtick.major.size':2.5,'ytick.major.size':2.5,
 'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'ps.fonttype':42,'savefig.dpi':600,'lines.linewidth':0.8})
C = {'q30':'#0072B2','q4':'#009E73','nano':'#E69F00','grey':'#8C8C8C','red':'#D55E00','dark':'#222222','purple':'#CC79A7','sky':'#56B4E9'}
def letter(ax,s,x=-0.12,y=1.04): ax.text(x,y,s,transform=ax.transAxes,fontsize=9,fontweight='bold',va='bottom',ha='left')
def save(fig,name):
    for ext in ('pdf','png'): fig.savefig(f'{OUT}/{name}.{ext}',bbox_inches='tight',pad_inches=0.02)
    plt.close(fig)

# ---------- Figure 1: the gatekeeper ----------
fields=['Psychology','Economics','Communication','Sociology','Management','Political science','Business & finance','Public admin.']
# (SFT, base) per architecture, ST13a-c
q30={'Psychology':(85.5,31.5),'Economics':(69.5,25.5),'Communication':(67.5,31.5),'Sociology':(65.5,28.0),'Management':(58.3,22.5),'Political science':(58.5,24.5),'Business & finance':(53.5,28.5),'Public admin.':(55.0,23.5)}
q4 ={'Psychology':(76.0,25.0),'Economics':(64.0,25.0),'Communication':(61.0,25.0),'Sociology':(51.0,24.5),'Management':(59.2,26.7),'Political science':(50.5,25.0),'Business & finance':(53.5,25.5),'Public admin.':(51.0,25.0)}
nano={'Psychology':(81.5,30.0),'Economics':(68.5,25.0),'Communication':(60.5,24.0),'Sociology':(54.0,26.5),'Management':(57.5,25.0),'Political science':(54.0,26.0),'Business & finance':(55.5,26.0),'Public admin.':(53.5,24.0)}
ctrl={'Psychology':33.5,'Economics':44.5,'Communication':31.5,'Sociology':31.9,'Management':38.8,'Political science':35.0,'Business & finance':33.5,'Public admin.':30.0}  # ST1 best non-SFT control
fig=plt.figure(figsize=(7.2,3.0))
gs=fig.add_gridspec(1,2,width_ratios=[1.35,1],wspace=0.55)
ax=fig.add_subplot(gs[0])
y=np.arange(len(fields))[::-1]
off={'q30':0.22,'nano':0.0,'q4':-0.22}
for key,d,lab in [('q30',q30,'Qwen3-30B-A3B'),('nano',nano,'GPT-4.1-nano'),('q4',q4,'Qwen3-4B')]:
    for i,f in enumerate(fields):
        s,b=d[f]; yy=y[i]+off[key]
        ax.plot([b,s],[yy,yy],color=C[key],lw=0.7,alpha=0.8)
        ax.scatter([b],[yy],s=9,facecolor='white',edgecolor=C[key],lw=0.6,zorder=3)
        ax.scatter([s],[yy],s=9,color=C[key],zorder=3,label=lab if i==0 else None)
ax.scatter([ctrl[f] for f in fields],y,marker='D',s=8,color=C['red'],zorder=4,label='Best non-fine-tuned control')
ax.axvline(25,ls='--',lw=0.5,color=C['grey']); ax.text(25.5,7.55,'Chance',fontsize=6,color=C['grey'])
ax.set_yticks(y); ax.set_yticklabels(fields); ax.set_xlim(18,92); ax.set_ylim(-0.6,7.9)
ax.set_xlabel('Four-tier accuracy on held-out benchmark (%)')
ax.legend(loc='lower center',bbox_to_anchor=(0.45,1.0),ncol=2,frameon=False,handletextpad=0.3,columnspacing=1.0,borderaxespad=0.1)
letter(ax,'a',x=-0.36,y=1.13)
ax2=fig.add_subplot(gs[1])
rows=[('Chance',25.0,C['grey']),('Frontier mean (11 models)',31.1,C['red']),('Best frontier (Gemini 3.1 Pro)',38.8,C['red']),
      ('Junior individual mean (n = 174)',31.7,C['sky']),('Junior majority vote',40.8,C['sky']),('Expert individual mean (n = 48)',36.2,C['purple']),
      ('Expert majority vote',41.6,C['purple']),('Fine-tuned GPT-4.1-nano',57.5,C['nano']),('Fine-tuned Qwen3-30B-A3B',58.3,C['q30']),('Fine-tuned Qwen3-4B',59.2,C['q4'])]
yy=np.arange(len(rows))[::-1]
ax2.barh(yy,[r[1] for r in rows],color=[r[2] for r in rows],height=0.62,edgecolor='none')
for yi,r in zip(yy,rows): ax2.text(r[1]+0.8,yi,f'{r[1]:.1f}',va='center',fontsize=6)
ax2.set_yticks(yy); ax2.set_yticklabels([r[0] for r in rows]); ax2.set_xlim(0,70)
ax2.set_xlabel('Accuracy on management benchmark (%)')
ax2.text(1.0,-0.20,'Majority votes exclude ties (experts 89, juniors 103 of 120 items)',transform=ax2.transAxes,ha='right',va='top',fontsize=5.6,color=C['grey'])
letter(ax2,'b',x=-0.78,y=1.13)
save(fig,'Fig1_gatekeeper')

# ---------- Figure 2: auto-research loop ----------
fig=plt.figure(figsize=(7.2,3.1))
gs=fig.add_gridspec(1,2,width_ratios=[1,1.1],wspace=0.32)
ax=fig.add_subplot(gs[0]); ax.set_xlim(0,10); ax.set_ylim(0,10); ax.axis('off')
def box(ax,x,y,w,h,t,fc='#F2F2F2',ec='#444444',fs=6.3,bold=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.02,rounding_size=0.25',fc=fc,ec=ec,lw=0.6))
    ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=fs,fontweight='bold' if bold else 'normal',linespacing=1.15)
def arr(ax,a,b,rad=0.0):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=6,lw=0.6,color='#444444',connectionstyle=f'arc3,rad={rad}'))
box(ax,0.0,8.0,10.0,1.6,'Investigator: research brief, 15 written\ndirectives, feasibility threshold set in advance',fc='#E8F1F8',fs=5.8)
box(ax,0.0,5.2,3.2,1.9,'Propose\nchange one\nelement',fs=5.8)
box(ax,3.4,5.2,3.2,1.9,'Generate\n50 pitches per\ncondition',fs=5.8)
box(ax,6.8,5.2,3.2,1.9,'Evaluate\nquality, novelty,\nfeasibility',fs=5.8)
box(ax,3.4,2.3,3.2,1.9,'Keep or discard\n(Pareto rule,\nlogged reason)',fs=5.8)
box(ax,0.0,0.1,10.0,1.5,'Validation: 1,200 blinded journal pitches\nand an independent pairwise judge',fc='#FBEFE6',fs=5.8)
arr(ax,(3.2,6.15),(3.4,6.15)); arr(ax,(6.6,6.15),(6.8,6.15)); arr(ax,(8.4,5.2),(6.6,3.6),rad=-0.2)
arr(ax,(3.5,3.25),(1.7,5.2),rad=-0.2); arr(ax,(5.0,8.0),(5.0,7.1)); arr(ax,(5.0,2.3),(5.0,1.6))
ax.text(0.0,3.9,'Agent\n(Claude Code)\nexecutes',fontsize=5.5,color=C['grey'],va='top')
ax.text(8.0,3.9,'Generators:\nGLM-5, GPT-5.4,\nothers',fontsize=5.5,color=C['grey'],va='top')
letter(ax,'a',x=0.0,y=1.0)
ax2=fig.add_subplot(gs[1])
base=[('M0 naive',2.411,0.300),('M1 gap-spotting',2.172,0.324),('M2 problematization',3.269,0.308),('M3 analogical import',3.662,0.355),
      ('M4 phenomenon-based',3.193,0.357),('M5 theory integration',3.009,0.312),('M6 disciplined imagination',3.379,0.318)]
for n,e,k in base:
    ax2.scatter(k,e,s=12,color=C['grey'],zorder=3)
    dx,dy,ha=(0.002,0.03,'left')
    if n.startswith('M1'): dy=-0.09
    if n.startswith('M4'): dx,dy,ha=-0.003,-0.02,'right'
    if n.startswith('M3'): dx,dy,ha=-0.002,0.045,'right'
    if n.startswith('M6'): dy=0.03
    ax2.text(k+dx,e+dy,n.split(' ')[0],fontsize=6,color=C['grey'],ha=ha)
pts=[('AR-01 winner (M3v06)',0.394,3.813,C['q30'],'o','left',0.002,-0.11),
     ('AR-02 headline\n(GPT-5.4, stacked prompt;\nfeasibility 2.44, inadmissible)',0.411,3.919,C['red'],'X','right',-0.003,0.03),
     ('AR-03 M6v05\n(feasibility 3.38)',0.379,3.390,C['q4'],'s','left',0.003,0.03),
     ('AR-03 M6v04\n(feasibility 3.38)',0.341,3.472,C['q4'],'s','right',-0.003,0.03)]
for n,k,e,c,m,ha,dx,dy in pts:
    ax2.scatter(k,e,s=20,color=c,marker=m,zorder=4); ax2.text(k+dx,e+dy,n,fontsize=5.8,color=c,ha=ha,va='bottom' if dy>0 else 'top',linespacing=1.1)
ax2.scatter(0.357,3.291,s=22,marker='D',facecolor='white',edgecolor=C['dark'],lw=0.8,zorder=4)
ax2.text(0.3585,3.24,'Exceptional-tier journals\n(AMJ, ASQ, OS; n = 300)',fontsize=5.8,va='top')
ax2.scatter(0.343,2.632,s=22,marker='D',facecolor='white',edgecolor=C['grey'],lw=0.8,zorder=4)
ax2.text(0.3445,2.60,'All 12 journals (n = 1,200)',fontsize=5.8,va='top',color=C['grey'])
ax2.axhline(3.291,lw=0.4,ls=':',color=C['dark']); ax2.axvline(0.357,lw=0.4,ls=':',color=C['dark'])
ax2.set_xlim(0.29,0.425); ax2.set_ylim(2.0,4.1)
ax2.set_xlabel('Novelty (mean cosine distance to 5 nearest pitches)'); ax2.set_ylabel('Quality (expected tier value, 1 to 4)')
letter(ax2,'b',x=-0.16)
save(fig,'Fig2_auto_research')

# ---------- Figure 3: platform screenshots ----------
shots=[('03_new_evaluation_form','New evaluation: idea reshaped into a pitch'),('04_evaluation_result_detail','Result: tier, probabilities, model agreement'),
       ('05_idea_lab_board','Idea Lab: rate AI-generated ideas'),('07_research_pulse','Research Pulse: literature monitoring')]
fig,axs=plt.subplots(2,2,figsize=(7.2,4.7)); 
for a,(f,t),l in zip(axs.flat,shots,'abcd'):
    a.imshow(Image.open(os.path.join(SHOTS,f'{f}.png'))); a.set_xticks([]); a.set_yticks([])
    for s in a.spines.values(): s.set_visible(True); s.set_linewidth(0.4); s.set_color('#999999')
    a.set_title(t,fontsize=7,loc='left',pad=3); a.text(-0.03,1.02,l,transform=a.transAxes,fontsize=9,fontweight='bold',va='bottom',ha='right')
plt.subplots_adjust(wspace=0.08,hspace=0.18)
save(fig,'Fig3_platform')

# ---------- Figure 4: proposed training studio ----------
fig,ax=plt.subplots(figsize=(7.2,2.6)); ax.set_xlim(0,20); ax.set_ylim(0,10); ax.axis('off')
steps=[('1  Frame','Student states\na phenomenon and\nwrites directives'),('2  Generate','Loop drafts\ncandidates across\nseven theorizing\nlogics'),
       ('3  Commit','Student rates\neach candidate\nbefore seeing\nmodel scores'),('4  Reveal','Tier, confidence,\nnovelty, and\nfeasibility gate\nare shown'),
       ('5  Decide','Keep, revise, or\ndiscard, with a\nwritten reason'),('6  Review','Mentor reviews\nthe judgment log;\nstudent revises\ndirectives')]
w=3.0; gap=0.28
for i,(h,t) in enumerate(steps):
    x=0.2+i*(w+gap)
    box(ax,x,4.6,w,4.0,'',fc='#F2F2F2')
    ax.text(x+w/2,7.85,h,ha='center',va='center',fontsize=7,fontweight='bold')
    ax.text(x+w/2,6.0,t,ha='center',va='center',fontsize=5.4,linespacing=1.2)
    if i<5: arr(ax,(x+w,6.6),(x+w+gap,6.6))
xe=0.2+5*(w+gap)+w/2; xs=0.2+w/2
ax.plot([xe,xe,xs],[4.6,3.4,3.4],color='#444444',lw=0.6)
arr(ax,(xs,3.4),(xs,4.6))
ax.text(10,2.75,'Next round with revised directives',fontsize=6,ha='center',color=C['grey'])
box(ax,0.2,0.1,6.3,1.5,'Taste Arena practice: judge pitches with\narchived expert and institutional outcomes',fc='#E8F1F8',fs=6)
box(ax,6.85,0.1,6.3,1.5,'Exploration lane: unusual ideas kept for\nmentor review (evaluator-free rule)',fc='#FBEFE6',fs=6)
box(ax,13.5,0.1,6.3,1.5,'Replayable record: every prompt, score,\ndecision, and reason is logged',fc='#EAF5EF',fs=6)
save(fig,'Fig4_training_studio')
print('done')
