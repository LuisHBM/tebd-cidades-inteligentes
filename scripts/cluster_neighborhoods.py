"""Agrupa os bairros com k-means a partir do perfil das solicitações de iluminação pública.

Lê os CSVs de data/processed, calcula sete indicadores por bairro no período inteiro,
padroniza-os (z-score), compara k de 2 a 8 e grava tabela e gráficos em docs/analysis.
"""
import pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1]
DATA, OUT = PROJECT_DIR/'data/processed', PROJECT_DIR/'docs/analysis'
K, K_RANGE, SEED = 4, range(2, 9), 42  # K fixado após comparar silhueta e cotovelo (ver kmeans.md)
ATENDIDA, CIRCUIT, STRUCTURE = 1, [51], [61, 63, 65, 289]
LABELS = {'volume': 'Volume (log)', 'mediana_dias': 'Mediana de dias', 'p90_dias': 'P90 de dias',
          'pct_nao_atendida': '% não atendida', 'pct_reincidencia': '% reincidência',
          'pct_circuito': '% acender circuito', 'pct_estrutura': '% estrutura'}
COLORS, MARKERS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100'], ['o', 's', '^', 'D']
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#e1e0d9'

# Indicadores por bairro
req = pd.read_csv(DATA/'requests.csv', parse_dates=['data_demanda', 'data_ultima_situacao'])
neighborhoods = pd.read_csv(DATA/'neighborhoods.csv').set_index('bairro_id')
req['dias'] = (req.data_ultima_situacao - req.data_demanda).dt.days
req['rua'] = req.logradouro.str.upper().str.split().str.join(' ')  # logradouro é texto livre
req['reincidente'] = req.groupby(['bairro_id', 'rua']).solicitacao_id.transform('size') >= 2
req['nao_atendida'] = req.situacao_id != ATENDIDA
req['circuito'] = req.servico_id.isin(CIRCUIT)
req['estrutura'] = req.servico_id.isin(STRUCTURE)
served = req[~req.nao_atendida].groupby('bairro_id').dias  # tempo só existe para ATENDIDA
by = req.groupby('bairro_id')
features = pd.DataFrame({
    'volume': by.size(), 'mediana_dias': served.median(), 'p90_dias': served.quantile(0.9),
    'pct_nao_atendida': by.nao_atendida.mean(), 'pct_reincidencia': by.reincidente.mean(),
    'pct_circuito': by.circuito.mean(), 'pct_estrutura': by.estrutura.mean()})
X = StandardScaler().fit_transform(features.assign(volume=np.log1p(features.volume)))

# Escolha de k: inércia (cotovelo) e silhueta
selection = pd.DataFrame([(k, m.inertia_, silhouette_score(X, m.labels_)) for k in K_RANGE
                          for m in [KMeans(k, n_init=20, random_state=SEED).fit(X)]],
                         columns=['k', 'inercia', 'silhueta'])
print(selection.round(3).to_string(index=False))

# Modelo final; clusters renumerados de 1 a K pelo volume médio decrescente
model = KMeans(K, n_init=20, random_state=SEED).fit(X)
ari = [adjusted_rand_score(model.labels_, KMeans(K, n_init=20, random_state=s).fit_predict(X)) for s in range(10)]
print(f'Estabilidade (ARI com sementes 0-9): mínimo {min(ari):.3f}')
order = np.argsort(-model.cluster_centers_[:, 0])
rank = {old: new for new, old in enumerate(order, 1)}
features['cluster'] = [rank[c] for c in model.labels_]
centers = pd.DataFrame(model.cluster_centers_[order], columns=LABELS.values(), index=range(1, K + 1))
result = neighborhoods.join(features).reset_index()[['bairro_id', 'nome', 'rpa_id', *features.columns]]
OUT.mkdir(parents=True, exist_ok=True)
result.round(4).to_csv(OUT/'kmeans_neighborhoods.csv', index=False)

summary = result.groupby('cluster').agg(n_bairros=('bairro_id', 'size'), **{
    c: (c, 'mean') for c in LABELS}, rpas=('rpa_id', lambda s: dict(s.value_counts().sort_index())))
with pd.option_context('display.width', 200, 'display.max_columns', None):
    print(summary.round(3))
    print(centers.round(2))
for c, g in result.sort_values('volume', ascending=False).groupby('cluster'):
    print(c, ', '.join(g.nome.head(6)))

# Gráfico da escolha de k (dois painéis, cada um com seu eixo)
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#c3c2b7', 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.spines.top': False,
                     'axes.spines.right': False})
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for ax, col, title in zip(axes, ['inercia', 'silhueta'], ['Inércia (cotovelo)', 'Silhueta média']):
    ax.plot(selection.k, selection[col], color=COLORS[0], lw=2, marker='o', ms=6)
    best = selection[selection.k == K].iloc[0]
    ax.plot(K, best[col], 'o', ms=11, mfc='none', mec=INK, mew=1.5)
    ax.annotate(f'k = {K}\n{best[col]:.3f}' if col == 'silhueta' else f'k = {K}', (K, best[col]),
                textcoords='offset points', xytext=(10, -26), color=INK)
    ax.set(title=title, xlabel='Número de clusters (k)', xticks=list(K_RANGE))
    ax.title.set_color(INK)
    ax.grid(axis='y', color=GRID, lw=0.8)
fig.suptitle('Escolha de k para os 93 bairros', color=INK, fontsize=12)
fig.tight_layout()
fig.savefig(OUT/'kmeans_selection.png', dpi=150)

# Perfil dos clusters: centróides em z-score e projeção PCA
names = [f'Cluster {c}\n({n} bairros)' for c, n in summary.n_bairros.items()]
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={'width_ratios': [1.35, 1]})
cmap = LinearSegmentedColormap.from_list('div', ['#2a78d6', '#f0efec', '#e34948'])
lim = np.ceil(np.abs(centers.values).max())
im = ax1.imshow(centers.values, cmap=cmap, vmin=-lim, vmax=lim, aspect='auto')
for (i, j), v in np.ndenumerate(centers.values):
    ax1.text(j, i, f'{v:+.2f}', ha='center', va='center', color=INK, fontsize=9)
ax1.set_xticks(range(len(LABELS)), LABELS.values(), rotation=30, ha='right')
ax1.set_yticks(range(K), names)
ax1.tick_params(length=0)
for side in ax1.spines.values():
    side.set_visible(False)
ax1.set_title('Centróides (z-score: 0 = média dos bairros)', color=INK)
fig.colorbar(im, ax=ax1, shrink=0.8, label='abaixo da média  ←  z  →  acima da média')

pca = PCA(2, random_state=SEED).fit(X)
P = pca.transform(X)
for c in range(1, K + 1):
    mask = features.cluster.values == c
    ax2.scatter(P[mask, 0], P[mask, 1], s=40, c=COLORS[c - 1], marker=MARKERS[c - 1],
                edgecolors='white', linewidths=0.8, label=f'Cluster {c}')
ev = pca.explained_variance_ratio_ * 100
ax2.set(xlabel=f'Componente 1 ({ev[0]:.0f}% da variância)', ylabel=f'Componente 2 ({ev[1]:.0f}%)')
ax2.set_title('Bairros projetados em 2D (PCA)', color=INK)
ax2.grid(color=GRID, lw=0.8)
ax2.legend(frameon=False, loc='best')
fig.tight_layout()
fig.savefig(OUT/'kmeans_profiles.png', dpi=150)
print(f'PCA: {ev.round(1)}; arquivos gravados em {OUT.relative_to(PROJECT_DIR)}')
