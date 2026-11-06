"""Análise de sobrevivência neural: quando a rua terá a próxima solicitação.

Modelo de risco discreto (logistic hazard). Para cada rua e mês de corte, a rede
estima o risco de nova solicitação em cada intervalo de dias após o corte.
O fim dos dados disponíveis em cada etapa é tratado como censura.
Compara com a regra simples e os classificadores de predict_street_recurrence.py.
Depois agrupa as curvas com k-means em tipos de rua (crônica, recorrente, esporádica)
e gera o plano de inspeção de setembro, cruzado com os perfis de bairro do k-means.
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.cluster import KMeans
from sklearn.metrics import roc_auc_score, silhouette_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import predict_street_recurrence as base  # noqa: E402

OUT_DIR = base.OUT_DIR
EDGES = np.array([0, 7, 14, 21, 31, 45, 62])  # intervalos em dias após o corte
K = len(EDGES) - 1
HORIZONS = {7: 1, 14: 2, 31: 4}  # dias -> nº de intervalos acumulados
SEEDS = [0, 1, 2]
STREET_TYPES = ['crônica', 'recorrente', 'esporádica']
torch.set_num_threads(1)  # rede pequena: mais threads só deixam o treino lento


def event_times(req, df, month, censor_date):
    """Dias até a próxima solicitação depois do corte, censurados em `censor_date`."""
    cutoff = pd.Timestamp(2025, month, 1)
    nxt = (req[req['data_demanda'] >= cutoff].groupby(['bairro_id', 'logradouro'])['data_demanda']
           .min().rename('proxima').reset_index())
    df = df.merge(nxt, on=['bairro_id', 'logradouro'], how='left')
    limit = min((pd.Timestamp(censor_date) - cutoff).days, EDGES[-1])
    days = (df['proxima'] - cutoff).dt.days
    df['evento'] = (days < limit).astype(int)
    df['dias'] = days.where(df['evento'] == 1, limit).astype(int)
    return df


def to_targets(df):
    d = df['dias'].to_numpy()
    e = df['evento'].to_numpy().astype(bool)
    bin_idx = np.searchsorted(EDGES, d, side='right') - 1
    # Intervalos em que a rua sobreviveu: terminam antes do evento ou até a censura.
    upper = EDGES[1:][None, :]
    survived = np.where(e[:, None], np.arange(K)[None, :] < bin_idx[:, None], upper <= d[:, None])
    failed = e[:, None] & (np.arange(K)[None, :] == bin_idx[:, None])
    return torch.tensor(survived, dtype=torch.float32), torch.tensor(failed, dtype=torch.float32)


def hazard_loss(logits, survived, failed):
    ll = survived * torch.nn.functional.logsigmoid(-logits) + failed * torch.nn.functional.logsigmoid(logits)
    return -ll.sum(1).mean()


def make_net(n_in, hidden):
    layers, size = [], n_in
    for h in hidden:
        layers += [torch.nn.Linear(size, h), torch.nn.ReLU()]
        size = h
    return torch.nn.Sequential(*layers, torch.nn.Linear(size, K))


def train(x, targets, hidden, seed, epochs=None, val=None, max_epochs=200, patience=10):
    torch.manual_seed(seed)
    net = make_net(x.shape[1], hidden)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    x = torch.tensor(x, dtype=torch.float32)
    s, f = targets
    best, best_epoch, wait = np.inf, 0, 0
    gen = torch.Generator().manual_seed(seed)
    for epoch in range(1, (epochs or max_epochs) + 1):
        net.train()
        for idx in torch.randperm(len(x), generator=gen).split(256):
            opt.zero_grad()
            hazard_loss(net(x[idx]), s[idx], f[idx]).backward()
            opt.step()
        if val is not None:
            net.eval()
            with torch.no_grad():
                loss = hazard_loss(net(torch.tensor(val[0], dtype=torch.float32)), *val[1]).item()
            if loss < best - 1e-4:
                best, best_epoch, wait = loss, epoch, 0
            else:
                wait += 1
                if wait >= patience:
                    break
    return net, best_epoch


def cumulative_risk(net, x):
    """P(nova solicitação até o fim de cada intervalo)."""
    with torch.no_grad():
        h = torch.sigmoid(net(torch.tensor(x, dtype=torch.float32))).numpy()
    return 1 - np.cumprod(1 - h, axis=1)


def c_index(time, event, risk):
    order = np.argsort(time)
    time, event, risk = time[order], event[order], risk[order]
    num = den = 0.0
    for i in np.flatnonzero(event):
        later = time > time[i]
        den += later.sum()
        num += (risk[i] > risk[later]).sum() + 0.5 * (risk[i] == risk[later]).sum()
    return num / den


def street_types(te, curves, event, time, curves_sep, snap_sep):
    """Agrupa as curvas em três tipos de rua, valida em agosto e monta o plano de setembro."""
    z = StandardScaler().fit(curves)
    sil = {k: round(float(silhouette_score(z.transform(curves), KMeans(k, n_init=20, random_state=0)
                                           .fit_predict(z.transform(curves)))), 3) for k in range(2, 7)}
    km = KMeans(3, n_init=20, random_state=0).fit(z.transform(curves))
    # Nomeia os grupos pelo risco médio em 31 dias, do maior para o menor.
    rank = np.argsort(-km.cluster_centers_[:, HORIZONS[31] - 1])
    names = {c: STREET_TYPES[i] for i, c in enumerate(rank)}
    te = te.assign(tipo=[names[c] for c in km.labels_], r7=curves[:, 0], r31=curves[:, HORIZONS[31] - 1],
                   ev7=(event == 1) & (time < 7), ev31=(event == 1) & (time < 31))
    validation = {}
    for tipo in STREET_TYPES:
        g = te[te['tipo'] == tipo]
        validation[tipo] = {
            'ruas': len(g), 'pct_ruas': round(len(g) / len(te), 3),
            'risco_previsto_7d': round(float(g['r7'].mean()), 3), 'ocorrido_7d': round(float(g['ev7'].mean()), 3),
            'risco_previsto_31d': round(float(g['r31'].mean()), 3), 'ocorrido_31d': round(float(g['ev31'].mean()), 3),
            'cobertura_7d': round(float(g['ev7'].sum() / te['ev7'].sum()), 3),
            'cobertura_31d': round(float(g['ev31'].sum() / te['ev31'].sum()), 3),
            'mediana_chamados': float(g['n_chamados'].median()),
            'mediana_dias_desde_ultimo': float(g['dias_desde_ultimo'].median()),
        }

    # Gráfico: parte das ruas e parte das solicitações de cada tipo no teste.
    fig, ax = plt.subplots(figsize=(7, 4))
    series = {'% das ruas': 'pct_ruas', '% das solicitações da 1ª semana': 'cobertura_7d',
              '% das solicitações do mês': 'cobertura_31d'}
    width = 0.26
    for i, (label, key) in enumerate(series.items()):
        vals = [100 * validation[tp][key] for tp in STREET_TYPES]
        bars = ax.bar(np.arange(3) + (i - 1) * width, vals, width, label=label,
                      color=['#9aa5b1', '#d1495b', '#edae49'][i])
        ax.bar_label(bars, fmt='%.0f%%', fontsize=8, padding=2)
    ax.set_xticks(np.arange(3), [tp.capitalize() for tp in STREET_TYPES])
    ax.set_ylabel('%')
    ax.set_ylim(0, 80)
    ax.set_title('Ruas e solicitações por tipo de rua (teste de agosto de 2025)')
    ax.legend(frameon=False, fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT_DIR / 'street_types.png', dpi=150)
    plt.close(fig)

    sep = snap_sep.assign(tipo=[names[c] for c in km.predict(z.transform(curves_sep))],
                          risco_7d=curves_sep[:, 0].round(3), risco_31d=curves_sep[:, HORIZONS[31] - 1].round(3))
    profiles = base.DATA_DIR.parent.parent / 'docs' / 'analysis' / 'kmeans_neighborhoods.csv'
    hoods = pd.read_csv(profiles)[['bairro_id', 'nome', 'cluster']].rename(
        columns={'nome': 'bairro', 'cluster': 'perfil_bairro'})
    sep = sep.merge(hoods, on='bairro_id', how='left')
    sep['prioridade'] = sep['tipo'].map({'crônica': 'semana 1', 'recorrente': 'mês', 'esporádica': 'sem ação preventiva'})
    sep['logradouro'] = sep['logradouro'].str.title()
    plan = sep[sep['tipo'] != 'esporádica'].sort_values(['tipo', 'risco_7d'], ascending=[True, False])
    plan[['prioridade', 'tipo', 'bairro', 'rpa_id', 'perfil_bairro', 'logradouro', 'risco_7d', 'risco_31d',
          'n_chamados', 'dias_desde_ultimo']].to_csv(OUT_DIR / 'inspection_plan_2025_09.csv', index=False)
    cross = pd.crosstab(sep['tipo'], sep['perfil_bairro']).reindex(STREET_TYPES)
    return ({'k': 3, 'silhueta': sil, 'validacao_agosto': validation},
            {'ruas_avaliadas': len(sep), 'arquivo': 'inspection_plan_2025_09.csv',
             'tipo_x_perfil_bairro': {t: {str(c): int(v) for c, v in row.items()} for t, row in cross.iterrows()}})


def main():
    req = base.load_requests()
    snaps = {m: base.build_snapshot(req, m)[0] for m in [4, 5, 6, 7, 8, 9]}
    fit_base = pd.concat([snaps[m] for m in [4, 5, 6]])
    fill = float(fit_base['mediana_dias'].median())
    scaler = StandardScaler().fit(base.to_matrix(fit_base, fill))
    prep = lambda df: scaler.transform(base.to_matrix(df, fill))

    # Validação: treino de abril a junho censurado em 01/07; validação em julho censurada em 01/08.
    tr_val = pd.concat([event_times(req, snaps[m], m, '2025-07-01') for m in [4, 5, 6]])
    va = event_times(req, snaps[7], 7, '2025-08-01')
    # Final: abril a julho censurado em 01/08. Teste: agosto, censurado no fim dos dados.
    tr = pd.concat([event_times(req, snaps[m], m, '2025-08-01') for m in [4, 5, 6, 7]])
    te = event_times(req, snaps[8], 8, '2025-09-01')
    x_tv, x_va, x_tr, x_te = prep(tr_val), prep(va), prep(tr), prep(te)

    models = {'Sobrevivência linear': (), 'Sobrevivência neural': (32, 16)}
    risks, epochs_used, forecast = {}, {}, []
    for name, hidden in models.items():
        runs = []
        for seed in SEEDS:
            _, n_ep = train(x_tv, to_targets(tr_val), hidden, seed, val=(x_va, to_targets(va)))
            net, _ = train(x_tr, to_targets(tr), hidden, seed, epochs=max(n_ep, 1))
            runs.append(cumulative_risk(net, x_te))
            if hidden:
                forecast.append(cumulative_risk(net, prep(snaps[9])))
            epochs_used.setdefault(name, []).append(n_ep)
        risks[name] = np.stack(runs)  # sementes x ruas x intervalos

    # Kaplan-Meier discreto: risco médio por intervalo no treino final, igual para todas as ruas.
    s, f = to_targets(tr)
    km_h = f.sum(0) / (s.sum(0) + f.sum(0))
    km = 1 - np.cumprod(1 - km_h.numpy())

    # Classificadores do item 6, treinados para "solicitação no mês seguinte".
    y_fit = tr['alvo'].to_numpy()
    clf_scores = {
        'Regra simples': base.rule_score(te).to_numpy(),
        'Regressão logística': LogisticRegression(max_iter=1000).fit(x_tr, y_fit).predict_proba(x_te)[:, 1],
        'Rede neural (classificação)': np.mean([MLPClassifier(hidden_layer_sizes=(32, 16), alpha=1e-3,
            early_stopping=True, max_iter=500, random_state=sd).fit(x_tr, y_fit).predict_proba(x_te)[:, 1]
            for sd in SEEDS], axis=0),
    }

    time, event = te['dias'].to_numpy(), te['evento'].to_numpy()
    rows = []
    for name, score in clf_scores.items():
        row = {'modelo': name}
        for h in HORIZONS:
            row[f'auc_{h}d'] = roc_auc_score((event == 1) & (time < h), score)
        row['c_index'] = c_index(time, event, score)
        y31 = ((event == 1) & (time < 31)).astype(float)
        row['precisao@200'] = y31[np.argsort(-score, kind='stable')[:200]].mean()
        row['brier_31d'] = np.mean((score - y31) ** 2) if name != 'Regra simples' else np.nan
        rows.append(row)
    for name, r in risks.items():
        per_seed = []
        for run in r:
            row = {}
            for h, b in HORIZONS.items():
                y = ((event == 1) & (time < h)).astype(float)
                row[f'auc_{h}d'] = roc_auc_score(y, run[:, b - 1])
                row[f'brier_{h}d'] = np.mean((run[:, b - 1] - y) ** 2)
            row['c_index'] = c_index(time, event, run[:, HORIZONS[31] - 1])
            y31 = ((event == 1) & (time < 31)).astype(float)
            row['precisao@200'] = y31[np.argsort(-run[:, HORIZONS[31] - 1], kind='stable')[:200]].mean()
            per_seed.append(row)
        mean = pd.DataFrame(per_seed).mean().to_dict()
        mean['modelo'] = name
        mean['c_index_desvio'] = float(pd.DataFrame(per_seed)['c_index'].std())
        rows.append(mean)
    km_row = {'modelo': 'Kaplan-Meier (sem variáveis)'}
    for h, b in HORIZONS.items():
        y = ((event == 1) & (time < h)).astype(float)
        km_row[f'brier_{h}d'] = np.mean((km[b - 1] - y) ** 2)
    rows.append(km_row)
    table = pd.DataFrame(rows).set_index('modelo')

    # Curvas de exemplo: rua crônica, rua com um chamado recente e rua com um chamado antigo.
    neural = risks['Sobrevivência neural'].mean(0)
    te = te.assign(r31=neural[:, HORIZONS[31] - 1])
    one = te[te['n_chamados'] == 1]
    examples = {
        'Crônica: ' + te.loc[te['r31'].idxmax(), 'logradouro'].title(): te['r31'].idxmax(),
        'Um chamado recente': one['dias_desde_ultimo'].idxmin(),
        'Um chamado antigo': one['dias_desde_ultimo'].idxmax(),
    }
    plt.figure(figsize=(7, 4.5))
    for label, i in examples.items():
        pos = te.index.get_loc(i)
        plt.plot(EDGES, np.r_[0, neural[pos]] * 100, marker='o', label=label, lw=2)
    plt.plot(EDGES, np.r_[0, km] * 100, marker='o', ls='--', c='grey', label='Média (Kaplan-Meier)')
    plt.xticks(EDGES)
    plt.xlabel('Dias após o corte (01/08/2025)')
    plt.ylabel('% de chance de nova solicitação até o dia')
    plt.title('Chance de nova solicitação estimada pela rede neural')
    plt.ylim(0, 100)
    plt.grid(alpha=.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'survival_curves.png', dpi=150)

    types, plan = street_types(te, neural, event, time, np.mean(forecast, axis=0), snaps[9])

    summary = {
        'intervalos_dias': EDGES.tolist(),
        'amostras': {'treino': len(tr), 'teste': len(te)},
        'teste_eventos_ate_31d': int(((event == 1) & (time < 31)).sum()),
        'epocas_validacao': epochs_used,
        'resultados': json.loads(table.round(3).to_json(orient='index', force_ascii=False)),
        'tipos_de_rua': types,
        'plano_setembro': plan,
    }
    (OUT_DIR / 'survival_results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n',
                                                   encoding='utf-8')
    print(table.round(3).to_string())
    print(json.dumps({k: v for k, v in summary.items() if k != 'resultados'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
