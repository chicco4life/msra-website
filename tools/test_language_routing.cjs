#!/usr/bin/env node
/* Offline unit/DOM fixtures only. No browser automation or real IP requests. */
'use strict';
const assert = require('node:assert/strict');
const api = require('../assets/js/language-routing.js');
const locales = Object.fromEntries(['en','de','fr','it','es','nl','pl','sv','ja','pt-BR','ko','zh-Hans','pt-PT','da','nb','fi','ru','hi'].map(code => [code,{}]));
const fragments = ['top','project-feline-urinary','ref-41'];
function configuration() {
  return { enabled:true, siteUrl:'https://msralab.com', resourceKey:'page:learn', currentLocale:'en', sourceRoute:'/learn/',
    countryEndpoint:api.endpoint, timeoutMs:1200, locales,
    variants:Object.fromEntries(Object.keys(locales).map(code => [code,{ url:code === 'en' ? '/learn/' : '/'+code.toLowerCase()+'/learn/', fragmentIds:fragments }])) };
}
function storage(initial={}) {
  const map = new Map(Object.entries(initial));
  return { getItem:key=>map.has(key)?map.get(key):null, setItem:(key,value)=>map.set(key,String(value)), entries:()=>[...map.entries()] };
}
function environment(overrides={}) {
  const calls = [], events = [];
  return Object.assign({ url:'https://msralab.com/learn/', userAgent:'Mozilla/5.0', languages:['zz-ZZ'],
    localStorage:storage(), sessionStorage:storage(), calls, events,
    fetch:async (url,options)=>{calls.push({url,options});return {ok:true,json:async()=>({ip:'192.0.2.1',country:'FR'})};},
    AbortController, setTimeout, clearTimeout, status:detail=>events.push(detail) },overrides);
}
let checks = 0;
async function test(name, body) {
  try { await body(); checks++; }
  catch(error) { error.message=name+': '+error.message; throw error; }
}
(async function () {
  await test('18 configured locale identities',()=>assert.equal(Object.keys(locales).length,18));
  await test('case and legacy locale aliases',()=>{
    assert.equal(api.locale('PT_br',locales),'pt-BR'); assert.equal(api.locale('zh-CN',locales),'zh-Hans');
    assert.equal(api.locale('no',locales),'nb'); assert.equal(api.locale('xx',locales),null);
  });
  await test('supported browser language matching',()=>{
    assert.equal(api.browserLocale(['xx','fr-CA'],locales),'fr');
    assert.equal(api.browserLocale(['pt'],locales),'pt-PT');
    assert.equal(api.browserLocale(['pt-AO'],locales),'pt-PT');
    assert.equal(api.browserLocale(['zh-Hans-CN'],locales),'zh-Hans');
    assert.equal(api.browserLocale(['zh-TW'],locales),'en');
  });
  await test('country defaults and language regions',()=>{
    for(const [country,expected] of Object.entries({DE:'de',BR:'pt-BR',PT:'pt-PT',CN:'zh-Hans',KR:'ko',NO:'nb',IN:'en',US:'en',CH:'en',ZZ:'en'})) assert.equal(api.countryLocale(country,locales),expected);
  });
  await test('multilingual markets use supported browser language as a tiebreaker',()=>{
    for(const [country,languages,expected] of [
      ['CA',['fr-CA','en'],'fr'],['CA',['en-CA','fr'],'en'],['BE',['fr-BE'],'fr'],['BE',['nl-BE'],'nl'],['BE',['de-BE'],'de'],
      ['CH',['it-CH'],'it'],['CH',['fr-CH'],'fr'],['CH',['de-CH'],'de'],['CH',['ja'],'en'],
      ['IN',['en-IN','hi'],'en'],['IN',['hi-IN','en'],'hi'],['IN',['bn'],'en'],['SG',['zh-CN','en'],'zh-Hans'],['SG',['en-SG'],'en'],
      ['CA',['xx','es','fr-CA'],'fr']
    ]) assert.equal(api.countryLocale(country,locales,languages),expected);
  });
  await test('Indian English browser is not forced into Hindi',async()=>{
    let requests=0;
    const env=environment({languages:['en-IN','hi'],fetch:async()=>{requests++;return {ok:true,json:async()=>({country:'IN'})};}});
    const result=await api.run(configuration(),env);assert.equal(result.status,'stay');assert.equal(result.locale,'en');assert.equal(requests,0);
  });
  await test('supported French browser wins before a conflicting country hint',async()=>{
    let requests=0;
    const env=environment({languages:['fr-CA'],fetch:async()=>{requests++;return {ok:true,json:async()=>({country:'JP'})};}});
    assert.equal((await api.run(configuration(),env)).locale,'fr');assert.equal(requests,0);
  });
  await test('supported English browser stays English without any IP lookup',async()=>{
    let requests=0;
    const env=environment({languages:['en-US'],fetch:async()=>{requests++;return {ok:true,json:async()=>({country:'DE'})};}});
    assert.equal((await api.run(configuration(),env)).locale,'en');assert.equal(requests,0);
  });
  await test('browser language priority is global, not restricted to country languages',async()=>{
    let requests=0;
    const env=environment({languages:['ja'],fetch:async()=>{requests++;return {ok:true,json:async()=>({country:'CH'})};}});
    assert.equal((await api.run(configuration(),env)).locale,'ja');assert.equal(requests,0);
  });
  await test('best browser match must have a released same-content variant',async()=>{
    const config=configuration();delete config.variants.fr;
    const env=environment({languages:['fr-CA','ja'],fetch:async()=>{throw new Error('must not fetch');}});
    assert.equal((await api.run(config,env)).locale,'ja');
  });
  await test('Portuguese browser regions retain distinct editions without country lookup',async()=>{
    for(const [language,expected] of [['pt-BR','pt-BR'],['pt-PT','pt-PT'],['pt-AO','pt-PT']]) {
      let requests=0;const env=environment({languages:[language],fetch:async()=>{requests++;throw new Error('must not fetch');}});
      assert.equal((await api.run(configuration(),env)).locale,expected);assert.equal(requests,0);
    }
  });
  await test('unsupported browser uses coarse country as the secondary hint',async()=>{
    let requests=0;
    const env=environment({languages:['el-GR'],fetch:async()=>{requests++;return {ok:true,json:async()=>({country:'DE'})};}});
    assert.equal((await api.run(configuration(),env)).locale,'de');assert.equal(requests,1);
  });
  await test('Traditional Chinese is not converted to Simplified by a country fallback',async()=>{
    for(const language of ['zh-Hant','zh-TW','zh-HK','zh-MO']) {
      let requests=0;const env=environment({languages:[language],fetch:async()=>{requests++;return {ok:true,json:async()=>({country:'CN'})};}});
      const result=await api.run(configuration(),env);assert.equal(result.locale,'en');assert.equal(result.status,'stay');assert.equal(requests,1);
    }
  });
  await test('a supported alternative after Traditional Chinese prevents IP lookup',async()=>{
    let requests=0;
    const env=environment({languages:['zh-TW','en-US'],fetch:async()=>{requests++;throw new Error('must not fetch');}});
    assert.equal((await api.run(configuration(),env)).locale,'en');assert.equal(requests,0);
  });
  await test('browser-based automatic routing keeps session loop protection',async()=>{
    const env=environment({languages:['fr'],fetch:async()=>{throw new Error('must not fetch');}});
    assert.equal((await api.run(configuration(),env)).status,'redirect');
    assert.equal((await api.run(configuration(),env)).reason,'session-attempted');assert.equal(env.calls.length,0);
  });
  await test('saved choice still wins over multilingual market',async()=>{
    const env=environment({localStorage:storage({[api.keys.preference]:'ja'}),languages:['fr-CA']});
    assert.equal((await api.run(configuration(),env)).locale,'ja');assert.equal(env.calls.length,0);
  });
  await test('no bot redirect; no webdriver cloaking',()=>{
    for(const agent of ['Googlebot/2.1','bingbot/2','GPTBot/1.0','YandexBot/3','Baiduspider','ChatGPT-User','Claude-User','Perplexity-User','Google-InspectionTool']) assert.equal(api.isBot(agent),true);
    assert.equal(api.isBot('Mozilla HeadlessChrome'),false);
  });
  for(const [name,changes,override,reason] of [
    ['preview',{enabled:false},{},'disabled'],
    ['localhost',{}, {url:'http://localhost:8768/learn/'},'local-or-insecure'],
    ['loopback',{}, {url:'https://127.0.0.1/learn/'},'local-or-insecure'],
    ['alternate preview host',{}, {url:'https://preview.example.com/learn/'},'nonproduction-host'],
    ['bot',{}, {userAgent:'Googlebot'},'bot'],
    ['explicit locale URL',{currentLocale:'fr'}, {url:'https://msralab.com/fr/learn/'},'explicit-or-unmatched-route'],
    ['unknown path',{}, {url:'https://msralab.com/missing/'},'explicit-or-unmatched-route'],
    ['unregistered marketing route',{resourceKey:null,variants:{}},{},'unregistered-route']
  ]) await test(name+' makes no request',async()=>{
    const env=environment(override);const result=await api.run({...configuration(),...changes},env);
    assert.equal(result.reason,reason);assert.equal(env.calls.length,0);
  });
  await test('legacy lang selection wins and persists without country lookup',async()=>{
    const env=environment({url:'https://msralab.com/learn/?x=a%20b&lang=fr&topic=cat#top',localStorage:storage({[api.keys.preference]:'ja'})});
    const result=await api.run(configuration(),env);assert.equal(result.reason,'query');
    assert.equal(result.url,'https://msralab.com/fr/learn/?x=a%20b&topic=cat#top');
    assert.equal(env.localStorage.getItem(api.keys.preference),'fr');assert.equal(env.calls.length,0);
  });
  await test('legacy cn selects Simplified Chinese',async()=>{
    const env=environment({url:'https://msralab.com/learn/?lang=cn'});
    assert.equal((await api.run(configuration(),env)).locale,'zh-Hans');assert.equal(env.calls.length,0);
  });
  await test('unknown lang is ignored and preserved',async()=>{
    const env=environment({url:'https://msralab.com/learn/?lang=unknown&x=1',localStorage:storage({[api.keys.preference]:'it'})});
    assert.equal((await api.run(configuration(),env)).url,'https://msralab.com/it/learn/?lang=unknown&x=1');
  });
  await test('explicit locale route is stronger than legacy lang query',async()=>{
    const env=environment({url:'https://msralab.com/ja/learn/?lang=fr'});
    const result=await api.run({...configuration(),currentLocale:'ja'},env);
    assert.equal(result.reason,'explicit-or-unmatched-route');assert.equal(env.localStorage.getItem(api.keys.preference),null);assert.equal(env.calls.length,0);
  });
  await test('explicit legacy selector works independently of automatic release gate',async()=>{
    const env=environment({url:'https://msralab.com/learn/?lang=fr'});
    assert.equal((await api.run({...configuration(),enabled:false},env)).locale,'fr');assert.equal(env.calls.length,0);
  });
  await test('explicit legacy choice bypasses an earlier same-content redirect',async()=>{
    const env=environment({url:'https://msralab.com/learn/?x=a%20b&lang=fr#top',
      localStorage:storage({[api.keys.preference]:'ja'}),
      sessionStorage:storage({[api.keys.redirects]:JSON.stringify(['page:learn::fr'])})});
    const result=await api.run(configuration(),env);
    assert.equal(result.reason,'query');assert.equal(result.status,'redirect');
    assert.equal(result.url,'https://msralab.com/fr/learn/?x=a%20b#top');
    assert.equal(env.localStorage.getItem(api.keys.preference),'fr');assert.equal(env.calls.length,0);
  });
  await test('implicit preference bounce remains guarded after explicit query choice',async()=>{
    const env=environment({url:'https://msralab.com/learn/?lang=fr'});
    assert.equal((await api.run(configuration(),env)).reason,'query');
    env.url='https://msralab.com/learn/';
    const result=await api.run(configuration(),env);
    assert.equal(result.reason,'redirect-already-attempted');assert.equal(result.status,'stay');assert.equal(env.calls.length,0);
  });
  await test('repeated explicit selectors work without duplicating guard tokens',async()=>{
    const env=environment({url:'https://msralab.com/learn/?lang=fr',
      sessionStorage:storage({[api.keys.redirects]:JSON.stringify(['page:learn::fr'])})});
    for(let index=0;index<3;index++) assert.equal((await api.run(configuration(),env)).reason,'query');
    assert.deepEqual(JSON.parse(env.sessionStorage.getItem(api.keys.redirects)),['page:learn::fr']);assert.equal(env.calls.length,0);
  });
  await test('manual English switch consumes stale supported lang selector',()=>{
    const result=api.destination(configuration(),'en',new URL('https://msralab.com/fr/learn/?lang=fr&x=a%2Fb'),true);
    assert.equal(result.url,'https://msralab.com/learn/?x=a%2Fb');
  });
  await test('saved explicit choice precedes lookup',async()=>{
    const env=environment({localStorage:storage({[api.keys.preference]:'ja'})});
    const result=await api.run(configuration(),env);assert.equal(result.url,'https://msralab.com/ja/learn/');assert.equal(result.reason,'preference');assert.equal(env.calls.length,0);
  });
  await test('explicit English stays English',async()=>{
    const env=environment({localStorage:storage({[api.keys.preference]:'en'})});
    assert.equal((await api.run(configuration(),env)).reason,'preference-english');assert.equal(env.calls.length,0);
  });
  await test('valid legacy explicit choice survives',async()=>{
    const env=environment({localStorage:storage({'msra-lang':'zh'})});
    assert.equal((await api.run(configuration(),env)).locale,'zh-Hans');assert.equal(env.calls.length,0);
  });
  await test('new preference overrides old one',async()=>{
    const env=environment({localStorage:storage({[api.keys.preference]:'it','msra-lang':'nl'})});
    assert.equal((await api.run(configuration(),env)).locale,'it');
  });
  await test('country hint preserves exact query and compatible fragment',async()=>{
    const env=environment({url:'https://msralab.com/learn/?topic=feline-urinary&x=a%2Fb#project-feline-urinary'});
    const result=await api.run(configuration(),env);
    assert.equal(result.url,'https://msralab.com/fr/learn/?topic=feline-urinary&x=a%2Fb#project-feline-urinary');
    assert.equal(env.calls[0].url,'https://api.country.is/');
    for(const [key,value] of Object.entries({method:'GET',mode:'cors',credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store'})) assert.equal(env.calls[0].options[key],value);
  });
  await test('IP payload never read or persisted; status contains no PII',async()=>{
    const payload={country:'FR'};Object.defineProperty(payload,'ip',{get(){throw new Error('IP must not be read');}});
    const env=environment({url:'https://msralab.com/learn/?email=private%40example.test',fetch:async()=>({ok:true,json:async()=>payload})});
    const result=await api.run(configuration(),env);assert.equal(result.locale,'fr');
    for(const event of env.events){assert.deepEqual(Object.keys(event).sort(),['locale','reason','status']);assert.equal(JSON.stringify(event).includes('private'),false);}
    assert.equal(JSON.stringify(env.localStorage.entries()).includes('192.0.2'),false);
    assert.equal(JSON.stringify(env.sessionStorage.entries()).includes('private'),false);
    assert.equal(JSON.stringify(env.sessionStorage.entries()).includes('country'),false);
  });
  await test('unsupported country and browser stay English',async()=>{
    let requests=0;
    const env=environment({fetch:async()=>{requests++;return {ok:true,json:async()=>({country:'US'})};}});
    const result=await api.run(configuration(),env);assert.equal(result.locale,'en');assert.equal(result.status,'stay');assert.equal(requests,1);
  });
  await test('HTTP error after unsupported browser defaults to English',async()=>{
    let requests=0;
    const env=environment({fetch:async()=>{requests++;return {ok:false};}});
    assert.equal((await api.run(configuration(),env)).locale,'en');assert.equal(requests,1);
  });
  await test('network error after unsupported browser defaults to English',async()=>{
    let requests=0;
    const env=environment({fetch:async()=>{requests++;throw new Error('offline');}});
    assert.equal((await api.run(configuration(),env)).locale,'en');assert.equal(requests,1);
  });
  await test('null country after unsupported browser defaults to English',async()=>{
    let requests=0;
    const env=environment({fetch:async()=>{requests++;return {ok:true,json:async()=>({country:null})};}});
    assert.equal((await api.run(configuration(),env)).locale,'en');assert.equal(requests,1);
  });
  await test('slow lookup times out and aborts; no waiting on service',async()=>{
    let aborted=false,delay;
    const env=environment({fetch:()=>new Promise(()=>{}),
      AbortController:class{constructor(){this.signal={};}abort(){aborted=true;}},
      setTimeout:(fn,ms)=>{delay=ms;return setTimeout(fn,0);}});
    const result=await api.run(configuration(),env);assert.equal(result.locale,'en');assert.equal(delay,1200);assert.equal(aborted,true);
  });
  await test('session lookup runs once',async()=>{
    const env=environment();assert.equal((await api.run(configuration(),env)).status,'redirect');
    assert.equal((await api.run(configuration(),env)).reason,'session-attempted');assert.equal(env.calls.length,1);
  });
  await test('saved preference loop protection per content',async()=>{
    const env=environment({localStorage:storage({[api.keys.preference]:'fr'})});
    assert.equal((await api.run(configuration(),env)).status,'redirect');
    assert.equal((await api.run(configuration(),env)).reason,'redirect-already-attempted');
  });
  await test('blocked session storage prevents automatic loops and requests',async()=>{
    const blocked={getItem(){throw new Error('blocked');},setItem(){throw new Error('blocked');}};
    const env=environment({sessionStorage:blocked});assert.equal((await api.run(configuration(),env)).reason,'session-storage-unavailable');assert.equal(env.calls.length,0);
  });
  await test('a missing translation never invents a locale URL',async()=>{
    const config=configuration();delete config.variants.fr;
    const result=await api.run(config,environment());assert.equal(result.locale,'en');assert.equal(result.status,'stay');assert.equal(result.url,undefined);
  });
  await test('an incompatible auto hash keeps the English deep link',async()=>{
    const env=environment({url:'https://msralab.com/learn/?x=1#english-heading'});
    assert.equal((await api.run(configuration(),env)).reason,'incompatible-fragment');
  });
  await test('manual hash compatibility preserves only actual target IDs',()=>{
    const config=configuration();
    assert.equal(api.destination(config,'fr',new URL('https://msralab.com/learn/?x=1#english-heading'),true).url,'https://msralab.com/fr/learn/?x=1');
    assert.equal(api.destination(config,'fr',new URL('https://msralab.com/learn/#%72ef-41'),true).fragmentPreserved,true);
    assert.equal(api.destination(config,'fr',new URL('https://msralab.com/learn/#%E0'),true).fragmentPreserved,false);
    assert.equal(api.destination(config,'fr',new URL('https://msralab.com/learn/#:~:text=private'),false).reason,'incompatible-fragment');
  });
  await test('absent fragment map is conservative',()=>{
    const config=configuration();delete config.variants.fr.fragmentIds;
    assert.equal(api.destination(config,'fr',new URL('https://msralab.com/learn/#top'),false).reason,'incompatible-fragment');
  });
  await test('unsafe configured targets are rejected',()=>{
    for(const url of ['//evil.test/a','https://evil.test/','/fr/learn/?capture=x','/fr/learn/#target','/fr\\evil/']) {
      const config=configuration();config.variants.fr.url=url;
      assert.equal(api.destination(config,'fr',new URL('https://msralab.com/learn/'),true).url,undefined);
    }
  });
  await test('endpoint cannot be replaced with an arbitrary receiver',async()=>{
    const env=environment();const result=await api.run({...configuration(),countryEndpoint:'https://evil.test/'},env);
    assert.equal(result.reason,'invalid-country-endpoint');assert.equal(env.calls.length,0);
  });
  await test('choice made while lookup is pending wins',async()=>{
    const local=storage();const env=environment({localStorage:local,fetch:async()=>{local.setItem(api.keys.preference,'it');return {ok:true,json:async()=>({country:'FR'})};}});
    const result=await api.run(configuration(),env);assert.equal(result.locale,'it');assert.equal(result.reason,'preference');
  });
  await test('manual navigation cancels stale automatic result',async()=>{
    const env=environment({manualChoice:()=>true});assert.equal((await api.run(configuration(),env)).reason,'manual-choice-in-progress');
  });
  await test('lookup completion uses the live fragment',async()=>{
    let live='https://msralab.com/learn/#top';
    const env=environment({currentUrl:()=>live,fetch:async()=>{live='https://msralab.com/learn/?x=1#ref-41';return {ok:true,json:async()=>({country:'FR'})};}});
    assert.equal((await api.run(configuration(),env)).url,'https://msralab.com/fr/learn/?x=1#ref-41');
  });
  await test('new incompatible fragment during lookup prevents redirect',async()=>{
    let live='https://msralab.com/learn/';
    const env=environment({currentUrl:()=>live,fetch:async()=>{live='https://msralab.com/learn/#not-translated';return {ok:true,json:async()=>({country:'FR'})};}});
    assert.equal((await api.run(configuration(),env)).reason,'incompatible-fragment');
  });
  await test('changed route during lookup is not replaced',async()=>{
    const env=environment({currentUrl:()=> 'https://msralab.com/shop/'});
    assert.equal((await api.run(configuration(),env)).reason,'navigation-changed');
  });
  await test('English source project links retain their authored queries',async()=>{
    const config={...configuration(),enabled:false,resourceKey:'page:research-project',sourceRoute:'/research/project/',currentLocale:'it',
      variants:{en:{url:'/research/project/',fragmentIds:[]},it:{url:'/it/research/project/',fragmentIds:[]}}};
    const entries=[];const links=['cat-project','rabbit-project'].map(project=>{
      const events={};const link={href:'https://msralab.com/research/project/?p='+project,getAttribute:()=>null,addEventListener:(name,fn)=>{events[name]=fn;}};
      entries.push(events);return link;
    });
    const local=storage();const win={document:{getElementById:()=>({dataset:{},textContent:JSON.stringify(config)}),querySelectorAll:()=>links,dispatchEvent(){}},
      location:{href:'https://msralab.com/it/research/project/',replace(){throw new Error('disabled');}},localStorage:local,sessionStorage:storage(),navigator:{userAgent:'Mozilla',languages:['it']},
      setTimeout,clearTimeout,AbortController,CustomEvent:class{constructor(name,init){this.detail=init.detail;}}};
    api.install(win);entries[0].click({button:0});
    assert.equal(links[0].href,'https://msralab.com/research/project/?p=cat-project');
    assert.equal(links[1].href,'https://msralab.com/research/project/?p=rabbit-project');
    assert.equal(local.getItem(api.keys.preference),'en');await new Promise(resolve=>setImmediate(resolve));
  });
  await test('manual native anchor stores choice and updates a newly changed hash',async()=>{
    const config={...configuration(),enabled:false,currentLocale:'en'};const events={};
    const link={href:'',getAttribute:name=>name==='data-language-choice'?'fr':null,addEventListener:(name,fn)=>{events[name]=fn;}};
    const node={dataset:{},textContent:JSON.stringify(config)};const messages=[];const local=storage();
    const win={document:{getElementById:()=>node,querySelectorAll:()=>[link],dispatchEvent:event=>messages.push(event.detail)},
      location:{href:'https://msralab.com/learn/?topic=cat#top',replace(){throw new Error('preview must not redirect');}},
      localStorage:local,sessionStorage:storage(),navigator:{userAgent:'Mozilla',languages:['en']},
      fetch(){throw new Error('preview must not fetch');},setTimeout,clearTimeout,AbortController,
      CustomEvent:class{constructor(name,init){this.detail=init.detail;}}};
    api.install(win);assert.equal(link.href,'https://msralab.com/fr/learn/?topic=cat#top');
    win.location.href='https://msralab.com/learn/?topic=rabbit#ref-41';
    events.click({button:0,ctrlKey:true});assert.equal(link.href,'https://msralab.com/fr/learn/?topic=rabbit#ref-41');
    assert.equal(local.getItem(api.keys.preference),'fr');assert.equal(events.auxclick instanceof Function,true);
    await new Promise(resolve=>setImmediate(resolve));assert.equal(messages.some(item=>item.status==='manual-choice'),true);
  });
  console.log(JSON.stringify({result:'PASS',checks,networkRequests:0,scope:'offline pure resolution, injected fetch/storage/timers and minimal DOM fixtures; no browser/account operations'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
