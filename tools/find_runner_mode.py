#!/usr/bin/env python3
"""Locate likely runner/shooter minigame resources inside XAPK; export only candidate files.
No claim that the output is a playable APK. No code execution or decryption.
"""
import collections, hashlib, json, pathlib, re, shutil, sys, tempfile, zipfile
source=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
TERMS={
 'runner':r'runner|runway|running|parkour|run_game|runmode|run_mode|跑酷|跑步',
 'soldier':r'soldier|troop|squad|army|battalion|军队|士兵|部队',
 'shooting':r'shooter|shooting|bullet|firearm|projectile|gunfight|射击|子弹',
 'gate':r'multiplier|multiply|gate|portal|倍增|增兵|传送门',
 'minigame':r'minigame|mini_game|mini-game|小游戏|玩法|副玩法',
 'horde':r'horde|crowd|swarm|zombie|人群|僵尸',
}
patterns={k:re.compile(v,re.I) for k,v in TERMS.items()}
def category(path):
    return [k for k,p in patterns.items() if p.search(path)]
results={'source':source.name,'packages':[],'candidates':[],'warnings':[]}
candidates=[]
with zipfile.ZipFile(source) as x:
    for apkinfo in x.infolist():
        if not apkinfo.filename.lower().endswith('.apk'):continue
        with tempfile.SpooledTemporaryFile(max_size=64*1024*1024) as tmp:
            with x.open(apkinfo) as a:shutil.copyfileobj(a,tmp,4*1024*1024)
            tmp.seek(0)
            with zipfile.ZipFile(tmp) as z:
                entries=z.infolist()
                record={'apk':apkinfo.filename,'files':len(entries),'path_matches':[],'text_matches':[],'cocos_bundles':[],'large_shared_scripts':[]}
                for info in entries:
                    if info.is_dir():continue
                    name=info.filename
                    matches=category(name)
                    if matches:
                        obj={'path':name,'size':info.file_size,'signals':matches}
                        record['path_matches'].append(obj)
                        if name.startswith('assets/') and info.file_size<=12*1024*1024:
                            candidates.append((apkinfo.filename,name,info.file_size,matches))
                    if name.endswith(('config.json','settings.json')) and '/assets/' in name and info.file_size<4*1024*1024:
                        record['cocos_bundles'].append({'path':name,'bytes':info.file_size})
                    if name.endswith(('.jsc','.js')) and info.file_size>500000:
                        record['large_shared_scripts'].append({'path':name,'bytes':info.file_size})
                    # Only search short, readable config/manifest files; encrypted .jsc is not parsed.
                    if (name.lower().endswith(('.json','.txt','.js')) and info.file_size<150000
                        and ('assets/' in name or name.startswith('assets'))):
                        try:
                            data=z.read(info)
                            if not data:continue
                            txt=data.decode('utf-8',errors='ignore')
                            hits={k:len(p.findall(txt)) for k,p in patterns.items()}
                            hits={k:v for k,v in hits.items() if v}
                            if len(hits)>=2 and sum(hits.values())>=3:
                                record['text_matches'].append({'path':name,'signals':hits,'bytes':info.file_size})
                        except Exception:pass
                record['path_matches']=record['path_matches'][:250]
                record['text_matches']=sorted(record['text_matches'],key=lambda t:-sum(t['signals'].values()))[:90]
                results['packages'].append(record)
# Only package candidate resources when there are clear path signals; preserve original paths.
results['candidates']=[{'apk':a,'path':n,'bytes':s,'signals':m} for a,n,s,m in candidates[:400]]
results['candidate_count']=len(candidates)
results['warnings']=[
 'File-name/text matches are hypotheses; the runner minigame may not be installed in this XAPK.',
 'Candidate ZIP is NOT a playable APK, and may omit encrypted/remote/shared dependencies.',
 'No assets are published as a GitHub Release; archive remains an expiring private-to-run workflow artifact unless repository permissions allow access.'
]
(out/'runner_candidates.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# Localização do minijogo de soldados e tiros','','**Origem:** '+source.name,'',
'Esta é uma triagem por nomes e configurações, não uma identificação confirmada do modo.',
'','## Pacotes analisados','']
for r in results['packages']:
    lines.extend(['### '+r['apk'],'',
        f"- Arquivos internos: {r['files']}",
        f"- Nomes com indícios: {len(r['path_matches'])}",
        f"- Configurações com múltiplos indícios: {len(r['text_matches'])}",
        f"- Configurações Cocos: {len(r['cocos_bundles'])}",'',
        '**Possíveis recursos por caminho:**',''])
    lines.extend('- `'+p['path']+'` ('+', '.join(p['signals'])+')' for p in r['path_matches'][:60])
    lines.extend(['','**Configurações com termos relacionados:**',''])
    lines.extend('- `'+p['path']+'` — '+str(p['signals']) for p in r['text_matches'][:30])
    lines.append('')
lines.extend(['## Arquivo de recursos candidatos','',
f"Arquivos com indícios por nome: **{len(candidates)}**.",'',
'Se existir, `runner_candidate_assets.zip` contém somente recursos com nomes sugestivos, **não** um jogo independente.',
'','## Próxima decisão técnica','',
'Se não houver um conjunto claro de scripts/cenas e dependências do runner, não é possível isolar com segurança um APK jogável apenas removendo outros modos.',
'Uma gravação do modo original ou identificadores da cena são necessários para confirmar a correspondência.',''])
(out/'RUNNER_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
# Avoid extracting irrelevant bulk data; zip candidates only when unambiguous path match,
# capped to 100 MiB, with explicit provenance.
eligible=[(a,n,s,m) for a,n,s,m in candidates if ('runner' in m or 'shooting' in m or 'minigame' in m) and s<15*1024*1024]
if eligible and sum(t[2] for t in eligible)<100*1024*1024:
    with zipfile.ZipFile(out/'runner_candidate_assets.zip','w',compression=zipfile.ZIP_DEFLATED) as dest:
        with zipfile.ZipFile(source) as x:
            by_apk=collections.defaultdict(list)
            for a,n,s,m in eligible:by_apk[a].append(n)
            for a,names in by_apk.items():
                with tempfile.SpooledTemporaryFile(max_size=64*1024*1024) as tmp:
                    with x.open(a) as f:shutil.copyfileobj(f,tmp,4*1024*1024)
                    tmp.seek(0)
                    with zipfile.ZipFile(tmp) as apk:
                        for n in names:
                            if n.startswith('/') or '..' in pathlib.PurePosixPath(n).parts:continue
                            dest.writestr(pathlib.PurePosixPath(a).name+'/'+n,apk.read(n))
print('Packages:',len(results['packages']),'candidates:',len(candidates),'archive:',(out/'runner_candidate_assets.zip').exists())
