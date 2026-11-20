#!/usr/bin/env python3
"""Inventory a user-supplied XAPK without executing game code or redistributing assets."""
import collections, hashlib, json, os, pathlib, re, sys, zipfile
from datetime import datetime, timezone

source = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
MAX_NAMES = 250000
MAX_APK_INSPECT = 80
SAMPLE_LIMIT = 120
def classify(n):
    p = n.lower()
    if p.endswith(('.so',)): return 'native_library'
    if p.endswith(('.apk',)): return 'apk'
    if p.endswith(('.obb',)): return 'obb'
    if p.endswith(('.bundle','.unity3d','.assets','.resource','.resS'.lower())): return 'unity_asset'
    if p.endswith(('.png','.jpg','.jpeg','.webp','.ktx','.ktx2','.pvr','.astc','.dds')): return 'texture_image'
    if p.endswith(('.fbx','.obj','.gltf','.glb','.mesh','.skel','.anim')): return 'model_animation'
    if p.endswith(('.mp3','.ogg','.wav','.bank','.wem')): return 'audio'
    if p.endswith(('.json','.xml','.txt','.ini','.cfg')): return 'config_text'
    if p.endswith(('.dex',)): return 'dex'
    return 'other'
def inspect_zip(z, label, limit=MAX_NAMES):
    data = {'label':label, 'files':0, 'total_uncompressed_bytes':0, 'categories':collections.Counter(), 'extensions':collections.Counter(), 'sample_paths':[], 'engine_evidence':[], 'largest':[]}
    evidence = []
    largest = []
    for i, info in enumerate(z.infolist()):
        if i >= limit:
            data['truncated'] = True
            break
        if info.is_dir(): continue
        name = info.filename
        lower = name.lower()
        cat = classify(name)
        data['files'] += 1
        data['total_uncompressed_bytes'] += info.file_size
        data['categories'][cat] += 1
        ext = pathlib.PurePosixPath(lower).suffix or '(none)'
        data['extensions'][ext] += 1
        if len(data['sample_paths']) < SAMPLE_LIMIT and cat != 'other':
            data['sample_paths'].append({'path':name[:280],'bytes':info.file_size,'category':cat})
        if any(x in lower for x in ('libunity.so','globalgamemanagers','assets/bin/data','unityplayer','il2cpp','libue4.so','libunreal.so','libgodot','godot','cocos2d','libcocos','flutter','libflutter.so')):
            evidence.append(name[:280])
        largest.append((info.file_size,name[:280]))
        if len(largest)>100:
            largest.sort(reverse=True)
            largest=largest[:30]
    data['engine_evidence'] = evidence[:100]
    data['largest'] = [{'bytes':n,'path':p} for n,p in sorted(largest,reverse=True)[:30]]
    data['categories'] = dict(data['categories'].most_common())
    data['extensions'] = dict(data['extensions'].most_common(40))
    return data

with source.open('rb') as f:
    h=hashlib.sha256()
    while True:
        block=f.read(4*1024*1024)
        if not block: break
        h.update(block)
report={'generated_utc':datetime.now(timezone.utc).isoformat(), 'source_filename':source.name, 'source_bytes':source.stat().st_size, 'sha256':h.hexdigest(), 'warnings':['Inventory only; no game binaries or proprietary assets are republished.','Extension and path based engine detection is indicative, not definitive.']}
with zipfile.ZipFile(source) as z:
    report['xapk']=inspect_zip(z,'xapk')
    manifest=next((x for x in z.infolist() if x.filename.lower()=='manifest.json' and x.file_size < 2000000),None)
    if manifest:
        try:
            report['manifest']=json.loads(z.read(manifest).decode('utf-8-sig'))
        except Exception as e:
            report['manifest_error']=str(e)
    apks=[i for i in z.infolist() if i.filename.lower().endswith('.apk')]
    report['apk_inspections']=[]
    for info in apks[:MAX_APK_INSPECT]:
        if info.file_size>900*1024*1024:
            report['apk_inspections'].append({'name':info.filename,'skipped':'APK exceeds 900 MiB'})
            continue
        try:
            import tempfile
            with tempfile.SpooledTemporaryFile(max_size=32*1024*1024) as tmp:
                with z.open(info) as src:
                    while True:
                        block=src.read(4*1024*1024)
                        if not block: break
                        tmp.write(block)
                tmp.seek(0)
                with zipfile.ZipFile(tmp) as apk:
                    report['apk_inspections'].append(inspect_zip(apk,info.filename))
        except Exception as e:
            report['apk_inspections'].append({'name':info.filename,'error':str(e)})
    report['apk_count']=len(apks)
(out/'inventory.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
lines=['# Relatório técnico do XAPK','','**Arquivo:** '+source.name,'','**Tamanho:** '+str(source.stat().st_size)+' bytes','', '**SHA-256:** `'+report['sha256']+'`','','## Indícios de motor gráfico','']
ev=report['xapk']['engine_evidence'][:]+[e for a in report['apk_inspections'] for e in a.get('engine_evidence',[])]
if ev:
    lines.extend('- `'+e.replace('`','')+'`' for e in ev[:80])
else:
    lines.append('Nenhum indicador conhecido detectado por nomes de arquivos. Não é conclusão definitiva.')
lines.extend(['','## Resumo de arquivos',''])
for name,group in [('XAPK',report['xapk'])]+[(a.get('label',a.get('name','APK')),a) for a in report['apk_inspections']]:
    lines.extend(['### '+name,'','Arquivos: '+str(group.get('files','não inspecionado')),''])
    for cat,num in group.get('categories',{}).items():
        lines.append('- '+cat+': '+str(num))
    lines.append('')
    if group.get('largest'):
        lines.extend(['Maiores arquivos:',''])
        for entry in group['largest'][:12]:
            lines.append('- '+entry['path']+' ('+str(entry['bytes'])+' bytes)')
        lines.append('')
lines.extend(['## Limitações','','A análise lista nomes, formatos e tamanhos sem executar o aplicativo. Não comprova as mecânicas ou a qualidade gráfica; vídeos de jogabilidade continuam úteis.'])
(out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Created',out/'inventory.json',out/'REPORT.md')
