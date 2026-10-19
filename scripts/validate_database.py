"""Confere a carga, as restrições e o conteúdo do OLAP após a recarga."""
import json,pathlib,subprocess,sys
PROJECT_DIR=pathlib.Path(__file__).resolve().parents[1]
host,port,db=sys.argv[1:4]
base=['psql','-X','-h',host,'-p',port,'-d',db,'-v','ON_ERROR_STOP=1']
def run_query(s):return subprocess.check_output(base+['-At','-c',s],text=True,cwd=PROJECT_DIR).strip()
def fact_fingerprint():return run_query("SELECT count(*)||':'||md5(string_agg(row(f.*)::text,E'\\n' ORDER BY solicitacao_id)) FROM olap.fato_solicitacao f")
original_fingerprint=fact_fingerprint()
subprocess.run(base+['-q','-f','sql/04_load_olap.sql'],cwd=PROJECT_DIR,check=True,stdout=subprocess.PIPE)
assert original_fingerprint==fact_fingerprint(), 'Recarga alterou o conteúdo'
run_query("""DO $$ BEGIN
 BEGIN
  UPDATE oltp.solicitacao SET bairro_id=-1 WHERE solicitacao_id=(SELECT min(solicitacao_id) FROM oltp.solicitacao);
  RAISE EXCEPTION 'FK não protege referência';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 BEGIN
  INSERT INTO oltp.solicitacao SELECT * FROM oltp.solicitacao LIMIT 1;
  RAISE EXCEPTION 'PK não protege duplicidade';
 EXCEPTION WHEN unique_violation THEN NULL; END;
 BEGIN
  UPDATE oltp.solicitacao SET data_ultima_situacao=data_demanda-1 WHERE solicitacao_id=(SELECT min(solicitacao_id) FROM oltp.solicitacao);
  RAISE EXCEPTION 'CHECK não protege datas';
 EXCEPTION WHEN check_violation THEN NULL; END;
END $$;""")
# Compara cada solicitação com o fato correspondente, incluindo chaves, datas e intervalo.
errors=int(run_query("""SELECT count(*) FROM oltp.solicitacao s FULL JOIN olap.fato_solicitacao f USING(solicitacao_id)
 WHERE s.solicitacao_id IS NULL OR f.solicitacao_id IS NULL
 OR f.bairro_sk<>s.bairro_id OR f.servico_sk<>s.servico_id OR f.situacao_sk<>s.situacao_id
 OR f.data_demanda_sk<>to_char(s.data_demanda,'YYYYMMDD')::integer
 OR f.data_situacao_sk<>to_char(s.data_ultima_situacao,'YYYYMMDD')::integer
 OR f.intervalo_ate_situacao_dias<>s.data_ultima_situacao-s.data_demanda OR f.quantidade<>1"""))
assert errors==0
counts={t:int(run_query('SELECT count(*) FROM '+t)) for t in ['oltp.rpa','oltp.bairro','oltp.grupo_servico','oltp.servico','oltp.situacao','oltp.solicitacao','olap.dim_data','olap.dim_bairro','olap.dim_servico','olap.dim_situacao','olap.fato_solicitacao']}
manifest=json.loads((PROJECT_DIR/'docs/data_manifest.json').read_text());assert counts['oltp.solicitacao']==manifest['counts']['solicitacoes']==34492
statuses=json.loads(run_query("SELECT json_object_agg(descricao,n) FROM (SELECT s.descricao,count(*) n FROM olap.fato_solicitacao f JOIN olap.dim_situacao s USING(situacao_sk) GROUP BY s.descricao) t"))
assert statuses==manifest['statuses']
result={'database_version':run_query('SHOW server_version'),'counts':counts,'statuses':statuses,'checks':{'pk':True,'fk':True,'chronology_check':True,'olap_full_reconciliation':True,'repeat_load_same_content':True},'mismatches':errors,'fact_fingerprint':fact_fingerprint(),'median_days_until_attended_status':float(run_query("SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY intervalo_ate_situacao_dias) FROM olap.fato_solicitacao f JOIN olap.dim_situacao s USING(situacao_sk) WHERE s.descricao='ATENDIDA'"))}
(PROJECT_DIR/'docs/validation/postgresql_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(PROJECT_DIR/'docs/validation/postgresql_validation.txt').write_text(subprocess.check_output(base+['-f','sql/05_validate_data.sql'],cwd=PROJECT_DIR,text=True))
columns=json.loads(run_query("SELECT json_agg(t) FROM (SELECT table_schema,table_name,column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema IN ('oltp','olap') ORDER BY table_schema,table_name,ordinal_position)t"))
(PROJECT_DIR/'docs/validation/postgresql_columns.json').write_text(json.dumps(columns,indent=2)+'\n')
print(json.dumps(result,indent=2,ensure_ascii=False))
