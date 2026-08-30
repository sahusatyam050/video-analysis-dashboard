import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ReactECharts from "echarts-for-react";

export function TransactionsTab({ metrics }: { metrics: any }) {
  if (!metrics) return null;

  const buildFunnel = () => {
    const f_total = metrics.segmentCount;
    const f_betting = metrics.bettingNonZero.length;
    const f_banking = metrics.bankingSegs.length;
    const f_crypto = metrics.cryptoSegs.length;
    const f_qr = metrics.qrSegments.length;
    const f_txhigh = metrics.txLikelySegs.length;
    const f_txexec = metrics.txExecSegs.length;

    const funnelData = [
      { name: "Total Segments", value: f_total, pct: 100.0 },
      { name: "Betting Segments", value: f_betting, pct: (f_betting/f_total*100).toFixed(1) },
      { name: "Banking Segments", value: f_banking, pct: (f_banking/f_total*100).toFixed(1) },
      { name: "Crypto Segments", value: f_crypto, pct: (f_crypto/f_total*100).toFixed(1) },
      { name: "QR Events", value: f_qr, pct: (f_qr/f_total*100).toFixed(1) },
      { name: "High Tx Segments", value: f_txhigh, pct: (f_txhigh/f_total*100).toFixed(1) },
      { name: "Successful Transactions", value: f_txexec, pct: (f_txexec/f_total*100).toFixed(1) },
    ];

    return {
      tooltip: {
        trigger: 'item',
        formatter: (p: any) => `<b>${p.name}</b><br/>Count: ${p.value}<br/>Share of total: ${(p.value/f_total*100).toFixed(1)}%`
      },
      color: ["#475569","#D97706","#0891B2","#7C3AED","#F59E0B","#DC2626","#059669"],
      series: [{
        type: 'funnel',
        left: '15%', right: '20%', top: 20, bottom: 10, width: '65%',
        min: 0, max: f_total, minSize: '4%', maxSize: '100%',
        sort: 'none', gap: 3,
        label: { show: true, position: 'right', formatter: (p: any) => `${p.value} (${(p.value/f_total*100).toFixed(1)}%)` },
        itemStyle: { borderWidth: 0, opacity: 0.9 },
        emphasis: { label: { fontWeight: 'bold' }, itemStyle: { opacity: 1 } },
        data: funnelData.map(d => ({ name: d.name, value: d.value }))
      }]
    };
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Transaction Funnel</CardTitle>
          <p className="text-xs text-slate-500">Count-based pipeline: from all segments down to successful transactions.</p>
        </CardHeader>
        <CardContent>
          <ReactECharts option={buildFunnel()} style={{ height: '340px', width: '100%' }} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader><CardTitle className="text-sm">QR / Payment Flow Events</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {metrics.qrSegments.length > 0 ? metrics.qrSegments.map((v: any, i: number) => (
              <div key={i} className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm">
                <div className="flex justify-between items-center mb-1">
                  <span className="font-bold text-amber-900">Seg {v.segment_index}</span>
                  <span className="text-xs bg-amber-200 text-amber-900 px-2 py-0.5 rounded font-bold">QR DETECTED</span>
                </div>
                <div className="text-xs text-amber-800 font-mono mb-1">{v.start_time.toFixed(2)}s - {v.end_time.toFixed(2)}s</div>
                <div className="text-[10px] text-amber-700">Tx Likely: {v.transaction_likely}% · Banking: {v.banking_context}% · Crypto: {v.crypto_context}%</div>
              </div>
            )) : <div className="text-slate-500 italic text-sm">No QR codes detected.</div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-sm">Failed / Unconfirmed Transaction Attempts</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {metrics.failedTxRecords.length > 0 ? metrics.failedTxRecords.map((t: any, i: number) => {
              const score = t.evidence?.final_score || t.betting_purpose_score || 0;
              return (
                <div key={i} className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm">
                  <div className="font-bold text-red-900 mb-1">✗ {t.transaction_time} — Attempt Not Confirmed</div>
                  <div className="text-[10px] text-red-700">Betting Score: {score.toFixed(1)} · Confidence: {t.confidence.toFixed(0)}%</div>
                  <div className="text-[10px] text-red-700 italic mt-1">No execution confirmation.</div>
                </div>
              );
            }) : <div className="text-slate-500 italic text-sm">No failed transactions detected.</div>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
