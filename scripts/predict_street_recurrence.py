"""Prevê quais ruas terão nova solicitação de iluminação no mês seguinte.

Janela deslizante: as variáveis usam os 3 meses anteriores ao corte e o alvo indica
se a rua (bairro + logradouro) teve ao menos uma solicitação no mês do corte.
Treino: cortes de abril a junho. Validação: julho. Teste: agosto.
Compara a regra simples (mais chamados no trimestre), a regressão logística e a
rede neural (MLP). Também gera a lista de ruas para setembro de 2025.
"""
import json
import pathlib
from datetime import date

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler

PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / 'data' / 'processed'
OUT_DIR = PROJECT_DIR / 'docs' / 'analysis'
HISTORY_MONTHS = 3
TRAIN_CUTOFFS, VALID_CUTOFF, TEST_CUTOFF, FORECAST_CUTOFF = [4, 5, 6], 7, 8, 9
ATTENDED, CIRCUIT, STRUCTURE = 1, 51, {61, 63, 65, 289}
BUDGETS = [100, 200, 500]
SEED = 0


def load_requests():
    req = pd.read_csv(DATA_DIR / 'requests.csv', parse_dates=['data_demanda', 'data_ultima_situacao'])
    rpa = pd.read_csv(DATA_DIR / 'neighborhoods.csv').set_index('bairro_id')['rpa_id']
    req['logradouro'] = req['logradouro'].str.upper().str.split().str.join(' ')
    # "0", "00", "SN", "S/N" e vazio viram um único valor "SN": contam como um ponto da rua,
    # pois imóveis sem número existem, mas não dá para distinguir um do outro.
    numero = req['numero'].astype(str).str.strip().str.upper()
    req['numero'] = numero.mask(numero.str.fullmatch(r'0+|S/?N|NAN|'), 'SN')
    req['rpa_id'] = req['bairro_id'].map(rpa)
    req['mes'] = req['data_demanda'].dt.month
    return req


def build_snapshot(req, month):
    """Variáveis por rua conhecidas no primeiro dia de `month` e o alvo desse mês."""
    cutoff = pd.Timestamp(date(2025, month, 1))
    hist = req[(req['mes'] >= month - HISTORY_MONTHS) & (req['mes'] < month)].copy()
    # Evita vazamento: só conta como resolvido o que já estava ATENDIDA antes do corte.
    hist['aberto'] = (hist['situacao_id'] != ATTENDED) | (hist['data_ultima_situacao'] >= cutoff)
    hist['dias'] = (hist['data_ultima_situacao'] - hist['data_demanda']).dt.days.where(~hist['aberto'])
    hist['circuito'] = hist['servico_id'] == CIRCUIT
    hist['estrutura'] = hist['servico_id'].isin(STRUCTURE)
    g = hist.groupby(['bairro_id', 'logradouro'])
    x = pd.DataFrame({
        'n_chamados': g.size(),
        'meses_com_chamado': g['mes'].nunique(),
        'dias_desde_ultimo': (cutoff - g['data_demanda'].max()).dt.days,
        'pct_abertos': g['aberto'].mean(),
        'pct_circuito': g['circuito'].mean(),
        'pct_estrutura': g['estrutura'].mean(),
        'mediana_dias': g['dias'].median(),
        'n_numeros': g['numero'].nunique(),
        'rpa_id': g['rpa_id'].first(),
    }).reset_index()
    future = req.loc[req['mes'] == month, ['bairro_id', 'logradouro']].drop_duplicates()
    future['alvo'] = 1
    x = x.merge(future, on=['bairro_id', 'logradouro'], how='left').fillna({'alvo': 0})
    x['corte'] = month
    return x, len(future)


def to_matrix(df, fill_days):
    m = pd.DataFrame({
        'log_chamados': np.log1p(df['n_chamados']),
        'meses_com_chamado': df['meses_com_chamado'] / HISTORY_MONTHS,
        'recencia': df['dias_desde_ultimo'] / (HISTORY_MONTHS * 30),
        'pct_abertos': df['pct_abertos'],
        'pct_circuito': df['pct_circuito'],
        'pct_estrutura': df['pct_estrutura'],
        'log_mediana_dias': np.log1p(df['mediana_dias'].fillna(fill_days)),
        'sem_atendimento': df['mediana_dias'].isna().astype(float),
        'log_numeros': np.log1p(df['n_numeros']),
    })
    for r in range(1, 7):
        m[f'rpa_{r}'] = (df['rpa_id'] == r).astype(float)
    return m.to_numpy()


def rule_score(df):
    # Regra simples: mais chamados no trimestre; empate decidido pelo chamado mais recente.
    return df['n_chamados'] - df['dias_desde_ultimo'] / 1000


def evaluate(y, score, total_positive):
    order = np.argsort(-np.asarray(score), kind='stable')
    hits = np.cumsum(np.asarray(y)[order])
    out = {'auc': round(float(roc_auc_score(y, score)), 3)}
    for k in BUDGETS:
        out[f'precisao@{k}'] = round(float(hits[k - 1] / k), 3)
        out[f'cobertura@{k}'] = round(float(hits[k - 1] / total_positive), 3)
    return out, hits


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    req = load_requests()
    snaps = {m: build_snapshot(req, m) for m in TRAIN_CUTOFFS + [VALID_CUTOFF, TEST_CUTOFF]}
    train = pd.concat([snaps[m][0] for m in TRAIN_CUTOFFS])
    valid, test = snaps[VALID_CUTOFF][0], snaps[TEST_CUTOFF][0]
    fill_days = float(train['mediana_dias'].median())

    # Normalização ajustada só no treino e reaplicada nos demais cortes.
    scaler = StandardScaler().fit(to_matrix(train, fill_days))
    prep = lambda df: scaler.transform(to_matrix(df, fill_days))
    x_tr, x_va, x_te = prep(train), prep(valid), prep(test)
    y_tr, y_va, y_te = train['alvo'].to_numpy(), valid['alvo'].to_numpy(), test['alvo'].to_numpy()

    configs = [(16,), (32, 16), (64, 32)]
    val_auc = {}
    for hidden in configs:
        mlp = MLPClassifier(hidden_layer_sizes=hidden, alpha=1e-3, early_stopping=True,
                            max_iter=500, random_state=SEED).fit(x_tr, y_tr)
        val_auc[hidden] = roc_auc_score(y_va, mlp.predict_proba(x_va)[:, 1])
    best = max(val_auc, key=val_auc.get)

    # Modelo final treinado com abril a julho e avaliado em agosto.
    x_fit, y_fit = np.vstack([x_tr, x_va]), np.concatenate([y_tr, y_va])
    mlp = MLPClassifier(hidden_layer_sizes=best, alpha=1e-3, early_stopping=True,
                        max_iter=500, random_state=SEED).fit(x_fit, y_fit)
    logreg = LogisticRegression(max_iter=1000).fit(x_fit, y_fit)

    positives_with_history = int(y_te.sum())
    positives_all = snaps[TEST_CUTOFF][1]
    scores = {
        'Regra simples': rule_score(test).to_numpy(),
        'Regressão logística': logreg.predict_proba(x_te)[:, 1],
        'Rede neural (MLP)': mlp.predict_proba(x_te)[:, 1],
    }
    results, curves = {}, {}
    for name, s in scores.items():
        results[name], curves[name] = evaluate(y_te, s, positives_with_history)

    seeds_auc = []
    for seed in range(1, 6):
        m = MLPClassifier(hidden_layer_sizes=best, alpha=1e-3, early_stopping=True,
                          max_iter=500, random_state=seed).fit(x_fit, y_fit)
        seeds_auc.append(roc_auc_score(y_te, m.predict_proba(x_te)[:, 1]))

    n_test = len(test)
    plt.figure(figsize=(7, 4.5))
    frac = np.arange(1, n_test + 1) / n_test
    for name, hits in curves.items():
        plt.plot(100 * frac, 100 * hits / positives_with_history, label=name)
    plt.plot([0, 100], [0, 100], ls='--', c='grey', label='Escolha aleatória')
    plt.xlabel('% das ruas inspecionadas (ordenadas pelo modelo)')
    plt.ylabel('% das ruas com chamado em agosto cobertas')
    plt.title('Curva de ganho — teste em agosto de 2025')
    plt.grid(alpha=.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUT_DIR / 'neural_gain_curve.png', dpi=150)

    # Lista de inspeção para setembro: histórico de junho a agosto.
    forecast, _ = build_snapshot(req, FORECAST_CUTOFF)
    forecast['probabilidade'] = mlp.predict_proba(prep(forecast))[:, 1].round(3)
    names = pd.read_csv(DATA_DIR / 'neighborhoods.csv').set_index('bairro_id')['nome']
    forecast['bairro'] = forecast['bairro_id'].map(names)
    top = forecast.sort_values('probabilidade', ascending=False).head(200)
    top[['bairro', 'rpa_id', 'logradouro', 'n_chamados', 'meses_com_chamado', 'dias_desde_ultimo',
         'probabilidade']].to_csv(OUT_DIR / 'inspection_list_2025_09.csv', index=False)

    summary = {
        'janela_meses': HISTORY_MONTHS,
        'amostras': {'treino': len(train), 'validacao': len(valid), 'teste': n_test},
        'taxa_positivos': {'treino': round(float(y_tr.mean()), 3), 'teste': round(float(y_te.mean()), 3)},
        'teste_ruas_com_chamado': {'com_historico': positives_with_history, 'total': positives_all},
        'arquitetura_escolhida': list(best),
        'auc_validacao': {str(list(k)): round(float(v), 3) for k, v in val_auc.items()},
        'resultados_teste': results,
        'mlp_auc_5_sementes': {'media': round(float(np.mean(seeds_auc)), 3),
                               'desvio': round(float(np.std(seeds_auc)), 3)},
        'previsao_setembro': {'ruas_avaliadas': len(forecast), 'lista': 'inspection_list_2025_09.csv'},
    }
    (OUT_DIR / 'neural_network_results.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
