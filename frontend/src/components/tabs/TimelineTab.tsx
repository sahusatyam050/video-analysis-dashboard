import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import ReactECharts from "echarts-for-react";
import { PlayCircle, Wallet, Bitcoin, AlertTriangle, QrCode, CheckCircle2, ShieldAlert } from "lucide-react";

export function TimelineTab({ metrics, summaryData }: { metrics: any, summaryData: any }) {
  if (!metrics || !summaryData) return null;

  const buildSankeyData = () => {
    const n_betting = metrics.bettingNonZero.length;
    const n_banking = metrics.bankingSegs.length;
    const n_qr = metrics.qrSegments.length;
    const n_tx_att = metrics.nTxAtt;
    const n_tx_fail = metrics.failedTxRecords.length;
    const n_tx_succ = metrics.nTxExec;
    const n_no_act = Math.max(metrics.segmentCount - n_betting, 1);
    const n_qr_only = Math.max(n_qr - n_tx_fail, 0);

    const nodes = [
      { name: "Video" },
      { name: "Betting UI" },
      { name: "No Betting Activity" },
      { name: "Wallet / Banking" },
      { name: "QR Payment Code" },
      { name: "Transaction Attempt" },
      { name: "Transaction Failed" },
      { name: "QR — No Transaction" }
    ];

    const links = [];
    if (n_betting > 0) links.push({ source: "Video", target: "Betting UI", value: n_betting });
    if (n_no_act > 0) links.push({ source: "Video", target: "No Betting Activity", value: n_no_act });
    if (n_banking > 0) links.push({ source: "Betting UI", target: "Wallet / Banking", value: n_banking });
    if (n_qr > 0) links.push({ source: "Wallet / Banking", target: "QR Payment Code", value: n_qr });
    if (n_tx_att > 0) links.push({ source: "QR Payment Code", target: "Transaction Attempt", value: n_tx_att });
    if (n_tx_fail > 0) links.push({ source: "Transaction Attempt", target: "Transaction Failed", value: n_tx_fail });
    if (n_qr_only > 0) links.push({ source: "QR Payment Code", target: "QR — No Transaction", value: n_qr_only });

    return {
      tooltip: {
        trigger: 'item',
        triggerOn: 'mousemove',
        formatter: (params: any) => `<b>${params.name}</b><br/>${params.value || ''} segments`
      },
      series: [{
        type: 'sankey',
        layout: 'none',
        emphasis: { focus: 'adjacency' },
        nodeAlign: 'left',
        nodeGap: 16,
        nodeWidth: 24,
        left: '2%', right: '10%', top: '6%', bottom: '6%',
        data: nodes,
        links: links,
        lineStyle: { color: 'source', opacity: 0.22, curveness: 0.5 },
        label: { fontSize: 12, fontWeight: 600, color: '#1E293B' },
        color: ['#475569','#D97706','#CBD5E1','#0891B2','#F59E0B','#DC2626','#991B1B','#94A3B8']
      }]
    };
  };

  // Build the chronological event feed
  const buildTimelineEvents = () => {
    const events: any[] = [];
    const verdicts = summaryData.segment_verdicts || [];
    const betScores = summaryData.betting_segment_scores || [];
    const betTxs = summaryData.betting_transaction_attribution || [];

    verdicts.forEach((seg: any, idx: number) => {
      const bScore = betScores[idx] || 0;
      
      // Determine if there is a significant event here
      let isSignificant = false;
      let title = "Normal Activity";
      let description = "No major forensic signals detected.";
      let color = "bg-slate-200";
      let textColor = "text-slate-500";
      let Icon = PlayCircle;

      if ((seg.transaction_executed || 0) > 50) {
        title = "Transaction Executed";
        description = "A confirmed payment or transaction occurred on screen.";
        color = "bg-emerald-500";
        textColor = "text-emerald-700";
        Icon = CheckCircle2;
        isSignificant = true;
      } else if (seg.qr_detected) {
        title = "QR / Payment Scan Detected";
        description = "A QR code or explicit payment mechanism was found.";
        color = "bg-[#D97706]";
        textColor = "text-[#D97706]";
        Icon = QrCode;
        isSignificant = true;
      } else if ((seg.transaction_likely || 0) > 50) {
        title = "High Transaction Likelihood";
        description = `Transaction context score is very high (${seg.transaction_likely}%).`;
        color = "bg-red-500";
        textColor = "text-red-700";
        Icon = ShieldAlert;
        isSignificant = true;
      } else if (bScore > 50) {
        title = "Betting UI Detected";
        description = `Betting application features found (Score: ${bScore}%).`;
        color = "bg-amber-500";
        textColor = "text-amber-700";
        Icon = AlertTriangle;
        isSignificant = true;
      } else if ((seg.banking_context || 0) > 40) {
        title = "Wallet / Banking App Opened";
        description = `Financial application context detected (Score: ${seg.banking_context}%).`;
        color = "bg-cyan-500";
        textColor = "text-cyan-700";
        Icon = Wallet;
        isSignificant = true;
      } else if ((seg.crypto_context || 0) > 40) {
        title = "Crypto Application Context";
        description = `Cryptocurrency interface detected (Score: ${seg.crypto_context}%).`;
        color = "bg-purple-500";
        textColor = "text-purple-700";
        Icon = Bitcoin;
        isSignificant = true;
      }

      // Check if a failed tx happened here
      const failedTx = betTxs.find((tx: any) => tx.transaction_time && tx.transaction_time.includes(seg.start_time.toFixed(1)));
      if (failedTx && !failedTx.transaction_used_for_betting) {
        title = "Failed Transaction Attempt";
        description = "A transaction was initiated but did not complete successfully.";
        color = "bg-red-800";
        textColor = "text-red-900";
        Icon = ShieldAlert;
        isSignificant = true;
      }

      if (isSignificant || idx === 0 || idx === verdicts.length - 1) {
        if (idx === 0 && !isSignificant) {
          title = "Video Analysis Started";
          description = "Beginning chronological scan.";
        }
        if (idx === verdicts.length - 1 && !isSignificant) {
          title = "Analysis Complete";
          description = "End of video feed.";
          color = "bg-slate-400";
          textColor = "text-slate-600";
        }

        events.push({
          time: `${seg.start_time.toFixed(1)}s - ${seg.end_time.toFixed(1)}s`,
          title,
          description,
          color,
          textColor,
          Icon,
          ocr: seg.ocr_text || null
        });
      }
    });
    return events;
  };

  const timelineEvents = buildTimelineEvents();

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Sankey — Inference Story</CardTitle>
          <p className="text-xs text-slate-500">End-to-end narrative from raw content to transaction outcome. Node widths = segment counts from your data.</p>
        </CardHeader>
        <CardContent>
          <ReactECharts option={buildSankeyData()} style={{ height: '400px', width: '100%' }} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Chronological Event Feed</CardTitle>
          <p className="text-xs text-slate-500">A forensic step-by-step reconstruction of the video's activity timeline.</p>
        </CardHeader>
        <CardContent>
          <div className="relative pl-6 border-l-2 border-slate-200 space-y-8 ml-4 mt-4 font-['Inter']">
            {timelineEvents.map((evt, idx) => (
              <div key={idx} className="relative">
                {/* Timeline Dot */}
                <div className={`absolute -left-[35px] w-6 h-6 rounded-full border-4 border-white ${evt.color} shadow-sm flex items-center justify-center`} />
                
                <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <evt.Icon className={`w-4 h-4 ${evt.textColor}`} />
                      <h4 className={`text-sm font-bold ${evt.textColor}`}>{evt.title}</h4>
                    </div>
                    <span className="font-['JetBrains_Mono'] text-xs font-bold text-slate-400 bg-slate-50 px-2 py-1 rounded">
                      {evt.time}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mb-2">{evt.description}</p>
                  
                  {evt.ocr && (
                    <div className="mt-2 bg-slate-50 border border-slate-100 p-2 rounded text-xs font-['JetBrains_Mono'] text-slate-500 line-clamp-2" title={evt.ocr}>
                      <span className="font-bold text-slate-400 mr-2">OCR:</span>{evt.ocr}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
