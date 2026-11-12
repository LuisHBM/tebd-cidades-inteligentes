"""Agrega os CSVs do projeto em tabelas pequenas para o dashboard.

Lê data/processed/ e docs/analysis/, grava um CSV por tabela e confere os
agregados com os números de docs/dashboards.md, kmeans.md e survival.md.
Usa apenas a biblioteca padrão.

Uso: python3 scripts/build_dashboard_data.py [pasta_de_saida]
A pasta de saída padrão é data/dashboard/.
"""
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / 'data' / 'dashboard'
OUT.mkdir(parents=True, exist_ok=True)
PROC = REPO / 'data' / 'processed'
ANALYSIS = REPO / 'docs' / 'analysis'


def read(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write(name, columns, rows):
    with open(OUT / f'{name}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(columns)
        for r in rows:
            w.writerow(['' if r.get(c) is None else r[c] for c in columns])
    print(f'{name}.csv: {len(rows)} linhas')


def rnd(value, places=1):
    """Arredonda como o round() do PostgreSQL em numeric (metade para cima)."""
    q = Decimal(1).scaleb(-places)
    d = Decimal(value).quantize(q, rounding=ROUND_HALF_UP)
    return int(d) if places == 0 else float(d)


def ratio(num, den, places=1, scale=100):
    return rnd(Decimal(scale) * Decimal(num) / Decimal(den), places)


def pdisc(values, p):
    """percentile_disc do PostgreSQL: menor valor com distribuição acumulada >= p."""
    s = sorted(values)
    return s[max(0, math.ceil(p * len(s)) - 1)]


# ---------------------------------------------------------------- carga
bairros = {r['bairro_id']: r for r in read(PROC / 'neighborhoods.csv')}
servicos = {r['servico_id']: r['descricao'] for r in read(PROC / 'services.csv')}
situacoes = {r['situacao_id']: r['descricao'] for r in read(PROC / 'statuses.csv')}

reqs = []
for r in read(PROC / 'requests.csv'):
    b = bairros[r['bairro_id']]
    ab = date.fromisoformat(r['data_demanda'])
    us = date.fromisoformat(r['data_ultima_situacao'])
    reqs.append({
        'bairro': b['nome'], 'rpa': b['rpa_id'],
        'servico': servicos[r['servico_id']],
        'situacao': situacoes[r['situacao_id']],
        'abertura': ab, 'dias': (us - ab).days,
        'atendida': situacoes[r['situacao_id']] == 'ATENDIDA',
    })

HOJE = max(r['abertura'] for r in reqs)
TOTAL = len(reqs)
SCOPES = ['Todas'] + sorted({r['rpa'] for r in reqs})
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago']
DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']


def scope_rows(scope):
    return reqs if scope == 'Todas' else [r for r in reqs if r['rpa'] == scope]


def nome_scope(scope):
    return 'Recife' if scope == 'Todas' else f'RPA {scope}'


# ---------------------------------------------------------------- resumo
resumo = []
for sc in SCOPES:
    rows = scope_rows(sc)
    n = len(rows)
    att = [r['dias'] for r in rows if r['atendida']]
    por_mes = Counter(r['abertura'].month for r in rows)
    ultimo = por_mes[HOJE.month]
    anteriores = [por_mes[m] for m in range(1, HOJE.month)]
    media_ant = Decimal(sum(anteriores)) / Decimal(len(anteriores))
    nb = len({r['bairro'] for r in rows})
    resumo.append({
        'rpa': sc, 'nome': nome_scope(sc),
        'solicitacoes': n, 'atendidas': len(att), 'nao_atendidas': n - len(att),
        'pct_atendida': ratio(len(att), n),
        'pct_do_total': ratio(n, TOTAL),
        'bairros': nb, 'chamados_por_bairro': rnd(Decimal(n) / Decimal(nb), 0),
        'mediana_dias': pdisc(att, 0.5), 'p75_dias': pdisc(att, 0.75), 'p90_dias': pdisc(att, 0.9),
        'pct_ate_3_dias': ratio(sum(1 for d in att if d <= 3), len(att)),
        'ultimo_mes': ultimo, 'media_meses_anteriores': rnd(media_ant),
        'variacao_pct': rnd(Decimal(100) * Decimal(ultimo) / media_ant - 100),
    })
write('resumo', list(resumo[0].keys()), resumo)

# ---------------------------------------------------------------- diário
diario = []
first = min(r['abertura'] for r in reqs)
dates = [first + timedelta(days=i) for i in range((HOJE - first).days + 1)]
for sc in SCOPES:
    cnt = Counter(r['abertura'] for r in scope_rows(sc))
    series = [cnt[d] for d in dates]
    for i, d in enumerate(dates):
        mm = rnd(Decimal(sum(series[i - 6:i + 1])) / 7) if i >= 6 else None
        diario.append({'rpa': sc, 'data': d.isoformat(), 'chamados': series[i], 'media_7_dias': mm})
write('diario', ['rpa', 'data', 'chamados', 'media_7_dias'], diario)

# ---------------------------------------------------------------- mensal
mensal = []
for sc in SCOPES:
    by = defaultdict(list)
    for r in scope_rows(sc):
        by[r['abertura'].month].append(r)
    for m in sorted(by):
        rows = by[m]
        n = len(rows)
        dias = len({r['abertura'] for r in rows})
        mensal.append({
            'rpa': sc, 'mes': m, 'mes_nome': MESES[m - 1], 'chamados': n, 'dias': dias,
            'media_diaria': rnd(Decimal(n) / Decimal(dias)),
            'pct_atendida': ratio(sum(r['atendida'] for r in rows), n),
            'pct_atendida_ate_7_dias': ratio(sum(1 for r in rows if r['atendida'] and r['dias'] <= 7), n),
        })
write('mensal', list(mensal[0].keys()), mensal)

# ---------------------------------------------------------------- dia da semana
semana = []
for sc in SCOPES:
    by = defaultdict(list)
    for r in scope_rows(sc):
        by[r['abertura'].isoweekday()].append(r['abertura'])
    for dw in sorted(by):
        dias = len(set(by[dw]))
        semana.append({
            'rpa': sc, 'dia_semana': dw, 'dia_nome': DIAS[dw - 1], 'dias': dias,
            'chamados': len(by[dw]), 'media_por_dia': rnd(Decimal(len(by[dw])) / Decimal(dias)),
        })
write('dia_semana', list(semana[0].keys()), semana)

# ---------------------------------------------------------------- bairros (+ k-means)
PERFIS = {
    '1': 'Alta demanda, atendimento mais lento',
    '2': 'Muitos circuitos apagados',
    '3': 'Mais pendências',
    '4': 'Danos na estrutura',
}
km = {r['nome']: r for r in read(ANALYSIS / 'kmeans_neighborhoods.csv')}
vol = Counter(r['bairro'] for r in reqs)
vol_rpa = Counter(r['rpa'] for r in reqs)
nao_b = Counter(r['bairro'] for r in reqs if not r['atendida'])
rpa_of = {b['nome']: b['rpa_id'] for b in bairros.values()}
ordered = sorted(vol.items(), key=lambda kv: (-kv[1], kv[0]))
tab_bairros = []
for pos, (nome, n) in enumerate(ordered, start=1):
    k = km[nome]
    assert int(k['volume']) == n, nome
    tab_bairros.append({
        'bairro': nome, 'rpa_id': rpa_of[nome], 'posicao': pos, 'chamados': n,
        'pct_da_rpa': ratio(n, vol_rpa[rpa_of[nome]]),
        'nao_atendidos': nao_b[nome],
        'mediana_dias': float(k['mediana_dias']), 'p90_dias': float(k['p90_dias']),
        'pct_circuito': rnd(Decimal(k['pct_circuito']) * 100),
        'pct_estrutura': rnd(Decimal(k['pct_estrutura']) * 100),
        'cluster': k['cluster'], 'perfil': PERFIS[k['cluster']],
    })
write('bairros', list(tab_bairros[0].keys()), tab_bairros)

# ---------------------------------------------------------------- perfis de bairros
perfis = []
for c in sorted(PERFIS):
    g = [r for r in km.values() if r['cluster'] == c]

    def mean(col, scale=1, places=2):
        return rnd(sum(Decimal(r[col]) for r in g) * scale / len(g), places)

    rp = Counter(r['rpa_id'] for r in g)
    perfis.append({
        'cluster': c, 'perfil': PERFIS[c], 'bairros': len(g),
        'volume_total': sum(int(r['volume']) for r in g),
        'volume_medio': mean('volume', places=1),
        'mediana_dias': mean('mediana_dias'), 'p90_dias': mean('p90_dias'),
        'pct_nao_atendida': mean('pct_nao_atendida', 100, 1),
        'pct_reincidencia': mean('pct_reincidencia', 100, 1),
        'pct_circuito': mean('pct_circuito', 100, 1),
        'pct_estrutura': mean('pct_estrutura', 100, 1),
        'rpas': ', '.join(f'{k} ({v})' for k, v in sorted(rp.items())),
        'exemplos': ', '.join(r['nome'] for r in sorted(g, key=lambda r: -int(r['volume']))[:4]),
    })
write('perfis_bairros', list(perfis[0].keys()), perfis)

# ---------------------------------------------------------------- serviços
tab_serv = []
for sc in SCOPES:
    rows = scope_rows(sc)
    by = defaultdict(list)
    for r in rows:
        by[r['servico']].append(r)
    for s, rs in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        att = [r['dias'] for r in rs if r['atendida']]
        tab_serv.append({
            'rpa': sc, 'servico': s, 'chamados': len(rs),
            'pct_do_total': ratio(len(rs), len(rows)),
            'atendidos': len(att), 'pct_atendida': ratio(len(att), len(rs)),
            'nao_atendidos': len(rs) - len(att),
            'mediana_dias': pdisc(att, 0.5) if att else None,
            'p90_dias': pdisc(att, 0.9) if att else None,
        })
write('servicos', list(tab_serv[0].keys()), tab_serv)

# ---------------------------------------------------------------- pendências
FAIXAS = ['ate_30_dias', 'de_31_a_90', 'de_91_a_180', 'acima_180']


def faixa(d):
    return FAIXAS[0] if d <= 30 else FAIXAS[1] if d <= 90 else FAIXAS[2] if d <= 180 else FAIXAS[3]


pend = []
for sc in SCOPES:
    by = defaultdict(Counter)
    for r in scope_rows(sc):
        if not r['atendida']:
            by[r['situacao']][faixa((HOJE - r['abertura']).days)] += 1
    for s, c in sorted(by.items(), key=lambda kv: (-sum(kv[1].values()), kv[0])):
        pend.append({'rpa': sc, 'situacao': s, **{f: c[f] for f in FAIXAS}, 'total': sum(c.values())})
write('pendencias', ['rpa', 'situacao', *FAIXAS, 'total'], pend)

by = defaultdict(list)
for r in reqs:
    if not r['atendida']:
        by[(r['bairro'], r['rpa'], r['servico'])].append(r['abertura'])
pbs = [{'bairro': b, 'rpa_id': rp, 'servico': s, 'local_servico': f'{b} · {s}',
        'nao_atendidos': len(v), 'abertura_mais_antiga': min(v).isoformat()}
       for (b, rp, s), v in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0][0]))]
write('pendencias_bairro_servico', list(pbs[0].keys()), pbs)

# ---------------------------------------------------------------- mineração
surv = json.loads((ANALYSIS / 'survival_results.json').read_text(encoding='utf-8'))
PRIOR = {'crônica': 'semana 1', 'recorrente': 'no mês', 'esporádica': 'sem ação preventiva'}

tipos = []
for t, v in surv['tipos_de_rua']['validacao_agosto'].items():
    tipos.append({
        'tipo': t, 'ruas': v['ruas'], 'pct_ruas': rnd(Decimal(str(v['pct_ruas'])) * 100),
        'previsto_7d': rnd(Decimal(str(v['risco_previsto_7d'])) * 100),
        'ocorrido_7d': rnd(Decimal(str(v['ocorrido_7d'])) * 100),
        'previsto_31d': rnd(Decimal(str(v['risco_previsto_31d'])) * 100),
        'ocorrido_31d': rnd(Decimal(str(v['ocorrido_31d'])) * 100),
        'pct_chamados_7d': rnd(Decimal(str(v['cobertura_7d'])) * 100),
        'pct_chamados_31d': rnd(Decimal(str(v['cobertura_31d'])) * 100),
        'mediana_chamados_trimestre': int(v['mediana_chamados']),
        'mediana_dias_desde_ultimo': int(v['mediana_dias_desde_ultimo']),
    })
write('tipos_rua', list(tipos[0].keys()), tipos)

matriz = []
for t, v in surv['plano_setembro']['tipo_x_perfil_bairro'].items():
    matriz.append({'tipo': t, 'prioridade': PRIOR[t], 'perfil_1': v['1'], 'perfil_2': v['2'],
                   'perfil_3': v['3'], 'perfil_4': v['4'], 'total': sum(v.values())})
write('plano_matriz', list(matriz[0].keys()), matriz)

modelos = []
for m, v in surv['resultados'].items():
    modelos.append({'modelo': m, 'auc_7d': v['auc_7d'], 'auc_14d': v['auc_14d'], 'auc_31d': v['auc_31d'],
                    'c_index': v['c_index'],
                    'precisao_200': None if v['precisao@200'] is None else rnd(Decimal(str(v['precisao@200'])) * 100),
                    'brier_31d': v['brier_31d']})
write('modelos', list(modelos[0].keys()), modelos)

# Curva de ganho: tabela publicada em docs/analysis/neural_network.md (teste de agosto de 2025).
ganho = [{'pct_ruas_inspecionadas': a, 'rede_neural': b, 'regra_simples': c}
         for a, b, c in [(5, 14, 14), (10, 26, 25), (20, 41, 40), (30, 52, 51), (50, 72, 68)]]
md = (ANALYSIS / 'neural_network.md').read_text(encoding='utf-8')
assert '| Rede neural | 14% | 26% | 41% | 52% | 72% |' in md
assert '| Regra simples | 14% | 25% | 40% | 51% | 68% |' in md
write('curva_ganho', list(ganho[0].keys()), ganho)

plano = read(ANALYSIS / 'inspection_plan_2025_09.csv')
for i, r in enumerate(plano, start=1):
    r['ordem'] = i
    r['risco_7d_pct'] = rnd(Decimal(r['risco_7d']) * 100)
    r['risco_31d_pct'] = rnd(Decimal(r['risco_31d']) * 100)
    r['perfil'] = PERFIS[r['perfil_bairro']]
write('plano_setembro', ['ordem', 'prioridade', 'tipo', 'bairro', 'rpa_id', 'perfil_bairro', 'perfil', 'logradouro',
                         'risco_7d_pct', 'risco_31d_pct', 'n_chamados', 'dias_desde_ultimo'], plano)

# ---------------------------------------------------------------- cubo para os filtros
# Uma linha por combinação das dimensões do esquema estrela, com a contagem de solicitações.
cubo = Counter((r['abertura'].isoformat(), r['rpa'], r['bairro'], r['servico'], r['situacao'], r['dias']) for r in reqs)
cubo_rows = [{'data': d, 'rpa': rp, 'bairro': b, 'servico': sv, 'situacao': st, 'dias': di, 'solicitacoes': n}
             for (d, rp, b, sv, st, di), n in sorted(cubo.items())]
write('solicitacoes', list(cubo_rows[0].keys()), cubo_rows)

# ---------------------------------------------------------------- tabelas do banco (validação no PostgreSQL)
val = json.loads((REPO / 'docs' / 'validation' / 'postgresql_validation.json').read_text(encoding='utf-8'))
PAPEL = {
    'oltp.rpa': ('OLTP', 'cadastro', 'rpa_id'),
    'oltp.bairro': ('OLTP', 'cadastro', 'bairro_id, rpa_id, nome'),
    'oltp.grupo_servico': ('OLTP', 'cadastro', 'grupo_id, descricao'),
    'oltp.servico': ('OLTP', 'cadastro', 'servico_id, grupo_id, descricao'),
    'oltp.situacao': ('OLTP', 'cadastro', 'situacao_id, descricao'),
    'oltp.solicitacao': ('OLTP', 'transação', 'solicitacao_id, bairro_id, servico_id, situacao_id, logradouro, numero, data_demanda, data_ultima_situacao'),
    'olap.dim_data': ('OLAP', 'dimensão', 'data_sk, data, ano, mes, dia, dia_semana'),
    'olap.dim_bairro': ('OLAP', 'dimensão', 'bairro_sk, nome, rpa_id'),
    'olap.dim_servico': ('OLAP', 'dimensão', 'servico_sk, descricao, grupo_id, grupo_descricao'),
    'olap.dim_situacao': ('OLAP', 'dimensão', 'situacao_sk, descricao'),
    'olap.fato_solicitacao': ('OLAP', 'fato', 'solicitacao_id, data_demanda_sk, data_situacao_sk, bairro_sk, servico_sk, situacao_sk, quantidade, intervalo_ate_situacao_dias'),
}
tabelas = [{'tabela': t, 'modelo': PAPEL[t][0], 'papel': PAPEL[t][1], 'linhas': n, 'colunas': PAPEL[t][2]}
           for t, n in val['counts'].items()]
write('tabelas_banco', list(tabelas[0].keys()), tabelas)

# ---------------------------------------------------------------- conferência com docs/dashboards.md
def find(rows, **kw):
    out = [r for r in rows if all(str(r[k]) == str(v) for k, v in kw.items())]
    assert len(out) == 1, (kw, len(out))
    return out[0]


def check(label, got, expected):
    assert got == expected, f'{label}: obtido {got!r}, esperado {expected!r}'


city = find(resumo, rpa='Todas')
check('total', city['solicitacoes'], 34492)
check('atendidas', city['atendidas'], 33662)
check('não atendidas', city['nao_atendidas'], 830)
check('mediana', city['mediana_dias'], 2)
check('% até 3 dias', city['pct_ate_3_dias'], 81.8)
check('referência', HOJE, date(2025, 8, 31))

# estratégico Q1 e Q5, tático Q1
for rpa, nb, n, pct, por_b, pa, att, p50, p75, p90, p3, um, ma, var in [
    ('6', 8, 8172, 23.7, 1022, 96.4, 7877, 2, 4, 5, 72.3, 1154, 1002.6, 15.1),
    ('3', 28, 6082, 17.6, 217, 97.8, 5947, 1, 2, 2, 98.1, 710, 767.4, -7.5),
    ('1', 11, 6076, 17.6, 552, 98.6, 5993, 1, 3, 4, 83.5, 786, 755.7, 4.0),
    ('5', 16, 5361, 15.5, 335, 97.7, 5238, 2, 4, 5, 73.7, 597, 680.6, -12.3),
    ('4', 12, 5281, 15.3, 440, 97.7, 5160, 2, 4, 6, 72.7, 645, 662.3, -2.6),
    ('2', 18, 3520, 10.2, 196, 97.9, 3447, 1, 2, 2, 98.4, 425, 442.1, -3.9),
]:
    r = find(resumo, rpa=rpa)
    got = (r['bairros'], r['solicitacoes'], r['pct_do_total'], r['chamados_por_bairro'], r['pct_atendida'],
           r['atendidas'], r['mediana_dias'], r['p75_dias'], r['p90_dias'], r['pct_ate_3_dias'],
           r['ultimo_mes'], r['media_meses_anteriores'], r['variacao_pct'])
    check(f'RPA {rpa}', got, (nb, n, pct, por_b, pa, att, p50, p75, p90, p3, um, ma, var))

# tático Q3 e estratégico Q2
for m, n, dias, md_, pa, p7 in [
    (1, 4296, 31, 138.6, 98.8, 97.2), (2, 4303, 28, 153.7, 98.6, 96.6), (3, 4030, 31, 130.0, 98.6, 95.9),
    (4, 4081, 30, 136.0, 98.2, 95.6), (5, 4481, 31, 144.5, 98.0, 95.7), (6, 4359, 30, 145.3, 97.9, 93.3),
    (7, 4625, 31, 149.2, 97.2, 94.4), (8, 4317, 31, 139.3, 93.6, 88.6),
]:
    r = find(mensal, rpa='Todas', mes=m)
    check(f'mês {m}', (r['chamados'], r['dias'], r['media_diaria'], r['pct_atendida'], r['pct_atendida_ate_7_dias']),
          (n, dias, md_, pa, p7))

# tático Q5
for dw, dias, n, media in [(1, 34, 4752, 139.8), (2, 34, 6808, 200.2), (3, 35, 6352, 181.5), (4, 35, 6013, 171.8),
                           (5, 35, 6090, 174.0), (6, 35, 2364, 67.5), (7, 35, 2113, 60.4)]:
    r = find(semana, rpa='Todas', dia_semana=dw)
    check(f'dia {dw}', (r['dias'], r['chamados'], r['media_por_dia']), (dias, n, media))

# tático Q2 e estratégico Q4
for s, n, pct, pa, na, att, med, p90 in [
    ('MANUTENCAO EM LAMPADA APAGADA', 26164, 75.9, 99.5, 138, 26026, 2, 5),
    ('ACENDER CIRCUITO', 6080, 17.6, 98.9, 65, 6015, 1, 4),
    ('LUMINARIAS', 645, 1.9, 31.3, 443, 202, 0, 63),
    ('APAGAR LAMPADA', 501, 1.5, 100.0, 0, 501, 1, 3),
    ('REPOSICAO DE LUMINARIA', 364, 1.1, 69.5, 111, 253, 0, 0),
    ('REPOSICAO VAO DE REDE', 355, 1.0, 99.4, 2, 353, 0, 0),
    ('REPOSICAO DESL. E RET. DE POSTE', 191, 0.6, 63.9, 69, 122, 0, 4),
    ('APAGAR CIRCUITO', 115, 0.3, 99.1, 1, 114, 1, 4),
    ('POSICIONAR LUMINARIA', 76, 0.2, 98.7, 1, 75, 2, 5),
    ('IMPLANTACAO DE VAO DE REDE', 1, 0.0, 100.0, 0, 1, 0, 0),
]:
    r = find(tab_serv, rpa='Todas', servico=s)
    check(s, (r['chamados'], r['pct_do_total'], r['pct_atendida'], r['nao_atendidos'], r['atendidos'],
              r['mediana_dias'], r['p90_dias']), (n, pct, pa, na, att, med, p90))

# operacional Q2 e Q3
for s, a, b, c, d, t in [('PENDENCIA', 199, 155, 200, 106, 660), ('PREPARACAO', 52, 54, 12, 3, 121),
                         ('EXECUCAO', 24, 11, 5, 2, 42), ('CADASTRADA', 0, 0, 7, 0, 7)]:
    r = find(pend, rpa='Todas', situacao=s)
    check(s, tuple(r[k] for k in [*FAIXAS, 'total']), (a, b, c, d, t))
check('pend. Brasília Teimosa', (pbs[0]['bairro'], pbs[0]['servico'], pbs[0]['nao_atendidos'],
                                  pbs[0]['abertura_mais_antiga']),
      ('Brasilia Teimosa', 'LUMINARIAS', 61, '2025-02-10'))
check('soma pendências', sum(r['nao_atendidos'] for r in pbs), 830)

# tático Q4 e estratégico Q3
for pos, nome, n, pct in [(1, 'Boa Viagem', 2420, 29.6), (2, 'Santo Amaro', 1937, 31.9), (3, 'Boa Vista', 1345, 22.1),
                          (8, 'Brasilia Teimosa', 956, 11.7), (10, 'Areias', 888, 16.6)]:
    r = find(tab_bairros, posicao=pos)
    check(f'bairro {pos}', (r['bairro'], r['chamados'], r['pct_da_rpa']), (nome, n, pct))
check('top 10', sum(r['chamados'] for r in tab_bairros[:10]), 13006)
check('11 a 30', sum(r['chamados'] for r in tab_bairros[10:30]), 11297)

# k-means (docs/analysis/kmeans.md)
for c, nb, vm, vt, med, p90, na, re, ci, es in [
    ('1', 39, 596.6, 23267, 2.27, 5.18, 2.5, 94.3, 15.8, 2.2),
    ('2', 26, 277.2, 7206, 1.00, 2.21, 1.1, 95.7, 25.3, 2.7),
    ('3', 23, 154.1, 3544, 1.04, 2.02, 3.5, 87.4, 8.1, 1.6),
    ('4', 5, 95.0, 475, 2.10, 4.46, 4.2, 88.0, 9.4, 10.4),
]:
    r = find(perfis, cluster=c)
    check(f'cluster {c}', (r['bairros'], r['volume_medio'], r['volume_total'], r['mediana_dias'], r['p90_dias'],
                           r['pct_nao_atendida'], r['pct_reincidencia'], r['pct_circuito'], r['pct_estrutura']),
          (nb, vm, vt, med, p90, na, re, ci, es))

# plano de setembro (docs/analysis/survival.md)
check('plano', Counter(r['tipo'] for r in plano), Counter({'recorrente': 857, 'crônica': 328}))
check('matriz', [(r['tipo'], r['total']) for r in matriz], [('crônica', 328), ('recorrente', 857), ('esporádica', 2307)])
for r in matriz[:2]:
    for p in '1234':
        check(f"matriz {r['tipo']} {p}", sum(1 for x in plano if x['tipo'] == r['tipo'] and x['perfil_bairro'] == p),
              r[f'perfil_{p}'])

check('cubo', sum(r['solicitacoes'] for r in cubo_rows), 34492)
check('fato', find(tabelas, tabela='olap.fato_solicitacao')['linhas'], 34492)

print('Conferência concluída: todos os agregados batem com a documentação do projeto.')
