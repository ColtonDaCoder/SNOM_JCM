"""Schematic of the three uniform-stack setups (layer heights not to scale): figures/stack_setups.png"""
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
COL = {'Air': '#ffffff', 'Si$_3$N$_4$': '#9ecae1', 'OTS': '#fdae6b', 'Si': '#969696'}
# top to bottom: (material, thickness label, drawn height)
SETUPS = [
    ('1)  Air / 5 nm Si$_3$N$_4$ / 1.5 nm OTS / Air',
     [('Si$_3$N$_4$', '5 nm', 1.0), ('OTS', '1.5 nm', 0.45)], 'Air'),
    ('2)  Air / 1.5 nm OTS / 5 nm Si$_3$N$_4$ / Air',
     [('OTS', '1.5 nm', 0.45), ('Si$_3$N$_4$', '5 nm', 1.0)], 'Air'),
    ('3)  Air / 1.5 nm OTS / 20 nm Si$_3$N$_4$ / Si',
     [('OTS', '1.5 nm', 0.45), ('Si$_3$N$_4$', '20 nm', 2.2)], 'Si'),
]
W, GAP, YB = 10.0, 0.8, -4.6     # YB: common bottom of the drawing

with plt.rc_context({'font.size': 15}):
    fig, axs = plt.subplots(1, 3, figsize=(17, 6.2))
    for ax, (title, layers, sub) in zip(axs, SETUPS):
        y = 0.0
        for mat, lab, h in layers:
            ax.add_patch(Rectangle((-W/2, y - h), W, h, fc=COL[mat], ec='k', lw=1.2))
            ax.text(W/2 - 0.3, y - h/2, f'{mat}  {lab}', ha='right', va='center', fontsize=14)
            y -= h
        ax.add_patch(Rectangle((-W/2, YB), W, y - YB, fc=COL[sub], ec='k', lw=1.2))
        ax.text(W/2 - 0.3, (y + YB)/2, f'{sub} (semi-infinite)', ha='right', va='center', fontsize=14)
        ax.text(W/2 - 0.3, 3.6, 'Air', ha='right', va='center', fontsize=14)
        # tip: rounded cone, apex a gap above the top surface
        t = np.linspace(-np.pi/2 - 1.05, -np.pi/2 + 1.05, 40)
        r = 0.6
        arc = np.c_[r*np.cos(t), GAP + r + r*np.sin(t)]
        tip = np.r_[[[-2.3, 4.6]], arc, [[2.3, 4.6]]]
        ax.add_patch(Polygon(tip, fc='#bdbdbd', ec='k', lw=1.2))
        ax.text(0, 4.0, 'Pt tip', ha='center', va='center', fontsize=14)
        ax.annotate('', xy=(-1.2, 0), xytext=(-1.2, GAP), arrowprops=dict(arrowstyle='<->', lw=1.2))
        ax.text(-1.4, GAP/2, 'gap 1–101 nm', ha='right', va='center', fontsize=12)
        # incident beam, 60 deg from the normal
        ax.annotate('', xy=(-0.25, 0.9), xytext=(-0.25 - 3.4*np.sin(np.pi/3), 0.9 + 3.4*np.cos(np.pi/3)),
                    arrowprops=dict(arrowstyle='->', lw=2, color='C3'))
        ax.text(-4.6, 2.9, '6.1 µm, p\n60°', color='C3', fontsize=12, va='center')
        ax.set_xlim(-W/2, W/2)
        ax.set_ylim(YB, 4.6)
        ax.set_title(title, fontsize=15)
        ax.axis('off')
    fig.text(0.5, 0.02, 'Layer thicknesses not to scale.  Layers are uniform in x; the tip taps above the top surface.',
             ha='center', fontsize=13)
    out = os.path.join(HERE, 'figures', 'stack_setups.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    print('wrote', out)
