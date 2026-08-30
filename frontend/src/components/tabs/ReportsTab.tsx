import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, Printer, AlertTriangle, CheckCircle, ShieldAlert, FileText, ArrowRight, Table } from "lucide-react";
import { cn } from "@/lib/utils";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function ReportsTab({ summaryData }: { summaryData: any }) {
  if (!summaryData) return null;

  const downloadJson = (data: any, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  // 1. Calculate Verdict
  const hasBetting = summaryData.betting_segment_scores?.some((s: number) => s > 50);
  const hasTransactions = summaryData.betting_transaction_attribution?.length > 0 || summaryData.crypto_betting_attribution?.length > 0;
  const qrSegments = summaryData.segment_verdicts?.filter((s: any) => s.qr_detected) || [];
  
  let verdictStatus = "PASS";
  let verdictTitle = "LOW RISK - No Major Violations Detected";
  let verdictColor = "bg-[#D1FAE5] text-[#064E3B] border-[#A7F3D0]";
  let VerdictIcon = CheckCircle;

  if (hasBetting && hasTransactions) {
    verdictStatus = "FAIL";
    verdictTitle = "CRITICAL RISK - Illegal Betting Application with Active Transactions Detected";
    verdictColor = "bg-[#FEE2E2] text-[#7F1D1D] border-[#FECACA]";
    VerdictIcon = ShieldAlert;
  } else if (hasBetting || hasTransactions || qrSegments.length > 0) {
    verdictStatus = "WARNING";
    verdictTitle = "MEDIUM RISK - Suspicious Keywords or Payment Mechanisms Found";
    verdictColor = "bg-[#FFF7ED] text-[#7C2D12] border-[#FED7AA]";
    VerdictIcon = AlertTriangle;
  }

  // 2. Key Evidence Table
  const keyEvidence = summaryData.segment_verdicts?.filter((s: any) => 
    s.betting_score > 50 || s.transaction_likely > 50 || s.qr_detected || s.transaction_executed > 0
  ).sort((a: any, b: any) => b.betting_score - a.betting_score).slice(0, 10) || [];

  return (
    <div className="space-y-6 font-['Inter'] print:bg-white print:p-8" id="report-content">
      
      {/* Action Bar (Hidden in Print) */}
      <div className="flex justify-end gap-3 print:hidden">
        <Button onClick={handlePrint} className="bg-slate-800 text-white hover:bg-slate-700 h-9 px-4 rounded-md text-sm font-semibold flex gap-2">
          <Printer size={16} /> Print Official Audit Report (PDF)
        </Button>
      </div>

      {/* 1. Final Verdict Banner */}
      <div className={cn("p-6 rounded-lg border-2 flex items-start gap-4", verdictColor)}>
        <VerdictIcon className="w-8 h-8 shrink-0 mt-1" />
        <div>
          <div className="text-xs font-bold uppercase tracking-widest opacity-80 mb-1">Final Compliance Verdict: {verdictStatus}</div>
          <h2 className="text-xl font-black">{verdictTitle}</h2>
          <div className="mt-3 text-sm font-medium opacity-90">
            Analysis analyzed {summaryData.segment_verdicts?.length || 0} video segments. 
            Found {qrSegments.length} QR codes, {summaryData.betting_transaction_attribution?.length || 0} fiat transaction attempts, and {summaryData.crypto_betting_attribution?.length || 0} crypto transaction attempts.
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 2. Key Evidence Table */}
        <div className="lg:col-span-2">
          <div className="section-header !mt-0">Key Evidence Findings</div>
          <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
            {keyEvidence.length > 0 ? (
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                  <tr>
                    <th className="p-3">Time</th>
                    <th className="p-3">Violation Signal</th>
                    <th className="p-3">Score</th>
                    <th className="p-3">Extracted OCR Proof</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-['JetBrains_Mono']">
                  {keyEvidence.map((seg: any, idx: number) => {
                    let signal = "Suspicious Activity";
                    if (seg.transaction_executed > 50) signal = "Transaction Executed";
                    else if (seg.qr_detected) signal = "QR Payment Code";
                    else if (seg.transaction_likely > 50) signal = "Transaction Context";
                    else if (seg.betting_score > 50) signal = "Betting UI";
                    
                    const score = Math.max(seg.transaction_executed, seg.transaction_likely, seg.betting_score);
                    
                    return (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="p-3 text-slate-500 whitespace-nowrap">{seg.start_time.toFixed(1)}s - {seg.end_time.toFixed(1)}s</td>
                        <td className="p-3 font-semibold text-[#1E293B]">{signal}</td>
                        <td className="p-3 text-[#DC2626] font-bold">{score.toFixed(0)}%</td>
                        <td className="p-3 text-xs text-slate-500 max-w-[300px] truncate" title={seg.ocr_text}>{seg.ocr_text || "No readable text"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div className="p-6 text-center text-slate-500 font-['JetBrains_Mono']">No significant violations found in segments.</div>
            )}
          </div>
        </div>

        {/* 3. Transaction Chains */}
        <div className="lg:col-span-2">
          <div className="section-header !mt-0">Attributed Transaction Flows</div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-sm font-bold flex items-center gap-2 text-[#64748B]"><FileText size={16}/> Fiat Payment Flow</CardTitle></CardHeader>
              <CardContent>
                {summaryData.betting_transaction_attribution?.length > 0 ? (
                  <div className="space-y-4">
                    {summaryData.betting_transaction_attribution.map((tx: any, i: number) => (
                      <div key={i} className="flex items-center gap-2 p-3 bg-slate-50 rounded border border-slate-200">
                        <div className="text-center p-2 bg-white rounded border border-slate-200 shadow-sm shrink-0">
                          <div className="text-[10px] font-bold text-slate-400">BETTING UI</div>
                          <div className="font-['JetBrains_Mono'] text-xs font-bold text-[#D97706]">Detected</div>
                        </div>
                        <ArrowRight size={14} className="text-slate-400 shrink-0" />
                        <div className="text-center p-2 bg-white rounded border border-slate-200 shadow-sm shrink-0">
                          <div className="text-[10px] font-bold text-slate-400">QR / INTENT</div>
                          <div className="font-['JetBrains_Mono'] text-xs font-bold text-[#0891B2]">Scanned</div>
                        </div>
                        <ArrowRight size={14} className="text-slate-400 shrink-0" />
                        <div className="text-center p-2 bg-[#FEE2E2] rounded border border-[#FECACA] shadow-sm flex-1">
                          <div className="text-[10px] font-bold text-[#7F1D1D]">TRANSACTION ATTEMPT</div>
                          <div className="font-['JetBrains_Mono'] text-xs font-bold text-[#991B1B]">{tx.transaction_time}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <div className="text-slate-400 italic text-sm font-['JetBrains_Mono']">No fiat transactions attributed.</div>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3"><CardTitle className="text-sm font-bold flex items-center gap-2 text-[#64748B]"><FileText size={16}/> Crypto Flow</CardTitle></CardHeader>
              <CardContent>
                {summaryData.crypto_betting_attribution?.length > 0 ? (
                  <div className="space-y-4">
                    {summaryData.crypto_betting_attribution.map((tx: any, i: number) => (
                      <div key={i} className="flex items-center gap-2 p-3 bg-slate-50 rounded border border-slate-200">
                        <div className="text-center p-2 bg-white rounded border border-slate-200 shadow-sm shrink-0">
                          <div className="text-[10px] font-bold text-slate-400">CRYPTO CONTEXT</div>
                          <div className="font-['JetBrains_Mono'] text-xs font-bold text-[#7C3AED]">Score: {tx.crypto_support?.toFixed(0)}</div>
                        </div>
                        <ArrowRight size={14} className="text-slate-400 shrink-0" />
                        <div className={`text-center p-2 rounded border shadow-sm flex-1 ${tx.decision === 'LINKED' ? 'bg-[#FEE2E2] border-[#FECACA]' : 'bg-amber-50 border-amber-200'}`}>
                          <div className={`text-[10px] font-bold ${tx.decision === 'LINKED' ? 'text-[#7F1D1D]' : 'text-amber-800'}`}>VERDICT: {tx.decision}</div>
                          <div className={`font-['JetBrains_Mono'] text-xs font-bold ${tx.decision === 'LINKED' ? 'text-[#991B1B]' : 'text-amber-700'}`}>Conf: {tx.confidence}%</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <div className="text-slate-400 italic text-sm font-['JetBrains_Mono']">No crypto transactions attributed.</div>}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Raw Data Deep Dive UIs (Hidden in Print) */}
      <div className="print:hidden mt-8">
        <div className="section-header">Raw Data Audit Logs</div>
        <Tabs defaultValue="segments" className="w-full">
          <TabsList className="grid grid-cols-4 bg-slate-100">
            <TabsTrigger value="segments" className="text-xs font-bold data-[state=active]:bg-white">Segment Ledger</TabsTrigger>
            <TabsTrigger value="fiat" className="text-xs font-bold data-[state=active]:bg-white">Fiat Audit</TabsTrigger>
            <TabsTrigger value="crypto" className="text-xs font-bold data-[state=active]:bg-white">Crypto Audit</TabsTrigger>
            <TabsTrigger value="downloads" className="text-xs font-bold data-[state=active]:bg-white">JSON Downloads</TabsTrigger>
          </TabsList>
          
          <TabsContent value="segments" className="mt-4">
            <div className="border border-slate-200 rounded-lg overflow-x-auto bg-white max-h-[500px] overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold sticky top-0 z-10 shadow-sm">
                  <tr>
                    <th className="p-3 whitespace-nowrap">Seg # (Time)</th>
                    <th className="p-3">OCR Snippet</th>
                    <th className="p-3 text-center">Bank %</th>
                    <th className="p-3 text-center">Crypto %</th>
                    <th className="p-3 text-center">Tx Likely %</th>
                    <th className="p-3 text-center">Tx Exec %</th>
                    <th className="p-3 text-center">Bet Score</th>
                    <th className="p-3 text-center">QR?</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-['JetBrains_Mono']">
                  {summaryData.segment_verdicts?.map((seg: any, idx: number) => {
                    const bScore = summaryData.betting_segment_scores?.[idx] || 0;
                    return (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="p-3 text-slate-500 whitespace-nowrap">
                          <span className="font-bold text-slate-700">#{seg.segment_index}</span> <br/>
                          {seg.start_time.toFixed(1)}s - {seg.end_time.toFixed(1)}s
                        </td>
                        <td className="p-3 text-slate-500 max-w-[200px] truncate" title={seg.ocr_text}>{seg.ocr_text || "-"}</td>
                        <td className={`p-3 text-center ${seg.banking_context > 50 ? 'text-[#0891B2] font-bold bg-cyan-50' : 'text-slate-400'}`}>{seg.banking_context || 0}%</td>
                        <td className={`p-3 text-center ${seg.crypto_context > 50 ? 'text-[#7C3AED] font-bold bg-purple-50' : 'text-slate-400'}`}>{seg.crypto_context || 0}%</td>
                        <td className={`p-3 text-center ${seg.transaction_likely > 50 ? 'text-[#DC2626] font-bold bg-red-50' : 'text-slate-400'}`}>{seg.transaction_likely || 0}%</td>
                        <td className={`p-3 text-center ${seg.transaction_executed > 50 ? 'text-[#059669] font-bold bg-emerald-50' : 'text-slate-400'}`}>{seg.transaction_executed || 0}%</td>
                        <td className={`p-3 text-center ${bScore > 50 ? 'text-[#D97706] font-bold bg-amber-50' : 'text-slate-400'}`}>{bScore}%</td>
                        <td className="p-3 text-center">{seg.qr_detected ? <span className="bg-[#FEF3C7] text-[#92400E] px-2 py-1 rounded text-[10px] font-bold">YES</span> : <span className="text-slate-300">-</span>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="fiat" className="mt-4">
             <div className="border border-slate-200 rounded-lg overflow-x-auto bg-white max-h-[500px] overflow-y-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold sticky top-0 z-10 shadow-sm">
                  <tr>
                    <th className="p-3">Time Window</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Linked to Betting?</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-['JetBrains_Mono']">
                  {summaryData.betting_transaction_attribution?.length > 0 ? (
                    summaryData.betting_transaction_attribution.map((tx: any, idx: number) => (
                      <tr key={idx} className={tx.transaction_used_for_betting ? 'bg-red-50' : ''}>
                        <td className="p-3 text-slate-700 font-bold">{tx.transaction_time}</td>
                        <td className="p-3 text-slate-500">{tx.transaction_used_for_betting ? 'Executed' : 'Attempted'}</td>
                        <td className="p-3">
                          {tx.transaction_used_for_betting 
                            ? <span className="bg-[#FEE2E2] text-[#7F1D1D] px-2 py-1 rounded text-xs font-bold">YES - VIOLATION</span> 
                            : <span className="text-amber-600 font-bold">Attempted / Unknown</span>}
                        </td>
                      </tr>
                    ))
                  ) : <tr><td colSpan={3} className="p-6 text-center text-slate-500 italic">No fiat transactions recorded.</td></tr>}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="crypto" className="mt-4">
             <div className="border border-slate-200 rounded-lg overflow-x-auto bg-white max-h-[500px] overflow-y-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold sticky top-0 z-10 shadow-sm">
                  <tr>
                    <th className="p-3">Segment Index</th>
                    <th className="p-3">Crypto Support</th>
                    <th className="p-3">Betting Purpose</th>
                    <th className="p-3">AI Decision</th>
                    <th className="p-3">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-['JetBrains_Mono']">
                  {summaryData.crypto_betting_attribution?.length > 0 ? (
                    summaryData.crypto_betting_attribution.map((tx: any, idx: number) => {
                      const isLinked = tx.decision === 'LINKED';
                      return (
                        <tr key={idx} className={isLinked ? 'bg-red-50' : ''}>
                          <td className="p-3 text-slate-700 font-bold">#{tx.segment_index}</td>
                          <td className="p-3 text-[#7C3AED] font-bold">{tx.crypto_support?.toFixed(0)}%</td>
                          <td className="p-3 text-[#D97706] font-bold">{tx.betting_purpose?.toFixed(0)}%</td>
                          <td className="p-3">
                            <span className={`px-2 py-1 rounded text-xs font-bold ${isLinked ? 'bg-[#FEE2E2] text-[#7F1D1D]' : 'bg-amber-100 text-amber-800'}`}>
                              {tx.decision}
                            </span>
                          </td>
                          <td className="p-3 text-slate-500 font-bold">{tx.confidence}%</td>
                        </tr>
                      );
                    })
                  ) : <tr><td colSpan={5} className="p-6 text-center text-slate-500 italic">No crypto transactions recorded.</td></tr>}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="downloads" className="mt-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-50 p-6 rounded-lg border border-slate-200">
              <Button variant="outline" className="w-full text-xs flex gap-2 h-9 font-['JetBrains_Mono']" onClick={() => downloadJson(summaryData.segment_verdicts, 'segment_verdicts.json')}>
                <Download size={14} /> segment_verdicts.json
              </Button>
              <Button variant="outline" className="w-full text-xs flex gap-2 h-9 font-['JetBrains_Mono']" onClick={() => downloadJson(summaryData.betting_segment_scores, 'betting_segment_scores.json')}>
                <Download size={14} /> betting_scores.json
              </Button>
              <Button variant="outline" className="w-full text-xs flex gap-2 h-9 font-['JetBrains_Mono']" onClick={() => downloadJson(summaryData.betting_transaction_attribution, 'betting_tx_attr.json')}>
                <Download size={14} /> betting_tx_attr.json
              </Button>
              <Button variant="outline" className="w-full text-xs flex gap-2 h-9 font-['JetBrains_Mono']" onClick={() => downloadJson(summaryData.crypto_betting_attribution, 'crypto_tx_attr.json')}>
                <Download size={14} /> crypto_tx_attr.json
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
