"""Filtra o CSV da Central 156 e gera os arquivos para carga do banco."""
import csv, hashlib, json, pathlib, sys
from collections import Counter
PROJECT_DIR = pathlib.Path(__file__).resolve().parents[1]
SOURCE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_DIR/'data/raw/emlurb_156_2025.csv'
EXPECTED = '11ef6498bf5bef2305945caecc01293ec326237a2ac87df88d0d9261d19f3166'
def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
if sha256(SOURCE) != EXPECTED:
    raise SystemExit('Versão da fonte diferente da versão congelada; não sobrescrever a demonstração.')
with SOURCE.open(encoding='utf-8-sig', newline='') as f:
    source = list(csv.DictReader(f, delimiter=';'))
rows = [(i, {k:v.strip() for k,v in r.items()}) for i,r in enumerate(source,1)
        if r['GRUPOSERVICO_DESCRICAO'].strip() == 'ILUMINACAO PUBLICA'
        and '2025-01-01' <= r['DATA_DEMANDA'] <= '2025-08-31']
# A chave usa a linha do CSV porque a fonte não publica o protocolo.
region_ids = sorted({int(r['RPA']) for _,r in rows})
neighborhood_keys = sorted({(int(r['RPA']),r['BAIRRO']) for _,r in rows})
neighborhood_ids = {k:i for i,k in enumerate(neighborhood_keys,1)}
groups = sorted({(int(r['GRUPOSERVICO_CODIGO']),r['GRUPOSERVICO_DESCRICAO']) for _,r in rows})
services = sorted({(int(r['SERVICO_CODIGO']),int(r['GRUPOSERVICO_CODIGO']),r['SERVICO_DESCRICAO']) for _,r in rows})
statuses = {s:i for i,s in enumerate(sorted({r['SITUACAO'] for _,r in rows}),1)}
assert len({i for i,g,n in services}) == len(services)
assert len({g for g,n in groups}) == len(groups)
assert all(r['DATA_ULT_SITUACAO'] >= r['DATA_DEMANDA'] for _,r in rows)
def write_csv(name, fields, values):
    with (PROJECT_DIR/'data/processed'/f'{name}.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(fields);w.writerows(values)
write_csv('regions',['rpa_id'], [(r,) for r in region_ids])
write_csv('neighborhoods',['bairro_id','rpa_id','nome'],[(i,r,n) for (r,n),i in neighborhood_ids.items()])
write_csv('service_groups',['grupo_id','descricao'],groups)
write_csv('services',['servico_id','grupo_id','descricao'],services)
write_csv('statuses',['situacao_id','descricao'],[(i,s) for s,i in statuses.items()])
write_csv('requests',['solicitacao_id','bairro_id','servico_id','situacao_id','logradouro','numero','data_demanda','data_ultima_situacao'],
    [(i,neighborhood_ids[(int(r['RPA']),r['BAIRRO'])],int(r['SERVICO_CODIGO']),statuses[r['SITUACAO']],r['LOGRADOURO'],r['NUMERO'],r['DATA_DEMANDA'],r['DATA_ULT_SITUACAO']) for i,r in rows])
manifest = {
 'municipality':'Recife','agency':'EMLURB / Emprel','obtained_at':'2026-10-18',
 'catalog_url':'https://dados.recife.pe.gov.br/dataset/central-de-atendimento-de-servicos-da-emlurb-156',
 'resource_url':'https://dados.recife.pe.gov.br/dataset/central-de-atendimento-de-servicos-da-emlurb-156/resource/06872af2-9350-4c34-aa39-6337a1822ff7',
 'download_url':'https://dados.recife.pe.gov.br/dataset/331e88a9-d878-464b-b0bb-cb803d7091b3/resource/06872af2-9350-4c34-aa39-6337a1822ff7/download/2025-central-de-atendimento-de-servicos-da-emlurb-156.csv',
 'license':'Open Data Commons Open Database License (ODbL)',
 'raw_sha256':sha256(SOURCE),'raw_rows':len(source),
 'selection':"GRUPOSERVICO_DESCRICAO = ILUMINACAO PUBLICA; DATA_DEMANDA entre 2025-01-01 e 2025-08-31 (inclusive). Não corresponde ao ano completo.",
 'source_last_status_range':[min(r['DATA_ULT_SITUACAO'] for _,r in rows),max(r['DATA_ULT_SITUACAO'] for _,r in rows)],
 'request_id_rule':'Posição do registro de dados (1-based, sem cabeçalho) no CSV original de hash fixo; não é protocolo oficial nem chave estável entre versões.',
 'transforms':['Remoção de espaços nas extremidades dos textos','Chaves locais para bairro e situação; códigos oficiais de RPA, grupo e serviço preservados','Latitude e longitude não importadas; não há análise geográfica por ponto','Sem deduplicação por endereço ou imputação de dados'],
 'counts':{'rpas':len(region_ids),'bairros':len(neighborhood_ids),'grupos':len(groups),'servicos':len(services),'situacoes':len(statuses),'solicitacoes':len(rows)},
 'statuses':dict(Counter(r['SITUACAO'] for _,r in rows)),
 'missing_coordinates':sum(not r['latitude'] or not r['longitude'] for _,r in rows),
 'invalid_date_order':0,'simulation':False,
 'processed_sha256':{p.name:sha256(p) for p in sorted((PROJECT_DIR/'data/processed').glob('*.csv'))}
}
(PROJECT_DIR/'docs/data_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest['counts'],ensure_ascii=False))
