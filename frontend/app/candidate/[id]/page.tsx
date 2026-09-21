import Candidate from '@/components/candidate';
import {Footer} from '@/components/shell';
import Link from 'next/link';
export default async function Page({params,searchParams}:{params:Promise<{id:string}>,searchParams:Promise<{compound?:string}>}){const{id}=await params;const{compound}=await searchParams;return <main><div className="page-head"><Link className="breadcrumb" href={'/analysis/'+id}>← Back to analysis</Link></div>{compound?<Candidate id={id} compound={compound}/>:<div className="notice">Select a compound from an analysis.</div>}<div style={{height:35}}/><Footer/></main>}
