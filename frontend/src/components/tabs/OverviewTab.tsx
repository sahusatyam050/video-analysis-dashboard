import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import ReactECharts from "echarts-for-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Film, QrCode, Building, Bitcoin, Target, XOctagon, CheckCircle2, ShieldAlert, Timer, Activity } from "lucide-react";

export function OverviewTab({ metrics, summaryData }: { metrics: any, summaryData: any }) {
  if (!metrics) return null;

  const buildGanttData = () => {
    const lanes = [
      { name: "Crypto Context", data: metrics.cryptoSegs, color: "#7C3AED", laneIdx: 0 },
      { name: "Banking Context", data: metrics.bankingSegs, color: "#0891B2", laneIdx: 1 },
      { name: "Failed Transaction", data: metrics.failedTxRecords.map((t: any) => {
          const match = t.transaction_time.match(/([\d.]+)[–\-]([\d.]+)/);
          if (match) return { start_time: parseFloat(match[1]), end_time: parseFloat(match[2]) };
          return { start_time: 0, end_time: 0 };
      }), color: "#991B1B", laneIdx: 2 },
      { name: "High Tx Likelihood", data: metrics.txLikelySegs, color: "#DC2626", laneIdx: 3 },
      { name: "QR / Payment", data: metrics.qrSegments, color: "#F59E0B", laneIdx: 4 },
      { name: "Betting UI", data: metrics.bettingNonZero.map((s: any, i: number) => metrics.verdicts[i] || {start_time: 0, end_time: 0}), color: "#D97706", laneIdx: 5 },
    ];

    const allItems: any[] = [];
    lanes.forEach(lane => {
      lane.data.forEach((seg: any) => {
        if (!seg.end_time) return; // skip invalid
        allItems.push({
          name: lane.name,
          value: [
            lane.laneIdx, 
            seg.start_time, 
            seg.end_time, 
            `${lane.name}\nStart: ${seg.start_time.toFixed(2)}s | End: ${seg.end_time.toFixed(2)}s`
          ],
          itemStyle: { color: lane.color }
        });
      });
    });

    return {
      tooltip: {
        formatter: (params: any) => params.value[3].replace(/\n/g, '<br/>')
      },
      grid: { left: 140, right: 20, top: 10, bottom: 30 },
      xAxis: { type: 'value', min: 0, max: metrics.totalDuration },
      yAxis: { 
        data: ["Crypto Context", "Banking Context", "Failed Transaction", "High Tx Likelihood", "QR / Payment", "Betting UI"],
        axisLine: { show: false }, axisTick: { show: false }
      },
      series: [{
        type: 'custom',
        renderItem: (params: any, api: any) => {
          const categoryIndex = api.value(0);
          const start = api.coord([api.value(1), categoryIndex]);
          const end = api.coord([api.value(2), categoryIndex]);
          const height = api.size([0, 1])[1] * 0.6;
          
          return {
            type: 'rect',
            shape: {
              x: start[0],
              y: start[1] - height / 2,
              width: Math.max(end[0] - start[0], 2),
              height: height
            },
            style: api.style()
          };
        },
        encode: { x: [1, 2], y: 0 },
        data: allItems
      }]
    };
  };

  return (
    <div className="space-y-8 font-['Inter']">
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <MetricCard title="Segments" value={metrics.segmentCount} sub={`${metrics.totalDuration.toFixed(1)}s video`} Icon={Film} />
        <MetricCard title="QR Detected" value={metrics.qrSegments.length} sub={`${metrics.qrSegments.length} events`} Icon={QrCode} />
        <MetricCard title="Banking Segs" value={metrics.bankingSegs.length} sub={`${(metrics.bankingSegs.length/metrics.segmentCount*100).toFixed(0)}% coverage`} Icon={Building} />
        <MetricCard title="Crypto Segs" value={metrics.cryptoSegs.length} sub={`${(metrics.cryptoSegs.length/metrics.segmentCount*100).toFixed(0)}% coverage`} Icon={Bitcoin} />
        <MetricCard title="Betting Coverage" value={`${metrics.bettingPct}%`} sub={`${metrics.bettingNonZero.length} segments`} Icon={Target} />
        <MetricCard title="Failed Tx" value={metrics.failedTxTimes.length} sub="unconfirmed attempts" highlight={metrics.failedTxTimes.length > 0} Icon={XOctagon} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <div className="md:col-span-6">
          <div className="section-header flex items-center gap-2"><Target className="w-4 h-4 text-slate-400" /> Executive Summary</div>
          <div className="grid grid-cols-2 gap-3">
            <ExecCard label="Betting Coverage" value={`${metrics.bettingPct}%`} />
            <ExecCard label="Max Betting Score" value={`${metrics.maxBetScore.toFixed(1)} / 100`} />
            <ExecCard label="Avg Betting Score" value={`${metrics.avgBetScore.toFixed(1)} / 100`} />
            <ExecCard label="Banking Segments" value={`${metrics.bankingSegs.length} / ${metrics.segmentCount}`} />
            <ExecCard label="Crypto Segments" value={`${metrics.cryptoSegs.length} / ${metrics.segmentCount}`} />
            <ExecCard label="QR / Payment Events" value={`${metrics.qrSegments.length} events`} />
            <ExecCard label="High Tx Likelihood" value={`${metrics.txLikelySegs.length} segments`} />
            <ExecCard label="Failed Transactions" value={`${metrics.failedTxTimes.length} attempts`} />
            <ExecCard label="Tx Executed" value={`${metrics.txExecSegs.length} confirmed`} />
            <ExecCard label="Video Duration" value={`${metrics.totalDuration.toFixed(1)}s`} />
          </div>
        </div>
        
        <div className="md:col-span-6">
          <div className="section-header flex items-center gap-2"><ShieldAlert className="w-4 h-4 text-slate-400" /> Signal Coverage</div>
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-5">
            <SignalBar label="Banking Context" count={metrics.bankingSegs.length} total={metrics.segmentCount} color="bg-[#0891B2]" />
            <SignalBar label="Crypto Context" count={metrics.cryptoSegs.length} total={metrics.segmentCount} color="bg-[#7C3AED]" />
            <SignalBar label="Transaction Likely" count={metrics.txLikelySegs.length} total={metrics.segmentCount} color="bg-[#DC2626]" />
            <SignalBar label="QR Code Detected" count={metrics.qrSegments.length} total={metrics.segmentCount} color="bg-[#D97706]" />
            <SignalBar label="Betting Coverage" count={metrics.bettingNonZero.length} total={metrics.betScores.length || 1} color="bg-[#F59E0B]" />
            <SignalBar label="Failed Tx" count={metrics.failedTxTimes.length} total={Math.max(metrics.failedTxRecords?.length || 1, 1)} color="bg-[#991B1B]" />
          </div>
        </div>
      </div>

      <div>
        <div className="section-header flex items-center gap-2"><Activity className="w-4 h-4 text-slate-400" /> Signal Strength Over Time</div>
        <div className="text-[0.79rem] text-[#64748B] mb-3">
          Continuous tracking of banking, crypto, and transaction intent across the video duration.
        </div>
        <div className="border border-slate-200 rounded-lg bg-white p-4 h-[300px] shadow-sm">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={metrics.verdicts.map((v: any) => ({ time: parseFloat(v.start_time.toFixed(1)), banking: v.banking_context || 0, crypto: v.crypto_context || 0, transaction: v.transaction_likely || 0 }))} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorBanking" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0891B2" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#0891B2" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorCrypto" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7C3AED" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#7C3AED" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorTx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#DC2626" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#DC2626" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={(val) => `${val}s`} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                labelFormatter={(val) => `Time: ${val}s`}
              />
              <Area type="monotone" dataKey="banking" name="Banking" stroke="#0891B2" strokeWidth={2} fillOpacity={1} fill="url(#colorBanking)" />
              <Area type="monotone" dataKey="crypto" name="Crypto" stroke="#7C3AED" strokeWidth={2} fillOpacity={1} fill="url(#colorCrypto)" />
              <Area type="monotone" dataKey="transaction" name="Tx Likely" stroke="#DC2626" strokeWidth={2} fillOpacity={1} fill="url(#colorTx)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <div className="section-header">Video Event Timeline — Full Duration Overview</div>
        <div className="text-[0.79rem] text-[#64748B] mb-3">
          Six signal lanes plotted across the full video. Hover each bar for exact timestamps and context scores.
        </div>
        <div className="border border-slate-200 rounded-lg bg-white p-2">
           <ReactECharts option={buildGanttData()} style={{ height: '310px', width: '100%' }} />
        </div>
        <div className="flex gap-4 flex-wrap text-[0.71rem] text-[#64748B] mt-2">
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#D97706]"></span>Betting UI</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#F59E0B]"></span>QR / Payment</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#DC2626]"></span>High Tx Likelihood</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#991B1B]"></span>Failed Transaction</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#0891B2]"></span>Banking Context</span>
          <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-[#7C3AED]"></span>Crypto Context</span>
        </div>
      </div>

      <div>
        <div className="section-header">Key Event Alerts</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <AlertBox 
            title="⬛ QR / Payment Codes Detected" 
            items={metrics.qrSegments.map((v:any) => `${v.start_time.toFixed(2)}s–${v.end_time.toFixed(2)}s`)} 
            empty="No QR codes detected" 
            type="qr"
          />
          <AlertBox 
            title="⚡ High-Confidence Transaction Segments" 
            items={metrics.txLikelySegs.slice(0, 6).map((v:any) => `${v.start_time.toFixed(2)}s–${v.end_time.toFixed(2)}s`)} 
            empty="No high-confidence transactions" 
            type="qr"
          />
          <AlertBox 
            title="✗ Failed / Unconfirmed Transaction Attempts" 
            items={metrics.failedTxTimes} 
            empty="No failed transactions detected" 
            type="tx"
          />
        </div>
      </div>
    </div>
  );
}

function AlertBox({ title, items, empty, type }: any) {
  if (items.length === 0) {
    return <div className="verdict-row text-slate-400">{empty}</div>;
  }
  
  const alertClass = type === 'tx' ? 'tx-alert' : 'qr-alert';
  const titleClass = type === 'tx' ? 'tx-alert-title' : 'qr-alert-title';
  
  return (
    <div className={alertClass}>
      <div className={titleClass}>{title}</div>
      <div className="space-y-1 mt-1">
        {items.map((item: string, i: number) => <div key={i}>• {item}</div>)}
      </div>
    </div>
  );
}

function MetricCard({ title, value, sub, highlight, Icon }: any) {
  return (
    <div className={`p-4 rounded-xl border shadow-sm transition-all hover:shadow-md ${highlight ? 'bg-[#1E293B] text-white border-[#1E293B]' : 'bg-white border-slate-200'}`}>
      <div className="flex items-center justify-between mb-2">
        <div className={`text-xs font-semibold uppercase tracking-wider ${highlight ? 'text-slate-400' : 'text-slate-500'}`}>{title}</div>
        {Icon && <Icon className={`w-4 h-4 ${highlight ? 'text-slate-400' : 'text-slate-400'}`} />}
      </div>
      <div className={`text-3xl font-bold font-['JetBrains_Mono'] ${highlight ? 'text-white' : 'text-slate-800'}`}>{value}</div>
      <div className={`text-[11px] font-['Inter'] mt-1 font-medium ${highlight ? 'text-slate-400' : 'text-slate-500'}`}>{sub}</div>
    </div>
  );
}

function ExecCard({ label, value }: { label: string, value: string }) {
  return (
    <div className="flex flex-col p-3 bg-slate-50 rounded-lg border border-slate-100">
      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">{label}</span>
      <span className="font-['JetBrains_Mono'] text-sm font-bold text-slate-800">{value}</span>
    </div>
  );
}

function SignalBar({ label, count, total, color }: any) {
  const pct = total ? (count / total) * 100 : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm items-center">
        <span className="font-semibold text-slate-700">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{count} / {total}</span>
          <span className="font-['JetBrains_Mono'] text-xs font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">{pct.toFixed(1)}%</span>
        </div>
      </div>
      <Progress value={pct} className={`h-2.5 bg-slate-100 [&>div]:${color}`} />
    </div>
  );
}
