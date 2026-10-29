#!/usr/bin/env node
/**
 * Offline design preview for this repository, NOT a Jekyll build or deployment.
 * Uses an intentionally small, fail-on-unsupported Liquid subset plus marked.
 * It reads the real layouts/includes/content and writes only to a temp directory.
 * Run with the bundled Node runtime; no dependency installation is required.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.resolve(process.argv[2] || '/private/tmp/msra-library-preview');
if (path.dirname(OUT) !== '/private/tmp' || !/^msra-library-preview(?:-[a-z0-9-]+)?$/.test(path.basename(OUT))) {
  throw new Error('Preview output must be /private/tmp/msra-library-preview or an explicitly suffixed preview directory.');
}
const MODULES = process.env.MSRA_PREVIEW_MODULES || '/Users/work/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const { marked } = await import(path.join(MODULES, 'marked/lib/marked.esm.js'));
const ruby = spawnSync('/usr/bin/ruby', ['-EUTF-8', '-ryaml', '-rjson', '-rdate', '-e', `
root=ARGV[0]; result={config:YAML.load_file(root+'/_config.yml'),data:{},documents:[],layouts:{},includes:{}}
Dir.glob(root+'/_data/**/*.{yml,yaml,json}').sort.each do |f|
  keys=f.sub(root+'/_data/', '').sub(/\\.(yml|yaml|json)$/, '').split('/')
  target=result[:data]; keys[0...-1].each { |key| target[key]||={}; target=target[key] }
  target[keys[-1]]=File.extname(f)=='.json' ? JSON.parse(File.read(f)) : YAML.load_file(f)
end
files=Dir.glob(root+'/{index.html,404.html,learn/**/*.{html,md,xml},research/**/*.html,shop/**/*.html,privacy/**/*.{html,md},_articles/**/*.md,_research/**/*.md,_localized/**/*.{md,html,xml}}')
files.each { |f| s=File.read(f); if s.start_with?("---\\n"); _,front,body=s.split(/^---\\s*$\\n/,3); result[:documents]<<{file:f.sub(root+'/', ''),meta:YAML.load(front)||{},body:body||''}; end }
%w[layouts includes].each { |k| Dir.glob(root+'/_'+k+'/*').each { |f| next unless File.file?(f); s=File.read(f); meta={}; if s.start_with?("---\\n"); _,front,s=s.split(/^---\\s*$\\n/,3); meta=YAML.load(front)||{}; end; result[k.to_sym][File.basename(f,File.extname(f))]={meta:meta,body:s}; } }
puts JSON.generate(result)
`, ROOT], { encoding: 'utf8', maxBuffer: 30 * 1024 * 1024 });
if (ruby.status !== 0) throw new Error(ruby.stderr);
const input = JSON.parse(ruby.stdout);
const site = { ...input.config, data: input.data, time: new Date().toISOString() };
const truth = v => v !== false && v !== null && v !== undefined;
const empty = v => v === '' || v === false || v === null || v === undefined || (Array.isArray(v) && !v.length);
const string = v => v === null || v === undefined ? '' : typeof v === 'object' ? JSON.stringify(v) : String(v);
const escape = v => string(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

function splitOutside(text, delimiter) {
  const result = []; let start = 0, quote = '', depth = 0;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quote) { if (c === quote && text[i-1] !== '\\') quote = ''; continue; }
    if (c === '"' || c === "'") { quote = c; continue; }
    if (c === '[' || c === '(') depth++;
    if (c === ']' || c === ')') depth--;
    if (!depth && text.slice(i, i + delimiter.length) === delimiter) {
      result.push(text.slice(start, i).trim()); start = i + delimiter.length; i += delimiter.length - 1;
    }
  }
  return [...result, text.slice(start).trim()];
}

function value(text, scope) {
  text = text.trim();
  if (/^(['"]).*\1$/s.test(text)) return text.slice(1, -1);
  if (/^-?\d+(\.\d+)?$/.test(text)) return Number(text);
  if (text === 'true') return true;
  if (text === 'false') return false;
  if (text === 'nil' || text === 'null') return null;
  let name = text.match(/^[\w-]+/);
  if (!name) throw new Error(`Unsupported Liquid value: ${text}`);
  let result = scope[name[0]], rest = text.slice(name[0].length);
  while (rest) {
    let key;
    if (rest.startsWith('.')) {
      const match = rest.match(/^\.([\w-]+)/); if (!match) throw new Error(`Bad property: ${text}`);
      key = match[1]; rest = rest.slice(match[0].length);
    } else if (rest.startsWith('[')) {
      const end = rest.indexOf(']'); if (end < 0) throw new Error(`Bad index: ${text}`);
      key = evaluate(rest.slice(1, end), scope); rest = rest.slice(end + 1);
    } else throw new Error(`Unsupported Liquid path: ${text}`);
    if (key === 'size') result = result?.length ?? (result && Object.keys(result).length) ?? 0;
    else if (key === 'first' && Array.isArray(result)) result = result[0];
    else if (key === 'last' && Array.isArray(result)) result = result.at(-1);
    else result = result?.[key];
  }
  return result;
}

function formatDate(inputValue, fmt) {
  const date = inputValue === 'now' ? new Date() : new Date(inputValue);
  if (Number.isNaN(date.valueOf())) return string(inputValue);
  const pad = x => String(x).padStart(2, '0');
  const fields = { '%Y': date.getUTCFullYear(), '%m': pad(date.getUTCMonth()+1), '%d': pad(date.getUTCDate()), '%B': date.toLocaleString('en-GB', {month:'long',timeZone:'UTC'}), '%b': date.toLocaleString('en-GB', {month:'short',timeZone:'UTC'}), '%s': Math.floor(date.valueOf()/1000) };
  return String(fmt).replace(/%[YmdBbs]/g, token => fields[token]);
}

const filters = {
  default: (v, fallback) => empty(v) ? fallback : v,
  append: (v, x) => string(v)+string(x), prepend: (v, x) => string(x)+string(v),
  relative_url: v => `${site.baseurl || ''}/${string(v).replace(/^\//,'')}`,
  absolute_url: v => /^https?:\/\//.test(string(v)) ? v : `${site.url}${site.baseurl || ''}/${string(v).replace(/^\//,'')}`,
  escape, xml_escape: escape, jsonify: v => JSON.stringify(v ?? null),
  strip: v => string(v).trim(), downcase: v => string(v).toLowerCase(), upcase: v => string(v).toUpperCase(),
  strip_html: v => string(v).replace(/<[^>]*>/g,''), normalize_whitespace: v => string(v).replace(/\s+/g,' ').trim(),
  date: formatDate, date_to_rfc822: v => new Date(v).toUTCString().replace('GMT','+0000'),
  where: (v,k,x) => (v||[]).filter(item => item[k] === x || (Array.isArray(item[k]) && item[k].includes(x))),
  first: v => v?.[0], last: v => v?.at(-1), reverse: v => [...(v||[])].reverse(),
  sort: (v,k) => [...(v||[])].sort((a,b) => { a=k?a[k]:a; b=k?b[k]:b; return a < b ? -1 : a > b ? 1 : 0; }),
  map: (v,k) => (v||[]).map(item => item[k]), join: (v,x=' ') => (v||[]).join(x), split: (v,x) => string(v).split(x),
  replace: (v,x,y) => string(v).split(string(x)).join(string(y)),
  slice: (v,start,length) => { const data = v ?? ''; start = Number(start); if (start < 0) start = data.length + start; return data.slice(start, length === undefined ? start + 1 : start + Number(length)); },
  minus: (v,x) => Number(v)-Number(x), plus: (v,x) => Number(v)+Number(x), size: v => v?.length || 0,
  url_encode: v => encodeURIComponent(string(v)).replace(/[!'()*]/g,c=>'%'+c.charCodeAt(0).toString(16).toUpperCase()),
  slugify: v => string(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,''),
};

function evaluate(text, scope) {
  const pipeline = splitOutside(text, '|'); let result = value(pipeline.shift(), scope);
  for (const part of pipeline) {
    const colon = splitOutside(part, ':'); const name = colon.shift();
    if (!filters[name]) throw new Error(`Unsupported Liquid filter: ${name}`);
    const args = colon.length ? splitOutside(colon.join(':'), ',').map(arg => evaluate(arg, scope)) : [];
    result = filters[name](result, ...args);
  }
  return result;
}

function condition(text, scope) {
  const or = splitOutside(text, ' or '); if (or.length > 1) return or.some(part => condition(part,scope));
  const and = splitOutside(text, ' and '); if (and.length > 1) return and.every(part => condition(part,scope));
  for (const operator of [' contains ', ' == ', ' != ', ' >= ', ' <= ', ' > ', ' < ']) {
    const parts = splitOutside(text, operator); if (parts.length !== 2) continue;
    const a=evaluate(parts[0],scope), b=evaluate(parts[1],scope);
    return operator.trim() === 'contains' ? (a?.includes(b) || false) : ({' == ':a===b,' != ':a!==b,' >= ':a>=b,' <= ':a<=b,' > ':a>b,' < ':a<b})[operator];
  }
  return truth(evaluate(text,scope));
}

function tokenize(source) {
  source=source.replace(/\s+({[{%]-)/g,'$1').replace(/(-[}%]})\s+/g,'$1');
  return source.split(/({{[\s\S]*?}}|{%[\s\S]*?%})/).filter(Boolean).map(raw => {
    if (raw.startsWith('{{')) return { type:'output', text:raw.slice(2,-2).replace(/^-|-$/g,'').trim() };
    if (raw.startsWith('{%')) return { type:'tag', text:raw.slice(2,-2).replace(/^-|-$/g,'').trim() };
    return { type:'text', text:raw };
  });
}

function parse(source) {
  const tokens=tokenize(source); let index=0;
  function block(stops=[]) {
    const nodes=[];
    while(index<tokens.length) {
      const token=tokens[index++], name=token.text.split(/\s/,1)[0];
      if(token.type==='tag' && stops.includes(name)) return {nodes, stop:token};
      if(token.type!=='tag') { nodes.push(token); continue; }
      const rest=token.text.slice(name.length).trim();
      if(name==='comment' || name==='raw') {
        const raw=[]; while(index<tokens.length) { const x=tokens[index++]; if(x.type==='tag' && x.text===`end${name}`) break; raw.push(x.type==='text'?x.text:x.type==='output'?`{{${x.text}}}`:`{%${x.text}%}`); }
        if(name==='raw') nodes.push({type:'text',text:raw.join('')});
      } else if(name==='if' || name==='unless') {
        const branches=[]; let test=rest, result;
        do { result=block(['elsif','else',`end${name}`]); branches.push({test,nodes:result.nodes}); test=result.stop?.text.slice(5).trim(); } while(result.stop?.text.startsWith('elsif '));
        if(result.stop?.text==='else') { result=block([`end${name}`]); branches.push({test:null,nodes:result.nodes}); }
        if(!result.stop) throw new Error(`Unclosed ${name}`);
        nodes.push({type:name,branches});
      } else if(name==='for') {
        const result=block(['else','endfor']); let fallback=[];
        if(result.stop?.text==='else') fallback=block(['endfor']).nodes;
        nodes.push({type:'for',text:rest,nodes:result.nodes,fallback});
      } else if(name==='case') {
        const branches=[]; let result=block(['when','else','endcase']);
        while(result.stop?.text.startsWith('when ')) { const test=result.stop.text.slice(5); result=block(['when','else','endcase']); branches.push({test,nodes:result.nodes}); }
        if(result.stop?.text==='else') branches.push({test:null,nodes:block(['endcase']).nodes});
        nodes.push({type:'case',text:rest,branches});
      } else if(name==='capture') { nodes.push({type:'capture',text:rest,nodes:block(['endcapture']).nodes});
      } else if(['assign','include','break','continue'].includes(name)) nodes.push({type:name,text:rest});
      else throw new Error(`Unsupported Liquid tag: ${token.text}`);
    }
    return {nodes};
  }
  return block().nodes;
}

const parsed=new Map();
function render(source, scope) {
  if(!parsed.has(source)) parsed.set(source,parse(source));
  return renderNodes(parsed.get(source),scope);
}
function renderNodes(nodes, scope) {
  let output='';
  for(const node of nodes) {
    if(node.type==='text') output+=node.text;
    else if(node.type==='output') output+=string(evaluate(node.text,scope));
    else if(node.type==='assign') { const match=node.text.match(/^([\w-]+)\s*=\s*([\s\S]+)$/); if(!match) throw new Error(`Bad assign: ${node.text}`); scope[match[1]]=evaluate(match[2],scope); }
    else if(node.type==='capture') scope[node.text]=renderNodes(node.nodes,scope);
    else if(node.type==='if' || node.type==='unless') {
      for(const branch of node.branches) if(branch.test===null || (condition(branch.test,scope)!==(node.type==='unless'))) { output+=renderNodes(branch.nodes,scope); break; }
    } else if(node.type==='case') {
      const candidate=evaluate(node.text,scope);
      for(const branch of node.branches) if(branch.test===null || splitOutside(branch.test,' or ').some(x=>evaluate(x,scope)===candidate)) { output+=renderNodes(branch.nodes,scope); break; }
    } else if(node.type==='for') {
      const match=node.text.match(/^([\w-]+)\s+in\s+([\s\S]+?)(?:\s+limit:\s*(\w+))?(?:\s+offset:\s*(\w+))?$/);
      if(!match) throw new Error(`Unsupported for: ${node.text}`);
      let list=evaluate(match[2],scope)||[]; if(!Array.isArray(list)) list=Object.entries(list);
      list=list.slice(Number(match[4]||0),match[3]?Number(match[4]||0)+Number(evaluate(match[3],scope)):undefined);
      if(!list.length) output+=renderNodes(node.fallback,scope);
      const previous=scope.forloop;
      for(let i=0;i<list.length;i++) { scope[match[1]]=list[i]; scope.forloop={index:i+1,index0:i,first:i===0,last:i===list.length-1,length:list.length}; output+=renderNodes(node.nodes,scope); }
      scope.forloop=previous;
    } else if(node.type==='include') {
      const match=node.text.match(/^([^\s]+)([\s\S]*)$/), key=match[1].replace(/\.html$/,'');
      const include={}; for(const arg of match[2].matchAll(/([\w-]+)=('[^']*'|"[^"]*"|[^\s]+)/g)) include[arg[1]]=evaluate(arg[2],scope);
      if(!input.includes[key]) throw new Error(`Missing include: ${key}`);
      output+=render(input.includes[key].body,{...scope,include});
    } else throw new Error(`Unsupported render node: ${node.type}`);
  }
  return output;
}

function collectionFor(doc) {
  return doc.file.startsWith('_articles/')?'articles':doc.file.startsWith('_research/')?'research':doc.file.startsWith('_localized/')?'localized':null;
}
function routeFor(doc) {
  if(doc.meta.permalink) return doc.meta.permalink;
  const collection=collectionFor(doc);
  if(collection === 'localized') throw new Error(`${doc.file}: localized documents require an explicit actual permalink`);
  if(collection) return site.collections[collection].permalink.replace(':name',path.basename(doc.file,'.md'));
  return '/'+doc.file.replace(/\.md$/,'.html').replace(/index\.html$/,'');
}
const docs=input.documents.map(doc => {
  const collection=collectionFor(doc);
  let defaults={};
  for(const entry of site.defaults||[]) {
    const scopePath=(entry.scope.path||'').replace(/^\/+|\/+$/g,'');
    const pathMatches=!scopePath || doc.file===scopePath || doc.file.startsWith(scopePath+'/');
    if(pathMatches && (!entry.scope.type || entry.scope.type===collection)) defaults={...defaults,...entry.values};
  }
  return {...doc,meta:{...defaults,...doc.meta,url:routeFor(doc),...(collection?{collection}:{})}};
});
site.articles=docs.filter(doc=>doc.meta.collection==='articles').map(doc=>doc.meta);
site.research=docs.filter(doc=>doc.meta.collection==='research').map(doc=>doc.meta);
site.localized=docs.filter(doc=>doc.meta.collection==='localized').map(doc=>doc.meta);
site.pages=docs.filter(doc=>!doc.meta.collection).map(doc=>doc.meta);
fs.rmSync(OUT,{recursive:true,force:true});
fs.mkdirSync(OUT,{recursive:true});
fs.cpSync(path.join(ROOT,'assets'),path.join(OUT,'assets'),{recursive:true});
const manifest=[];
for(const doc of docs) {
  try {
    const scope={site,page:doc.meta,jekyll:{environment:'preview'}};
    let html=render(doc.body,scope);
    if(doc.file.endsWith('.md')) html=marked.parse(html);
    let layout=doc.meta.layout;
    const seen=new Set();
    while(layout && layout!=='null') {
      if(seen.has(layout)) throw new Error('Circular layout'); seen.add(layout);
      const item=input.layouts[layout]; if(!item) throw new Error(`Missing layout: ${layout}`);
      html=render(item.body,{...scope,content:html,layout:item.meta}); layout=item.meta.layout;
    }
    if(html.includes('</body>')) html=html.replace('</body>','<div data-design-preview style="position:fixed;bottom:8px;left:8px;padding:5px 9px;background:#17242b;color:white;border-radius:3px;font:11px/1.4 sans-serif;z-index:9999;pointer-events:none">Design preview · not a Jekyll build</div></body>');
    const relative=doc.meta.url.endsWith('/')?doc.meta.url+'index.html':doc.meta.url;
    const dest=path.join(OUT,relative); fs.mkdirSync(path.dirname(dest),{recursive:true}); fs.writeFileSync(dest,html);
    manifest.push({source:doc.file,url:doc.meta.url,output:path.relative(OUT,dest)});
  } catch(error) { throw new Error(`${doc.file}: ${error.message}`,{cause:error}); }
}
const previewSitemap=docs.filter(doc=>doc.meta.sitemap!==false && doc.meta.sitemap!=='false').map(doc=>`${site.url}${doc.meta.url}`);
fs.writeFileSync(path.join(OUT,'sitemap.xml'),'<?xml version="1.0" encoding="UTF-8"?>\n<!-- DESIGN PREVIEW ONLY: modeled front-matter exclusions; not generated by jekyll-sitemap. -->\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+previewSitemap.map(url=>`<url><loc>${escape(url)}</loc></url>`).join('')+'</urlset>\n');
const fingerprintResult=spawnSync('python3',['-c',"import sys;sys.path.insert(0,'tools');from prepare_localizations import marketing_source_fingerprint;print(marketing_source_fingerprint('.'))"],{cwd:ROOT,encoding:'utf8'});
if(fingerprintResult.status!==0)throw new Error(fingerprintResult.stderr);
const summary={marketingSourceFingerprint:fingerprintResult.stdout.trim(),renderer:'MSRA subset Liquid + marked design preview',isJekyllBuild:false,generatedAt:new Date().toISOString(),output:OUT,pages:manifest.length,previewSitemap:{isJekyllPluginOutput:false,entries:previewSitemap.length},limitations:['Not Jekyll; Liquid subset and marked can differ from Liquid/Ruby and kramdown.','Does not run Jekyll plugins or verify deployment. Preview sitemap models front-matter exclusions only.','Analytics is disabled in this local preview.'],manifest};
fs.writeFileSync(path.join(OUT,'preview-manifest.json'),JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify({...summary,manifest:undefined},null,2));
