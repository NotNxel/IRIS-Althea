'use client';
import {useEffect,useState,useRef} from 'react';
import Link from 'next/link';
import {X,ExternalLink} from 'lucide-react';
import {api,decimal} from './api';
export default function Candidate({id,compound,onClose}:{id:string,compound:string,onClose?:()=>void}){
 const drawerRef=useRef<HTMLDivElement>(null);
 const closeRef=useRef(onClose);closeRef.current=onClose;
 const[data,setData]=useState<any>(null);
 const[loadedKey,setLoadedKey]=useState('');
 const[error,setError]=useState('');
 const[term,setTerm]=useState('');
 const[retry,setRetry]=useState(0);
 const requestKey=JSON.stringify([id,compound]);
 useEffect(()=>{
  const controller=new AbortController();
  setData(null);setLoadedKey('');setError('');setTerm('');
  api(`/analyses/${id}/candidates/${encodeURIComponent(compound)}`,{signal:controller.signal})
   .then(r=>{if(!controller.signal.aborted){setData(r);setLoadedKey(requestKey);setTerm(r.context_details[0]?.terms[0]||'')}})
   .catch(e=>{if(!controller.signal.aborted)setError(e.message)});
  return()=>controller.abort();
 },[id,compound,requestKey,retry]);
 const isDrawer=Boolean(onClose);
 useEffect(()=>{
  if(!isDrawer)return;
  const previous=document.activeElement as HTMLElement|null;
  const overflow=document.body.style.overflow;document.body.style.overflow='hidden';
  drawerRef.current?.focus();
  const handler=(e:KeyboardEvent)=>{
   if(e.key==='Escape'){e.preventDefault();closeRef.current?.()}
   if(e.key==='Tab'){
    const elements=Array.from(drawerRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]),a[href],select:not([disabled]),input:not([disabled]),[tabindex="0"]')||[]).filter(element=>element.getClientRects().length>0);
    if(!elements.length){e.preventDefault();drawerRef.current?.focus();return}
    const first=elements[0],last=elements[elements.length-1];
    if(e.shiftKey&&(document.activeElement===first||document.activeElement===drawerRef.current)){e.preventDefault();last.focus()}
    else if(!e.shiftKey&&(document.activeElement===last||document.activeElement===drawerRef.current)){e.preventDefault();first.focus()}
   }
  };
  window.addEventListener('keydown',handler);
  return()=>{window.removeEventListener('keydown',handler);document.body.style.overflow=overflow;if(previous?.isConnected)previous.focus()}
 },[isDrawer]);
 const evidence=loadedKey===requestKey?data:null;
 const content=<>{onClose&&<button className="close" onClick={onClose} aria-label="Close candidate"><X size={18}/></button>}<span className="eyebrow">COMPUTATIONAL CANDIDATE</span><h2>{compound}</h2>{error&&<div className="notice error" role="alert">{error} <button className="secondary" onClick={()=>setRetry(value=>value+1)}>Try again</button></div>}{!evidence&&!error&&<p className="muted">Loading calculated evidence…</p>}{evidence&&<><p className="small">Rank #{evidence.rank} · median context score</p><div className="stats" style={{gridTemplateColumns:'repeat(3,1fr)'}}>{[['Reversal score',decimal(evidence.score)],['Supporting contexts',`${evidence.supporting_contexts}/${evidence.contexts}`],['Consistency',`${Math.round(evidence.consistency*100)}%`]].map(([label,value])=><div className="stat" key={label}><div className="label">{label}</div><div className="value" style={{fontSize:23}}>{value}</div></div>)}</div><div className="notice">{evidence.interpretation} Computational prioritization does not establish therapeutic efficacy.</div><h3>Perturbation contexts <span className="kind">/ observed metadata + calculated scores</span></h3><p className="small">{evidence.signatures} paired directional signatures; {evidence.supporting_signatures} in reversing contexts. Dose units and replicate counts are not available in this source.</p><div className="table-wrap" style={{maxHeight:310,overflow:'auto'}}><table><thead><tr><th>Cell line</th><th>Time</th><th>Dose label</th><th>Score</th><th>Signatures</th></tr></thead><tbody>{evidence.context_details.map((c:any,i:number)=><tr key={i}><td>{c.cell_line}</td><td>{c.time}</td><td>{c.dose}</td><td className="score">{decimal(c.score)}</td><td>{c.signatures}</td></tr>)}</tbody></table></div><h3>Gene-level direction comparison</h3><label className="small">Select a source perturbation signature<select aria-label="Perturbation signature" className="search-small" style={{display:'block',width:'100%',margin:'10px 0 20px'}} value={term} onChange={e=>setTerm(e.target.value)}>{evidence.context_details.flatMap((c:any)=>c.terms).map((t:string)=><option key={t}>{t}</option>)}</select></label><div className="evidence muted"><span>GENE</span><span>CANCER log₂FC</span><span>DRUG DIRECTION</span><span>CONTRIBUTION</span></div><div style={{maxHeight:370,overflow:'auto'}}>{evidence.gene_evidence.filter((g:any)=>g.term===term).map((g:any)=><div className="evidence" key={g.gene}><span>{g.gene}</span><span className={g.cancer_log2fc>0?'up':'down'}>{g.cancer_log2fc>0?'↑':'↓'} {decimal(g.cancer_log2fc,2)}</span><span className={g.drug_direction==='up'?'direction-cell up':'direction-cell down'}>{g.drug_direction==='up'?'↑ Increased':'↓ Decreased'}</span><span className="contribution-cell" style={{color:g.opposing?'var(--accent)':'var(--up)'}}>{decimal(g.contribution,5)}</span></div>)}</div><p className="small">Drug magnitudes are unavailable in the GMT export. Arrows encode direction only. Negative contributions oppose the cancer signature.</p><h3>Exact score calculation</h3><p className="small">S = Σ(log₂FC × drug direction) / Σ|log₂FC|. The denominator includes signature genes in the tested LINCS gene universe. Drug direction is +1 (up), −1 (down), or 0 (absent). Scores are averaged within identical context labels, then the median across contexts is used for ranking.</p><p className="small">Exploratory gene-label permutation p: <b>{decimal(evidence.permutation_p,4)}</b> · BH-adjusted: <b>{decimal(evidence.permutation_fdr,4)}</b>. These values are not clinical or independent biological validation.</p>{onClose&&<Link className="secondary" href={`/candidate/${id}?compound=${encodeURIComponent(compound)}`}>Open evidence page <ExternalLink size={13}/></Link>}</>}</>;return onClose?<div className="modal-backdrop" onClick={onClose}><div ref={drawerRef} tabIndex={-1} role="dialog" aria-modal="true" aria-label={compound+' evidence'} className="drawer" onClick={e=>e.stopPropagation()}>{content}</div></div>:<div className="panel">{content}</div>}
