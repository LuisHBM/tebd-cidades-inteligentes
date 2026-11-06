"""Verificações do modelo de reincidência por rua.

Overfitting (treino, validação e teste), controle com alvo embaralhado, desempenho por
subgrupo, bootstrap da diferença entre modelos, série semanal como entrada e janelas
de histórico e horizonte diferentes. Resultados em docs/analysis/verification_results.json.
"""
import json
import pathlib
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import predict_street_recurrence as base  # noqa: E402

warnings.filterwarnings('ignore', category=ConvergenceWarning)
r3 = lambda v: round(float(v), 3)


def mlp(hidden=(32, 16), alpha=1e-3, early=True, iters=500, seed=0):
    return MLPClassifier(hidden_layer_sizes=hidden, alpha=alpha, early_stopping=early,
                         max_iter=iters, random_state=seed)


def auc(y, s):
    return roc_auc_score(y, s) if len(set(y)) == 2 else np.nan


def snapshot(req, month, history, horizon):
    base.HISTORY_MONTHS = history
    x, _ = base.build_snapshot(req, month)
    fut = req.loc[req['mes'].between(month, month + horizon - 1), ['bairro_id', 'logradouro']].drop_duplicates()
    x = x.drop(columns='alvo').merge(fut.assign(alvo=1), on=['bairro_id', 'logradouro'], how='left')
    return x.fillna({'alvo': 0})


def weekly_counts(req, df, month):
    cutoff = pd.Timestamp(2025, month, 1)
    h = req[(req['data_demanda'] < cutoff) & (req['data_demanda'] >= cutoff - pd.Timedelta(days=91))].copy()
    h['semana'] = ((cutoff - h['data_demanda']).dt.days // 7).clip(upper=12)
    w = h.groupby(['bairro_id', 'logradouro', 'semana']).size().unstack(fill_value=0).reindex(columns=range(13),
                                                                                              fill_value=0)
    m = df.merge(w, left_on=['bairro_id', 'logradouro'], right_index=True, how='left')
    return np.log1p(m[list(range(13))].fillna(0).to_numpy())


def main():
    req = base.load_requests()
    out = {}
    s = {m: base.build_snapshot(req, m)[0] for m in [4, 5, 6, 7, 8]}
    fit = pd.concat([s[m] for m in [4, 5, 6]])
    tr = pd.concat([fit, s[7]])
    te = s[8].copy()
    fill = float(fit['mediana_dias'].median())
    sc = StandardScaler().fit(base.to_matrix(fit, fill))
    prep = lambda d: sc.transform(base.to_matrix(d, fill))
    x_fit, x_va, x_tr, x_te = prep(fit), prep(s[7]), prep(tr), prep(te)

    # 1. Treino (abr-jun) x validação (jul) x teste (ago).
    rows = {}
    for name, model in {'Rede (16)': mlp((16,)), 'Rede (32, 16)': mlp(), 'Rede (64, 32)': mlp((64, 32)),
                        'Regressão logística': LogisticRegression(max_iter=2000)}.items():
        model.fit(x_fit, fit['alvo'])
        rows[name] = [r3(auc(d['alvo'], model.predict_proba(x)[:, 1]))
                      for d, x in ((fit, x_fit), (s[7], x_va), (te, x_te))]
    rows['Regra simples'] = [r3(auc(d['alvo'], base.rule_score(d))) for d in (fit, s[7], te)]
    out['treino_validacao_teste'] = rows

    # 2. Redes sem proteção contra overfitting (treino abr-jul, teste ago).
    gap = {}
    for name, model in {'Rede (32, 16) com L2 e parada antecipada': mlp(),
                        'Rede (32, 16) sem proteção': mlp(alpha=0.0, early=False, iters=300),
                        'Rede (256, 128) sem proteção': mlp((256, 128), alpha=0.0, early=False, iters=300)}.items():
        model.fit(x_tr, tr['alvo'])
        gap[name] = {'auc_treino': r3(auc(tr['alvo'], model.predict_proba(x_tr)[:, 1])),
                     'auc_teste': r3(auc(te['alvo'], model.predict_proba(x_te)[:, 1])), 'epocas': model.n_iter_}
    out['protecao_overfitting'] = gap

    # 3. Controle: com o alvo embaralhado, a AUC deve ficar perto de 0,5.
    shuffled = tr['alvo'].sample(frac=1, random_state=0).to_numpy()
    out['alvo_embaralhado_auc_teste'] = r3(auc(te['alvo'], mlp().fit(x_tr, shuffled).predict_proba(x_te)[:, 1]))

    # 4. Subgrupos e bootstrap pareado.
    te['rede'] = mlp().fit(x_tr, tr['alvo']).predict_proba(x_te)[:, 1]
    te['logistica'] = LogisticRegression(max_iter=2000).fit(x_tr, tr['alvo']).predict_proba(x_te)[:, 1]
    te['regra'] = base.rule_score(te)
    te['faixa'] = pd.cut(te['n_chamados'], [0, 1, 2, 4, 9, np.inf], labels=['1', '2', '3-4', '5-9', '10+'])
    groups = list(te.groupby('faixa', observed=True)) + [(f'RPA {r}', g) for r, g in te.groupby('rpa_id')]
    out['subgrupos'] = {f'{name}': {'ruas': len(g), 'taxa_positivos': r3(g['alvo'].mean()),
                                    **{c: r3(auc(g['alvo'], g[c])) for c in ('regra', 'logistica', 'rede')}}
                        for name, g in groups}
    rng = np.random.default_rng(0)
    diffs = {'rede_menos_logistica': [], 'rede_menos_regra': []}
    for _ in range(500):
        g = te.iloc[rng.integers(0, len(te), len(te))]
        diffs['rede_menos_logistica'].append(auc(g['alvo'], g['rede']) - auc(g['alvo'], g['logistica']))
        diffs['rede_menos_regra'].append(auc(g['alvo'], g['rede']) - auc(g['alvo'], g['regra']))
    out['bootstrap_auc'] = {k: {'media': r3(np.mean(v)), 'ic95': [r3(np.percentile(v, 2.5)),
                                                                   r3(np.percentile(v, 97.5))]}
                            for k, v in diffs.items()}

    # 5. Série semanal bruta como entrada.
    weeks = {m: weekly_counts(req, s[m], m) for m in s}
    feats = {'variáveis': lambda ms: np.vstack([base.to_matrix(s[m], fill) for m in ms]),
             'semanas': lambda ms: np.vstack([weeks[m] for m in ms]),
             'variáveis + semanas': lambda ms: np.hstack([np.vstack([base.to_matrix(s[m], fill) for m in ms]),
                                                          np.vstack([weeks[m] for m in ms])])}
    seq = {}
    for name, build in feats.items():
        z = StandardScaler().fit(build([4, 5, 6]))
        a, b = z.transform(build([4, 5, 6, 7])), z.transform(build([8]))
        nets = [auc(te['alvo'], mlp(seed=sd).fit(a, tr['alvo']).predict_proba(b)[:, 1]) for sd in range(3)]
        seq[name] = {'rede': r3(np.mean(nets)), 'logistica': r3(auc(
            te['alvo'], LogisticRegression(max_iter=2000).fit(a, tr['alvo']).predict_proba(b)[:, 1]))}
    out['serie_semanal'] = seq

    # 6. Janelas de histórico e horizontes de previsão.
    windows = {}
    for hist, hor in ((1, 1), (1, 2), (3, 1), (3, 2)):
        test_month = 9 - hor
        train_months = [m for m in range(hist + 1, test_month) if m + hor - 1 < test_month]
        a_df = pd.concat([snapshot(req, m, hist, hor) for m in train_months])
        b_df = snapshot(req, test_month, hist, hor)
        f = float(a_df['mediana_dias'].median())
        z = StandardScaler().fit(base.to_matrix(a_df, f))
        a, b = z.transform(base.to_matrix(a_df, f)), z.transform(base.to_matrix(b_df, f))
        nets = [auc(b_df['alvo'], mlp(seed=sd).fit(a, a_df['alvo']).predict_proba(b)[:, 1]) for sd in range(3)]
        windows[f'{hist} -> {hor}'] = {
            'ruas_teste': len(b_df), 'regra': r3(auc(b_df['alvo'], base.rule_score(b_df))),
            'logistica': r3(auc(b_df['alvo'], LogisticRegression(max_iter=2000).fit(a, a_df['alvo'])
                                .predict_proba(b)[:, 1])),
            'rede': r3(np.mean(nets)), 'rede_desvio': r3(np.std(nets))}
    base.HISTORY_MONTHS = 3
    out['janelas'] = windows

    path = base.OUT_DIR / 'verification_results.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
