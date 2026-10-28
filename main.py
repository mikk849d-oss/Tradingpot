"""Gratis cloud-aktiescreener: parallelle faktor-agenter, valgfrie AI-kritikere.

Ingen rigtig ordreafgivelse. Kursbaseret screening, IKKE en valideret strategi.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
UNIVERSE = [
    'MSFT','GOOGL','AMZN','META','ADBE','UBER','TOST','BKNG',
    'CRDO','TSM','NVDA','AMD','SNEX','RKLB','GRAB','V',
    'MA','COST','ISRG','LLY','UNH','RTX','XOM','GEV',
    'ASML.AS','SAP.DE','NOVO-B.CO','DSV.CO','7203.T','SONY','MELI','BHP',
]


def synthetic_prices():
    """Kun til offline tests. Aldrig en investeringsanbefaling."""
    result = {}
    for j, ticker in enumerate(UNIVERSE[:12]):
        rng = random.Random(1000+j)
        values = [50.0 + 5*j]
        for _ in range(320):
            values.append(values[-1]*math.exp((j-5)*0.00025+rng.gauss(0,0.017)))
        result[ticker] = {'prices':values,'date':'DEMO - fiktiv','currency':'N/A'}
    return result


def live_prices():
    import yfinance as yf
    tickers = os.getenv('TICKERS','').strip().split(',') if os.getenv('TICKERS') else UNIVERSE
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    if not tickers:
        raise RuntimeError('Ingen aktier i TICKERS')
    result, errors = {}, []
    for i in range(0,len(tickers),8):
        chunk = tickers[i:i+8]
        try:
            frame = yf.download(tickers=chunk, period='18mo', interval='1d',
                 auto_adjust=True, group_by='ticker', multi_level_index=True,
                 progress=False, threads=False, timeout=25)
            for ticker in chunk:
                try:
                    closes = frame[ticker]['Close'].dropna()
                    series = [float(x) for x in closes.tolist() if math.isfinite(float(x)) and float(x)>0]
                    if len(series)<255:
                        errors.append(f'{ticker}: for få handelsdage ({len(series)})')
                        continue
                    date = closes.index[-1].date().isoformat()
                    if (datetime.now(timezone.utc).date()-datetime.fromisoformat(date).date()).days > 7:
                        errors.append(f'{ticker}: forældede kurser fra {date}')
                        continue
                    result[ticker]={'prices':series,'date':date,'currency':'Ikke angivet'}
                except (KeyError,IndexError,AttributeError,ValueError,TypeError) as exc:
                    errors.append(f'{ticker}: {type(exc).__name__}')
        except Exception as exc:
            errors.append(f'Fejl ved {chunk}: {type(exc).__name__}: {str(exc)[:120]}')
    if errors:
        print('Datakilde-advarsler: '+', '.join(errors[:16]),file=sys.stderr)
    if len(result)<5:
        raise RuntimeError(f'Kun {len(result)} brugbare aktier. Afbryder frem for at vise tvivlsomme signaler.')
    return result


def raw_momentum_6(p):
    return p[-22]/p[-127]-1


def raw_momentum_12(p):
    return p[-22]/p[-253]-1


def raw_low_volatility(p):
    returns=[math.log(p[i]/p[i-1]) for i in range(len(p)-126,len(p))]
    return -statistics.stdev(returns)*math.sqrt(252)


def raw_drawdown(p):
    return p[-1]/max(p[-126:])-1


FACTORS = {
    'momentum_6m':(raw_momentum_6, .40),
    'momentum_12m':(raw_momentum_12, .25),
    'low_volatility':(raw_low_volatility, .20),
    'distance_from_high':(raw_drawdown, .15),
}


def percentile_ranks(values):
    ordered=sorted(values.items(),key=lambda t:t[1])
    count=len(ordered)
    return {ticker:round(100*i/(count-1),2) if count>1 else 50.0
            for i,(ticker,_) in enumerate(ordered)}


def rank_universe(data):
    if len(data)<5:
        raise ValueError('Kræver mindst fem aktier')
    for ticker, info in data.items():
        p=info['prices']
        if len(p)<255 or not all(math.isfinite(x) and x>0 for x in p):
            raise ValueError(f'For få eller ugyldige kurser: {ticker}')
    # Faktormodulerne kan senere udskiftes uden at ændre agentkoordinationen.
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(lambda fn: {ticker:fn(info['prices']) for ticker,info in data.items()},fn):name
                 for name,(fn,_) in FACTORS.items()}
        outputs={futures[fut]:fut.result() for fut in as_completed(futures)}
    ranks={name:percentile_ranks(scores) for name,scores in outputs.items()}
    rows=[]
    for ticker,info in data.items():
        score=sum(weight*ranks[name][ticker] for name,(_,weight) in FACTORS.items())
        rows.append({'ticker':ticker,'date':info['date'],'price':round(info['prices'][-1],4),
            'score':round(score,2), 'priority':'UNDERSØG' if score>=75 else 'AFVENT',
            'factors':{name:round(outputs[name][ticker],5) for name in FACTORS}})
    return sorted(rows,key=lambda x:x['score'],reverse=True)


def call_ai(provider, rows):
    config={
        'kimi':('KIMI_API_KEY','KIMI_MODEL','https://api.moonshot.ai/v1/chat/completions',
            'Undersøg svagheder ved det datagrundlag, som kræves til fundamental analyse.'),
        'grok':('XAI_API_KEY','GROK_MODEL','https://api.x.ai/v1/chat/completions',
            'Vær kritisk: identificér risici og grunde til at prisdata kan være misvisende.'),
        'openai':('OPENAI_API_KEY','OPENAI_MODEL','https://api.openai.com/v1/chat/completions',
            'Vurder om rangering er robust og hvilke kontroller der mangler.'),
    }
    key_name,model_name,url,task=config[provider]
    key=os.getenv(key_name,'').strip()
    model=os.getenv(model_name,'').strip()
    if not key or not model:
        return {'agent':provider,'status':'ikke konfigureret','comment':'Kræver API-nøgle og modelnavn.'}
    body={'model':model,'messages':[
        {'role':'system','content':'Du er en kritisk dansk researchagent. Dette er kun forsinkede kursdata; du har IKKE regnskaber eller realtidsnyheder. Opfind ingen fakta. Giv max 4 korte observationer. Ingen handler.'},
        {'role':'user','content':task+'\nData (kan være ufuldstændige): '+json.dumps(rows[:8],ensure_ascii=False)}],
        'max_tokens':450}
    try:
        req=urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
           headers={'Content-Type':'application/json','Authorization':'Bearer '+key},method='POST')
        with urllib.request.urlopen(req,timeout=65) as resp:
            payload=json.load(resp)
        reply=payload['choices'][0]['message']['content']
        return {'agent':provider,'status':'ok','comment':str(reply)[:3000]}
    except (urllib.error.URLError,TimeoutError,ValueError,KeyError,IndexError) as exc:
        return {'agent':provider,'status':'fejl','comment':f'{type(exc).__name__}: {str(exc)[:160]}'}


def research_parallel(rows):
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(call_ai,provider,rows):provider for provider in ('kimi','grok','openai')}
        output=[fut.result() for fut in as_completed(futures)]
    return sorted(output,key=lambda x:x['agent'])


def render_report(ranked,agents,demo):
    timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    flag='**DEMO: FIKTIVE DATA**' if demo else '**Rigtige historiske kursdata (ikke realtid)**'
    lines=['# Multi-agent investeringsscanner',f'Kørsel: {timestamp}',flag,
      '', '**Ikke en køb/salg-anbefaling. Modellen er ikke backtestet; ingen handler udføres.**',
      '',f'Univers: {len(ranked)} aktier med tilstrækkelig kurshistorik. Ikke en fuld global screening.',
      '', '| Aktie | Seneste kurs* | Kursdato | Score / 100 | Status |',
      '|---|---:|---|---:|---|']
    for x in ranked[:20]:
        lines.append(f"| {x['ticker']} | {x['price']} | {x['date']} | {x['score']} | {x['priority']} |")
    lines+=['','*Kurs er i den enkelte børsnoterings valuta; sammenlign ikke kursbeløb direkte.*',
        '', '## AI-agenter (valgfri)', '']
    for a in agents:
        lines.extend([f"### {a['agent']} — {a['status']}",a['comment'],''])
    lines+=['## Hvad modellen ikke gør',
       'Ingen regnskabsanalyse, værdiansættelse, skatteberegning, optimal positionering eller valideret backtest.',
       'Faktorvægte er eksempelværdier, og scores er kun prioritering til videre research.',
       'Datakilden yfinance/Yahoo er uofficiel og kan være forsinket eller utilgængelig.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true',help='Test med helt fiktive kurser')
    args=parser.parse_args(argv)
    data=synthetic_prices() if args.demo else live_prices()
    ranked=rank_universe(data)
    agents=research_parallel(ranked)
    OUT.mkdir(exist_ok=True)
    report=render_report(ranked,agents,args.demo)
    (OUT/'rapport.md').write_text(report,encoding='utf-8')
    (OUT/'resultater.json').write_text(json.dumps({'demo':args.demo,'generated_utc':datetime.now(timezone.utc).isoformat(),
            'ranked':ranked,'agents':agents},ensure_ascii=False,indent=2),encoding='utf-8')
    summary_path=os.getenv('GITHUB_STEP_SUMMARY')
    if summary_path:
        with open(summary_path,'a',encoding='utf-8') as f:
            f.write(report[:50000])
    print(report[:10000])
    return ranked


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(f'BOT FEJLEDE: {type(exc).__name__}: {exc}',file=sys.stderr)
        sys.exit(1)
