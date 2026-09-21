import type {Metadata} from 'next';
import './globals.css';
import {Header} from '@/components/shell';
export const metadata:Metadata={title:'IRIS — Molecular Reversal Research',description:'A reproducible research workspace for transcriptomic drug reversal using public TCGA and LINCS data.'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en" data-scroll-behavior="smooth"><body><Header/>{children}</body></html>}
