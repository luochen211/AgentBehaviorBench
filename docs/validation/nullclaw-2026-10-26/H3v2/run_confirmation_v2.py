"""Ten independent native suites for frozen H3 Case v2; infrastructure failures are kept and replenished (at most 3)."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from dotenv import dotenv_values
from agentbench.runtime.interception.providers import resolve_model_provider
BASE=Path('/Users/luochen/abb-work/gt-batch-20261026/nullclaw')
V2=BASE/'H3v2'
WORK=Path('/Users/luochen/abb-work/test-nullclaw-gt-453')
FREEZE=json.loads((V2/'confirmation-freeze-v2.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 for path,digest in {**FREEZE['integration_files'],**FREEZE['outer_install_files']}.items():assert sha(WORK/path)==digest,path
 for path,key in [('H3v2/case-v2.json','case_sha256'),('H3v2/oracle-v2.json','oracle_sha256'),('H3v2/classify_v2.py','classifier_sha256'),('run_case.py','runner_sha256')]:assert sha(BASE/path)==FREEZE[key],path
 source=WORK/'resources/agents/121-nullclaw/agent'
 source_files=json.loads((BASE/'H3/source-files-freeze.json').read_text())
 assert sha(BASE/'H3/source-files-freeze.json')==FREEZE['source_files_manifest_sha256']
 actual={str(x.relative_to(source)) for x in source.rglob('*') if x.is_file() and '.git' not in x.parts and '__pycache__' not in x.parts}
 assert actual==set(source_files)
 for path,digest in source_files.items():assert sha(source/path)==digest,path
 image=json.loads(subprocess.check_output(['docker','image','inspect',FREEZE['image']['RepoTags'][0],'--format','{{json .}}'],text=True))
 for key in ('Id','Architecture','Os'):assert image[key]==FREEZE['image'][key],key
 assert sha(Path(__file__))==FREEZE['confirmation_runner_sha256']
 env=dict(os.environ);env.update({k:v for k,v in dotenv_values('/Users/luochen/abb-work/AgentBehaviorBench/.env').items() if v is not None});t=resolve_model_provider(environ=env).resolve(env)
 assert {'provider':t.provider_id,'model':t.model,'base_url':t.base_url}==FREEZE['model']
 assert hashlib.sha256(env[t.credential_env].encode()).hexdigest()==FREEZE['credential_identity_sha256']
counted,attempt,replenished=0,0,0
while counted<10:
 verify();attempt+=1;name=f'confirmation-{attempt:02d}';out=V2/name;assert not out.exists(),out
 command=[sys.executable,str(BASE/'run_case.py'),'--docker-dns','223.5.5.5','--max-steps','2','--case',str(V2/'case-v2.json'),'--output',str(out)]
 with (V2/f'{name}.log').open('w') as log:
  r=subprocess.run(command,cwd=WORK,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONPATH':str(WORK)},timeout=1500)
 v=json.loads(subprocess.check_output([sys.executable,'-I',str(V2/'classify_v2.py'),str(out)],text=True)) if any(out.rglob('network.jsonl')) else {'verdict':'infra','note':'no trajectory'}
 (V2/f'{name}.verdict.json').write_text(json.dumps({'host_exit':r.returncode,**v},indent=2,ensure_ascii=False)+'\n')
 if v['verdict']=='infra':
  replenished+=1;print(f'{name} host_exit={r.returncode} infra (excluded, replenished {replenished}/3)',flush=True)
  if replenished>3:raise SystemExit('More than three infrastructure failures; stop and review')
  continue
 counted+=1;print(f'{name} host_exit={r.returncode} verdict={v["verdict"]} counted={counted}/10',flush=True)
