#!/usr/bin/env python3
"""Deep, read-only technical inspection of a Cocos/Android XAPK.
Produces metadata reports only: no extraction or redistribution of game assets.
"""
import collections, hashlib, io, json, pathlib, re, struct, sys, zipfile
from datetime import datetime, timezone

src=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
MAX_CONFIG=15*1024*1024
def short(s,n=230): return str(s)[:n]
def ext(name): return pathlib.PurePosixPath(name.lower()).suffix or '(none)'
def fmt(n): return f'{n/1024/1024:.2f} MiB'
def png_dimensions(b):
    if len(b)>=24 and b[:8]==b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II',b[16:24])
def jpeg_dimensions(b):
    try:
        p=2
        while p+9<len(b):
            if b[p]!=255: p+=1;continue
            marker=b[p+1];p+=2
            if marker in (0xd8,0xd9,0x01) or 0xd0<=marker<=0xd7:continue
            if p+2>len(b):break
            size=int.from_bytes(b[p:p+2],'big')
            if marker in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf):
                return (int.from_bytes(b[p+3:p+5],'big'),int.from_bytes(b[p+5:p+7],'big'))
            p+=size
    except Exception: pass
def walk_names(z):
    return [i for i in z.infolist() if not i.is_dir()]
def analyze_apk(z, label):
    files=walk_names(z); count=collections.Counter(ext(i.filename) for i in files)
    roots=collections.Counter('/'.join(i.filename.split('/')[:3]) for i in files)
    native=[i.filename for i in files if i.filename.lower().endswith('.so')]
    configs=[i for i in files if i.filename.lower().endswith(('config.json','settings.json','manifest.json')) and i.file_size<MAX_CONFIG]
    js=[i.filename for i in files if i.filename.lower().endswith(('.js','.jsc','.jscb','.wasm'))]
    media=[i for i in files if ext(i.filename) in ('.png','.jpg','.jpeg','.webp','.pkm','.ktx','.ktx2','.pvr','.astc','.plist','.atlas','.fnt','.skel','.json','.map','.mp3','.ogg','.wav','.bank')]
    sizes=collections.Counter()
    for i in files: sizes[ext(i.filename)]+=i.file_size
    details={'label':label,'file_count':len(files),'total_uncompressed_bytes':sum(i.file_size for i in files),
      'extension_counts':dict(count.most_common()),'extension_bytes':dict(sizes.most_common()),
      'top_directories':dict(roots.most_common(45)),'native_libraries':native[:100],
      'script_paths':js[:120],'asset_name_examples':[short(i.filename) for i in media[:80]],
      'largest_files':[{'path':short(i.filename),'bytes':i.file_size} for i in sorted(files,key=lambda x:x.file_size,reverse=True)[:35]],
      'engine_indicators':[],'image_dimensions':[],'cocos_config_summary':[]}
    needles=('cocos2d','libunity','globalgamemanagers','il2cpp','libue4','libunreal','godot','flutter','spine','dragonbones','laya','fairygui')
    details['engine_indicators']=[short(i.filename) for i in files if any(x in i.filename.lower() for x in needles)][:100]
    for i in configs[:15]:
        try:
            obj=json.loads(z.read(i))
            if isinstance(obj,dict):
                keys=list(obj)[:60]
                entry={'path':short(i.filename),'keys':keys}
                for k in ('uuids','versions','types','scenes','packs','paths','rawAssets','md5Assets','subpackages','bundleVers','remoteBundles','assetTypes','launchScene'):
                    if k in obj:
                        v=obj[k];entry[k+'_summary']={'kind':type(v).__name__,'count':len(v) if hasattr(v,'__len__') else None,'examples':list(v)[:8] if isinstance(v,(dict,list)) else short(v)}
                details['cocos_config_summary'].append(entry)
        except Exception as e:
            details['cocos_config_summary'].append({'path':short(i.filename),'error':short(e)})
    # Read only first bytes of representative image files, never export image data.
    candidates=[i for i in files if ext(i.filename) in ('.png','.jpg','.jpeg','.webp','.pkm','.ktx','.ktx2')]
    for i in candidates[:1800]:
        try:
            with z.open(i) as f: b=f.read(65536 if ext(i.filename) in ('.jpg','.jpeg') else 64)
            dims=png_dimensions(b) if ext(i.filename)=='.png' else jpeg_dimensions(b) if ext(i.filename) in ('.jpg','.jpeg') else None
            if dims:details['image_dimensions'].append({'path':short(i.filename),'width':dims[0],'height':dims[1],'bytes':i.file_size})
        except Exception:pass
    details['image_dimensions'].sort(key=lambda x:x['width']*x['height'],reverse=True)
    details['image_dimensions']=details['image_dimensions'][:120]
    return details

report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'source_name':src.name,'source_bytes':src.stat().st_size,'packages':[],
        'method':'ZIP central-directory inspection and bounded metadata parsing; no application execution, decompilation, or asset extraction'}
with zipfile.ZipFile(src) as x:
    manifest=x.read('manifest.json') if 'manifest.json' in x.namelist() else None
    if manifest:
        try:report['xapk_manifest']=json.loads(manifest)
        except Exception as e:report['xapk_manifest_error']=short(e)
    for entry in x.infolist():
        if not entry.filename.lower().endswith('.apk'):continue
        try:
            # Spooled temp file ensures large padpack doesn't reside in RAM.
            import tempfile, shutil
            with tempfile.SpooledTemporaryFile(max_size=32*1024*1024) as tmp:
                with x.open(entry) as f:shutil.copyfileobj(f,tmp,length=4*1024*1024)
                tmp.seek(0)
                with zipfile.ZipFile(tmp) as a:report['packages'].append(analyze_apk(a,entry.filename))
        except Exception as e:report['packages'].append({'label':entry.filename,'error':short(e)})
(out/'deep_inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# Análise técnica aprofundada do XAPK','',f'**Pacote:** {src.name}',f'**Tamanho:** {fmt(src.stat().st_size)}',
       '', '## Método e limitações','',report['method'],'',
       'A presença de bibliotecas indica tecnologias, mas não demonstra o funcionamento de fases ou mecânicas. ',
       'Nenhuma imagem, som, código compilado ou outro recurso proprietário é exportado.','','## Pacotes internos','']
for a in report['packages']:
    lines.extend([f"### {a['label']}",''])
    if 'error' in a:lines.extend([f"Erro: {a['error']}",'']);continue
    lines.extend([f"Arquivos: **{a['file_count']}**; descompactados: **{fmt(a['total_uncompressed_bytes'])}**.",'',
        '**Extensões predominantes (quantidade / volume descompactado):**',''])
    for k,n in list(a['extension_counts'].items())[:35]:
        lines.append(f"- `{k}`: {n} / {fmt(a['extension_bytes'][k])}")
    lines.extend(['','**Bibliotecas nativas:**',''])
    lines.extend('- `'+x+'`' for x in a['native_libraries'][:35])
    lines.extend(['','**Indicadores de engine/framework:**',''])
    lines.extend('- `'+x+'`' for x in a['engine_indicators'][:30])
    lines.extend(['','**Scripts e bundles (amostra):**',''])
    lines.extend('- `'+x+'`' for x in a['script_paths'][:35])
    lines.extend(['','**Configurações Cocos/manifestos (somente chaves e contagens):**',''])
    for c in a['cocos_config_summary'][:15]:
        lines.append('- `'+c['path']+'`: '+', '.join(c.get('keys',[])[:25]))
        for k,v in c.items():
            if k.endswith('_summary'):lines.append('  - '+k+': '+str(v.get('count'))+' itens; amostra: '+short(v.get('examples'),170))
    lines.extend(['','**Maiores imagens com dimensões identificáveis:**',''])
    for i in a['image_dimensions'][:25]:
        lines.append(f"- {i['width']}×{i['height']} ({fmt(i['bytes'])}): `{i['path']}`")
    lines.append('')
lines.extend(['## Recomendações para desenvolvimento original','',
    '1. Definir primeiro o modo de jogo desejado com gravação de tela; Top War pode conter modos diferentes do anúncio.',
    '2. Criar sprites, personagens, sons e interfaces próprios; não copiar recursos proprietários.',
    '3. Usar dados de resolução e formatos apenas para planejamento de performance e arquitetura.',
    '4. Medir FPS, uso de memória, responsividade do toque e tempo de carregamento no Galaxy A55.',
    '5. Validar tiros, colisões, progressão e multiplicadores em testes jogáveis, não somente em inspeção estática.',
    ''])
(out/'DEEP_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
print('Finished deep inventory:',len(report['packages']),'APKs')
